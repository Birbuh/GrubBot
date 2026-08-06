from typing import Any

import discord
from other_addons import MOD_LOG_IDS
from bot_commands import (
    check_for_perms,
    contains_fancy_fonts,
    contains_long_unspaced_text,
    automute,
    mentions_spam,
    spam,
)


async def on_message_delete(
    msg: Any,
    bot: Any = None,
    mod_logs: dict[str, Any] = {},
):
    embed = discord.Embed(
        title="Deleted message!",
        description=(f"Deleted {msg.author.mention} message: \n {msg.content} \n \n Channel: {msg.channel.mention}"),
        color=0x000CFF,
    )
    if msg.attachments:
        for attachment in msg.attachments:
            # Forward the file to the logging channel
            await mod_logs["actions"].send(
                content=f"File received from {msg.author.mention} in {msg.channel.mention}:",
                file=await attachment.to_file(),
            )

    if msg.embeds:
        if msg.attachments:
            for embed in msg.embeds:
                for file in msg.attachments:
                    await mod_logs["actions"].send(
                        content=(f"Deleted {msg.author.mention}'s message: \n {msg.content} \n \n Channel: {msg.channel.mention}"),
                        embed=msg.embeds,
                        file=await file.to_file(),
                    )

        for embed in msg.embeds:
            await mod_logs["actions"].send(
                content=(f"Deleted {msg.author.mention}'s message: \n {msg.content} \n \n Channel: {msg.channel.mention}"),
                embed=embed,
            )

    else:
        await mod_logs["actions"].send(embed=embed)

    await bot.process_commands(msg)


async def on_message_edit(
    before: Any,
    after: Any,
    mod_logs: dict[str, Any] = {},
):
    if not before.author.bot:
        if before.channel.id not in MOD_LOG_IDS:
            edited_msg_log = discord.Embed(
                description=(f"{before.author.name} edited their message! \nBefore: {before.content}\n\nAfter: {after.content}")
            )
            await mod_logs["actions"].send(embed=edited_msg_log)
            if before.embeds:
                for embed in before.embeds:
                    await mod_logs["actions"].send(embed=embed)


async def on_message(message: Any, bot: Any, mentions_spam_cache: Any):
    # Skip all moderation checks if the user has the admin role
    if not check_for_perms(message.author):
        _id = message.author.id

        # Check for fancy fonts
        await contains_fancy_fonts(message)

        # Check for long unspaced text
        if contains_long_unspaced_text(message.content):
            await automute(message, 5 * 60, reason="AUTOMOD: Automatically muted for possibly spam.")
            await message.delete()
            print(f"Deleted message from {message.author}: {message.content}")

        # Check for mention spam
        if mentions_spam(message.content):
            mentions = mentions_spam_cache.get(_id, 0)
            if mentions < 10:
                mentions += 1
                mentions_spam_cache[_id] = mentions
            else:
                await automute(message, 60, reason="AUTOMOD: Automatically muted for spamming mentions.")
                await message.delete()

        # Check for message spam (rapid messages)
        is_spam = await spam(message)
        if is_spam:
            await automute(message, 60, "AUTOMOD: Automatically muted for spam.")
