import discord
from discord.ext import commands
from discord import app_commands
import json, os, time
from datetime import datetime, timezone

CONFIG_FILE = "antiraid_config.json"
BLACKLIST_FILE = "antiraid_blacklist.json"


# ============================================================
# CONFIG POR SERVIDOR (JSON)
# ============================================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f, indent=4)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_guild_config(guild_id: int):
    data = load_config()
    gid = str(guild_id)

    if gid not in data:
        data[gid] = {
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
        save_config(data)

    return data[gid]

def update_guild_config(guild_id: int, new_data: dict):
    data = load_config()
    data[str(guild_id)] = new_data
    save_config(data)


# ============================================================
# COG ANTI-RAID COMPLETO
# ============================================================

class AntiRaid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================================================
    # SISTEMA DE RIESGO
    # ============================================================

    def add_risk(self, guild_id: int, user_id: int, amount: int, reason: str):
        config = get_guild_config(guild_id)
        uid = str(user_id)

        if uid not in config["user_risk"]:
            config["user_risk"][uid] = {"risk": 0, "reasons": [], "messages": []}

        config["user_risk"][uid]["risk"] += amount
        config["user_risk"][uid]["reasons"].append(reason)

        if config["user_risk"][uid]["risk"] > 100:
            config["user_risk"][uid]["risk"] = 100

        update_guild_config(guild_id, config)

    def get_global_risk(self, guild_id: int):
        config = get_guild_config(guild_id)
        return sum(data["risk"] for data in config["user_risk"].values())

    # ============================================================
    # DETECCIÓN: ENTRADAS
    # ============================================================

    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = get_guild_config(member.guild.id)
        if not config["enabled"]:
            return

        now = time.time()
        config["join_times"].append(now)
        config["join_times"] = [t for t in config["join_times"] if now - t <= config["settings"]["join_window"]]

        # Cuenta nueva
        age = (datetime.now(timezone.utc) - member.created_at).days
        if age < config["settings"]["min_account_days"]:
            self.add_risk(member.guild.id, member.id, 25, f"Cuenta nueva ({age} días)")

        # Nombre sospechoso
        if any(x in member.name.lower() for x in ["bot", "raid", "spam", "xxx", "123"]):
            self.add_risk(member.guild.id, member.id, 15, "Nombre sospechoso")

        # Entradas masivas
        if len(config["join_times"]) >= config["settings"]["join_limit"]:
            self.add_risk(member.guild.id, member.id, 40, "Entradas masivas detectadas")

        update_guild_config(member.guild.id, config)

        await self.auto_lockdown_check(member.guild)
        await self.punish_high_risk_users(member.guild)

    # ============================================================
    # DETECCIÓN: MENSAJES
    # ============================================================

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        config = get_guild_config(message.guild.id)
        if not config["enabled"]:
            return

        uid = str(message.author.id)
        now = time.time()

        if uid not in config["user_risk"]:
            config["user_risk"][uid] = {"risk": 0, "reasons": [], "messages": []}

        config["user_risk"][uid]["messages"].append(now)
        config["user_risk"][uid]["messages"] = [
            t for t in config["user_risk"][uid]["messages"]
            if now - t <= config["settings"]["spam_window"]
        ]

        if len(config["user_risk"][uid]["messages"]) >= config["settings"]["spam_messages"]:
            self.add_risk(message.guild.id, message.author.id, 20, "Spam coordinado detectado")

        update_guild_config(message.guild.id, config)

        await self.auto_lockdown_check(message.guild)
        await self.punish_high_risk_users(message.guild)

    # ============================================================
    # DETECCIÓN: CANALES
    # ============================================================

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        config = get_guild_config(channel.guild.id)
        now = time.time()

        config["channel_deletions"].append(now)
        config["channel_deletions"] = [t for t in config["channel_deletions"] if now - t <= 10]

        if len(config["channel_deletions"]) >= config["settings"]["channel_delete_limit"]:
            self.add_risk(channel.guild.id, 0, 30, "Borrado masivo de canales")

        update_guild_config(channel.guild.id, config)

        await self.auto_lockdown_check(channel.guild)
        await self.punish_high_risk_users(channel.guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        config = get_guild_config(channel.guild.id)
        now = time.time()

        config["channel_creations"].append(now)
        config["channel_creations"] = [t for t in config["channel_creations"] if now - t <= 10]

        if len(config["channel_creations"]) >= config["settings"]["channel_create_limit"]:
            self.add_risk(channel.guild.id, 0, 30, "Creación masiva de canales")

        update_guild_config(channel.guild.id, config)

        await self.auto_lockdown_check(channel.guild)
        await self.punish_high_risk_users(channel.guild)

    # ============================================================
    # LOGS PRO
    # ============================================================

    async def send_log(self, guild, embed):
        config = get_guild_config(guild.id)
        log_id = config.get("log_channel")

        if log_id:
            ch = guild.get_channel(log_id)
            if ch:
                try:
                    await ch.send(embed=embed)
                    return
                except:
                    pass

        print(f"[AntiRaid LOG] {guild.name}: {embed.title}")

    async def log_action(self, guild, user, action, reason):
        embed = discord.Embed(
            title="🚨 Acción Anti-Raid",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Usuario", value=f"{user} (`{user.id}`)", inline=False)
        embed.add_field(name="Acción", value=action, inline=False)
        embed.add_field(name="Razón", value=reason, inline=False)
        await self.send_log(guild, embed)

    # ============================================================
    # BLACKLIST
    # ============================================================

    def load_blacklist(self):
        if not os.path.exists(BLACKLIST_FILE):
            with open(BLACKLIST_FILE, "w") as f:
                json.dump({}, f, indent=4)
        with open(BLACKLIST_FILE, "r") as f:
            return json.load(f)

    def save_blacklist(self, data):
        with open(BLACKLIST_FILE, "w") as f:
            json.dump(data, f, indent=4)

    async def add_to_blacklist(self, guild, user, reason):
        data = self.load_blacklist()
        uid = str(user.id)

        if uid not in data:
            data[uid] = {
                "razon": reason,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "guild": guild.id
            }
            self.save_blacklist(data)

    # ============================================================
    # LOCKDOWN
    # ============================================================

    async def enable_lockdown(self, guild):
        config = get_guild_config(guild.id)
        if config["lockdown_active"]:
            return

        config["lockdown_active"] = True
        config["lockdown_state"] = {}

        for channel in guild.channels:
            try:
                ow = channel.overwrites_for(guild.default_role)
                config["lockdown_state"][str(channel.id)] = {
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

        update_guild_config(guild.id, config)

    async def disable_lockdown(self, guild):
        config = get_guild_config(guild.id)
        if not config["lockdown_active"]:
            return

        for channel in guild.channels:
            cid = str(channel.id)
            if cid in config["lockdown_state"]:
                try:
                    ow = config["lockdown_state"][cid]
                    await channel.set_permissions(
                        guild.default_role,
                        send_messages=ow["send_messages"],
                        add_reactions=ow["add_reactions"]
                    )
                except:
                    pass

        config["lockdown_active"] = False
        config["lockdown_state"] = {}
        update_guild_config(guild.id, config)

    async def auto_lockdown_check(self, guild):
        config = get_guild_config(guild.id)
        if not config["enabled"]:
            return

        risk = self.get_global_risk(guild.id)

        if risk >= 200 and not config["lockdown_active"]:
            await self.enable_lockdown(guild)

        if risk < 80 and config["lockdown_active"]:
            await self.disable_lockdown(guild)

    # ============================================================
    # AUTO-BAN
    # ============================================================

    async def punish_high_risk_users(self, guild):
        config = get_guild_config(guild.id)
        to_reset = []

        for uid, data in config["user_risk"].items():
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
            config["user_risk"][uid]["risk"] = 0
            config["user_risk"][uid]["reasons"] = []

        update_guild_config(guild.id, config)

    # ============================================================
    # RESET / PURGA
    # ============================================================

    def reset_global_risk(self, guild_id: int):
        config = get_guild_config(guild_id)
        for uid in config["user_risk"]:
            config["user_risk"][uid]["risk"] = 0
            config["user_risk"][uid]["reasons"] = []
        update_guild_config(guild_id, config)

    def purge_suspicious(self, guild_id: int):
        config = get_guild_config(guild_id)
        to_delete = [uid for uid, data in config["user_risk"].items() if data["risk"] < 30]
        for uid in to_delete:
            del config["user_risk"][uid]
        update_guild_config(guild_id, config)

    def purge_antiraid(self, guild_id: int):
        config = get_guild_config(guild_id)
        config["join_times"] = []
        config["user_risk"] = {}
        config["channel_deletions"] = []
        config["channel_creations"] = []
        config["lockdown_active"] = False
        config["lockdown_state"] = {}
        update_guild_config(guild_id, config)

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
            config = get_guild_config(self.guild.id)
            config["log_channel"] = channel_id
            update_guild_config(self.guild.id, config)

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
            config = get_guild_config(self.guild.id)
            config["enabled"] = not config["enabled"]
            update_guild_config(self.guild.id, config)
            await interaction.response.send_message(
                f"🛡 Anti-Raid ahora está **{'activado' if config['enabled'] else 'desactivado'}**",
                ephemeral=True
            )

        @discord.ui.button(label="Cambiar sensibilidad", style=discord.ButtonStyle.secondary)
        async def sensitivity(self, interaction, button):
            config = get_guild_config(self.guild.id)
            order = ["low", "medium", "high"]
            new = order[(order.index(config["settings"]["sensitivity"]) + 1) % 3]
            config["settings"]["sensitivity"] = new
            update_guild_config(self.guild.id, config)
            await interaction.response.send_message(f"📊 Sensibilidad cambiada a **{new}**", ephemeral=True)

        @discord.ui.button(label="Ver riesgo global", style=discord.ButtonStyle.secondary)
        async def risk(self, interaction, button):
            risk = self.cog.get_global_risk(self.guild.id)
            await interaction.response.send_message(f"📊 Riesgo global: **{risk}**", ephemeral=True)

        @discord.ui.button(label="Usuarios sospechosos", style=discord.ButtonStyle.secondary)
        async def suspicious(self, interaction, button):
            config = get_guild_config(self.guild.id)
            suspects = [
                f"<@{uid}> — Riesgo: {data['risk']}"
                for uid, data in config["user_risk"].items()
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

        # ----------------------------
        # BOTÓN: CONFIGURACIÓN (ABRE SUBPANEL)
        # ----------------------------
        @discord.ui.button(label="⚙ Configuración", style=discord.ButtonStyle.primary)
        async def open_setup(self, interaction, button):
            await interaction.response.send_message(
                "⚙ Abriendo configuración...",
                view=AntiRaid.SetupPanel(self.cog, self.guild),
                ephemeral=True
            )

    # ============================================================
    # SUBPANEL DE CONFIGURACIÓN (SETUP FINAL)
    # ============================================================

    class SetupPanel(discord.ui.View):
        def __init__(self, cog, guild):
            super().__init__(timeout=120)
            self.cog = cog
            self.guild = guild

            # Select menu para elegir canal de logs
            self.add_item(AntiRaid.LogChannelSelect(cog, guild))

        # ----------------------------
        # VER CONFIGURACIÓN
        # ----------------------------
        @discord.ui.button(label="Ver configuración", style=discord.ButtonStyle.secondary)
        async def view_config(self, interaction, button):
            config = get_guild_config(self.guild.id)

            embed = discord.Embed(
                title="⚙ Configuración Anti-Raid",
                color=discord.Color.blurple()
            )
            embed.add_field(name="Estado", value="Activado" if config["enabled"] else "Desactivado", inline=False)
            embed.add_field(name="Sensibilidad", value=config["settings"]["sensitivity"], inline=False)
            embed.add_field(name="Canal de logs", value=f"<#{config['log_channel']}>" if config["log_channel"] else "No configurado", inline=False)
            embed.add_field(name="Join limit", value=config["settings"]["join_limit"], inline=True)
            embed.add_field(name="Spam mensajes", value=config["settings"]["spam_messages"], inline=True)
            embed.add_field(name="Riesgo global", value=str(self.cog.get_global_risk(self.guild.id)), inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        # ----------------------------
        # RESET CONFIGURACIÓN
        # ----------------------------
        @discord.ui.button(label="Reset configuración", style=discord.ButtonStyle.danger)
        async def reset_config(self, interaction, button):
            config = get_guild_config(self.guild.id)

            config["enabled"] = True
            config["log_channel"] = None
            config["settings"] = {
                "sensitivity": "medium",
                "join_limit": 5,
                "join_window": 10,
                "min_account_days": 7,
                "spam_window": 5,
                "spam_messages": 4,
                "channel_delete_limit": 3,
                "channel_create_limit": 3
            }

            update_guild_config(self.guild.id, config)

            await interaction.response.send_message("🔄 Configuración restablecida.", ephemeral=True)

        # ----------------------------
        # VOLVER AL PANEL PRINCIPAL
        # ----------------------------
        @discord.ui.button(label="Volver", style=discord.ButtonStyle.primary)
        async def back(self, interaction, button):
            await interaction.response.send_message(
                "⬅ Volviendo al panel principal...",
                view=AntiRaid.Panel(self.cog, self.guild),
                ephemeral=True
            )

# ============================================================
# SETUP DEL COG (FINAL DEL ARCHIVO)
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiRaid(bot))
        
