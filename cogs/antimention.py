import discord
from discord.ext import commands
from discord import app_commands
import json, os, time
from datetime import timedelta

CONFIG_FILE = "antimention.json"

# ============================================================
# CONFIG SEGURO (PERSISTENTE)
# ============================================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_config(data):
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, CONFIG_FILE)


# ============================================================
# COG ANTI‑MENTION
# ============================================================

class AntiMention(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.cooldowns = {}

    # --------------------------------------------------------
    # CONFIG POR SERVIDOR
    # --------------------------------------------------------

    def ensure_guild(self, guild_id: int):
        gid = str(guild_id)

        if gid not in self.config:
            self.config[gid] = {
                "enabled": False,
                "accion": "warn",
                "mute_time": 600,
                "cooldown": 3,
                "logs": None,

                "limit_users": 3,
                "limit_roles": 3,
                "limit_everyone": 1,

                "blocked_users": [],
                "blocked_roles": [],

                "whitelist_users": [],
                "whitelist_roles": [],
                "whitelist_channels": []
            }
            save_config(self.config)

        return self.config[gid]

    # ============================================================
    # COMANDO PRINCIPAL /antimention
    # ============================================================

    @app_commands.command(name="antimention", description="Configura el Anti‑Mention.")
    @app_commands.describe(
        opcion="Qué quieres configurar",
        valor="Valor a aplicar (si aplica)",
        canal="Canal para logs (si aplica)"
    )
    @app_commands.choices(
        opcion=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar"),
            app_commands.Choice(name="Acción", value="accion"),
            app_commands.Choice(name="Límite usuarios", value="limit_users"),
            app_commands.Choice(name="Límite roles", value="limit_roles"),
            app_commands.Choice(name="Límite everyone", value="limit_everyone"),
            app_commands.Choice(name="Cooldown", value="cooldown"),
            app_commands.Choice(name="Logs", value="logs")
        ]
    )
    async def antimention_cmd(
        self,
        interaction: discord.Interaction,
        opcion: app_commands.Choice[str],
        valor: int = None,
        canal: discord.TextChannel = None
    ):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        op = opcion.value

        # Activar / desactivar
        if op == "activar":
            cfg["enabled"] = True

        elif op == "desactivar":
            cfg["enabled"] = False

        # Acción
        elif op == "accion":
            if valor is None:
                return await interaction.response.send_message("Debes indicar: 1=warn, 2=mute, 3=kick, 4=ban", ephemeral=True)

            acciones = {1: "warn", 2: "mute", 3: "kick", 4: "ban"}
            if valor not in acciones:
                return await interaction.response.send_message("Valor inválido.", ephemeral=True)

            cfg["accion"] = acciones[valor]

        # Límites
        elif op in ["limit_users", "limit_roles", "limit_everyone"]:
            if valor is None or valor < 1:
                return await interaction.response.send_message("Debes indicar un número mayor a 0.", ephemeral=True)

            cfg[op] = valor

        # Cooldown
        elif op == "cooldown":
            if valor is None or valor < 0:
                return await interaction.response.send_message("Debes indicar un número válido.", ephemeral=True)
            cfg["cooldown"] = valor

        # Logs
        elif op == "logs":
            if canal is None:
                return await interaction.response.send_message("Debes seleccionar un canal.", ephemeral=True)
            cfg["logs"] = canal.id

        save_config(self.config)

        embed = discord.Embed(
            title="🛡 Configuración Anti‑Mention actualizada",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Opción", value=op, inline=False)
        embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ============================================================
    # WHITELIST
    # ============================================================

    @app_commands.command(name="antimention_whitelist", description="Gestiona la whitelist del Anti‑Mention.")
    @app_commands.describe(
        tipo="Tipo de whitelist",
        objetivo="Usuario/Rol/Canal a añadir o quitar"
    )
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="Usuario", value="user"),
            app_commands.Choice(name="Rol", value="role"),
            app_commands.Choice(name="Canal", value="channel")
        ]
    )
    async def whitelist_cmd(
        self,
        interaction: discord.Interaction,
        tipo: app_commands.Choice[str],
        objetivo
    ):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        t = tipo.value

        if t == "user":
            lista = cfg["whitelist_users"]
        elif t == "role":
            lista = cfg["whitelist_roles"]
        else:
            lista = cfg["whitelist_channels"]

        if objetivo.id in lista:
            lista.remove(objetivo.id)
            accion = "eliminado"
        else:
            lista.append(objetivo.id)
            accion = "añadido"

        save_config(self.config)

        await interaction.response.send_message(
            f"✅ {objetivo.id} {accion} en whitelist ({t}).",
            ephemeral=True
        )

    # ============================================================
    # BLOQUEO DE MENCIONES
    # ============================================================

    @app_commands.command(name="antimention_block", description="Bloquea usuarios o roles para que NO puedan ser mencionados.")
    @app_commands.describe(
        tipo="Usuario o rol",
        objetivo="Usuario o rol a bloquear/desbloquear"
    )
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="Usuario", value="user"),
            app_commands.Choice(name="Rol", value="role")
        ]
    )
    async def block_cmd(
        self,
        interaction: discord.Interaction,
        tipo: app_commands.Choice[str],
        objetivo
    ):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        if tipo.value == "user":
            lista = cfg["blocked_users"]
        else:
            lista = cfg["blocked_roles"]

        if objetivo.id in lista:
            lista.remove(objetivo.id)
            accion = "desbloqueado"
        else:
            lista.append(objetivo.id)
            accion = "bloqueado"

        save_config(self.config)

        await interaction.response.send_message(
            f"🚫 {objetivo.id} {accion} correctamente.",
            ephemeral=True
        )

    # ============================================================
    # DETECCIÓN DE MENCIONES
    # ============================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild = message.guild
        cfg = self.ensure_guild(guild.id)
        user = message.author
        content = message.content

        if not cfg["enabled"]:
            return

        # Whitelist
        if user.id in cfg["whitelist_users"]:
            return
        if any(r.id in cfg["whitelist_roles"] for r in user.roles):
            return
        if message.channel.id in cfg["whitelist_channels"]:
            return

        # Cooldown
        now = time.time()
        if user.id in self.cooldowns and now - self.cooldowns[user.id] < cfg["cooldown"]:
            return
        self.cooldowns[user.id] = now

        # Bloqueo directo
        if any(u.id in cfg["blocked_users"] for u in message.mentions):
            return await self.apply_action(message, "Mención a usuario bloqueado")

        if any(r.id in cfg["blocked_roles"] for r in message.role_mentions):
            return await self.apply_action(message, "Mención a rol bloqueado")

        # Límites
        if len(message.mentions) > cfg["limit_users"]:
            return await self.apply_action(message, "Exceso de menciones a usuarios")

        if len(message.role_mentions) > cfg["limit_roles"]:
            return await self.apply_action(message, "Exceso de menciones a roles")

        if ("@everyone" in content or "@here" in content) and cfg["limit_everyone"] < 1:
            return await self.apply_action(message, "Uso de @everyone/@here")

    # ============================================================
    # APLICAR SANCIÓN (EMBEDS PRO)
    # ============================================================

    async def apply_action(self, message: discord.Message, reason: str):
        guild = message.guild
        cfg = self.ensure_guild(guild.id)
        user = message.author
        action = cfg["accion"]

        # Borrar mensaje del usuario
        try:
            await message.delete()
        except:
            pass

        # Logs
        if cfg["logs"]:
            ch = guild.get_channel(cfg["logs"])
            if ch:
                embed = discord.Embed(
                    title="📘 Log Anti‑Mention",
                    description=f"Usuario: {user.mention}\nRazón: `{reason}`",
                    color=discord.Color.blue()
                )
                await ch.send(embed=embed)

        # Intentar sanción
        sancionado = False

        try:
            if action == "ban":
                await guild.ban(user, reason=f"Anti‑Mention: {reason}")
            elif action == "kick":
                await guild.kick(user, reason=f"Anti‑Mention: {reason}")
            elif action == "mute":
                await user.timeout(
                    discord.utils.utcnow() + timedelta(seconds=cfg["mute_time"]),
                    reason=f"Anti‑Mention: {reason}"
                )
            sancionado = True
        except:
            sancionado = False

        # Embed según resultado
        if not sancionado:
            embed = discord.Embed(
                title="⚠️ No se pudo aplicar sanción",
                description=f"Detecté abuso de menciones de {user.mention}, pero no tengo permisos.",
                color=discord.Color.yellow()
            )
        else:
            embed = discord.Embed(
                title="⛔ Sanción aplicada",
                description=f"Usuario: {user.mention}\nAcción: **{action}**\nRazón: {reason}",
                color=discord.Color.red()
            )

        await message.channel.send(embed=embed)


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiMention(bot)) 
