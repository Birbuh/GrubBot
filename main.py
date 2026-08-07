import asyncio
import json
import os
import re
from typing import Any

import aiofiles
import aiomcrcon
import discord
from cachetools import TTLCache
from discord.ext import commands as _commands
from discord.member import Member
from dotenv import load_dotenv

import bot_commands as botcmd
import earning
import events
import gambling_commands as gambling
import mod_commands as modcmd
import operations
import reports as rpts
from host import os_recog
from other_addons import MOD_LOG_IDS

commands: Any = _commands


class CategoryHelpCommand(commands.HelpCommand):
    """Display prefix commands grouped by their player-facing category."""

    category_order = (
        "Misc",
        "Moderation",
        "Economy",
        "Contact with Staff",
        "Minecraft-related commands",
    )

    async def send_bot_help(self, mapping):
        """Send the main help message with commands grouped by category."""
        available_commands = [command for command_list in mapping.values() for command in command_list]
        visible_commands = await self.filter_commands(available_commands, sort=True)
        categories: dict[str, list[Any]] = {}

        for command in visible_commands:
            category = command.extras.get("category", "Misc")
            categories.setdefault(category, []).append(command)

        lines = ["Use `?help <command>` to learn more about a command."]
        ordered_categories = [category for category in self.category_order if category in categories]
        ordered_categories.extend(sorted(set(categories) - set(ordered_categories)))

        for category in ordered_categories:
            command_names = ", ".join(f"`{command.name}`" for command in categories[category])
            lines.append(f"\n**{category}**\n{command_names}")

        await self.get_destination().send("\n".join(lines))

    async def send_command_help(self, command):
        """Send a detailed, player-facing description for one command."""
        category = command.extras.get("category", "Misc")
        usage = f"{self.context.clean_prefix}{command.qualified_name} {command.signature}".rstrip()
        description = command.help or "No description is available for this command."
        await self.get_destination().send(f"**{command.name}** — {description}\nCategory: **{category}**\nUsage: `{usage}`")

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Required to read message content
intents.members = True  # Required for the on_member_join function
# Setting up:
pattern = re.compile(r"[\uFF01-\uFF5E\u2000-\u200F\u2028-\u202F\uFEFF]")
spam_cache = TTLCache(maxsize=200, ttl=7)
mod_logs: dict[str, Any] = {}
IS_STABLE, BOT_PREFIX = os_recog()

# Load environment variables
load_dotenv()

# server stuff
RCON_HOST = os.getenv("RCON_HOST", "127.0.0.1")
RCON_PORT = int(os.getenv("RCON_PORT", "25575"))
RCON_PASSWORD = os.environ["RCON_PASSWORD"]
CHAT_CHANNEL_ID = int(os.environ["MC_CHAT_CHANNEL_ID"])
MC_LOG_PATH = os.environ["MC_LOG_PATH"]
MC_CHAT_PATTERN = re.compile(r"\]: <([^>]+)> (.+)$")
MC_CHAT_PATTERN2 = re.compile(r"\]: (?:\[Not Secure\] )?<([A-Za-z0-9_]{1,16})> (.*)$")
MC_FORMATTING_PATTERN = re.compile(r"§[0-9A-FK-ORa-fk-or]")
chat_watcher_task: asyncio.Task | None = None

# Function to check if a user is staff.

# Define bot prefix
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=CategoryHelpCommand())


last_message_time = {}
user_spam_count = {}  # individual spam counters
user_warns_count = {}


@bot.command(extras={"category": "Moderation"})
async def lock(msg: Any):
    """Lock this channel so only staff can send messages."""
    await modcmd.lock(msg)


@bot.command(extras={"category": "Moderation"})
async def unlock(msg: Any):
    """Let everyone send messages in this channel again."""
    await modcmd.unlock(msg)


@bot.command(extras={"category": "Contact with Staff"})
async def report(msg: Any, member: Any = None, reason: str | None = None):
    """Report a member by replying to their message and giving a reason. Use once every 2 hours."""
    await rpts.report(msg, member, reason, mod_logs)


@bot.event
async def on_raw_reaction_add(payload):
    """Forward report-approval reactions to the report handler."""
    await rpts.on_raw_reaction_add(payload, bot)


@bot.command(extras={"category": "Moderation"})
async def clear_warns(msg: Any, member: Any = None):
    """Clear a member's weekly warnings. Staff only."""
    await modcmd.clear_warns(msg, member)


@bot.command(name="send-msg", extras={"category": "Moderation"})
async def send_msg(msg: Any, channel_name: Any = None, *, content: Any = None) -> None:
    """Send a message to another channel. Usage: ?send-msg <channel> <message>. Staff only."""
    await modcmd.send_msg(msg, channel_name, content=content)


# ITS NOT !WARN ITS COMMAND FOR INFO
@bot.command(extras={"category": "Misc"})
async def warns_info(msg: Any):
    """Show your current warnings."""
    await botcmd.warns_info(msg)


@bot.command(extras={"category": "Moderation"})
async def info(msg: Any, member: Any = None):
    """Show a member's roles and warning history. Staff only."""
    await modcmd.info(msg, member)


@bot.command(extras={"category": "Misc"})
async def roles(msg: Any, member: Any = None):
    """Show the roles a member has."""
    await botcmd.roles(msg, member)


@bot.command(extras={"category": "Misc"})
async def rules(msg: Any, rule: str | None = None) -> None:
    """Show all server rules, or one rule. Usage: ?rules [rule]."""
    await botcmd.rules(msg, rule)


@bot.command(extras={"category": "Moderation"})
async def ban(msg: Any, member: Member | int | None, reason: str | None):
    """Ban a member or user ID. Usage: ?ban <member or ID> [reason]. Staff only."""
    await modcmd.ban(msg, bot, member, reason, mod_logs)


@bot.command(extras={"category": "Moderation"})
async def unban(msg: Any, user_id: int | None, reason: str | None):
    """Unban a user by their ID. Usage: ?unban <user ID> [reason]. Staff only."""
    await modcmd.unban(msg, bot, user_id, reason, mod_logs)


@bot.command(extras={"category": "Moderation"})
async def purge(msg: Any, amount: int | None = None):
    """Delete recent messages in this channel. Usage: ?purge <amount>. Staff only."""
    await modcmd.purge(msg, amount, mod_logs)


@bot.command(extras={"category": "Moderation"})
async def unmute(msg: Any, member: Any = None, reason: str | None = None):
    """Unmute a member. Usage: ?unmute @member [reason]. Staff only."""
    await modcmd.unmute(msg, member, reason, bot, mod_logs)


@bot.command(extras={"category": "Moderation"})
async def kick(msg: Any, member: Any, reason: str | None = None):
    """Remove a member from the server. Usage: ?kick @member [reason]. Staff only."""
    await modcmd.kick(msg, member, reason)


@bot.command(extras={"category": "Moderation"})
async def warn(msg: Any, member: Any = None, *, reason=None):
    """Warn a member. Usage: ?warn @member [reason]. Staff only."""
    await modcmd.warn(msg, member, reason, bot, mod_logs)


@bot.command(extras={"category": "Misc"})
async def helpme(msg: Any, type_of_help: str | None = None):
    """Get help with a command. Usage: ?helpme [topic]."""
    await botcmd.helpme(msg, type_of_help)


@bot.command(extras={"category": "Moderation"})
async def mute(msg: Any, member: Any, timeout: str = "10m", reason=None):
    """Mute a member for a time. Usage: ?mute @member [10m] [reason]. Staff only."""
    await modcmd.mute(msg, member, timeout, reason, bot, mod_logs)


@bot.event
async def on_ready():
    """Initialize moderation logs and the Minecraft chat watcher on startup."""
    print(f"Logged in as {bot.user}")
    mod_logs["actions"] = await bot.fetch_channel(MOD_LOG_IDS[0])
    mod_logs["users"] = await bot.fetch_channel(MOD_LOG_IDS[0])
    mod_logs["other"] = await bot.fetch_channel(MOD_LOG_IDS[0])

    global chat_watcher_task

    if chat_watcher_task is None or chat_watcher_task.done():
        chat_watcher_task = asyncio.create_task(
            watch_minecraft_chat(),
            name="minecraft-chat-watcher",
        )


@bot.event
async def on_message_delete(msg: Any):
    """Forward deleted messages to the moderation event handler."""
    await events.on_message_delete(msg, bot, mod_logs)


@bot.event
async def on_message_edit(before: Any, after: Any):
    """Forward edited messages to the moderation event handler."""
    await events.on_message_edit(before, after, mod_logs)


@bot.event
async def on_message(message: Any):
    """Moderate incoming messages and relay configured Discord chat to Minecraft."""
    if message.author.bot:  # Ignore bots
        return
    await events.on_message(message, bot, spam_cache)
    if message.channel.id == CHAT_CHANNEL_ID:
        content = message.clean_content.strip()

        if content and not content.startswith(bot.command_prefix):
            # Minecraft chat doesn't handle multiline Discord messages nicely.
            content = " ".join(content.splitlines())
            content = content[:300]

            minecraft_message = {"text": f"[Discord] {message.author.display_name}: {content}"}

            try:
                await run_rcon(f"tellraw @a {json.dumps(minecraft_message)}")
            except Exception as error:
                print(f"Discord → Minecraft failed: {error}")

    # Required, otherwise @bot.command commands stop working.
    await bot.process_commands(message)


@bot.event
async def on_member_join(member: Any):  # Greeting message on join (in DMs)
    """Welcome a newly joined non-bot member and log the event."""
    if member.bot:  # Ignore bots
        return
    new_members_channel = bot.get_channel(1529517779059740742)
    await new_members_channel.send(f"Welcome to the Grub Syndicate, {member.mention}!")
    embed = discord.Embed(title=f"User {member.name} ({member.display_name}) joined the server!")
    await mod_logs["users"].send(embed=embed)


@bot.command(extras={"category": "Misc"})
@commands.has_permissions(administrator=True)
async def sync(message: discord.Message):
    """Refresh the bot's slash commands. Administrators only."""
    await bot.tree.sync()
    await message.reply("synced!")


@bot.command(name="balance", aliases=("bal", "view-money", "ball"), extras={"category": "Economy"})
async def bal_prefix(message, user: None | str = None):
    """Show your balance or another member's balance. Usage: ?balance [member]."""
    await operations.bal(message, user, bot)


@bot.tree.command(name="balance", description="View user's (or yours) balance", extras={"category": "Economy"})
async def bal_slash(interaction, user: None | str = None):
    """Show your balance or another member's balance."""
    await operations.bal(interaction, user, bot)


@bot.command(aliases=("wd", "with"), extras={"category": "Economy"})
async def withdraw(msg, amount: int | str):
    """Move money from your bank to your cash. Usage: ?withdraw <amount, all, or half>."""
    await operations.transfer_money(msg, amount, "cash")


@bot.command(aliases=("dep",), extras={"category": "Economy"})
async def deposit(msg, amount: int | str):
    """Move money from your cash to your bank. Usage: ?deposit <amount, all, or half>."""
    await operations.transfer_money(msg, amount, "bank")
    

# @bot.command(name="give", aliases=("gift",))
# async def give_prefix(msg, member: Member | int | None, amount: int):
#     """Gives a specified member a specified amount of your money.
#     USAGE: ?give @mention/[ID] [amount]; ?gift @mention/[ID] [amount]

#     @mention/ID: A mention (or an ID) of a member you want to give your money.
#     amount: The amount you want to give.
#     """
#     await operations.give_money(msg, member, amount)


# @bot.tree.command(name="give", description="Give someone your precious money :wah:")
# async def give_slash(interaction, member: Member, amount: int):
#     """Gives a specified member a specified amount of your money."""
#     await operations.give_money(interaction, member, amount)


@bot.command(name="roulette", aliases=("rlt", "roulete"), extras={"category": "Economy"})
async def rlt_prefix(message, space, bet):
    """Play roulette. Usage: ?roulette <red, black, even, odd, or 0-36> <bet>."""
    await gambling.roulette(message, bet, space)


@bot.tree.command(name="rlt", description="Play Roulette", extras={"category": "Economy"})
async def rlt_slash(interaction, space: str, bet: str):
    """Play roulette by choosing a space and a bet."""
    await gambling.roulette(interaction, bet, space)


@bot.command(name="blackjack", aliases=("bj",), extras={"category": "Economy"})
async def blackjack_prefix(message, bet):
    """Play blackjack. Usage: ?blackjack <amount, all, or half>."""
    await gambling.blackjack(message, bet)


@bot.tree.command(name="blackjack", description="Play Blackjack", extras={"category": "Economy"})
async def blackjack_slash(interaction, bet: str):
    """Play blackjack with the bet you choose."""
    await gambling.blackjack(interaction, bet)


@bot.command(name="work", extras={"category": "Economy"})
async def work_prefix(message):
    """Work to earn some money. Usage: ?work."""
    await earning.work(message)


@bot.tree.command(name="work", extras={"category": "Economy"})
async def work_slash(command):
    """Work to earn some money."""
    await earning.work(command)


@bot.command(name="delay", extras={"category": "Economy"})
async def delay_prefix(msg, mode: str):
    """Turn the work waiting time on or off. Usage: ?delay <on or off>."""
    await earning.delay(msg, mode)


@bot.tree.command(name="delay", extras={"category": "Economy"})
async def delay_slash(msg, mode: str):
    """Turn the work waiting time on or off."""
    await earning.delay(msg, mode)


# normal bot stuff
#############################################################################################################################################
# minecraft stuff


async def run_rcon(command: str):
    """Open an RCON connection, execute a command, and close the connection."""
    client = aiomcrcon.Client(
        host=RCON_HOST,
        port=RCON_PORT,
        password=RCON_PASSWORD,
    )

    try:
        await client.connect()
        return await client.send_cmd(command)
    finally:
        await client.close()


@bot.command(name="mc-run", extras={"category": "Minecraft-related commands"})
async def mc_run(msg, *, command: str) -> None:
    """Run a command on the Minecraft server. Staff only."""
    if not botcmd.check_for_perms(msg.author):
        await msg.reply("You don't have permission to use this command.")
        return
    try:
        response = await run_rcon(command.removesuffix("\n"))
    except Exception as error:
        await msg.reply(f"RCON failed: `{error}`")
        return

    response = response or "Command completed with no output."
    await msg.reply(f"```text\n{response[:1900]}\n```")


@bot.command(
    name="list-mc-players",
    aliases=("list-mc", "list-players", "lmp", "online-players"),
    extras={"category": "Minecraft-related commands"},
)
async def players(ctx) -> None:
    """Show who is currently online on the Minecraft server."""
    try:
        response = await run_rcon("list")
    except Exception as error:
        await ctx.reply(f"RCON failed: `{error}`")
        return

    await ctx.reply(response or "No response.")


async def watch_minecraft_chat() -> None:
    """Tail the Minecraft log and relay player chat to the configured Discord channel."""
    await bot.wait_until_ready()

    channel = bot.get_channel(CHAT_CHANNEL_ID)

    if channel is None:
        try:
            channel = await bot.fetch_channel(CHAT_CHANNEL_ID)
        except discord.DiscordException as error:
            print(f"Could not access Discord channel: {error}")
            return

    try:
        async with aiofiles.open(
            MC_LOG_PATH,
            mode="r",
            encoding="utf-8",
            errors="replace",
        ) as log_file:
            # Ignore old messages and start at the end.
            await log_file.seek(0, 2)

            while not bot.is_closed():
                line = await log_file.readline()

                if not line:
                    await asyncio.sleep(0.2)
                    continue

                match = MC_CHAT_PATTERN.search(line)

                if not match:
                    
                    match2 = MC_CHAT_PATTERN2.search(line)
                    if not match2:
                        continue

                player_name, content = match.groups() if match else match2.groups() if match2 else ("sth didnt work", "sth didnt work")
                content = MC_FORMATTING_PATTERN.sub("", content)

                await channel.send(
                    f"**{discord.utils.escape_markdown(player_name)}:** {discord.utils.escape_markdown(content)}",
                    allowed_mentions=discord.AllowedMentions.none(),
                )

    except FileNotFoundError:
        print(f"Minecraft log not found: {MC_LOG_PATH}")
    except Exception as error:
        print(f"Minecraft chat watcher failed: {error}")


# Run the bot with token from environment variable
if IS_STABLE:
    token = os.getenv("STABLE_DISCORD_TOKEN")
else:
    token = os.getenv("UNSTABLE_DISCORD_TOKEN")
if not token:
    print("Error: No Discord token found. Please set the DISCORD_TOKEN environment variable.")
    exit(1)
if __name__ == "__main__":
    bot.run(token)
