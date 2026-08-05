import asyncio
from typing import Any

import discord

all_rules: dict[str, str] = {
    "1": "No harassing, racism, any type of being toxic or bullying is forbidden.",
    "2": "No selfpromo, unless Razer will agree.",
    "3": "No NSFW",
    "4": "Don't spam",
    "5": "Make sure to follow Discord ToS",
    "6": 'English only (and no other "fonts" than normal discord one) please',
    "7": "Do not swear too much",
    "8": "Don't write caps when unnecesary; it will be punishable.",
    "9": (
        "DO NOT open the tickets unless you have a valid reason - if you just want to "
        "contact someone, that is NOT a valid reason."
    ),
    "10": "Reporting without a reason will be punished",
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
    "report": (
        " -> ?report <user> reason (you also have to ping a message where a user broke the "
        "rules) reporting without a normal reason will be punished"
    ),
    # any user
}

member_types_of_help: dict[str, str] = {
    "rules": "Type ?rules in chat to see them!",  # any user
    "channel": "https://www.youtube.com/@RazerChess",  # any user
    "roles": " -> ?roles <user> (shows all roles of the user)",  # any user
    "warns": " -> ?warns (gives you your warns)",  # any user
    "report": (
        " -> ?report <user> reason (you also have to ping a message where a user broke the "
        "rules) reporting without a normal reason will be punished"
    ),
}


ADMIN_ID =  1529034592852508823
MOD_LOG_IDS = [1534468985272274975]


async def delay_func(func, timeout, **kwargs):
    """Delaying the function."""
    await asyncio.sleep(timeout)
    await func(**kwargs)


def check_for_perms(member: Any):
    if any(role.id == ADMIN_ID for role in member.roles):
        return True


def check_if_muted(member: Any):
    return discord.utils.get(member.roles, name="muted")
