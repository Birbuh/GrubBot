"""Automoderation and member commands"""

import asyncio
import json
from typing import Any

import discord
from discord.ext import commands

from other_addons import (
    all_rules,
    check_for_perms,
    check_if_muted,
    delay_func,
    member_types_of_help,
    types_of_help,
)


# Function to check for non-standard fonts
async def contains_fancy_fonts(message: Any):
    """Handle messages with banned haracters"""
    # # Regex patterns for detecting emojis and markdown
    # EMOJI_PATTERN = re.compile(
    # )
    # MARKDOWN_PATTERN = re.compile(r"(\*\*.*?\*\*|__.*?__|~~.*?~~|\*.*?\*|_.*?_)")
    # if EMOJI_PATTERN.match(message.content) or MARKDOWN_PATTERN.match(message.content):
    #     # If the message only contains allowed characters, let it pass
    #     print(f"Message from {message.author}: {message.content} is valid.")
    # else:
    #     # If the message contains disallowed characters, delete it
    #     await message.delete()
    #     await message.channel.send(
    #         f"{message.author.mention}, your message contains invalid characters!"
    #     )
    #     await automute(
    #         message,
    #         20,
    #         "AUTOMOD: User broke the rules and his message contains invalid characters.",
    #     )


last_message_time = {}
user_spam_count = {}  # individual spam counters
user_warns_count = {}


# Function finding mentions.
def mentions_spam(text: str):
    words: list[str] = text.split()
    mentions = sum(word.count("@") for word in words)
    return mentions


async def spam(message: Any):
    """Function for detecting spam."""
    if message.author.bot:
        return False

    user_id = message.author.id
    current_time = message.created_at.timestamp()
    spam_time: float = 0.5
    reset_time: float = 5.0

    # Get last message time
    last_time = last_message_time.get(user_id, None)

    if last_time:
        time_diff = current_time - last_time

        if time_diff < spam_time:
            user_spam_count[user_id] = user_spam_count.get(user_id, 0) + 1
        elif time_diff > reset_time:
            user_spam_count[user_id] = 0  # Reset if long time passed

        if user_spam_count.get(user_id, 0) >= 4:
            try:
                await message.delete()
                await message.channel.send(f"{message.author.mention}, please don't spam!")
                return True
            except discord.errors.NotFound as e:
                print(e)

    else:
        user_spam_count[user_id] = 0

    # Update message time
    last_message_time[user_id] = current_time
    return False


def is_message_too_long(text, max_chars=200):
    """Function to check if a message exceeds the length limit"""
    if "http" not in text or ".com" not in text:
        return len(text) > max_chars


# Function to check for long words without spaces
def contains_long_unspaced_text(text: str, max_length=50):
    if "http" not in text or ".com" not in text:
        words = text.split()  # Split the message into words
        return any(len(word) > max_length for word in words)


async def automute(msg: Any, time, reason, bot: Any = None, mod_logs: Any = None):
    muted = check_if_muted(msg.author)
    if muted:
        await msg.channel.send(content="Nice try, but you are muted already. lmfao.")
        return
    else:
        mute_role = bot.get_guild(1528934642630266900).get_role(1531352680142864587)  # TODO: change it to an actual mute role. #noqa:E501
        member: Any = msg.author
        await member.add_roles(mute_role)
        muted = True
        embed = discord.Embed(
            title="Automute!!!",
            description=(f"**{member}** got electrocuted by the AutoMod services! He is now muted for {time / 60} minutes for {reason}"),
            color=0xFF00F6,
        )
        automute_done_msg = await msg.channel.send(embed=embed)
        await mod_logs["actions"].send(embed=embed)
        await delay_func(automute_done_msg.delete, 5)
        await asyncio.sleep(time)
        await mod_logs["actions"].send(content=f"{member.mention} unmuted.")
        await member.remove_roles(mute_role)
        muted = False


async def warns_info(msg: Any):
    member = msg.author
    name = member.name

    try:
        with open("warns.json", "r") as warn_file:
            warns = json.load(warn_file)
            if member.name in warns:
                warns = f"{warns[member.name]['count']}, reasons: {warns[member.name]['reasons']}"
            else:
                warns = "No warnings for this user."

    except commands.errors.CommandInvokeError, json.decoder.JSONDecodeError:
        warns = "User got no warns!"

    try:
        weekly_display = user_warns_count[name]
    except KeyError:
        weekly_display = "0"

    await msg.reply(f"**Warns:** Weekly warns: {weekly_display}, total warns: {warns}")


async def roles(msg: Any, member: Any = None):
    user_roles = member.roles
    await msg.reply(f"{member.name}'s roles: \n\n{user_roles}")


async def rules(msg: Any, rule: str | None = None) -> None:
    if rule is None:
        await msg.reply(str(all_rules))
    else:
        await msg.reply(str(all_rules[rule]))


async def helpme(msg: Any, type_of_help: str | None = None):
    if type_of_help is None:
        if not check_for_perms(msg.author):
            await msg.reply("Please mention what I need to help you with: rules, channel, roles, warns, balance, roulette, work, or delay.")
        elif check_for_perms(msg.author):
            await msg.reply(
                "Please mention what I need to help you with: rules, channel, roles, warns, "
                "balance, roulette, work, or delay. Staff only: mute, info, warn, clear, purge."
            )
    else:
        if not check_for_perms(msg.author):
            try:
                await msg.reply(member_types_of_help[type_of_help])

            except KeyError:
                await msg.reply("Please mention the correct type of help!")
        elif check_for_perms(msg.author):
            try:
                await msg.reply(types_of_help[type_of_help])

            except KeyError:
                await msg.reply("Please mention the correct type of help!")
