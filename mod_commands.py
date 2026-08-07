import asyncio
import json
from typing import Any

import discord
from discord.ext import commands
from discord.member import Member

from other_addons import ADMIN_ID, check_for_perms, check_if_muted, delay_func

user_warns_count = {}
TIME_CONVERT = {"s": 1, "m": 60, "h": 3600}


# clears warns
async def clear_user_warns(msg: Any, username: Any):
    """Clears all warnings for a given username."""
    user_name = username.name
    user_warns_count[user_name] = 0


async def lock(msg: Any):
    """Prevent users without the specified role from sending messages in this channel."""
    channel = msg.channel  # Get the channel where the command was called
    role = discord.utils.get(msg.guild.roles, id=ADMIN_ID)  # Get the role by ID

    if not role:
        await msg.reply("Role not found!")
        return

    # Deny send messages permission for everyone except the role
    await channel.set_permissions(role, send_messages=True)  # Allow the role to send messages
    await channel.set_permissions(msg.guild.default_role, send_messages=False)  # Deny everyone else from sending messages

    await msg.reply("Channel locked for everyone except the authorized role!")


async def unlock(msg: Any):
    """Allow everyone except the specified role to send messages in this channel."""
    channel = msg.channel  # Get the channel where the command was called
    role = discord.utils.get(msg.guild.roles, id=ADMIN_ID)  # Get the role by ID
    if not role:
        await msg.reply("Role not found!")
        return

    # Restore send messages permission for everyone except the role
    await channel.set_permissions(role, send_messages=True)  # Allow the role to send messages
    await channel.set_permissions(msg.guild.default_role, send_messages=True)  # Allow everyone else to send messages

    await msg.reply("Channel unlocked for everyone!")


async def clear_warns(msg: Any, member: Any = None):
    """Usage: !clear @member
    Clears all warnings for a user."""
    try:
        if not check_for_perms(msg.author):
            await msg.reply("You don't have permission to use this command.")
            return
        elif check_for_perms(msg.author):
            await clear_user_warns(msg, member)
            await msg.reply("Weekly warns have been cleared")
    except Exception:
        await msg.reply("Please mention correct username!")


async def send_msg(msg: Any, channel_name: str | None = None, *, content: str | None = None) -> None:
    """Send staff-provided content to a named text channel."""
    # Check if all parameters were provided
    if channel_name is None or content is None:
        await msg.reply("Usage: !send-msg <channel_name> <content>")
        return

    # Get the channel by name
    channel = discord.utils.get(msg.guild.text_channels, name=channel_name)

    if channel is None:
        await msg.reply("Channel not found.")
        return

    if check_for_perms(msg.author):
        # Send the message content to the specified channel
        await channel.send(content)
        await msg.reply(f"Message sent to {channel.mention}")
    else:
        await msg.reply("You do not have permission to use this command.")


async def info(msg: Any, member: Any):
    """Reply with staff-visible member details, roles, and warnings."""
    if not check_for_perms(msg.author):
        await msg.reply("You don't have permission to use this command.")
        return
    if member is None:
        member = msg.author

    name = member.name

    roles = [role.name for role in member.roles if role.name != "@everyone"]
    roles_list = ", ".join(roles) if roles else "No roles"
    try:
        with open("warns.json", "r") as warn_file:
            warns = json.load(warn_file)
            if member.name in warns:
                warns = f"{warns[member.name]['count']}, reasons: {warns[member.name]['reasons']}"
            else:
                warns = "No warnings for this user."

    except commands.errors.CommandInvokeError, json.decoder.JSONDecodeError:
        warns = "User got no warns!"
    except commands.errors.MissingRequiredArgument:
        await msg.reply("Make sure to mention the user!")
        return

    try:
        weekly_display = user_warns_count[name]
    except KeyError:
        weekly_display = "0"

    info = (
        f"**User Info:**\n"
        f"**Name:** {member} (`{member.name}`)\n"
        f"**ID:** {member.id}\n"
        f"**Roles:** {roles_list}\n"
        f"**Warns:** Weekly warns: {weekly_display}, total warns: {warns}"
    )

    await msg.reply(info)


async def purge(msg: Any, amount: int | None = None, mod_logs: dict[str, Any] = {}):
    """Usage: !purge <amount of messages to purge>
    This command deletes <amount> of messages in the channel."""
    if amount is None:
        await msg.reply("Please specify the number of messages to purge. Usage: !purge <amount>")
        return

    if check_for_perms(msg.author):
        await msg.channel.purge(limit=amount + 1)
        embed = discord.Embed(
            title="Purged messages!",
            description=f"{msg.author.mention} purged {amount} messages!",
            color=0xFF00F6,
        )
        success_msg = await msg.channel.send(embed=embed)
        await mod_logs["actions"].send(embed=embed)
        await delay_func(success_msg.delete, 5)
    else:
        await msg.channel.send(content="Nuh uh, no perms >:]")


async def unmute(
    msg: Any,
    member: Any | None = None,
    reason: str | None = None,
    bot: Any = None,
    mod_logs: dict[str, Any] = {},
):
    """Remove the mute role from a member when requested by staff."""
    if member is None:
        await msg.reply("Please mention a member to unmute. Usage: !unmute @member [reason]")
        return

    mute_role = bot.get_guild(1528934642630266900).get_role(1534463181542522890)
    if check_if_muted(member):
        if check_for_perms(msg.author):
            await member.remove_roles(mute_role)
            embed = discord.Embed(
                title="User Unmuted!",
                description="**{0}** was unmuted for **{1}** by **{2}**!".format(member, reason or "No reason provided", msg.author),
                color=0xFF00F6,
            )
            success_msg = await msg.reply(embed=embed)
            await mod_logs["actions"].send(embed=embed)
            await delay_func(success_msg.delete, 5)
        else:
            await msg.reply("No perms for you!!! <:exploding_ass:1342513399191310428>")
    else:
        await msg.reply("This user isn't muted, you goober!")


async def kick(msg: Any, member: Any, reason: str | None = None):
    """Remove a member from the server and notify them of the reason."""
    await member.kick(reason=reason)
    await msg.reply(f"User kicked for {reason}")
    await member.dm_channel.send(f"You've been kicked from Razerchess server for {reason}!")


async def warn(
    msg: Any,
    member: Any | None = None,
    reason=None,
    bot: Any = None,
    mod_logs: dict[str, Any] = {},
):
    """Usage: !warn <member> <reason (none by default)>
    Warns a user, storing it in warns.json"""
    try:
        # Check if the command caller has permissions
        if not check_for_perms(msg.author):
            await msg.reply("You don't have permission to use this command.")
            return

        # Check if member parameter was provided
        if member is None:
            await msg.reply("Please mention a member to warn. Usage: !warn @member [reason]")
            return

        # Load existing warns or create empty dict if file doesn't exist
        try:
            with open("warns.json", "r") as warns_file:
                warns = json.load(warns_file)
        except FileNotFoundError, json.decoder.JSONDecodeError:
            warns = {}

        # Get user's name and update warns
        name = member.name
        if name not in warns:
            warns[name] = {"count": 0, "reasons": []}

        warns[name]["count"] += 1
        warns[name]["reasons"].append(reason or "No reason given")
        user_warns_count[name] = user_warns_count.get(name, 0) + 1

        # Save updated warns to file
        with open("warns.json", "w") as warns_file:
            json.dump(warns, warns_file)

        # Send confirmation message
        await msg.reply(f"{member.mention} has been warned. Total warns: {warns[name]['count']}. Weekly warns: {user_warns_count[name]} ")
        await member.send(
            f"**You've been warned in the Razerchess server for:**\n {reason}.\n\n\n "
            f"You have **{warns[name]['count']}** warns in total and "
            f"{user_warns_count[name]} weekly warns"
        )

        mute_role = bot.get_guild(1528934642630266900).get_role(1534463181542522890)

        # checks for how long to mute
        if user_warns_count[name] % 3 == 0:
            timeout = 10_800  # 2 hours
            if user_warns_count[name] // 3 == 1:
                timeout = 10_800  # 4 hours
            elif user_warns_count[name] // 3 == 2:
                timeout = 10_800 * 2  # 8 hours
            elif user_warns_count[name] // 3 == 3:
                timeout = 10_800 * 4  # 12 hours
            elif user_warns_count[name] // 3 == 4:
                timeout = 10_800 * 8  # 1 day
            elif user_warns_count[name] // 3 == 5:
                timeout = 10_800 * 16  # 2 days
            elif user_warns_count[name] // 3 == 6:
                timeout = 10_800 * 32  # 4 days
            elif user_warns_count[name] // 3 == 7:
                timeout = 10_800 * 64  # 8 days

            await member.add_roles(mute_role, reason="Auto mute due to too many warns")

            # muting part
            embed = discord.Embed(
                title="User Muted!",
                description=(f"**{member}** was muted for {timeout / 60 / 60} hours for **having too much warns** !"),
                color=0xFF00F6,
            )
            success_msg = await msg.reply(embed=embed)
            await mod_logs["actions"].send(embed=embed)
            await delay_func(success_msg.delete, 5)

            # Schedule unmute
            async def unmute_later():
                """Remove the automatic warning mute after its timeout."""
                await asyncio.sleep(timeout)
                if check_if_muted(member):
                    await member.remove_roles(mute_role)
                    embed = discord.Embed(
                        title="User Unmuted!",
                        description=f"The time for **{member}** being muted has finished!",
                        color=0xFF00F6,
                    )
                    mute_finished_msg = await msg.channel.send(content=msg.author.mention, embed=embed)
                    await mod_logs["actions"].send(embed=embed)
                    await delay_func(mute_finished_msg.delete, 5)

            # Start the unmute task
            asyncio.create_task(unmute_later())

            embed = discord.Embed(
                title="User Muted!",
                description=(f"**{member}** was muted for **{reason or 'No reason provided'}** by **{msg.author}**!"),
                color=0xFF00F6,
            )
            success_msg = await msg.reply(embed=embed)
            await mod_logs["actions"].send(embed=embed)
            await delay_func(success_msg.delete, 5)

    except Exception as e:
        await msg.reply(f"An error occurred: {str(e)}")


async def mute(
    msg: Any,
    member: Any,
    timeout: Any = "10m",
    reason=None,
    bot: Any = None,
    mod_logs: dict[str, Any] = {},
):
    """Temporarily mute a member for a staff-specified duration."""
    if check_for_perms(msg.author):  # Checking if the user is from staff (has permissions).
        try:
            if not member:
                await msg.reply("Please mention a member to mute.\nUsage: !mute @member [time] [reason]")
                return
            if not timeout:
                await msg.reply("Please mention the time to mute for (in s(econds), m(inutes) or h(ours)).\nUsage: !mute @member [time] [reason]")
            mute_role = bot.get_guild(1331651870107762732).get_role(1343249780322865247)
            if check_if_muted(member):
                await msg.reply("This member is already muted. Skill issue.")
            else:
                await member.add_roles(mute_role)
                try:
                    timeout = int(timeout[:-1]) * TIME_CONVERT[timeout[-1]]
                except ValueError, KeyError:
                    await msg.reply("Invalid time format! Use formats like 10s, 5m, 2h, 1d.")
                    return
                try:
                    timeout = int(timeout)
                    # muting part
                    embed = discord.Embed(
                        title="User Muted!",
                        description=(
                            f"**{member}** was muted for {timeout / 60} minutes for **{reason or 'No reason provided'}** by **{msg.author}**!"
                        ),
                        color=0x28A745,
                    )
                    success_msg = await msg.reply(embed=embed)
                    await mod_logs["actions"].send(embed=embed)
                    await delay_func(success_msg.delete, 5)

                    # Schedule unmute
                    async def unmute_later():
                        """Remove the manual mute role when the timeout ends."""
                        await asyncio.sleep(timeout)
                        if check_if_muted(member):
                            await member.remove_roles(mute_role)
                            embed = discord.Embed(
                                title="User Unmuted!",
                                description=f"The time for **{member}** being muted has finished!",
                                color=0x28A745,
                            )
                            mute_finished_msg = await msg.channel.send(content=msg.author.mention, embed=embed)
                            await mod_logs["actions"].send(embed=embed)
                            await delay_func(mute_finished_msg.delete, 5)

                    # Start the unmute task
                    asyncio.create_task(unmute_later())
                except ValueError:
                    await msg.reply("Make sure to mention the timeout as a NUMBER!")
                else:
                    embed = discord.Embed(
                        title="User Muted!",
                        description=(f"**{member}** was muted for **{reason or 'No reason provided'}** by **{msg.author}**!"),
                        color=0xFF00F6,
                    )
                    success_msg = await msg.reply(embed=embed)
                    await mod_logs["actions"].send(embed=embed)
                    await delay_func(success_msg.delete, 5)
        except commands.errors.MemberNotFound:
            await msg.reply("Couldn't find that user.")
        except Exception as e:
            await msg.reply(f"An error occurred: {str(e)}")
    else:
        embed = discord.Embed(
            title="**Nuh uh.**",
            description="You don't have permission to use this command.",
            color=0xFF00F6,
        )
        fail_msg = await msg.reply(embed=embed)
        await delay_func(fail_msg.delete, 5)


async def ban(msg, bot: commands.Bot, member: Member | int | None, reason: str | None = None, mod_logs: dict[str, Any] = {}):
    """Ban a member or user ID when the caller has staff permissions."""
    if check_for_perms(msg.author):  # Checking if the user is from staff (has permissions).
        try:
            print(member, type(member))
            if isinstance(member, int):
                user = await bot.fetch_user(member)
                await msg.guild.ban(user)
                embed = discord.Embed(
                    title="User Banned!",
                    description=(
                        f"""## Public Execution, Hooway!
                                    \n**{user}** was banned for **{reason or "No reason provided"}** by **{msg.author}**!
                                    \n -# Go on now, yap more. I hope there's more of you to behead..."""
                    ),
                    color=0x28A745,
                )
                await msg.reply(embed=embed)
                await mod_logs["users"].send(embed=embed)
                wall_of_shame = await bot.fetch_channel(1534571253892120666)
                #TOCHANGE# for the Wall of Shame in the stable version
                # await mod_logs["users"].send(f"{user} HAS BEEN TERMINATED BECAUSE OF {reason.capitalize() if reason else 'SEVERE RULE BREAKING'}.")
                print(user, type(user))
            elif isinstance(member, Member):
                await member.ban(delete_message_days=1, reason=reason)
                await msg.guild.ban(member)
                embed = discord.Embed(
                    title="User Banned!",
                    description=(
                        f"""## Public Execution, Hooway!
                                    \n**{member}** was banned for **{reason or "No reason provided"}** by **{msg.author}**!
                                    \n -# Go on now, yap more. I hope there's more of you to behead..."""
                    ),
                    color=0x28A745,
                )
                await msg.reply(embed=embed)
                await mod_logs["users"].send(embed=embed)
                wall_of_shame = await bot.fetch_channel(1534571253892120666)
                #TOUNCOMMENT# The Wall of Shame should be only in the stable version
                # await wall_of_shame.send(
                #     f"{member.mention} HAS BEEN TERMINATED BECAUSE OF {reason.capitalize() if reason else 'SEVERE RULE BREAKING'}."
                # )
            else:
                await msg.reply("Please mention a member to ban.\nUsage: ?ban @member [reason (optional)]")
        except Exception as e:
            await msg.reply("An error occurred! Check the terminal output for more info.")
            print(f"Exception: {e}")
    else:
        embed = discord.Embed(
            title="**Nuh uh.**",
            description="You don't have permission to use this command.",
            color=0xFF00F6,
        )
        fail_msg = await msg.reply(embed=embed)
        await delay_func(fail_msg.delete, 5)


async def unban(msg, bot: commands.Bot, user_id: int | None, reason=None, mod_logs={}):
    """Unban a user ID when the caller has staff permissions."""
    if check_for_perms(msg.author):  # Checking if the user is from staff (has permissions).
        try:
            if not user_id:
                await msg.reply("Please specify an user's ID to unban them.\nUsage: ?unban [user_id] [reason (optional)]")
                return
            user_to_unban = await bot.fetch_user(user_id)
            await msg.guild.unban(user_to_unban)
            embed = discord.Embed(
                title="User Banned!",
                description=(
                    f"""## The mercy call was answered...
                    \n**{user_to_unban}** was unbanned for **{reason or "No reason provided"}** by **{msg.author}**!"""
                ),
                color=0x28A745,
            )
            await msg.reply(embed=embed)
        except Exception as e:
            await msg.reply("An error occurred! Check the terminal output for more info.")
            print(f"Exception: {e}")
    else:
        embed = discord.Embed(
            title="**Nuh uh.**",
            description="You don't have permission to use this command.",
            color=0xFF00F6,
        )
        fail_msg = await msg.reply(embed=embed)
        await delay_func(fail_msg.delete, 5)
