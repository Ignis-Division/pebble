# 🛡️ Discord Member Filter & Moderation Bot

A Discord bot with slash commands for filtering members by various criteria (no avatar, role, join date, etc.) and taking moderation actions directly from Discord.

---

## Requirements

- Python 3.10+
- A Discord bot token
- Server Members Intent enabled

---

## Installation

```bash
pip install discord.py
```

---

## Setup

1. Open `discord_mod_bot.py` and set your bot token:

```python
BOT_TOKEN = "your-token-here"
```

2. In the [Discord Developer Portal](https://discord.com/developers/applications):
   - Go to your app → **Bot**
   - Enable **Server Members Intent**
   - Enable **Message Content Intent**

3. Invite your bot to your server using OAuth2 with these permissions:
   - `bot` + `applications.commands` scopes
   - Kick Members
   - Ban Members
   - Manage Roles
   - Moderate Members
   - Send Messages
   - Embed Links

4. Run the bot:

```bash
python discord_mod_bot.py
```

Slash commands sync automatically on startup.

---

## Commands

### Filtering & Listing

| Command | Description |
|---|---|
| `/filter` | Filter members by multiple criteria and list them with ID and @ |
| `/no_avatar` | Quick list of all members with no profile photo |

#### `/filter` options

| Option | Type | Description |
|---|---|---|
| `no_avatar` | bool | Only show members with no profile photo |
| `role` | string | Only show members with this exact role name |
| `no_roles` | bool | Only show members with zero roles |
| `joined_within_days` | int | Only show members who joined within the last N days |
| `include_bots` | bool | Include bot accounts (default: excluded) |

---

### Moderation Actions

| Command | Description |
|---|---|
| `/kick` | Kick a member |
| `/ban` | Ban a member |
| `/ban_id` | Ban a user by ID (even if they've already left) |
| `/mute` | Timeout a member for N minutes |
| `/unmute` | Remove an active timeout |
| `/remove_role` | Strip a role from a member |
| `/warn` | Send a DM warning to a member |
| `/kick_filtered` | Bulk kick members matching a filter |

---

### Bulk Kicking

`/kick_filtered` supports the same filters as `/filter`. It **always dry-runs by default** — it will show you a preview of who would be kicked without actually doing it.

```
/kick_filtered no_avatar:True dry_run:True   ← preview only
/kick_filtered no_avatar:True dry_run:False  ← actually kicks
```

Always confirm with a dry run first.

---

## Permissions

Each command requires the moderator using it to have the relevant Discord permission:

| Commands | Required Permission |
|---|---|
| `/filter`, `/no_avatar`, `/kick`, `/warn`, `/kick_filtered` | Kick Members |
| `/ban`, `/ban_id` | Ban Members |
| `/mute`, `/unmute` | Moderate Members |
| `/remove_role` | Manage Roles |

---

## Notes

- All kick/ban/mute actions are logged to your server's **Audit Log** with the moderator's name and reason.
- `/warn` sends a DM to the target member. If they have DMs disabled, the command will tell you it failed — only you (the mod) see this message.
- Results from `/filter` and `/no_avatar` are paginated automatically if the member list is long.
- The bot must have a role **above** any role it is trying to manage or remove.

---

## Running on a VPS (24/7)

Install PM2 to keep the bot alive:

```bash
npm install -g pm2
pm2 start discord_mod_bot.py --interpreter python3 --name modbot
pm2 save
pm2 startup
```

To view logs:

```bash
pm2 logs modbot
```
