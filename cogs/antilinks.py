import discord
from discord.ext import commands
from discord import app_commands
import json, os, time
from datetime import timedelta

CONFIG_FILE = "antilinks.json"

# ============================================================
# CONFIG
# ============================================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}

    with open(CONFIG_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================================================
# COG ANTI‑LINKS PRO
# ============================================================

class AntiLinks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.warns = {}  # user_id → warns

    # --------------------------------------------------------
    # CONFIG POR SERVIDOR
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

        return self.config[gid]

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

        if estado:
            cfg["enabled"] = (estado == "activar")

        if accion:
            cfg["accion"] = accion

        if mute_time:
            cfg["mute_time"] = max(1, mute_time)

        if allow_invites:
            cfg["allow_invites"] = (allow_invites == "si")

        if log_channel:
            cfg["log_channel"] = log_channel.id

        save_config(self.config)

        embed = discord.Embed(
            title="🛡 Configuración Anti‑Links actualizada",
            color=discord.Color.yellow()
        )

        embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)
        embed.add_field(name="Acción", value=cfg["accion"].capitalize(), inline=True)
        embed.add_field(name="Mute time", value=f"{cfg['mute_time']}s", inline=True)
        embed.add_field(name="Permitir invites", value="Sí" if cfg["allow_invites"] else "No", inline=True)
        embed.add_field(name="Log channel", value=f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "No configurado", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --------------------------------------------------------
    # COMANDO /antilinks_config
    # --------------------------------------------------------

    @app_commands.command(
        name="antilinks_config",
        description="Muestra la configuración actual del Anti‑Links."
    )
    async def antilinks_config(self, interaction: discord.Interaction):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        embed = discord.Embed(
            title="🛡 Configuración actual del Anti‑Links",
            color=discord.Color.blue()
        )

        embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)
        embed.add_field(name="Acción", value=cfg["accion"].capitalize(), inline=True)
        embed.add_field(name="Mute time", value=f"{cfg['mute_time']}s", inline=True)
        embed.add_field(name="Permitir invites", value="Sí" if cfg["allow_invites"] else "No", inline=True)
        embed.add_field(name="Log channel", value=f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "No configurado", inline=False)

        embed.add_field(name="Whitelist usuarios", value=", ".join(f"<@{u}>" for u in cfg["whitelist_users"]) or "Ninguno", inline=False)
        embed.add_field(name="Whitelist roles", value=", ".join(f"<@&{r}>" for r in cfg["whitelist_roles"]) or "Ninguno", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --------------------------------------------------------
    # COMANDO /antilinks_whitelist_users
    # --------------------------------------------------------

    @app_commands.command(
        name="antilinks_whitelist_users",
        description="Selecciona usuarios permitidos para enviar enlaces."
    )
    async def whitelist_users_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        class UserSelect(discord.ui.Select):
            def __init__(self, parent):
                options = [
                    discord.SelectOption(label=m.name, value=str(m.id))
                    for m in guild.members if not m.bot
                ][:25]

                super().__init__(
                    placeholder="Selecciona usuarios permitidos",
                    min_values=0,
                    max_values=len(options),
                    options=options
                )
                self.parent = parent

            async def callback(self, i: discord.Interaction):
                cfg["whitelist_users"] = [int(v) for v in self.values]
                save_config(self.parent.config)

                await i.response.send_message(
                    "✅ Whitelist de usuarios actualizada.",
                    ephemeral=True
                )

        view = discord.ui.View()
        view.add_item(UserSelect(self))

        await interaction.response.send_message(
            "Selecciona los usuarios permitidos:",
            view=view,
            ephemeral=True
        )

    # --------------------------------------------------------
    # COMANDO /antilinks_whitelist_roles
    # --------------------------------------------------------

    @app_commands.command(
        name="antilinks_whitelist_roles",
        description="Selecciona roles permitidos para enviar enlaces."
    )
    async def whitelist_roles_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        class RoleSelect(discord.ui.Select):
            def __init__(self, parent):
                options = [
                    discord.SelectOption(label=r.name, value=str(r.id))
                    for r in guild.roles if r.name != "@everyone"
                ][:25]

                super().__init__(
                    placeholder="Selecciona roles permitidos",
                    min_values=0,
                    max_values=len(options),
                    options=options
                )
                self.parent = parent

            async def callback(self, i: discord.Interaction):
                cfg["whitelist_roles"] = [int(v) for v in self.values]
                save_config(self.parent.config)

                await i.response.send_message(
                    "✅ Whitelist de roles actualizada.",
                    ephemeral=True
                )

        view = discord.ui.View()
        view.add_item(RoleSelect(self))

        await interaction.response.send_message(
            "Selecciona los roles permitidos:",
            view=view,
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

        # Whitelist usuarios
        if user.id in cfg["whitelist_users"]:
            return

        # Whitelist roles
        if any(r.id in cfg["whitelist_roles"] for r in user.roles):
            return

        # Permitir invites
        if cfg["allow_invites"]:
            if "discord.gg/" in content or "discord.com/invite/" in content:
                return

        # Detectar enlaces
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

        # Limpiar warns viejos (5 minutos)
        self.warns[uid] = [t for t in self.warns[uid] if now - t <= 300]

        warn_count = len(self.warns[uid])

        # Primer aviso
        if warn_count == 1:
            embed = discord.Embed(
                title="⚠️ Enlace no permitido",
                description=f"{user.mention}, has enviado un enlace que **no está permitido** aquí.\nEvita repetirlo o se aplicará una sanción.",
                color=discord.Color.yellow()
            )
            await message.channel.send(embed=embed)
            return

        # Segundo aviso → sanción
        await self.apply_action(message, cfg)

    # --------------------------------------------------------
    # APLICAR SANCIÓN (ACTUALIZADO)
    # --------------------------------------------------------

    async def apply_action(self, message: discord.Message, cfg):
        user = message.author
        guild = message.guild
        action = cfg["accion"]

        sancionado = False

        # Intentar sancionar primero
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

        # Si NO se pudo sancionar → embed amarillo
        if not sancionado:
            embed = discord.Embed(
                title="⚠️ Enlace detectado",
                description=(
                    f"Detecté un enlace prohibido de {user.mention}.\n"
                    f"Pero **no he podido aplicar la acción configurada**."
                ),
                color=discord.Color.yellow()
            )
            await message.channel.send(embed=embed)
            return

        # Si SÍ se sancionó → embed rojo
        embed = discord.Embed(
            title="⛔ Sanción aplicada",
            description=f"Usuario: {user.mention}\nAcción: **{action}**\nRazón: Enviar enlaces no permitidos",
            color=discord.Color.red()
        )
        await message.channel.send(embed=embed)


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiLinks(bot))
