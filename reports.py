import asyncio
import time
from typing import Any

import discord


# Dictionary to store last report times
user_last_report_time = {}

# You need to store message ID and who can react (optional, for security)
report_message_actions = {}


def check_if_muted(member: Any):
    return discord.utils.get(member.roles, name="muted")


async def report(
    msg: Any,
    member: Any | None = None,
    reason: str | None = None,
    mod_logs: dict[str, Any] = {},
):
    """Report someone by replying to their message with a reason. Can be used once every 2 hours."""
    author = msg.author

    # Check if user is on cooldown
    now = time.time()
    last_time = user_last_report_time.get(author.id, 0)
    if now - last_time < 7200:  # 2 hours = 7200 seconds
        remaining = int((7200 - (now - last_time)) // 60)
        await msg.reply(f"You can use this command again in {remaining} minutes.")
        return

    # Check if it's a reply
    if msg.message.reference is None:
        await msg.reply("Please reply to a message you want to report.")
        return

    # Get the replied message
    try:
        referenced_message = await msg.channel.fetch_message(msg.message.reference.message_id)
    except Exception:
        await msg.reply("Failed to fetch the referenced message.")
        return

    if member is None:
        await msg.reply("Please mention the user you're reporting. Usage: `!report @user <reason>`")
        return

    if reason is None:
        await msg.reply("Please tell us why do you report this user")
        return

    # Store report time
    user_last_report_time[author.id] = now

    # Find the #reports channel
    reports_channel = discord.utils.get(msg.guild.text_channels, name="reports")
    if not reports_channel:
        await msg.reply("Couldn't find the #reports channel.")
        return

    # Create and send the report embed
    embed = discord.Embed(title="New Report", color=0xFF0000, timestamp=msg.message.created_at)
    embed.add_field(name="Reported User", value=f"{member.mention} ({member.name})", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Reported By", value=f"{author.mention} ({author.name})", inline=False)
    embed.add_field(name="Reported Message", value=referenced_message.content, inline=False)
    embed.set_footer(text=f"User ID: {member.id}")

    await msg.reply("Report sent.")

    msg = await reports_channel.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    # Store action so we can handle it later
    report_message_actions[msg.id] = {"reported_user": member, "reporter": author, "reason": reason}

    # Save report context by message ID
    report_message_actions[msg.id] = {
        "reported_user_id": member.id,
        "reporter_id": author.id,
        "reason": reason,
    }


async def roles(msg: Any, member: Any = None):
    if member is None:
        member = msg.author
    roles = [role.name for role in member.roles if role.name != "@everyone"]
    roles_list = ", ".join(roles) if roles else "No roles"
    await msg.reply(f"**Roles:** {roles_list}\n")


async def rules(msg: Any, rule: str | None = None, rules_dict: dict[str, str] = {"": ""}) -> None:
    """Usage: !rules <rule> None by default"""
    try:
        if rule is not None:
            await msg.reply(rules_dict[rule])  # sends the rule by its number
        else:
            await msg.reply(rules_dict)
    except Exception:  # Checks for invalidly written command
        await msg.reply("You didn't write the command correctly")


async def on_raw_reaction_add(payload, bot: Any, mod_logs: dict[str, Any] = {}):
    if payload.message_id not in report_message_actions:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    data = report_message_actions[payload.message_id]

    reported_user = guild.get_member(data["reported_user_id"])
    reporter = guild.get_member(data["reporter_id"])
    reason = data["reason"]

    channel = guild.get_channel(payload.channel_id)
    if channel is None:
        return

    message = await channel.fetch_message(payload.message_id)
    if message is None:
        return

    if payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)
    mute_role = bot.get_guild(1331651870107762732).get_role(1534463181542522890)

    # Take action
    if emoji == "✅":
        await reported_user.add_roles(mute_role, reason=reason)
        await reported_user.send(
            f"You have been muted at razerchess's server for 3 hours for {reason}"
        )
        await reporter.send("Your report have been approved")

        # muting part
        embed = discord.Embed(
            title="User Muted!",
            description=f"**{reported_user}** was muted for {3} hours for **{reason}** !",
            color=0xFF00F6,
        )
        await mod_logs["actions"].send(embed=embed)

        # Schedule unmute
        async def unmute_later():
            await asyncio.sleep(10800)
            if check_if_muted(reported_user):
                await reported_user.remove_roles(mute_role)
                embed = discord.Embed(
                    title="User Unmuted!",
                    description=f"The time for **{reported_user}** being muted has finished!",
                    color=0xFF00F6,
                )

                await mod_logs["actions"].send(embed=embed)

        # Start the unmute task
        asyncio.create_task(unmute_later())

        await mod_logs["actions"].send(embed=embed)

    elif emoji == "❌":
        await reporter.add_roles(mute_role, reason="Falsely reporting")
        await reporter.send(
            "You have been muted at razerchess's server for 6 hours for false reporting"
        )

        # muting part
        embed = discord.Embed(
            title="User Muted!",
            description=f"**{reporter}** was muted for {3} hours for **{'Falsely warning'}** !",
            color=0xFF00F6,
        )
        await mod_logs["actions"].send(embed=embed)

        # Schedule unmute
        async def unmute_later():
            await asyncio.sleep(10800 * 2)
            if check_if_muted(reporter):
                await reporter.remove_roles(mute_role)
                embed = discord.Embed(
                    title="User Unmuted!",
                    description=f"The time for **{reporter}** being muted has finished!",
                    color=0xFF00F6,
                )

                await mod_logs["actions"].send(embed=embed)

        # Start the unmute task
        asyncio.create_task(unmute_later())

        await mod_logs["actions"].send(embed=embed)
