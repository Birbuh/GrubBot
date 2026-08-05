import json
import random
import operations
from typing import Any

from enum import StrEnum


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
