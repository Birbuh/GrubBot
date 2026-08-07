import asyncio
from typing import Any

import discord

all_rules: dict[str, str] = {

}

types_of_help: dict[str, str] = {
    "rules": "Type ?rules in chat to see them!",  # any user
    "channel": "https://www.youtube.com/@RazerChess",  # any user
    "mute": " -> ?mute <user> <time (s, m, h)>",  # staff only
    "info": " -> ?info <user>",  # staff only
    "warn": " -> ?warn <user> <reason>",  # staff only
    "clear": " -> ?clear <user> (clears warns)",  # staff only
    "purge": " -> ?purge <number> (removes the number of messages above)",  # staff only
    "roles": " -> ?roles <user> (shows all roles of the user)",  # any user
    "warns": " -> ?warns (gives you your warns)",  # any user
    "balance": " -> ?balance [user] (shows a balance; aliases: ?bal, ?view-money)",
    "roulette": " -> ?roulette <space> <bet> (aliases: ?rlt, ?roulete)",
    "work": " -> ?work (earns coins; subject to the work delay)",
    "delay": " -> ?delay <on|off> (enables or disables the work delay)",
    "report": (
        " -> ?report <user> reason (you also have to ping a message where a user broke the rules) reporting without a normal reason will be punished"
    ),
    # any user
}

member_types_of_help: dict[str, str] = {
    "rules": "Type ?rules in chat to see them!",  # any user
    "channel": "https://www.youtube.com/@RazerChess",  # any user
    "roles": " -> ?roles <user> (shows all roles of the user)",  # any user
    "warns": " -> ?warns (gives you your warns)",  # any user
    "balance": " -> ?balance [user] (shows a balance; aliases: ?bal, ?view-money)",
    "roulette": " -> ?roulette <space> <bet> (aliases: ?rlt, ?roulete)",
    "work": " -> ?work (earns coins; subject to the work delay)",
    "delay": " -> ?delay <on|off> (enables or disables the work delay)",
    "report": (
        " -> ?report <user> reason (you also have to ping a message where a user broke the rules) reporting without a normal reason will be punished"
    ),
}


ADMIN_ID = 1529034592852508823
MOD_LOG_IDS = [1534468985272274975]


async def delay_func(func, timeout, **kwargs):
    """Delaying the function."""
    await asyncio.sleep(timeout)
    await func(**kwargs)


def check_for_perms(member: Any):
    """Return whether a member has the configured administrator role."""
    if any(role.id == ADMIN_ID for role in member.roles):
        return True


def check_if_muted(member: Any):
    """Return the member's muted role, if present."""
    return discord.utils.get(member.roles, name="muted")
