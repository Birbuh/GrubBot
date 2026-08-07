import json
from typing import Any

from discord.member import Member


async def uid_to_name(bot: Any, uid: int) -> Any:
    """Fetch and return the Discord user associated with an ID."""
    return await bot.fetch_user(uid)

async def transfer_money(msg, amount: int | str, where: str) -> None:
    """Func to transfer money
    
    :param msg: The original message from prefix command
    :param amount: Money to transfer.
    :param where: Where to transfer the money.
    """
    with open("money_lb.json", "r") as money_lb:
        try:
            money: dict[str, dict[str, int]] = json.load(money_lb)
        except json.JSONDecodeError:
            money = {}
        try: 
            if amount == "all":
                if where in ["c", "cash"]:
                    final_amount = money[msg.author.name]["bank"]
                if where in ["b", "bank"]:
                    final_amount = money[msg.author.name]["cash"]
            elif amount == "half":
                if where in ["c", "cash"]:
                    final_amount = money[msg.author.name]["bank"] // 2
                if where in ["b", "bank"]:
                    final_amount = money[msg.author.name]["cash"] // 2
            else:
                if where in ["c", "cash"]:
                    if int(amount) < money[msg.author.name]["bank"]:
                        final_amount = int(amount)
                    else: 
                        await msg.reply("You don't have that much...")
                if where in ["b", "bank"]:
                    if int(amount) < money[msg.author.name]["cash"]:
                        final_amount = int(amount)
                    else: 
                        await msg.reply("You don't have that much...")
        except Exception:
            await msg.reply("Something is wrong with the amount. Make sure it's either a non-negative integer, `all` or `half`.")
        if where in ["c", "cash"]:
            money[msg.author.name]["bank"] -= final_amount
            money[msg.author.name]["cash"] += final_amount
            await msg.reply(f"""Money transferred successfully! Your current balance: 
                \ncash: {money[msg.author.name]["cash"]} \nbank: {money[msg.author.name]["bank"]}""")
        elif where in ["bank", "b"]:
            money[msg.author.name]["bank"] += final_amount
            money[msg.author.name]["cash"] -= final_amount
            await msg.reply(f"""Money transferred successfully! Your current balance: 
                \ncash: {money[msg.author.name]["cash"]} \nbank: {money[msg.author.name]["bank"]}""")
            
    with open("money_lb.json", "w") as money_lb:
        json.dump(money, money_lb)
        
async def add_or_del_money(user: str, new_money: int | float) -> None:
    """Func to add money

    :param user: User to add money to
    :param new_money: Money to add (or to subtract if < 0)
    """
    new_money = int(new_money)
    with open("money_lb.json", "r") as money_lb:
        try:
            money: dict[str, dict[str, int]] = json.load(money_lb)
        except json.JSONDecodeError:
            money = {}
        try:
            money[user]["cash"] += new_money
        except KeyError:
            money[user] = {}
            money[user]["cash"] = new_money
            money[user]["bank"] = 0 
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
            money: dict[str, dict[str, int]] = json.load(money_lb)
        except json.JSONDecodeError:
            money = {}
    try:
        u_money_cash = money[user.name]["cash"]
        u_money_bank = money[user.name]["bank"]
    except AttributeError:
        u_money_cash = money[user]["cash"]
        u_money_bank = money[user]["bank"]
    except KeyError:
        failed = True
    try:
        if not failed:
            await message.reply(f"{user} {have_or_has} {u_money_cash}$ in cash and {u_money_bank}$ in their bank account.")
        else:
            await message.reply(f"{self_bal} poor {self_bal} {have_or_has} no money")
    except AttributeError:
        if not failed:
            await message.response.send_message(f"{user} {have_or_has} {u_money_cash}$ in cash and {u_money_bank}$ in their bank account.")
        else:
            await message.response.send_message(f"{self_bal} poor {self_bal} {have_or_has} no money")


async def give_money(msg, member: Member | int | None, amount: int | None):
    """With this command, the riches give money to the poor.
    
    :param msg: The original message from prefix command or interaction from slash command
    :param member: A member's mention or ID. Not. A. String. It will be None this way.
    :param amount: An amount of the money to give.
    """
    try:
        if not member:
            await msg.reply("Please mention a member to give your money to.\nUsage: ?give @member [amount]")
            return
        if not amount: 
            await msg.reply(f"Please specify an amount of your money to give {member}.\nUsage: ?give @member [amount]")
            return
        await add_or_del_money(msg.author.name, -amount)
        if isinstance(member, int):
            user = msg.guild.fetch_member(member)
            await add_or_del_money(user.name, amount)
        else:
            await add_or_del_money(member.name, amount)
        try:
            await msg.reply("Money transferred successfully!")
        except AttributeError:
            await msg.response.send_message("Money transferred successfully!", ephemeral=True)
    except Exception as e:    
        try:
            await msg.reply("An error occurred! Check the terminal output for more info.")
        except AttributeError:
            await msg.response.send_message("An error occurred! Check the terminal output for more info.")
        print(e)
