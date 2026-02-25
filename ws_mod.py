"""
Discord Member Filter & Moderation Bot
=======================================
Install:  pip install discord.py
Run:      python discord_mod_bot.py

Required Bot Permissions (OAuth2 scopes: bot + applications.commands):
  ✅ Kick Members
  ✅ Ban Members
  ✅ Manage Roles
  ✅ Moderate Members (Timeout)
  ✅ Send Messages / Embed Links

In Discord Developer Portal → Bot:
  ✅ Enable SERVER MEMBERS INTENT
  ✅ Enable MESSAGE CONTENT INTENT
"""

import discord
from discord import app_commands
from datetime import datetime, timezone, timedelta

# ──────────────────────────────────────────
#  CONFIG — paste your bot token here
# ──────────────────────────────────────────
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# ──────────────────────────────────────────
#  SETUP
# ──────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True

class ModBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands synced globally.")

    async def on_ready(self):
        print(f"🤖 Logged in as {self.user} (ID: {self.user.id})")

bot = ModBot()

# ──────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────

def has_default_avatar(member: discord.Member) -> bool:
    """True if the member has no custom profile photo."""
    return member.avatar is None

def joined_days_ago(member: discord.Member) -> int:
    if not member.joined_at:
        return 0
    return (datetime.now(timezone.utc) - member.joined_at).days

def format_member_line(idx: int, member: discord.Member) -> str:
    roles = [r.name for r in member.roles if r.name != "@everyone"]
    role_str = ", ".join(roles) if roles else "*(no roles)*"
    avatar_flag = " 🚫🖼️" if has_default_avatar(member) else ""
    return (
        f"`{idx}.` **{member.display_name}**{avatar_flag}\n"
        f"    ID: `{member.id}` | {member.mention}\n"
        f"    Roles: {role_str} | Joined: {joined_days_ago(member)}d ago"
    )

async def send_paginated(
    interaction: discord.Interaction,
    title: str,
    lines: list[str],
    color=discord.Color.blurple()
):
    """Split results across embeds to stay within Discord's character limit."""
    if not lines:
        await interaction.followup.send(embed=discord.Embed(
            title=title,
            description="*No members matched this filter.*",
            color=discord.Color.orange()
        ))
        return

    pages, current, length = [], [], 0
    for line in lines:
        if length + len(line) > 3800:
            pages.append(current)
            current, length = [], 0
        current.append(line)
        length += len(line)
    if current:
        pages.append(current)

    for i, page in enumerate(pages):
        embed = discord.Embed(
            title=f"{title} (Page {i+1}/{len(pages)})",
            description="\n\n".join(page),
            color=color
        )
        embed.set_footer(text=f"Total matched: {len(lines)} member(s)")
        await interaction.followup.send(embed=embed)


# ══════════════════════════════════════════
#  SLASH COMMANDS
# ══════════════════════════════════════════

# ── /filter ───────────────────────────────

@bot.tree.command(name="filter", description="Filter and list server members by various criteria.")
@app_commands.describe(
    no_avatar="Only show members with no profile photo",
    role="Only show members who have this exact role name",
    no_roles="Only show members with no roles at all",
    joined_within_days="Only show members who joined within the last N days",
    include_bots="Include bot accounts in results (default: excluded)",
)
@app_commands.checks.has_permissions(kick_members=True)
async def filter_cmd(
    interaction: discord.Interaction,
    no_avatar: bool = False,
    role: str = None,
    no_roles: bool = False,
    joined_within_days: int = None,
    include_bots: bool = False,
):
    await interaction.response.defer(thinking=True)
    members = list(interaction.guild.members)
    applied = []

    if not include_bots:
        members = [m for m in members if not m.bot]

    if no_avatar:
        members = [m for m in members if has_default_avatar(m)]
        applied.append("No profile photo")

    if role:
        role_obj = discord.utils.get(interaction.guild.roles, name=role)
        if not role_obj:
            await interaction.followup.send(f"❌ Role **{role}** not found. Check the exact role name.", ephemeral=True)
            return
        members = [m for m in members if role_obj in m.roles]
        applied.append(f"Has role: {role}")

    if no_roles:
        members = [m for m in members if all(r.name == "@everyone" for r in m.roles)]
        applied.append("No roles")

    if joined_within_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=joined_within_days)
        members = [m for m in members if m.joined_at and m.joined_at >= cutoff]
        applied.append(f"Joined ≤ {joined_within_days} days ago")

    # Sort by join date (oldest first)
    members.sort(key=lambda m: m.joined_at or datetime.now(timezone.utc))

    lines = [format_member_line(i + 1, m) for i, m in enumerate(members)]
    filter_label = " | ".join(applied) if applied else "All Members (no filter)"
    await send_paginated(interaction, f"🔍 Filter: {filter_label}", lines)


# ── /no_avatar ────────────────────────────

@bot.tree.command(name="no_avatar", description="Quick list of all members who have no profile photo.")
@app_commands.checks.has_permissions(kick_members=True)
async def no_avatar_cmd(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    members = [m for m in interaction.guild.members if not m.bot and has_default_avatar(m)]
    members.sort(key=lambda m: m.joined_at or datetime.now(timezone.utc))
    lines = [format_member_line(i + 1, m) for i, m in enumerate(members)]
    await send_paginated(interaction, "🚫🖼️ Members With No Profile Photo", lines, discord.Color.yellow())


# ── /kick ─────────────────────────────────

@bot.tree.command(name="kick", description="Kick a member from the server.")
@app_commands.describe(
    user="The member to kick",
    reason="Reason shown in the audit log"
)
@app_commands.checks.has_permissions(kick_members=True)
async def kick_cmd(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    await interaction.response.defer(thinking=True)
    try:
        await user.kick(reason=f"[ModBot] {reason} — by {interaction.user}")
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"**{user}** (`{user.id}`) was kicked.\n**Reason:** {reason}",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed)
    except discord.Forbidden:
        await interaction.followup.send("❌ Missing permission to kick that member.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# ── /ban ──────────────────────────────────

@bot.tree.command(name="ban", description="Ban a member from the server.")
@app_commands.describe(
    user="The member to ban",
    reason="Reason shown in the audit log",
    delete_days="Days of message history to delete (0–7)"
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban_cmd(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: str = "No reason provided",
    delete_days: int = 0
):
    await interaction.response.defer(thinking=True)
    try:
        await user.ban(
            reason=f"[ModBot] {reason} — by {interaction.user}",
            delete_message_days=min(delete_days, 7)
        )
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=(
                f"**{user}** (`{user.id}`) was banned.\n"
                f"**Reason:** {reason}\n"
                f"**Messages deleted:** last {delete_days} day(s)"
            ),
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
    except discord.Forbidden:
        await interaction.followup.send("❌ Missing permission to ban that member.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


@bot.tree.command(name="ban_id", description="Ban a user by their Discord ID (even if not in server).")
@app_commands.describe(
    user_id="The user's Discord ID",
    reason="Reason for the ban"
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban_id_cmd(interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
    await interaction.response.defer(thinking=True)
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.ban(user, reason=f"[ModBot] {reason} — by {interaction.user}")
        embed = discord.Embed(
            title="🔨 User Banned",
            description=f"**{user}** (`{user_id}`) was banned.\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
    except ValueError:
        await interaction.followup.send("❌ That doesn't look like a valid user ID.", ephemeral=True)
    except discord.NotFound:
        await interaction.followup.send("❌ No Discord user found with that ID.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ Missing permission to ban that user.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# ── /mute & /unmute ───────────────────────

@bot.tree.command(name="mute", description="Timeout (mute) a member for a set duration.")
@app_commands.describe(
    user="The member to mute",
    minutes="How long to mute them (in minutes, max 40320 = 28 days)",
    reason="Reason for the mute"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def mute_cmd(
    interaction: discord.Interaction,
    user: discord.Member,
    minutes: int = 60,
    reason: str = "No reason provided"
):
    await interaction.response.defer(thinking=True)
    minutes = min(minutes, 40320)
    hours, mins = divmod(minutes, 60)
    duration_str = f"{hours}h {mins}m" if hours else f"{mins}m"
    try:
        await user.timeout(timedelta(minutes=minutes), reason=f"[ModBot] {reason} — by {interaction.user}")
        embed = discord.Embed(
            title="🔇 Member Muted",
            description=(
                f"**{user}** (`{user.id}`) was timed out for **{duration_str}**.\n"
                f"**Reason:** {reason}"
            ),
            color=discord.Color.yellow()
        )
        await interaction.followup.send(embed=embed)
    except discord.Forbidden:
        await interaction.followup.send("❌ Missing permission to timeout that member.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


@bot.tree.command(name="unmute", description="Remove an active timeout from a member.")
@app_commands.describe(user="The member to unmute")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute_cmd(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(thinking=True)
    try:
        await user.timeout(None)
        await interaction.followup.send(f"✅ Timeout cleared for **{user}** (`{user.id}`).")
    except discord.Forbidden:
        await interaction.followup.send("❌ Missing permission to remove timeout.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# ── /remove_role ──────────────────────────

@bot.tree.command(name="remove_role", description="Remove a role from a member.")
@app_commands.describe(
    user="The member to remove the role from",
    role="The role to remove"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def remove_role_cmd(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    await interaction.response.defer(thinking=True)
    if role not in user.roles:
        await interaction.followup.send(
            f"❌ **{user.display_name}** doesn't have the **{role.name}** role.", ephemeral=True
        )
        return
    try:
        await user.remove_roles(role, reason=f"[ModBot] Removed by {interaction.user}")
        embed = discord.Embed(
            title="🏷️ Role Removed",
            description=f"Removed **{role.name}** from **{user}** (`{user.id}`).",
            color=discord.Color.blurple()
        )
        await interaction.followup.send(embed=embed)
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I can't manage that role. Make sure my role is **above** it in the role list.", ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# ── /warn ─────────────────────────────────

@bot.tree.command(name="warn", description="Send a DM warning to a member.")
@app_commands.describe(
    user="The member to warn",
    message="The warning message to DM them"
)
@app_commands.checks.has_permissions(kick_members=True)
async def warn_cmd(interaction: discord.Interaction, user: discord.Member, message: str):
    await interaction.response.defer(thinking=True, ephemeral=True)
    warning_embed = discord.Embed(
        title=f"⚠️ Warning from {interaction.guild.name}",
        description=message,
        color=discord.Color.yellow(),
        timestamp=datetime.now(timezone.utc)
    )
    warning_embed.set_footer(text="Please review the server rules to avoid further action.")
    try:
        await user.send(embed=warning_embed)
        await interaction.followup.send(
            f"✅ Warning DM sent to **{user.display_name}** (`{user.id}`).", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send(
            f"❌ Couldn't DM **{user.display_name}** — they may have DMs disabled.", ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# ── /kick_filtered ────────────────────────

@bot.tree.command(name="kick_filtered", description="Bulk-kick members matching a filter. Always dry-run first!")
@app_commands.describe(
    no_avatar="Target members with no profile photo",
    role="Target members who have this role",
    joined_within_days="Target members who joined within the last N days",
    reason="Reason for the kick (audit log)",
    dry_run="Preview who would be kicked WITHOUT kicking (default: True — always start here)"
)
@app_commands.checks.has_permissions(kick_members=True)
async def kick_filtered_cmd(
    interaction: discord.Interaction,
    no_avatar: bool = False,
    role: str = None,
    joined_within_days: int = None,
    reason: str = "Bulk moderation",
    dry_run: bool = True,
):
    await interaction.response.defer(thinking=True)
    members = [m for m in interaction.guild.members if not m.bot]

    if no_avatar:
        members = [m for m in members if has_default_avatar(m)]
    if role:
        role_obj = discord.utils.get(interaction.guild.roles, name=role)
        if not role_obj:
            await interaction.followup.send(f"❌ Role **{role}** not found.", ephemeral=True)
            return
        members = [m for m in members if role_obj in m.roles]
    if joined_within_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=joined_within_days)
        members = [m for m in members if m.joined_at and m.joined_at >= cutoff]

    if not members:
        await interaction.followup.send("No members matched the filter.", ephemeral=True)
        return

    lines = [format_member_line(i + 1, m) for i, m in enumerate(members)]

    if dry_run:
        await send_paginated(
            interaction,
            f"👢 [DRY RUN] Would kick {len(members)} member(s)",
            lines,
            discord.Color.orange()
        )
        await interaction.followup.send(
            "⚠️ **Dry run only — nobody was kicked.** "
            "Run again with `dry_run: False` to execute."
        )
        return

    kicked, failed = 0, 0
    for m in members:
        try:
            await m.kick(reason=f"[ModBot Bulk] {reason} — by {interaction.user}")
            kicked += 1
        except Exception:
            failed += 1

    embed = discord.Embed(
        title="👢 Bulk Kick Complete",
        description=(
            f"✅ Kicked: **{kicked}**\n"
            f"❌ Failed: **{failed}**\n"
            f"**Reason:** {reason}"
        ),
        color=discord.Color.red()
    )
    await interaction.followup.send(embed=embed)


# ──────────────────────────────────────────
#  GLOBAL ERROR HANDLER
# ──────────────────────────────────────────

@bot.tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ You don't have permission to use this command."
    elif isinstance(error, app_commands.BotMissingPermissions):
        msg = "❌ I'm missing a required permission for that action."
    else:
        msg = f"❌ Unexpected error: {error}"
    try:
        await interaction.response.send_message(msg, ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(msg, ephemeral=True)


# ──────────────────────────────────────────
#  RUN
# ──────────────────────────────────────────

bot.run(BOT_TOKEN)
