import discord
import re
import os
from typing import Any

from discord.member import Member
import events
import bot_commands as botcmd
import mod_commands as modcmd
import reports as rpts
import earning
import operations
import gambling_commands as gambling
from other_addons import MOD_LOG_IDS
from host import os_recog
from cachetools import TTLCache
from discord.ext import commands as _commands
from dotenv import load_dotenv

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


@bot.event
async def on_message_delete(msg: Any):
    await events.on_message_delete(msg, bot, mod_logs)


@bot.event
async def on_message_edit(before: Any, after: Any):
    await events.on_message_edit(before, after, mod_logs)


@bot.event
async def on_message(message: Any):
    await events.on_message(message, bot, spam_cache)


@bot.event
async def on_member_join(member: Any):  # Greeting message on join (in DMs)
    if member.bot:  # Ignore bots
        return
    new_members_channel = bot.get_channel(1529517779059740742)
    await new_members_channel.send(f"Welcome to the Grub Syndicate server, {member.mention}!")
    embed = discord.Embed(title=f"User {member.mention} joined the server!")
    await mod_logs["users"].send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def sync(message: discord.Message):
    """Synchronizes the slash commands"""
    await bot.tree.sync()
    await message.reply("synced!")


@bot.command(name="balance", aliases=("bal", "view-money"))
async def bal_prefix(message, user: None | str = None):
    """Shows the balance of an user
    USAGE: {prefix}bal (user); {prefix}balance (user)

    user: User you want to show balance of. If empty, the command shows yours balance.
    """
    await operations.bal(message, user, bot)


@bot.tree.command(name="balance", description="View user's (or yours) balance")
async def bal_slash(interaction, user: None | str = None):
    """Shows the balance of an user"""
    await operations.bal(interaction, user, bot)


@bot.command(name="roulette", aliases=("rlt", "roulete"))
async def rlt_prefix(message, space, bet):
    """Plays Roulette
    USAGE: {prefix}rlt {space} {bet}

    space: On what you want to bet
    bet: what you want to bet
    """
    await gambling.roulette(message, bet, space)


@bot.tree.command(name="rlt", description="Play Roulette")
async def rlt_slash(interaction, space: str, bet: str):
    await gambling.roulette(interaction, bet, space)


@bot.command(name="work")
async def work_prefix(message):
    """Adds some money to your balance
    USAGE: {prefix}work
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


# Load environment variables
load_dotenv()

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
