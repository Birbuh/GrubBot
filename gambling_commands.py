import json
import random
import discord
import operations
from typing import Any

from discord import ui
from enum import StrEnum


RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["♠", "♥", "♦", "♣"]


def draw_card() -> tuple[str, str]:
    return (random.choice(RANKS), random.choice(SUITS))


def card_str(card: tuple[str, str]) -> str:
    return f"{card[0]}{card[1]}"


def hand_value(hand: list[tuple[str, str]]) -> int:
    total = 0
    aces = 0
    for rank, _ in hand:
        if rank == "A":
            aces += 1
            total += 11
        elif rank in ("J", "Q", "K"):
            total += 10
        else:
            total += int(rank)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def hand_str(hand: list[tuple[str, str]], hidden: bool = False) -> str:
    if hidden:
        return f"{card_str(hand[0])} ??"
    return " ".join(card_str(c) for c in hand)


def build_embed(
    player_hand: list[tuple[str, str]],
    dealer_hand: list[tuple[str, str]],
    bet: int,
    doubled: bool,
    state: str,
    double_available: bool = False,
) -> discord.Embed:
    colors = {
        "playing": discord.Color.blue(),
        "win": discord.Color.green(),
        "lose": discord.Color.red(),
        "push": discord.Color.gold(),
        "blackjack": discord.Color.gold(),
    }
    embed = discord.Embed(title="Blackjack", color=colors[state])
    player_total = hand_value(player_hand)
    if state == "playing":
        dealer_display = f"{hand_str(dealer_hand, hidden=True)} — ??"
        if double_available:
            embed.description = "Your move — Hit, Stand, or Double?"
        else:
            embed.description = "Your move — Hit or Stand?"
    else:
        dealer_display = f"{hand_str(dealer_hand)} — {hand_value(dealer_hand)}"
        wager = bet * (2 if doubled else 1)
        if state == "win":
            embed.description = f"You won {wager}$!"
        elif state == "lose":
            embed.description = f"You lost {wager}$."
        elif state == "push":
            embed.description = "Push — your bet is returned."
        elif state == "blackjack":
            embed.description = f"Blackjack! You won {int(bet * 1.5)}$!"
    embed.add_field(name="Your hand", value=f"{hand_str(player_hand)} — {player_total}", inline=False)
    embed.add_field(name="Dealer", value=dealer_display, inline=False)
    footer = f"Bet: {bet}$"
    if doubled:
        footer += " (doubled)"
    embed.set_footer(text=footer)
    return embed


class BlackjackView(ui.View):
    def __init__(self, user: str, bet: int, player_hand: list[tuple[str, str]], dealer_hand: list[tuple[str, str]], can_double: bool):
        super().__init__(timeout=60)
        self.user = user
        self.bet = bet
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.doubled = False
        self.settled = False
        self.msg: Any = None
        if not can_double:
            self.remove_item(self.double)

    @ui.button(label="Hit", style=discord.ButtonStyle.primary, custom_id="hit")
    async def hit(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if interaction.user.name != self.user:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        for child in self.children:
            if isinstance(child, ui.Button) and child.custom_id == "double":
                self.remove_item(child)
                break
        self.player_hand.append(draw_card())
        if hand_value(self.player_hand) > 21:
            await self.finish(interaction)
        else:
            embed = build_embed(self.player_hand, self.dealer_hand, self.bet, self.doubled, "playing", double_available=False)
            await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(label="Stand", style=discord.ButtonStyle.secondary, custom_id="stand")
    async def stand(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if interaction.user.name != self.user:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        await self.finish(interaction)

    @ui.button(label="Double", style=discord.ButtonStyle.success, custom_id="double")
    async def double(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if interaction.user.name != self.user:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        with open("money_lb.json", "r") as money_lb:
            try:
                money: dict[str, int] = json.load(money_lb)
            except json.JSONDecodeError:
                money = {}
        if money.get(self.user, 0) < self.bet:
            await interaction.response.send_message("Not enough money to double!", ephemeral=True)
            return
        await operations.add_or_del_money(self.user, -self.bet)
        self.doubled = True
        self.player_hand.append(draw_card())
        await self.finish(interaction)

    def dealer_play(self) -> int:
        while hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(draw_card())
        return hand_value(self.dealer_hand)

    async def finish(self, interaction: Any) -> None:
        self.settled = True
        for child in self.children:
            if isinstance(child, ui.Button):
                child.disabled = True
        wager = self.bet * (2 if self.doubled else 1)
        player_total = hand_value(self.player_hand)
        if player_total > 21:
            outcome = "lose"
        else:
            dealer_total = self.dealer_play()
            if dealer_total > 21 or player_total > dealer_total:
                outcome = "win"
            elif player_total < dealer_total:
                outcome = "lose"
            else:
                outcome = "push"
        if outcome == "win":
            await operations.add_or_del_money(self.user, 2 * wager)
        elif outcome == "push":
            await operations.add_or_del_money(self.user, wager)
        embed = build_embed(self.player_hand, self.dealer_hand, self.bet, self.doubled, outcome)
        if interaction is not None:
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await self.msg.edit(embed=embed, view=self)
        self.stop()

    async def on_timeout(self) -> None:
        if self.settled:
            return
        await self.finish(None)


async def blackjack(message: Any, bet: Any) -> None:
    """Blackjack gambling command

    :param message: The original message from prefix command or interaction from slash command.
    :param bet: The bet (an integer, or 'all'/'half').
    """
    try:
        user = message.author.name
    except AttributeError:
        user = message.user.name
    with open("money_lb.json", "r") as money_lb:
        try:
            money: dict[str, int] = json.load(money_lb)
        except json.JSONDecodeError:
            money = {}
    balance = money.get(user, 0)
    if balance <= 0:
        try:
            await message.reply("No money?")
        except AttributeError:
            await message.response.send_message("No money?", ephemeral=True)
        return
    if bet == "all":
        bet = balance
    elif bet == "half":
        bet = balance // 2
    else:
        bet = int(bet)
    if bet > balance or bet <= 0:
        try:
            await message.reply("No money?")
        except AttributeError:
            await message.response.send_message("No money?", ephemeral=True)
        return
    await operations.add_or_del_money(user, -bet)

    player_hand = [draw_card(), draw_card()]
    dealer_hand = [draw_card(), draw_card()]
    player_total = hand_value(player_hand)
    dealer_total = hand_value(dealer_hand)

    if player_total == 21 or dealer_total == 21:
        if player_total == 21 and dealer_total == 21:
            await operations.add_or_del_money(user, bet)
            embed = build_embed(player_hand, dealer_hand, bet, False, "push")
        elif player_total == 21:
            await operations.add_or_del_money(user, int(bet * 2.5))
            embed = build_embed(player_hand, dealer_hand, bet, False, "blackjack")
        else:
            embed = build_embed(player_hand, dealer_hand, bet, False, "lose")
        try:
            await message.reply(embed=embed)
        except AttributeError:
            await message.response.send_message(embed=embed)
        return

    can_double = balance >= bet * 2
    view = BlackjackView(user, bet, player_hand, dealer_hand, can_double)
    embed = build_embed(player_hand, dealer_hand, bet, False, "playing", double_available=can_double)
    try:
        sent = await message.reply(embed=embed, view=view)
    except AttributeError:
        await message.response.send_message(embed=embed, view=view)
        sent = await message.original_response()
    view.msg = sent


class RouletteEnum(StrEnum):
    EVEN = "even"
    ODD = "odd"
    BLACK = "black"
    RED = "red"


async def roulette(message: Any, bet: Any, space: Any) -> None:
    """Roulette gambling command

    :param message: The original message from prefix command or interaction from slash command.
    :param bet: The bet.
    :param space: The space you want to bet on.
    """
    if space not in RouletteEnum._value2member_map_ and int(space) not in [x for x in range(0, 37)]:
        try:
            await message.reply("Please mention an actual bet space next time!")
        except AttributeError:
            await message.response.send_message("Please mention an actual bet space next time!", ephemeral=True)
        return
    try:
        user = message.author.name
    except AttributeError:
        user = message.user.name
    num = random.randint(0, 36)
    with open("money_lb.json", "r") as money_lb:
        try:
            money: dict[str, int] = json.load(money_lb)
        except json.JSONDecodeError:
            money = {}
    if money[user] <= 0:
        try:
            await message.reply("No money?")
        except AttributeError:
            await message.response.send_message("No money?", ephemeral=True)
        return
    if bet == "all":
        bet = money[user]
    elif bet == "half":
        bet = money[user] / 2
    else:
        bet = int(bet)
    if bet > money[user]:
        try:
            await message.reply("No money?")
        except AttributeError:
            await message.response.send_message("No money?", ephemeral=True)
        return
    await operations.add_or_del_money(user, -bet)

    if num % 2 == 0:
        num_parity = "Even"
    else:
        num_parity = "Odd"
    if 1 <= num <= 10 or 19 <= num <= 28:
        if num_parity == "Even":
            num_color = "Red"
        else:
            num_color = "Black"
    elif num == 0:
        num_color = "Green"
    else:
        if num_parity == "Odd":
            num_color = "Red"
        else:
            num_color = "Black"
    is_gained = True
    if space == num_color or space == num_color.lower():
        gained_money = bet * 2
    elif space == num_parity or space == num_parity.lower():
        gained_money = bet * 2
    elif space == str(num):
        gained_money = bet * 36
    else:
        gained_money = 0
        is_gained = False
    await operations.add_or_del_money(user, gained_money)
    if is_gained:
        try:
            if not message.author.bot:
                await message.reply(f"The number is {num} ({num_color}, {num_parity}), you won {gained_money}$!")

        except AttributeError:
            await message.response.send_message(f"The number is {num} ({num_color}, {num_parity}), you won {gained_money}$!")
    else:
        try:
            if not message.author.bot:
                await message.reply(f"The number is {num} ({num_color}, {num_parity}), you lost {bet}$.")

        except AttributeError:
            await message.response.send_message(f"The number is {num} ({num_color}, {num_parity}), you lost {bet}$.")
