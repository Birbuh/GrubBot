# GrubBot

GrubBot is the Discord bot for the GrubSMP community. It provides moderation
tools, member reports, a small economy with games, and a bridge between a
Discord channel and Minecraft chat through RCON.

## Features

- Staff moderation commands: lock/unlock channels, warn, mute, unmute, kick,
  ban, unban, purge, and send a message to another channel.
- Automated moderation for rapid messages, repeated mentions, and long
  unspaced text.
- Member-facing reporting, role, rule, help, and balance commands.
- Economy commands for work, deposits, withdrawals, roulette, and blackjack.
- Optional Discord-to-Minecraft and Minecraft-to-Discord chat relay.

## Requirements

- Python 3.14 or newer (the project is configured for Python 3.14).
- A Discord bot application with the Message Content and Server Members intents
  enabled.
- A Minecraft server with RCON enabled if using the Minecraft commands or chat
  relay.

Install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root. The bot reads the following values:

```dotenv
STABLE_DISCORD_TOKEN=your-production-bot-token
UNSTABLE_DISCORD_TOKEN=your-development-bot-token
RCON_HOST=127.0.0.1
RCON_PORT=25575
RCON_PASSWORD=your-rcon-password
MC_CHAT_CHANNEL_ID=123456789012345678
MC_LOG_PATH=/path/to/logs/latest.log
```

The hostname determines which Discord token and command prefix are used:
`archlinux` uses `UNSTABLE_DISCORD_TOKEN` and `??`; every other hostname uses
`STABLE_DISCORD_TOKEN` and `?`.

Several Discord IDs (roles, channels, and guilds) are currently defined in the
source. Update them for your server before deployment. Runtime data is stored in
`money_lb.json` (economy balances) and `warns.json` (warnings); ensure those
files exist and contain `{}` initially.

## Running the bot

```bash
python main.py
```

On startup, GrubBot registers its event handlers and starts the Minecraft log
watcher. Use the administrator-only `?sync` command after adding or changing
slash commands.

## Commands

The standard prefix is `?` (or `??` on the development hostname). Most economy
commands are available both as prefix and slash commands.

| Area | Commands |
| --- | --- |
| Community | `?helpme`, `?rules [rule]`, `?roles [member]`, `?warns`, `?report @member reason` |
| Economy | `?balance [user]`, `?withdraw <amount>`, `?deposit <amount>`, `?work`, `?roulette <space> <bet>`, `?blackjack <bet>` |
| Staff | `?lock`, `?unlock`, `?send-msg <channel> <content>`, `?info [member]`, `?clear_warns [member]`, `?purge <amount>`, `?warn @member [reason]`, `?mute @member [timeout] [reason]`, `?unmute @member [reason]`, `?kick @member [reason]`, `?ban <member-or-id> [reason]`, `?unban <user-id> [reason]` |
| Minecraft | `?mc-run <command>` and `?list-mc-players` (staff only) |

For gambling, bets may be a positive number, `all`, or `half`. Roulette accepts
`red`, `black`, `even`, `odd`, or a number from `0` to `36`.

## Project layout

- `main.py` wires Discord commands, events, environment configuration, and the
  Minecraft relay together.
- `mod_commands.py`, `bot_commands.py`, and `reports.py` implement moderation
  and community features.
- `operations.py`, `earning.py`, and `gambling_commands.py` implement the
  economy and games.
- `events.py` contains message event processing; `other_addons.py` contains
  shared settings and helper functions.
