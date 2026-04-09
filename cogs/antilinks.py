import discord
from discord.ext import commands
from discord import app_commands
import json, time, os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "antilinks.json")

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

class AntiLinks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.warns = {}

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

    async def send_log(self, guild, cfg, embed):
        if cfg["log_channel"]:
            canal = guild.get_channel(cfg["log_channel"])
            if canal:
                try:
                    await canal.send(embed=embed)
                except:
                    pass

    @app_commands.command(name="antilinks", description="Configura el sistema Anti‑Links.")
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
            title="<a:warning:1485072594012209354> Configuración Anti‑Links actualizada",
            color=discord.Color(0x0A3D62)
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

    @app_commands.command(name="antilinks_whitelist", description="Gestiona la whitelist de usuarios o roles.")
    @app_commands.describe(
        accion="Selecciona si quieres añadir o eliminar de la whitelist.",
        tipo="Indica si es usuario o rol. Ejecuta el comando varias veces para añadir o eliminar varios.",
        objetivo="Selecciona el usuario o rol que quieres añadir o eliminar."
    )
    @app_commands.choices(
        accion=[
            app_commands.Choice(name="Añadir", value="añadir"),
            app_commands.Choice(name="Eliminar", value="eliminar")
        ],
        tipo=[
            app_commands.Choice(name="Usuario", value="usuario"),
            app_commands.Choice(name="Rol", value="rol")
        ]
    )
    async def whitelist_action(
        self,
        interaction: discord.Interaction,
        accion: str,
        tipo: str,
        objetivo: discord.Object
    ):
        cfg = self.ensure_guild(interaction.guild.id)
        lista = cfg["whitelist_users"] if tipo == "usuario" else cfg["whitelist_roles"]

        if accion == "añadir":
            if objetivo.id not in lista:
                lista.append(objetivo.id)
                save_config(self.config)
                msg = f"<a:ao_Tick:1485072554879357089> {tipo.capitalize()} añadido a la whitelist."
            else:
                msg = f"<a:warning:1485072594012209354> Ese {tipo} ya está en la whitelist."
        else:
            if objetivo.id in lista:
                lista.remove(objetivo.id)
                save_config(self.config)
                msg = f"<a:ao_Tick:1485072554879357089> {tipo.capitalize()} eliminado de la whitelist."
            else:
                msg = f"<a:warning:1485072594012209354> Ese {tipo} no está en la whitelist."

        embed = discord.Embed(description=msg, color=discord.Color(0x0A3D62))
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

        if user.id in cfg["whitelist_users"]:
            return
        if any(r.id in cfg["whitelist_roles"] for r in user.roles):
            return

        if cfg["allow_invites"] and ("discord.gg/" in content or "discord.com/invite/" in content):
            return

        if not ("http://" in content or "https://" in content):
            return

        try:
            await message.delete()
        except:
            pass

        uid = user.id
        now = time.time()
        if uid not in self.warns:
            self.warns[uid] = []
        self.warns[uid].append(now)
        self.warns[uid] = [t for t in self.warns[uid] if now - t <= 300]
        warn_count = len(self.warns[uid])

        if warn_count == 1:
            embed = discord.Embed(
                title="<a:warning:1485072594012209354> Enlace no permitido",
                description=f"{user.mention}, has enviado un enlace que **no está permitido**. Evita repetirlo o se aplicará una sanción.",
                color=discord.Color(0x0A3D62)
            )
            await message.channel.send(embed=embed)
            await self.send_log(guild, cfg, embed)
            return

        await self.apply_action(message, cfg)

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
                await user.timeout(discord.utils.utcnow() + timedelta(seconds=duration), reason="Anti‑Links")
            sancionado = True
        except:
            sancionado = False

        if not sancionado:
            embed = discord.Embed(
                title="<a:warning:1483506607265419466> Enlace detectado",
                description=f"Detecté un enlace prohibido de {user.mention}, pero **no pude aplicar la sanción**.",
                color=discord.Color(0x0A3D62)
            )
            await message.channel.send(embed=embed)
            await self.send_log(guild, cfg, embed)
            return

        embed = discord.Embed(
            title="<a:advertencia:1483506898509758690> Sanción aplicada",
            description=f"Usuario: {user.mention}\nAcción: **{action}**\nRazón: Enviar enlaces no permitidos.",
            color=discord.Color(0x0A3D62)
        )
        await message.channel.send(embed=embed)
        await self.send_log(guild, cfg, embed)

async def setup(bot):
    await bot.add_cog(AntiLinks(bot))
