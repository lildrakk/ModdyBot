import discord
from discord.ext import commands
from discord import app_commands
import json, os, time
from datetime import datetime, timezone

CONFIG_FILE = "antiraid_config.json"
BLACKLIST_FILE = "antiraid_blacklist.json"


# ============================================================
# CONFIG GLOBAL (CARGA UNA VEZ)
# ============================================================

def load_all_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}

    with open(CONFIG_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_all_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================================================
# COG ANTI-RAID
# ============================================================

class AntiRaid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Cargamos TODA la config una sola vez (persistente)
        self.config = load_all_config()

    # ============================================================
    # CONFIG POR SERVIDOR (PERSISTENTE)
    # ============================================================

    def ensure_guild_config(self, guild_id: int):
        gid = str(guild_id)

        if gid not in self.config:
            self.config[gid] = {
                "enabled": True,
                "log_channel": None,

                # Datos dinámicos
                "join_times": [],
                "user_risk": {},
                "channel_deletions": [],
                "channel_creations": [],

                # Ajustes
                "settings": {
                    "sensitivity": "medium",
                    "join_limit": 5,
                    "join_window": 10,
                    "min_account_days": 7,
                    "spam_window": 5,
                    "spam_messages": 4,
                    "channel_delete_limit": 3,
                    "channel_create_limit": 3
                },

                # Lockdown
                "lockdown_active": False,
                "lockdown_state": {}
            }

            save_all_config(self.config)

        return self.config[gid]

    def update_guild(self, guild_id: int, new_data: dict):
        """Actualiza SOLO la config del servidor sin borrar otras."""
        self.config[str(guild_id)] = new_data
        save_all_config(self.config)

    # ============================================================
    # SISTEMA DE RIESGO
    # ============================================================

    def add_risk(self, guild_id: int, user_id: int, amount: int, reason: str):
        cfg = self.ensure_guild_config(guild_id)
        uid = str(user_id)

        if uid not in cfg["user_risk"]:
            cfg["user_risk"][uid] = {"risk": 0, "reasons": [], "messages": []}

        cfg["user_risk"][uid]["risk"] += amount
        cfg["user_risk"][uid]["reasons"].append(reason)

        if cfg["user_risk"][uid]["risk"] > 100:
            cfg["user_risk"][uid]["risk"] = 100

        self.update_guild(guild_id, cfg)

    def get_global_risk(self, guild_id: int):
        cfg = self.ensure_guild_config(guild_id)
        return sum(data["risk"] for data in cfg["user_risk"].values())

    # ============================================================
    # DETECCIÓN: ENTRADAS
    # ============================================================

    @commands.Cog.listener()
    async def on_member_join(self, member):
        cfg = self.ensure_guild_config(member.guild.id)
        if not cfg["enabled"]:
            return

        now = time.time()
        cfg["join_times"].append(now)
        cfg["join_times"] = [t for t in cfg["join_times"] if now - t <= cfg["settings"]["join_window"]]

        # Cuenta nueva
        age = (datetime.now(timezone.utc) - member.created_at).days
        if age < cfg["settings"]["min_account_days"]:
            self.add_risk(member.guild.id, member.id, 25, f"Cuenta nueva ({age} días)")

        # Nombre sospechoso
        if any(x in member.name.lower() for x in ["bot", "raid", "spam", "xxx", "123"]):
            self.add_risk(member.guild.id, member.id, 15, "Nombre sospechoso")

        # Entradas masivas
        if len(cfg["join_times"]) >= cfg["settings"]["join_limit"]:
            self.add_risk(member.guild.id, member.id, 40, "Entradas masivas detectadas")

        self.update_guild(member.guild.id, cfg)

        await self.auto_lockdown_check(member.guild)
        await self.punish_high_risk_users(member.guild)

    # ============================================================
    # DETECCIÓN: MENSAJES
    # ============================================================

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        cfg = self.ensure_guild_config(message.guild.id)
        if not cfg["enabled"]:
            return

        uid = str(message.author.id)
        now = time.time()

        if uid not in cfg["user_risk"]:
            cfg["user_risk"][uid] = {"risk": 0, "reasons": [], "messages": []}

        cfg["user_risk"][uid]["messages"].append(now)
        cfg["user_risk"][uid]["messages"] = [
            t for t in cfg["user_risk"][uid]["messages"]
            if now - t <= cfg["settings"]["spam_window"]
        ]

        if len(cfg["user_risk"][uid]["messages"]) >= cfg["settings"]["spam_messages"]:
            self.add_risk(message.guild.id, message.author.id, 20, "Spam coordinado detectado")

        self.update_guild(message.guild.id, cfg)

        await self.auto_lockdown_check(message.guild)
        await self.punish_high_risk_users(message.guild)

    # ============================================================
    # DETECCIÓN: CANALES
    # ============================================================

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        cfg = self.ensure_guild_config(channel.guild.id)
        now = time.time()

        cfg["channel_deletions"].append(now)
        cfg["channel_deletions"] = [t for t in cfg["channel_deletions"] if now - t <= 10]

        if len(cfg["channel_deletions"]) >= cfg["settings"]["channel_delete_limit"]:
            self.add_risk(channel.guild.id, 0, 30, "Borrado masivo de canales")

        self.update_guild(channel.guild.id, cfg)

        await self.auto_lockdown_check(channel.guild)
        await self.punish_high_risk_users(channel.guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        cfg = self.ensure_guild_config(channel.guild.id)
        now = time.time()

        cfg["channel_creations"].append(now)
        cfg["channel_creations"] = [t for t in cfg["channel_creations"] if now - t <= 10]

        if len(cfg["channel_creations"]) >= cfg["settings"]["channel_create_limit"]:
            self.add_risk(channel.guild.id, 0, 30, "Creación masiva de canales")

        self.update_guild(channel.guild.id, cfg)

        await self.auto_lockdown_check(channel.guild)
        await self.punish_high_risk_users(channel.guild)



# ============================================================
    # LOCKDOWN
    # ============================================================

    async def enable_lockdown(self, guild):
        cfg = self.ensure_guild_config(guild.id)
        if cfg["lockdown_active"]:
            return

        cfg["lockdown_active"] = True
        cfg["lockdown_state"] = {}

        for channel in guild.channels:
            try:
                ow = channel.overwrites_for(guild.default_role)
                cfg["lockdown_state"][str(channel.id)] = {
                    "send_messages": ow.send_messages,
                    "add_reactions": ow.add_reactions
                }

                await channel.set_permissions(
                    guild.default_role,
                    send_messages=False,
                    add_reactions=False
                )
            except:
                pass

        self.update_guild(guild.id, cfg)

    async def disable_lockdown(self, guild):
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["lockdown_active"]:
            return

        for channel in guild.channels:
            cid = str(channel.id)
            if cid in cfg["lockdown_state"]:
                try:
                    ow = cfg["lockdown_state"][cid]
                    await channel.set_permissions(
                        guild.default_role,
                        send_messages=ow["send_messages"],
                        add_reactions=ow["add_reactions"]
                    )
                except:
                    pass

        cfg["lockdown_active"] = False
        cfg["lockdown_state"] = {}
        self.update_guild(guild.id, cfg)

    async def auto_lockdown_check(self, guild):
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["enabled"]:
            return

        risk = self.get_global_risk(guild.id)

        if risk >= 200 and not cfg["lockdown_active"]:
            await self.enable_lockdown(guild)

        if risk < 80 and cfg["lockdown_active"]:
            await self.disable_lockdown(guild)

    # ============================================================
    # AUTO-BAN
    # ============================================================

    async def punish_high_risk_users(self, guild):
        cfg = self.ensure_guild_config(guild.id)
        to_reset = []

        for uid, data in cfg["user_risk"].items():
            if data["risk"] < 70:
                continue

            try:
                user = await self.bot.fetch_user(int(uid))
            except:
                continue

            reason = " | ".join(data["reasons"])

            await self.add_to_blacklist(guild, user, reason)

            try:
                await user.send(
                    embed=discord.Embed(
                        title="🚫 Has sido sancionado",
                        description=f"Servidor: **{guild.name}**\nRazón: {reason}",
                        color=discord.Color.red()
                    )
                )
            except:
                pass

            try:
                await guild.ban(user, reason=f"Anti-Raid: {reason}")
                await self.log_action(guild, user, "Ban automático", reason)
            except:
                await self.log_action(guild, user, "Ban fallido", reason)

            to_reset.append(uid)

        for uid in to_reset:
            cfg["user_risk"][uid]["risk"] = 0
            cfg["user_risk"][uid]["reasons"] = []

        self.update_guild(guild.id, cfg)

    # ============================================================
    # RESET / PURGA
    # ============================================================

    def reset_global_risk(self, guild_id: int):
        cfg = self.ensure_guild_config(guild_id)
        for uid in cfg["user_risk"]:
            cfg["user_risk"][uid]["risk"] = 0
            cfg["user_risk"][uid]["reasons"] = []
        self.update_guild(guild_id, cfg)

    def purge_suspicious(self, guild_id: int):
        cfg = self.ensure_guild_config(guild_id)
        to_delete = [uid for uid, data in cfg["user_risk"].items() if data["risk"] < 30]
        for uid in to_delete:
            del cfg["user_risk"][uid]
        self.update_guild(guild_id, cfg)

    def purge_antiraid(self, guild_id: int):
        cfg = self.ensure_guild_config(guild_id)
        cfg["join_times"] = []
        cfg["user_risk"] = {}
        cfg["channel_deletions"] = []
        cfg["channel_creations"] = []
        cfg["lockdown_active"] = False
        cfg["lockdown_state"] = {}
        self.update_guild(guild_id, cfg)

    # ============================================================
    # SELECT MENU PARA LOGS
    # ============================================================

    class LogChannelSelect(discord.ui.Select):
        def __init__(self, cog, guild):
            self.cog = cog
            self.guild = guild

            options = [
                discord.SelectOption(label=ch.name, value=str(ch.id))
                for ch in guild.text_channels
            ]

            super().__init__(
                placeholder="Selecciona un canal de logs",
                min_values=1,
                max_values=1,
                options=options
            )

        async def callback(self, interaction: discord.Interaction):
            channel_id = int(self.values[0])
            cfg = self.cog.ensure_guild_config(self.guild.id)
            cfg["log_channel"] = channel_id
            self.cog.update_guild(self.guild.id, cfg)

            await interaction.response.send_message(
                f"📘 Canal de logs configurado en <#{channel_id}>",
                ephemeral=True
            )

    # ============================================================
    # PANEL PRINCIPAL
    # ============================================================

    class Panel(discord.ui.View):
        def __init__(self, cog, guild):
            super().__init__(timeout=120)
            self.cog = cog
            self.guild = guild

            self.add_item(AntiRaid.LogChannelSelect(cog, guild))

        @discord.ui.button(label="Activar / Desactivar", style=discord.ButtonStyle.primary)
        async def toggle(self, interaction, button):
            cfg = self.cog.ensure_guild_config(self.guild.id)
            cfg["enabled"] = not cfg["enabled"]
            self.cog.update_guild(self.guild.id, cfg)
            await interaction.response.send_message(
                f"🛡 Anti-Raid ahora está **{'activado' if cfg['enabled'] else 'desactivado'}**",
                ephemeral=True
            )

        @discord.ui.button(label="Cambiar sensibilidad", style=discord.ButtonStyle.secondary)
        async def sensitivity(self, interaction, button):
            cfg = self.cog.ensure_guild_config(self.guild.id)
            order = ["low", "medium", "high"]
            new = order[(order.index(cfg["settings"]["sensitivity"]) + 1) % 3]
            cfg["settings"]["sensitivity"] = new
            self.cog.update_guild(self.guild.id, cfg)
            await interaction.response.send_message(f"📊 Sensibilidad cambiada a **{new}**", ephemeral=True)

        @discord.ui.button(label="Ver riesgo global", style=discord.ButtonStyle.secondary)
        async def risk(self, interaction, button):
            risk = self.cog.get_global_risk(self.guild.id)
            await interaction.response.send_message(f"📊 Riesgo global: **{risk}**", ephemeral=True)

        @discord.ui.button(label="Usuarios sospechosos", style=discord.ButtonStyle.secondary)
        async def suspicious(self, interaction, button):
            cfg = self.cog.ensure_guild_config(self.guild.id)
            suspects = [
                f"<@{uid}> — Riesgo: {data['risk']}"
                for uid, data in cfg["user_risk"].items()
                if data["risk"] >= 30
            ]

            if not suspects:
                await interaction.response.send_message("✨ No hay usuarios sospechosos.", ephemeral=True)
                return

            await interaction.response.send_message(
                "🚨 **Usuarios sospechosos:**\n" + "\n".join(suspects),
                ephemeral=True
            )

        @discord.ui.button(label="Activar Lockdown", style=discord.ButtonStyle.danger)
        async def lock_on(self, interaction, button):
            await self.cog.enable_lockdown(self.guild)
            await interaction.response.send_message("🔒 Lockdown activado.", ephemeral=True)

        @discord.ui.button(label="Desactivar Lockdown", style=discord.ButtonStyle.success)
        async def lock_off(self, interaction, button):
            await self.cog.disable_lockdown(self.guild)
            await interaction.response.send_message("🔓 Lockdown desactivado.", ephemeral=True)

        @discord.ui.button(label="Reset riesgo global", style=discord.ButtonStyle.danger)
        async def reset_risk(self, interaction, button):
            self.cog.reset_global_risk(self.guild.id)
            await interaction.response.send_message("🧹 Riesgo global reseteado.", ephemeral=True)

        @discord.ui.button(label="Purgar sospechosos", style=discord.ButtonStyle.secondary)
        async def purge_sus(self, interaction, button):
            self.cog.purge_suspicious(self.guild.id)
            await interaction.response.send_message("🗑 Usuarios sospechosos purgados.", ephemeral=True)

        @discord.ui.button(label="Reset total Anti-Raid", style=discord.ButtonStyle.danger)
        async def purge_all(self, interaction, button):
            self.cog.purge_antiraid(self.guild.id)
            await interaction.response.send_message("🧨 Anti-Raid reseteado completamente.", ephemeral=True)

        @discord.ui.button(label="⚙ Configuración", style=discord.ButtonStyle.primary)
        async def open_setup(self, interaction, button):
            await interaction.response.send_message(
                "⚙ Abriendo configuración...",
                view=AntiRaid.SetupPanel(self.cog, self.guild),
                ephemeral=True
            )

    # ============================================================
    # SUBPANEL DE CONFIGURACIÓN
    # ============================================================

    class SetupPanel(discord.ui.View):
        def __init__(self, cog, guild):
            super().__init__(timeout=120)
            self.cog = cog
            self.guild = guild

            self.add_item(AntiRaid.LogChannelSelect(cog, guild))

        @discord.ui.button(label="Ver configuración", style=discord.ButtonStyle.secondary)
        async def view_config(self, interaction, button):
            cfg = self.cog.ensure_guild_config(self.guild.id)

            embed = discord.Embed(
                title="⚙ Configuración Anti-Raid",
                color=discord.Color.blurple()
            )
            embed.add_field(name="Estado", value="Activado" if cfg["enabled"] else "Desactivado", inline=False)
            embed.add_field(name="Sensibilidad", value=cfg["settings"]["sensitivity"], inline=False)
            embed.add_field(name="Canal de logs", value=f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "No configurado", inline=False)
            embed.add_field(name="Join limit", value=cfg["settings"]["join_limit"], inline=True)
            embed.add_field(name="Spam mensajes", value=cfg["settings"]["spam_messages"], inline=True)
            embed.add_field(name="Riesgo global", value=str(self.cog.get_global_risk(self.guild.id)), inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        @discord.ui.button(label="Reset configuración", style=discord.ButtonStyle.danger)
        async def reset_config(self, interaction, button):
            cfg = self.cog.ensure_guild_config(self.guild.id)

            cfg["enabled"] = True
            cfg["log_channel"] = None
            cfg["settings"] = {
                "sensitivity": "medium",
                "join_limit": 5,
                "join_window": 10,
                "min_account_days": 7,
                "spam_window": 5,
                "spam_messages": 4,
                "channel_delete_limit": 3,
                "channel_create_limit": 3
            }

            self.cog.update_guild(self.guild.id, cfg)

            await interaction.response.send_message("🔄 Configuración restablecida.", ephemeral=True)

        @discord.ui.button(label="Volver", style=discord.ButtonStyle.primary)
        async def back(self, interaction, button):
            await interaction.response.send_message(
                "⬅ Volviendo al panel principal...",
                view=AntiRaid.Panel(self.cog, self.guild),
                ephemeral=True
            )

# ============================================================
# SETUP DEL COG
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiRaid(bot))

