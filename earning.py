import random
import operations
import time
from typing import Any

# Delay control state
work_delay: bool = False
last_work_times: dict[str, float] = {}


# Smart reply wrapper to support both Message and Interaction
async def smart_reply(msg: Any, content: str) -> None:
    """Reply to either a prefix-command message or slash interaction."""
    try:
        await msg.reply(content)
    except AttributeError:
        await msg.response.send_message(content)


# Enables or disables the global work delay mode
async def delay(msg: Any, mode: str) -> None:
    """Enable or disable the global cooldown for the work command."""
    global work_delay

    if mode == "on":
        if not work_delay:
            work_delay = True
            await smart_reply(msg, "The work delay is on.")
        else:
            await smart_reply(msg, "The work delay is already on.")
    elif mode == "off":
        if work_delay:
            work_delay = False
            await smart_reply(msg, "The work delay is off.")
        else:
            await smart_reply(msg, "The work delay is already off.")
    else:
        await smart_reply(msg, "Please provide a valid argument: 'on' or 'off'.")


# Handles money transaction and response
async def work_transaction(message: Any, user: str) -> None:
    """Award a random work payment and report its fictional source."""
    earnt_coins = random.randint(200, 400)
    work_reasons: list[str] = [
        f"You worked at a store and earned {earnt_coins}$",
        f"You worked as a Rubik's cube assembler and earned {earnt_coins}$",
        f"You didn't work but got {earnt_coins}$ for some reason",
        f"You invented a source of infinite energy but got only {earnt_coins}$",
    ]
    await operations.add_or_del_money(user, earnt_coins)
    await smart_reply(message, random.choice(work_reasons))


# Main work command
async def work(message: Any) -> None:
    """Process a work command, applying the optional per-user cooldown."""
    global work_delay
    try:
        user = message.author.name
    except AttributeError:
        user = message.user.name

    if work_delay:
        now = time.time()
        last_time = last_work_times.get(user, 0)

        if now - last_time < 300:
            remaining = round(300 - (now - last_time))
            await smart_reply(message, f"You’re tired and can’t work yet! Wait {remaining} seconds.")
            return

        last_work_times[user] = now
        await work_transaction(message, user)
    else:
        await work_transaction(message, user)
