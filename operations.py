import json
from typing import Any


async def uid_to_name(bot: Any, uid: int) -> Any:
    return await bot.fetch_user(uid)


async def add_or_del_money(user: str, new_money: int | float) -> None:
    """Func to add money

    :param user: User to add money to
    :param new_money: Money to add (or to subtract if < 0)
    """
    new_money = int(new_money)
    with open("money_lb.json", "r") as money_lb:
        try:
            money: dict[str, int] = json.load(money_lb)
        except json.JSONDecodeError:
            money = {}
        money[user] = money.get(user, 0) + new_money
    with open("money_lb.json", "w") as money_lb:
        json.dump(money, money_lb)


async def bal(message: Any, user: Any, bot: Any) -> None:
    """Shows a balance of an user.

    :param message: The original message from prefix command or interaction from slash command
    :param user: Optional argument; user to show (if not given, the user which sent the command is the user).
    :param bot: Original discord bot, no need to worry about that.
    """
    failed = False
    if user:
        if user.find("@") != -1:  # checking if the format is ping
            mention_to_id = "<@>"
            # Transform ping to ID
            for char in mention_to_id:
                user = user.replace(char, "")
            user = int(user)
            user = await uid_to_name(bot, user)  # Transform ID to username
            self_bal = user.global_name
            have_or_has = "has"
    else:
        try:
            user = message.author.name
        except AttributeError:
            user = message.user.name
        self_bal = "You"
        have_or_has = "has"

    with open("money_lb.json", "r") as money_lb:
        try:
            money: dict[str, int] = json.load(money_lb)
        except json.JSONDecodeError:
            money = {}
    try:
        u_money = money[user.name]
    except AttributeError:
        u_money = money[user]
    except KeyError:
        failed = True
    try:
        if not failed:
            await message.reply(f"{user} {have_or_has} {u_money}$ at their balance")
        else:
            await message.reply(f"{self_bal} poor {self_bal} {have_or_has} no money")
    except AttributeError:
        if not failed:
            await message.response.send_message(f"{user} {have_or_has} {u_money}$ at their balance")
        else:
            await message.response.send_message(f"{self_bal} poor {self_bal} {have_or_has} no money")
