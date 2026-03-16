import discord
from discord.ext import commands
from discord import app_commands
import json, os, time
from datetime import datetime, timezone, timedelta

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
# COG ANTI‑RAID AVANZADO (SIN PANEL)
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
                "nivel": "medio",
                "log_channel": None,
                "accion": "ban",
                "sensibilidad": "media",

                "join_times": [],
                "user_risk": {},
                "channel_deletions": [],
                "channel_creations": [],

                "settings": {
                    "join_limit": 5,
                    "join_window": 10,
                    "min_account_days": 3,
                    "channel_delete_limit": 3,
                    "channel_create_limit": 3
                },

                "lockdown_active": False,
                "lockdown_state": {}
            }
            save_all_config(self.config)

        return self.config[gid]

    def update_guild(self, guild_id: int, new_data: dict):
        self.config[str(guild_id)] = new_data
        save_all_config(self.config)

    # ========================================================
    # LOGS
    # ========================================================

    async def log_action(self, guild: discord.Guild, message: str):
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["log_channel"]:
            return

        channel = guild.get_channel(cfg["log_channel"])
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
    # SISTEMA DE RIESGO
    # ========================================================

    def add_risk(self, guild_id: int, user_id: int, amount: int, reason: str):
        cfg = self.ensure_guild_config(guild_id)
        uid = str(user_id)

        # Sensibilidad
        sens = cfg["sensibilidad"]
        if sens == "baja":
            amount = int(amount * 0.6)
        elif sens == "alta":
            amount = int(amount * 1.4)

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
    # LOCKDOWN
    # ========================================================

    async def enable_lockdown(self, guild: discord.Guild):
        cfg = self.ensure_guild_config(guild.id)
        if cfg["lockdown_active"]:
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
        if not cfg["lockdown_active"]:
            return

        for channel in guild.text_channels:
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
        await self.log_action(guild, "🔓 Lockdown desactivado automáticamente por riesgo bajo.")

    async def auto_lockdown_check(self, guild: discord.Guild):
        cfg = self.ensure_guild_config(guild.id)
        risk = self.get_global_risk(guild.id)

        if risk >= 200 and not cfg["lockdown_active"]:
            await self.enable_lockdown(guild)
        elif risk < 80 and cfg["lockdown_active"]:
            await self.disable_lockdown(guild)

    # ========================================================
    # AUTO‑SANCIÓN
    # ========================================================

    async def punish_high_risk_users(self, guild: discord.Guild):
        cfg = self.ensure_guild_config(guild.id)
        action = cfg["accion"]

        for uid, data in cfg["user_risk"].items():
            if data["risk"] < 70:
                continue

            user = guild.get_member(int(uid))
            if not user:
                continue

            if user.guild_permissions.administrator:
                continue

            reason = " | ".join(data["reasons"][-5:]) or "Actividad sospechosa"

            try:
                await user.send(
                    embed=discord.Embed(
                        title="🚫 Acción disciplinaria",
                        description=f"Servidor: **{guild.name}**\nRazón: {reason}",
                        color=discord.Color.red()
                    )
                )
            except:
                pass

            try:
                if action == "ban":
                    await guild.ban(user, reason=f"Anti‑Raid: {reason}")
                elif action == "kick":
                    await guild.kick(user, reason=f"Anti‑Raid: {reason}")
                elif action == "mute":
                    await user.edit(timeout=discord.utils.utcnow() + timedelta(minutes=30))
            except:
                pass

            await self.log_action(guild, f"🚫 Usuario {user} sancionado ({action}). Razón: {reason}")

            data["risk"] = 0
            data["reasons"] = []

        self.update_guild(guild.id, cfg)

    # ========================================================
    # DETECCIONES
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

        # Cuentas nuevas
        age_days = (datetime.now(timezone.utc) - member.created_at).days
        if age_days < 1:
            self.add_risk(guild.id, member.id, 40, f"Cuenta muy nueva ({age_days} días)")
        elif age_days < 3:
            self.add_risk(guild.id, member.id, 25, f"Cuenta nueva ({age_days} días)")
        elif age_days < cfg["settings"]["min_account_days"]:
            self.add_risk(guild.id, member.id, 15, f"Cuenta relativamente nueva ({age_days} días)")

        # Joins masivos
        if len(cfg["join_times"]) >= cfg["settings"]["join_limit"]:
            self.add_risk(guild.id, member.id, 30, "Entradas masivas detectadas")

        self.update_guild(guild.id, cfg)
        await_check(guild)
        await self.punish_high_risk_users(guild)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["enabled"]:
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
    async def on_guild_channel_create(self, channel):
        guild = channel.guild
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["enabled"]:
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

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["enabled"]:
            return

        self.add_risk(guild.id, 0, 20, f"Rol eliminado: {role.name}")
        await self.log_action(guild, f"⚠️ Rol eliminado: {role.name}")
        await self.auto_lockdown_check(guild)
        await self.punish_high_risk_users(guild)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        guild = role.guild
        cfg = self.ensure_guild_config(guild.id)
        if not cfg["enabled"]:
            return

        self.add_risk(guild.id, 0, 15, f"Rol creado: {role.name}")
        await self.log_action(guild, f"⚠️ Rol creado: {role.name}")
        await self.auto_lockdown_check(guild)
        await self.punish_high_risk_users(guild)

    # ========================================================
    # COMANDO ÚNICO /antiraid
    # ========================================================

    @app_commands.command(
        name="antiraid",
        description="Configura el sistema Anti‑Raid avanzado."
    )
    @app_commands.describe(
        nivel="Nivel de seguridad: bajo, medio o alto",
        log_channel="Canal donde se enviarán los logs",
        estado="Activar o desactivar el Anti‑Raid",
        accion="Acción al detectar riesgo alto",
        sensibilidad="Ajusta la agresividad del sistema"
    )
    @app_commands.choices(
        nivel=[
            app_commands.Choice(name="Bajo", value="bajo"),
            app_commands.Choice(name="Medio", value="medio"),
            app_commands.Choice(name="Alto", value="alto")
        ],
        estado=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ],
        accion=[
            app_commands.Choice(name="Banear", value="ban"),
            app_commands.Choice(name="Expulsar", value="kick"),
            app_commands.Choice(name="Mutear", value="mute"),
            app_commands.Choice(name="Nada", value="nada")
        ],
        sensibilidad=[
            app_commands.Choice(name="Baja", value="baja"),
            app_commands.Choice(name="Media", value="media"),
            app_commands.Choice(name="Alta", value="alta")
        ]
    )
    async def antiraid_cmd(
        self,
        interaction: discord.Interaction,
        nivel: str = None,
        log_channel: discord.TextChannel = None,
        estado: str = None,
        accion: str = None,
        sensibilidad: str = None
    ):
        guild = interaction.guild
        cfg = self.ensure_guild_config(guild.id)

        # Nivel
        if nivel:
            cfg["nivel"] = nivel

            if nivel == "bajo":
                cfg["settings"]["join_limit"] = 10
                cfg["settings"]["min_account_days"] = 1
                cfg["settings"]["channel_delete_limit"] = 5
                cfg["settings"]["channel_create_limit"] = 5

            elif nivel == "medio":
                cfg["settings"]["join_limit"] = 5
                cfg["settings"]["min_account_days"] = 3
                cfg["settings"]["channel_delete_limit"] = 3
                cfg["settings"]["channel_create_limit"] = 3

            elif nivel == "alto":
                cfg["settings"]["join_limit"] = 3
                cfg["settings"]["min_account_days"] = 7
                cfg["settings"]["channel_delete_limit"] = 2
                cfg["settings"]["channel_create_limit"] = 2

        # Canal de logs
        if log_channel:
            cfg["log_channel"] = log_channel.id

        # Activar / desactivar
        if estado:
            cfg["enabled"] = (estado == "activar")

        # Acción
        if accion:
            cfg["accion"] = accion

        # Sensibilidad
        if sensibilidad:
            cfg["sensibilidad"] = sensibilidad

        self.update_guild(guild.id, cfg)

        embed = discord.Embed(
            title="🛡 Configuración Anti‑Raid actualizada",
            color=discord.Color.orange()
        )

        embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)
        embed.add_field(name="Nivel", value=cfg["nivel"].capitalize(), inline=True)
        embed.add_field(name="Acción", value=cfg["accion"].capitalize(), inline=True)
        embed.add_field(name="Sensibilidad", value=cfg["sensibilidad"].capitalize(), inline=True)
        embed.add_field(name="Canal de logs", value=f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "No configurado", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ========================================================
    # COMANDO /antiraid_config
    # ========================================================

    @app_commands.command(
        name="antiraid_config",
        description="Muestra la configuración actual del Anti‑Raid."
    )
    async def antiraid_config(self, interaction: discord.Interaction):
        guild = interaction.guild
        cfg = self.ensure_guild_config(guild.id)

        embed = discord.Embed(
            title="🛡 Configuración actual del Anti‑Raid",
            color=discord.Color.blue()
        )

        embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)
        embed.add_field(name="Nivel", value=cfg["nivel"].capitalize(), inline=True)
        embed.add_field(name="Acción", value=cfg["accion"].capitalize(), inline=True)
        embed.add_field(name="Sensibilidad", value=cfg["sensibilidad"].capitalize(), inline=True)
        embed.add_field(name="Canal de logs", value=f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "No configurado", inline=False)

        embed.add_field(name="Join limit", value=cfg["settings"]["join_limit"], inline=True)
        embed.add_field(name="Min account days", value=cfg["settings"]["min_account_days"], inline=True)
        embed.add_field(
            name="Límites de canales",
            value=f"{cfg['settings']['channel_delete_limit']} / {cfg['settings']['channel_create_limit']}",
            inline=True
        )

        embed.add_field(name="Lockdown", value="🟢 Activo" if cfg["lockdown_active"] else "🔴 Inactivo", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================================
# SETUP DEL COG
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiRaid(bot)) 
