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
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)


last_message_time = {}
user_spam_count = {}  # individual spam counters
user_warns_count = {}


@bot.command()
async def lock(msg: Any):
    await modcmd.lock(msg)


@bot.command()
async def unlock(msg: Any):
    await modcmd.unlock(msg)


@bot.command()
async def report(msg: Any, member: Any = None, reason: str | None = None):
    """Report someone by replying to their message with a reason. Can be used once every 2 hours."""
    await rpts.report(msg, member, reason, mod_logs)


@bot.event
async def on_raw_reaction_add(payload):
    await rpts.on_raw_reaction_add(payload, bot)


@bot.command()
async def clear_warns(msg: Any, member: Any = None):
    await modcmd.clear_warns(msg, member)


@bot.command(name="send-msg")
async def send_msg(msg: Any, channel_name: Any = None, *, content: Any = None) -> None:
    await modcmd.send_msg(msg, channel_name, content=content)


# ITS NOT !WARN ITS COMMAND FOR INFO
@bot.command()
async def warns_info(msg: Any):
    await botcmd.warns_info(msg)


@bot.command()
async def info(msg: Any, member: Any = None):
    await modcmd.info(msg, member)


@bot.command()
async def roles(msg: Any, member: Any = None):
    await botcmd.roles(msg, member)


@bot.command()
async def rules(msg: Any, rule: str | None = None) -> None:
    """Usage: !rules <rule> None by default"""
    await botcmd.rules(msg, rule)


@bot.command()
async def ban(msg: Any, member: Member | int | None, reason: str | None):
    await modcmd.ban(msg, bot, member, reason, mod_logs)


@bot.command()
async def unban(msg: Any, user_id: int | None, reason: str | None):
    await modcmd.unban(msg, bot, user_id, reason, mod_logs)


@bot.command()
async def purge(msg: Any, amount: int | None = None):
    await modcmd.purge(msg, amount, mod_logs)


@bot.command()
async def unmute(msg: Any, member: Any = None, reason: str | None = None):
    await modcmd.unmute(msg, member, reason, bot, mod_logs)


@bot.command()
async def kick(msg: Any, member: Any, reason: str | None = None):
    await modcmd.kick(msg, member, reason)


@bot.command()
async def warn(msg: Any, member: Any = None, *, reason=None):
    """Usage: !warn <member> <reason (none by default)>
    Warns a user, storing it in warns.json"""
    await modcmd.warn(msg, member, reason, bot, mod_logs)


@bot.command()
async def helpme(msg: Any, type_of_help: str | None = None):
    await botcmd.helpme(msg, type_of_help)


@bot.command()
async def mute(msg: Any, member: Any, timeout: str = "10m", reason=None):
    """Usage: !mute <member> <time (10m by default)> <reason (none by default)>
    Mutes a user."""
    await modcmd.mute(msg, member, timeout, reason, bot, mod_logs)


@bot.event
async def on_ready():
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
    await events.on_message_delete(msg, bot, mod_logs)


@bot.event
async def on_message_edit(before: Any, after: Any):
    await events.on_message_edit(before, after, mod_logs)


@bot.event
async def on_message(message: Any):
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
    if member.bot:  # Ignore bots
        return
    new_members_channel = bot.get_channel(1529517779059740742)
    await new_members_channel.send(f"Welcome to the Grub Syndicate, {member.mention}!")
    embed = discord.Embed(title=f"User {member.name} ({member.display_name}) joined the server!")
    await mod_logs["users"].send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def sync(message: discord.Message):
    """Synchronizes the slash commands"""
    await bot.tree.sync()
    await message.reply("synced!")


@bot.command(name="balance", aliases=("bal", "view-money", "ball"))
async def bal_prefix(message, user: None | str = None):
    """Shows the balance of an user
    USAGE: ?bal (user); ?balance (user)

    user: User you want to show balance of. If empty, the command shows yours balance.
    """
    await operations.bal(message, user, bot)


@bot.tree.command(name="balance", description="View user's (or yours) balance")
async def bal_slash(interaction, user: None | str = None):
    """Shows the balance of an user"""
    await operations.bal(interaction, user, bot)


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


@bot.command(name="roulette", aliases=("rlt", "roulete"))
async def rlt_prefix(message, space, bet):
    """Plays Roulette
    USAGE: ?rlt {space} {bet}

    space: On what you want to bet
    bet: what you want to bet
    """
    await gambling.roulette(message, bet, space)


@bot.tree.command(name="rlt", description="Play Roulette")
async def rlt_slash(interaction, space: str, bet: str):
    await gambling.roulette(interaction, bet, space)


@bot.command(name="blackjack", aliases=("bj",))
async def blackjack_prefix(message, bet):
    """Plays Blackjack
    USAGE: ?blackjack {bet} / ?bj {bet}

    bet: The amount you want to bet (an integer, or 'all'/'half').
    """
    await gambling.blackjack(message, bet)


@bot.tree.command(name="blackjack", description="Play Blackjack")
async def blackjack_slash(interaction, bet: str):
    await gambling.blackjack(interaction, bet)


@bot.command(name="work")
async def work_prefix(message):
    """Adds some money to your balance
    USAGE: ?work
    """
    await earning.work(message)


@bot.tree.command(name="work")
async def work_slash(command):
    await earning.work(command)


@bot.command(name="delay")
async def delay_prefix(msg, mode: str):

    await earning.delay(msg, mode)


@bot.tree.command(name="delay")
async def delay_slash(msg, mode: str):
    await earning.delay(msg, mode)


# normal bot stuff
#############################################################################################################################################
# minecraft stuff


async def run_rcon(command: str):
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


@bot.command(name="mc-run")
async def mc_run(msg, *, command: str) -> None:
    """Run a Minecraft console command through RCON."""
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


@bot.command(name="list-mc-players", aliases=("list-mc", "list-players", "lmp", "online-players"))
async def players(ctx) -> None:
    try:
        response = await run_rcon("list")
    except Exception as error:
        await ctx.reply(f"RCON failed: `{error}`")
        return

    await ctx.reply(response or "No response.")


async def watch_minecraft_chat() -> None:
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
