import discord
from discord.ext import commands
from discord import app_commands
import json, os, time
from datetime import datetime, timezone

CONFIG_FILE = "antiraid_config.json"


# ============================================================
# CONFIG GLOBAL
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
        self.config = load_all_config()

    # ========================================================
    # CONFIG POR SERVIDOR
    # ========================================================

    def ensure_guild_config(self, guild_id: int):
        gid = str(guild_id)

        if gid not in self.config:
            self.config[gid] = {
                "enabled": True,
                "log_channel": None,

                "join_times": [],
                "user_risk": {},
                "channel_deletions": [],
                "channel_creations": [],

                "settings": {
                    "sensitivity": "normal",
                    "join_limit": 5,
                    "join_window": 10,
                    "min_account_days": 7,
                    "channel_delete_limit": 3,
                    "channel_create_limit": 3
                },

                "modules": {
                    "bots": True,
                    "joins": True,
                    "accounts": True,
                    "roles": True,
                    "channels": True,
                    "autoban": True,
                    "lockdown": True,
                    "logs": True,
                    "reputation": True
                }
            }
            save_all_config(self.config)

        return self.config[gid]

    def update_guild(self, guild_id: int, new_data: dict):
        self.config[str(guild_id)] = new_data
        save_all_config(self.config)

    # ========================================================
    # SISTEMA DE RIESGO
    # ========================================================

    def add_risk(self, guild_id: int, user_id: int, amount: int, reason: str):
        cfg = self.ensure_guild_config(guild_id)
        uid = str(user_id)

        if uid not in cfg["user_risk"]:
            cfg["user_risk"][uid] = {
                "risk": 0,
                "reasons": [],
                "messages": [],
                "history": []
            }

        cfg["user_risk"][uid]["risk"] += amount
        cfg["user_risk"][uid]["reasons"].append(reason)
        cfg["user_risk"][uid]["history"].append(
            {"time": int(time.time()), "reason": reason, "amount": amount}
        )

        if cfg["user_risk"][uid]["risk"] > 100:
            cfg["user_risk"][uid]["risk"] = 100

        self.update_guild(guild_id, cfg)

    def get_global_risk(self, guild_id: int):
        cfg = self.ensure_guild_config(guild_id)
        return sum(data["risk"] for data in cfg["user_risk"].values())

    # ========================================================
    # LOGS
    # ========================================================

    async def log_action(self, guild: discord.Guild, message: str):
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["modules"]["logs"]:
            return

        channel_id = cfg["log_channel"]
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="🛡 Anti‑Raid — Log",
            description=message,
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        try:
            await channel.send(embed=embed)
        except:
            pass

    # ========================================================
    # LOCKDOWN
    # ========================================================

    async def enable_lockdown(self, guild: discord.Guild):
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["modules"]["lockdown"]:
            return

        if cfg.get("lockdown_active", False):
            return

        cfg["lockdown_active"] = True
        cfg["lockdown_state"] = {}

        for channel in guild.text_channels:
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
        await self.log_action(guild, "🔒 Lockdown activado automáticamente por riesgo alto.")

    async def disable_lockdown(self, guild: discord.Guild):
        cfg = self.ensure_guild_config(guild.id)
        if not cfg.get("lockdown_active", False):
            return

        for channel in guild.text_channels:
            cid = str(channel.id)
            if cid in cfg.get("lockdown_state", {}):
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
        await self.log_action(guild, "🔓 Lockdown desactivado automáticamente por riesgo bajo.")

    async def auto_lockdown_check(self, guild: discord.Guild):
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["modules"]["lockdown"]:
            return

        risk = self.get_global_risk(guild.id)

        if risk >= 200 and not cfg.get("lockdown_active", False):
            await self.enable_lockdown(guild)
        elif risk < 80 and cfg.get("lockdown_active", False):
            await self.disable_lockdown(guild)

    # ========================================================
    # AUTO-BAN
    # ========================================================

    async def punish_high_risk_users(self, guild: discord.Guild):
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["modules"]["autoban"]:
            return

        to_reset = []

        for uid, data in cfg["user_risk"].items():
            if data["risk"] < 70:
                continue

            try:
                user = await self.bot.fetch_user(int(uid))
            except:
                continue

            member = guild.get_member(int(uid))
            if member and member.guild_permissions.administrator:
                continue

            reason = " | ".join(data["reasons"][-5:]) or "Actividad sospechosa"

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
                await guild.ban(user, reason=f"Anti‑Raid: {reason}")
                await self.log_action(guild, f"🚫 Usuario {user} (`{user.id}`) baneado por riesgo alto. Razón: {reason}")
            except:
                pass

            to_reset.append(uid)

        for uid in to_reset:
            cfg["user_risk"][uid]["risk"] = 0
            cfg["user_risk"][uid]["reasons"] = []

        self.update_guild(guild.id, cfg)

    # ========================================================
    # DETECCIÓN: ENTRADAS
    # ========================================================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["enabled"]:
            return

        now = time.time()
        cfg["join_times"].append(now)
        cfg["join_times"] = [t for t in cfg["join_times"] if now - t <= cfg["settings"]["join_window"]]

        # Cuentas nuevas (módulo C)
        if cfg["modules"]["accounts"]:
            age_days = (datetime.now(timezone.utc) - member.created_at).days
            if age_days < 1:
                self.add_risk(guild.id, member.id, 40, f"Cuenta muy nueva ({age_days} días)")
            elif age_days < 3:
                self.add_risk(guild.id, member.id, 25, f"Cuenta nueva ({age_days} días)")
            elif age_days < cfg["settings"]["min_account_days"]:
                self.add_risk(guild.id, member.id, 15, f"Cuenta relativamente nueva ({age_days} días)")

        # Bots falsos (módulo A)
        if cfg["modules"]["bots"]:
            name = member.name.lower()
            sus_words = ["bot", "raid", "spam", "mod", "admin"]
            if any(w in name for w in sus_words) and not member.bot:
                self.add_risk(guild.id, member.id, 20, "Nombre sospechoso tipo bot")

        # Joins rápidos (módulo B)
        if cfg["modules"]["joins"]:
            if len(cfg["join_times"]) >= cfg["settings"]["join_limit"]:
                self.add_risk(guild.id, member.id, 30, "Entradas masivas detectadas")

        self.update_guild(guild.id, cfg)
        await self.auto_lockdown_check(guild)
        await self.punish_high_risk_users(guild)

    # ========================================================
    # DETECCIÓN: CANALES
    # ========================================================

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["enabled"] or not cfg["modules"]["channels"]:
            return

        now = time.time()
        cfg["channel_deletions"].append(now)
        cfg["channel_deletions"] = [t for t in cfg["channel_deletions"] if now - t <= 10]

        if len(cfg["channel_deletions"]) >= cfg["settings"]["channel_delete_limit"]:
            self.add_risk(guild.id, 0, 40, "Borrado masivo de canales")
            await self.log_action(guild, "⚠️ Borrado masivo de canales detectado.")

        self.update_guild(guild.id, cfg)
        await self.auto_lockdown_check(guild)
        await self.punish_high_risk_users(guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["enabled"] or not cfg["modules"]["channels"]:
            return

        now = time.time()
        cfg["channel_creations"].append(now)
        cfg["channel_creations"] = [t for t in cfg["channel_creations"] if now - t <= 10]

        if len(cfg["channel_creations"]) >= cfg["settings"]["channel_create_limit"]:
            self.add_risk(guild.id, 0, 40, "Creación masiva de canales")
            await self.log_action(guild, "⚠️ Creación masiva de canales detectada.")

        self.update_guild(guild.id, cfg)
        await self.auto_lockdown_check(guild)
        await self.punish_high_risk_users(guild)

    # ========================================================
    # DETECCIÓN: ROLES (simple)
    # ========================================================

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild = role.guild
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["enabled"] or not cfg["modules"]["roles"]:
            return

        self.add_risk(guild.id, 0, 20, f"Rol eliminado: {role.name}")
        await self.log_action(guild, f"⚠️ Rol eliminado: {role.name}")
        await self.auto_lockdown_check(guild)
        await self.punish_high_risk_users(guild)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        guild = role.guild
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["enabled"] or not cfg["modules"]["roles"]:
            return

        self.add_risk(guild.id, 0, 15, f"Rol creado: {role.name}")
        await self.log_action(guild, f"⚠️ Rol creado: {role.name}")
        await self.auto_lockdown_check(guild)
        await self.punish_high_risk_users(guild)

    # ========================================================
    # DETECCIÓN: MENSAJES (solo reputación / base)
    # ========================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        cfg = self.ensure_guild_config(message.guild.id)
        if not cfg["enabled"]:
            return

        uid = str(message.author.id)
        now = time.time()

        if uid not in cfg["user_risk"]:
            cfg["user_risk"][uid] = {"risk": 0, "reasons": [], "messages": [], "history": []}

        cfg["user_risk"][uid]["messages"].append(now)
        cfg["user_risk"][uid]["messages"] = [
            t for t in cfg["user_risk"][uid]["messages"]
            if now - t <= 5
        ]

        self.update_guild(message.guild.id, cfg)

    # ========================================================
    # PANEL PRINCIPAL + SUBPANELES
    # ========================================================

    class ModuleSelect(discord.ui.Select):
        def __init__(self, cog, guild):
            self.cog = cog
            self.guild = guild

            options = [
                discord.SelectOption(label="Bots falsos", value="bots", description="Detecta nombres sospechosos tipo bot."),
                discord.SelectOption(label="Joins rápidos", value="joins", description="Detecta entradas masivas en poco tiempo."),
                discord.SelectOption(label="Cuentas nuevas", value="accounts", description="Riesgo según edad de la cuenta."),
                discord.SelectOption(label="Roles", value="roles", description="Detecta cambios masivos en roles."),
                discord.SelectOption(label="Canales", value="channels", description="Detecta cambios masivos en canales."),
                discord.SelectOption(label="Auto‑ban", value="autoban", description="Banea usuarios con riesgo alto."),
                discord.SelectOption(label="Lockdown", value="lockdown", description="Bloquea el servidor si hay riesgo alto."),
                discord.SelectOption(label="Logs", value="logs", description="Registra acciones sospechosas."),
                discord.SelectOption(label="Reputación", value="reputation", description="Historial de riesgo por usuario.")
            ]

            super().__init__(
                placeholder="Selecciona un módulo para configurar",
                min_values=1,
                max_values=1,
                options=options,
                custom_id="antiraid_module_select"
            )

        async def callback(self, interaction: discord.Interaction):
            module_key = self.values[0]
            view = AntiRaid.ModuleConfigView(self.cog, self.guild, module_key)
            embed = view.build_embed()
            await interaction.response.edit_message(embed=embed, view=view)

    class ModuleConfigView(discord.ui.View):
        def __init__(self, cog, guild, module_key: str):
            super().__init__(timeout=120)
            self.cog = cog
            self.guild = guild
            self.module_key = module_key

            self.add_item(AntiRaid.ModuleSelect(cog, guild))

        def build_embed(self):
            cfg = self.cog.ensure_guild_config(self.guild.id)
            modules = cfg["modules"]

            names = {
                "bots": "Bots falsos",
                "joins": "Joins rápidos",
                "accounts": "Cuentas nuevas",
                "roles": "Roles",
                "channels": "Canales",
                "autoban": "Auto‑ban",
                "lockdown": "Lockdown",
                "logs": "Logs",
                "reputation": "Reputación"
            }

            descriptions = {
                "bots": "Detecta usuarios con nombres sospechosos tipo bot y les asigna riesgo.",
                "joins": "Detecta entradas masivas en poco tiempo y aumenta el riesgo global.",
                "accounts": "Evalúa la edad de la cuenta y asigna riesgo a cuentas nuevas.",
                "roles": "Registra creación y borrado de roles como actividad potencialmente peligrosa.",
                "channels": "Detecta creación y borrado masivo de canales.",
                "autoban": "Banea automáticamente usuarios con riesgo muy alto.",
                "lockdown": "Bloquea el servidor si el riesgo global es demasiado alto.",
                "logs": "Envía registros de seguridad al canal configurado.",
                "reputation": "Mantiene historial de riesgo y acciones sospechosas por usuario."
            }

            name = names.get(self.module_key, self.module_key)
            desc = descriptions.get(self.module_key, "Módulo de seguridad.")

            status = "🟢 Activado" if modules.get(self.module_key, False) else "🔴 Desactivado"

            embed = discord.Embed(
                title=f"🛡 Módulo: {name}",
                description=desc,
                color=discord.Color.green() if modules.get(self.module_key, False) else discord.Color.red()
            )
            embed.add_field(name="Estado", value=status, inline=False)

            if self.module_key == "accounts":
                cfg = self.cog.ensure_guild_config(self.guild.id)
                embed.add_field(
                    name="Edad mínima de cuenta",
                    value=f"{cfg['settings']['min_account_days']} días",
                    inline=False
                )

            if self.module_key == "joins":
                cfg = self.cog.ensure_guild_config(self.guild.id)
                embed.add_field(
                    name="Join limit / ventana",
                    value=f"{cfg['settings']['join_limit']} usuarios / {cfg['settings']['join_window']}s",
                    inline=False
                )

            if self.module_key == "channels":
                cfg = self.cog.ensure_guild_config(self.guild.id)
                embed.add_field(
                    name="Límites de canales",
                    value=f"Borrado: {cfg['settings']['channel_delete_limit']} | Creación: {cfg['settings']['channel_create_limit']}",
                    inline=False
                )

            return embed

        @discord.ui.button(
            label="Activar / Desactivar módulo",
            style=discord.ButtonStyle.primary,
            emoji="⚙",
            custom_id="antiraid_toggle_module_btn"
        )
        async def toggle_module(self, interaction: discord.Interaction, button: discord.ui.Button):
            cfg = self.cog.ensure_guild_config(self.guild.id)
            current = cfg["modules"].get(self.module_key, True)
            cfg["modules"][self.module_key] = not current
            self.cog.update_guild(self.guild.id, cfg)

            embed = self.build_embed()
            await interaction.response.edit_message(embed=embed, view=self)

        @discord.ui.button(
            label="Volver al panel",
            style=discord.ButtonStyle.secondary,
            emoji="⬅",
            custom_id="antiraid_back_panel_btn"
        )
        async def back_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
            view = AntiRaid.MainPanel(self.cog, self.guild)
            embed = view.build_main_embed()
            await interaction.response.edit_message(embed=embed, view=view)

    class MainPanel(discord.ui.View):
        def __init__(self, cog, guild):
            super().__init__(timeout=120)
            self.cog = cog
            self.guild = guild
            self.add_item(AntiRaid.ModuleSelect(cog, guild))

        def build_main_embed(self):
            cfg = self.cog.ensure_guild_config(self.guild.id)
            modules = cfg["modules"]

            def status(key):
                return "🟢" if modules.get(key, False) else "🔴"

            desc = (
                f"{status('bots')} **Bots falsos** — Detecta nombres sospechosos.\n"
                f"{status('joins')} **Joins rápidos** — Detecta entradas masivas.\n"
                f"{status('accounts')} **Cuentas nuevas** — Riesgo según edad.\n"
                f"{status('roles')} **Roles** — Cambios en roles.\n"
                f"{status('channels')} **Canales** — Cambios en canales.\n"
                f"{status('autoban')} **Auto‑ban** — Banea usuarios peligrosos.\n"
                f"{status('lockdown')} **Lockdown** — Bloquea el servidor por riesgo.\n"
                f"{status('logs')} **Logs** — Registra acciones sospechosas.\n"
                f"{status('reputation')} **Reputación** — Historial de riesgo.\n"
            )

            embed = discord.Embed(
                title="🛡 Anti‑Raid Avanzado",
                description="Selecciona un módulo en el menú para configurarlo.\n\n" + desc,
                color=discord.Color.red()
            )

            return embed

        @discord.ui.button(
            label="Reset total",
            style=discord.ButtonStyle.danger,
            emoji="🧨",
            custom_id="antiraid_reset_all_btn"
        )
        async def reset_all(self, interaction: discord.Interaction, button: discord.ui.Button):
            cfg = self.cog.ensure_guild_config(self.guild.id)

            cfg["enabled"] = True
            cfg["log_channel"] = None
            cfg["join_times"] = []
            cfg["user_risk"] = {}
            cfg["channel_deletions"] = []
            cfg["channel_creations"] = []
            cfg["settings"] = {
                "sensitivity": "normal",
                "join_limit": 5,
                "join_window": 10,
                "min_account_days": 7,
                "channel_delete_limit": 3,
                "channel_create_limit": 3
            }
            cfg["modules"] = {
                "bots": True,
                "joins": True,
                "accounts": True,
                "roles": True,
                "channels": True,
                "autoban": True,
                "lockdown": True,
                "logs": True,
                "reputation": True
            }

            self.cog.update_guild(self.guild.id, cfg)

            embed = self.build_main_embed()
            await interaction.response.edit_message(
                content="🧨 Anti‑Raid reseteado completamente.",
                embed=embed,
                view=self
            )

    # ========================================================
    # COMANDO PRINCIPAL
    # ========================================================

    @app_commands.command(
        name="antiraid",
        description="Abre el panel Anti‑Raid avanzado."
    )
    async def antiraid_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message(
                "❌ Este comando solo puede usarse en servidores.",
                ephemeral=True
            )

        self.ensure_guild_config(guild.id)
        view = AntiRaid.MainPanel(self, guild)
        embed = view.build_main_embed()

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )


# ============================================================
# SETUP DEL COG
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiRaid(bot)) 
