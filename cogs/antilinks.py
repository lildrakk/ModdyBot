import discord
from discord.ext import commands
from discord import app_commands
import json, time
import os
from datetime import timedelta 

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "antilinks.json") 

# ============================================================
# CONFIG (GUARDADO SEGURO)
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
# COG ANTI‑LINKS PRO
# ============================================================

class AntiLinks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.warns = {}  # user_id → warns

    # --------------------------------------------------------
    # CONFIG POR SERVIDOR (CON AUTOFIX)
    # --------------------------------------------------------

    def ensure_guild(self, guild_id: int):
        gid = str(guild_id)

        if gid not in self.config:
            self.config[gid] = {
                "enabled": False,
                "accion": "mute",
                "mute_time": 600,
                "allow_invites": False,
                "whitelist_users": [],
                "whitelist_roles": [],
                "log_channel": None
            }
            save_config(self.config)

        cfg = self.config[gid]

        cfg.setdefault("accion", "mute")
        cfg.setdefault("mute_time", 600)
        cfg.setdefault("allow_invites", False)
        cfg.setdefault("whitelist_users", [])
        cfg.setdefault("whitelist_roles", [])
        cfg.setdefault("log_channel", None)

        save_config(self.config)
        return cfg

    # --------------------------------------------------------
    # ENVIAR LOG
    # --------------------------------------------------------

    async def send_log(self, guild, cfg, embed):
        if cfg["log_channel"]:
            canal = guild.get_channel(cfg["log_channel"])
            if canal:
                try:
                    await canal.send(embed=embed)
                except:
                    pass

    # --------------------------------------------------------
    # COMANDO /antilinks
    # --------------------------------------------------------

    @app_commands.command(
        name="antilinks",
        description="Configura el sistema Anti‑Links."
    )
    @app_commands.describe(
        estado="Activar o desactivar el Anti‑Links",
        accion="Acción al detectar enlaces prohibidos",
        mute_time="Tiempo de mute en segundos",
        allow_invites="Permitir invitaciones de Discord",
        log_channel="Canal donde se enviarán los logs"
    )
    @app_commands.choices(
        estado=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ],
        accion=[
            app_commands.Choice(name="Mute", value="mute"),
            app_commands.Choice(name="Kick", value="kick"),
            app_commands.Choice(name="Ban", value="ban")
        ],
        allow_invites=[
            app_commands.Choice(name="Sí", value="si"),
            app_commands.Choice(name="No", value="no")
        ]
    )
    async def antilinks_cmd(
        self,
        interaction: discord.Interaction,
        estado: str = None,
        accion: str = None,
        mute_time: int = None,
        allow_invites: str = None,
        log_channel: discord.TextChannel = None
    ):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        if estado is not None:
            cfg["enabled"] = (estado == "activar")

        if accion is not None:
            cfg["accion"] = accion

        if mute_time is not None:
            cfg["mute_time"] = max(1, mute_time)

        if allow_invites is not None:
            cfg["allow_invites"] = (allow_invites == "si")

        if log_channel is not None:
            cfg["log_channel"] = log_channel.id

        save_config(self.config)

        embed = discord.Embed(
            title="⚠️ Configuración Anti‑Links actualizada",
            color=discord.Color.yellow()
        )

        embed.add_field(name="Estado", value="Activado" if cfg["enabled"] else "Desactivado", inline=False)
        embed.add_field(name="Acción", value=cfg["accion"].capitalize(), inline=True)
        embed.add_field(name="Mute time", value=f"{cfg['mute_time']}s", inline=True)
        embed.add_field(name="Permitir invites", value="Sí" if cfg["allow_invites"] else "No", inline=True)
        embed.add_field(
            name="Log channel",
            value=f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "No configurado",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --------------------------------------------------------
    # AÑADIR USER A WHITELIST
    # --------------------------------------------------------

    @app_commands.command(
        name="antilinks_whitelist_user",
        description="Añade un usuario a la whitelist."
    )
    async def whitelist_user(self, interaction: discord.Interaction, user: discord.Member):
        cfg = self.ensure_guild(interaction.guild.id)

        if user.id not in cfg["whitelist_users"]:
            cfg["whitelist_users"].append(user.id)
            save_config(self.config)

        await interaction.response.send_message(
            f"⚠️ Usuario {user.mention} añadido a la whitelist.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # ELIMINAR USER DE WHITELIST
    # --------------------------------------------------------

    @app_commands.command(
        name="antilinks_unwhitelist_user",
        description="Elimina un usuario de la whitelist."
    )
    async def unwhitelist_user(self, interaction: discord.Interaction, user: discord.Member):
        cfg = self.ensure_guild(interaction.guild.id)

        if user.id in cfg["whitelist_users"]:
            cfg["whitelist_users"].remove(user.id)
            save_config(self.config)

        await interaction.response.send_message(
            f"⚠️ Usuario {user.mention} eliminado de la whitelist.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # AÑADIR ROL A WHITELIST
    # --------------------------------------------------------

    @app_commands.command(
        name="antilinks_whitelist_role",
        description="Añade un rol a la whitelist."
    )
    async def whitelist_role(self, interaction: discord.Interaction, rol: discord.Role):
        cfg = self.ensure_guild(interaction.guild.id)

        if rol.id not in cfg["whitelist_roles"]:
            cfg["whitelist_roles"].append(rol.id)
            save_config(self.config)

        await interaction.response.send_message(
            f"⚠️ Rol {rol.mention} añadido a la whitelist.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # ELIMINAR ROL DE WHITELIST
    # --------------------------------------------------------

    @app_commands.command(
        name="antilinks_unwhitelist_role",
        description="Elimina un rol de la whitelist."
    )
    async def unwhitelist_role(self, interaction: discord.Interaction, rol: discord.Role):
        cfg = self.ensure_guild(interaction.guild.id)

        if rol.id in cfg["whitelist_roles"]:
            cfg["whitelist_roles"].remove(rol.id)
            save_config(self.config)

        await interaction.response.send_message(
            f"⚠️ Rol {rol.mention} eliminado de la whitelist.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # DETECCIÓN DE LINKS
    # --------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild = message.guild
        cfg = self.ensure_guild(guild.id)
        user = message.author
        content = message.content.lower()

        if not cfg["enabled"]:
            return

        # Whitelist
        if user.id in cfg["whitelist_users"]:
            return

        if any(r.id in cfg["whitelist_roles"] for r in user.roles):
            return

        # Invites permitidos
        if cfg["allow_invites"]:
            if "discord.gg/" in content or "discord.com/invite/" in content:
                return

        # No es link
        if not ("http://" in content or "https://" in content):
            return

        # Borrar mensaje
        try:
            await message.delete()
        except:
            pass

        # Registrar warn
        uid = user.id
        now = time.time()

        if uid not in self.warns:
            self.warns[uid] = []

        self.warns[uid].append(now)
        self.warns[uid] = [t for t in self.warns[uid] if now - t <= 300]

        warn_count = len(self.warns[uid])

        # Primer aviso
        if warn_count == 1:
            embed = discord.Embed(
                title="⚠️ Enlace no permitido",
                description=(
                    f"{user.mention}, has enviado un enlace que **no está permitido**.\n"
                    f"Evita repetirlo o se aplicará una sanción."
                ),
                color=discord.Color.yellow()
            )
            await message.channel.send(embed=embed)
            await self.send_log(guild, cfg, embed)
            return

        # Sanción
        await self.apply_action(message, cfg)

    # --------------------------------------------------------
    # APLICAR SANCIÓN
    # --------------------------------------------------------

    async def apply_action(self, message: discord.Message, cfg):
        user = message.author
        guild = message.guild
        action = cfg["accion"]

        sancionado = False

        try:
            if action == "ban":
                await guild.ban(user, reason="Anti‑Links")
            elif action == "kick":
                await guild.kick(user, reason="Anti‑Links")
            elif action == "mute":
                duration = cfg["mute_time"]
                await user.timeout(
                    discord.utils.utcnow() + timedelta(seconds=duration),
                    reason="Anti‑Links"
                )
            sancionado = True
        except:
            sancionado = False

        # No se pudo sancionar
        if not sancionado:
            embed = discord.Embed(
                title="⚠️ Enlace detectado",
                description=(
                    f"Detecté un enlace prohibido de {user.mention}, pero **no pude aplicar la sanción**."
                ),
                color=discord.Color.yellow()
            )
            await message.channel.send(embed=embed)
            await self.send_log(guild, cfg, embed)
            return

        # Sanción aplicada
        embed = discord.Embed(
            title="⛔ Sanción aplicada",
            description=f"Usuario: {user.mention}\nAcción: **{action}**\nRazón: Enviar enlaces no permitidos",
            color=discord.Color.red()
        )
        await message.channel.send(embed=embed)
        await self.send_log(guild, cfg, embed)


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiLinks(bot))
