import discord
from discord.ext import commands
from discord import app_commands
import json, os, time
from datetime import timedelta

CONFIG_FILE = "antiflood.json"

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
# COG ANTI‑FLOOD PRO
# ============================================================

class AntiFlood(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.user_messages = {}
        self.warned = {}

    # --------------------------------------------------------
    # CONFIG POR SERVIDOR
    # --------------------------------------------------------

    def ensure_guild(self, guild_id: int):
        gid = str(guild_id)

        if gid not in self.config:
            self.config[gid] = {
                "enabled": False,
                "nivel": "medio",
                "accion": "mute",
                "mute_time": 600,

                "settings": {
                    "interval": 4,
                    "max_messages": 5,
                    "delete_count": 2
                }
            }
            save_config(self.config)

        return self.config[gid]

    # --------------------------------------------------------
    # COMANDO /antiflood
    # --------------------------------------------------------

    @app_commands.command(
        name="antiflood",
        description="Configura el sistema Anti‑Flood."
    )
    @app_commands.describe(
        estado="Activar o desactivar el Anti‑Flood",
        nivel="Nivel de seguridad",
        accion="Acción al detectar flood",
        mute_time="Tiempo de mute en segundos"
    )
    @app_commands.choices(
        estado=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ],
        nivel=[
            app_commands.Choice(name="Bajo", value="bajo"),
            app_commands.Choice(name="Medio", value="medio"),
            app_commands.Choice(name="Alto", value="alto")
        ],
        accion=[
            app_commands.Choice(name="Mute", value="mute"),
            app_commands.Choice(name="Kick", value="kick"),
            app_commands.Choice(name="Ban", value="ban")
        ]
    )
    async def antiflood_cmd(
        self,
        interaction: discord.Interaction,
        estado: str = None,
        nivel: str = None,
        accion: str = None,
        mute_time: int = None
    ):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        if estado:
            cfg["enabled"] = (estado == "activar")

        if nivel:
            cfg["nivel"] = nivel

            if nivel == "bajo":
                cfg["settings"]["interval"] = 3
                cfg["settings"]["max_messages"] = 7
                cfg["settings"]["delete_count"] = 1

            elif nivel == "medio":
                cfg["settings"]["interval"] = 4
                cfg["settings"]["max_messages"] = 5
                cfg["settings"]["delete_count"] = 2

            elif nivel == "alto":
                cfg["settings"]["interval"] = 5
                cfg["settings"]["max_messages"] = 3
                cfg["settings"]["delete_count"] = 3

        if accion:
            cfg["accion"] = accion

        if mute_time:
            cfg["mute_time"] = max(1, mute_time)

        save_config(self.config)

        embed = discord.Embed(
            title="🛡 Configuración Anti‑Flood actualizada",
            color=discord.Color.yellow()
        )

        embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)
        embed.add_field(name="Nivel", value=cfg["nivel"].capitalize(), inline=True)
        embed.add_field(name="Acción", value=cfg["accion"].capitalize(), inline=True)
        embed.add_field(name="Mute time", value=f"{cfg['mute_time']}s", inline=True)
        embed.add_field(
            name="Límite",
            value=f"{cfg['settings']['max_messages']} mensajes / {cfg['settings']['interval']}s",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --------------------------------------------------------
    # DETECCIÓN DE FLOOD
    # --------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild = message.guild
        user = message.author
        cfg = self.ensure_guild(guild.id)
        now = time.time()

        if not cfg["enabled"]:
            return

        # Historial
        if user.id not in self.user_messages:
            self.user_messages[user.id] = []

        self.user_messages[user.id].append((now, message))

        interval = cfg["settings"]["interval"]
        max_msgs = cfg["settings"]["max_messages"]
        delete_count = cfg["settings"]["delete_count"]

        # Limpiar mensajes viejos
        self.user_messages[user.id] = [
            (t, msg) for t, msg in self.user_messages[user.id]
            if now - t <= interval
        ]

        # Flood detectado
        if len(self.user_messages[user.id]) >= max_msgs:

            # Borrar mensajes recientes del usuario
            to_delete = self.user_messages[user.id][-delete_count:]
            for _, msg in to_delete:
                try:
                    await msg.delete()
                except:
                    pass

            # Primer aviso
            if user.id not in self.warned or now - self.warned[user.id] > interval:
                self.warned[user.id] = now

                embed = discord.Embed(
                    title="⚠️ Actividad sospechosa",
                    description=f"{user.mention}, estás enviando mensajes **demasiado rápido**.\nReduce la velocidad o se aplicará una sanción.",
                    color=discord.Color.yellow()
                )

                await message.channel.send(embed=embed)
                return

            # Aplicar sanción
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
                await guild.ban(user, reason="Flood")
            elif action == "kick":
                await guild.kick(user, reason="Flood")
            elif action == "mute":
                duration = cfg["mute_time"]
                await user.timeout(
                    discord.utils.utcnow() + timedelta(seconds=duration),
                    reason="Flood"
                )
            sancionado = True
        except:
            sancionado = False

        # Si NO se pudo sancionar → embed amarillo
        if not sancionado:
            embed = discord.Embed(
                title="⚠️ Flood detectado",
                description=(
                    f"Detecté flood de {user.mention}.\n"
                    f"Pero **no he podido aplicar la acción configurada por que no tengo permisos**."
                ),
                color=discord.Color.yellow()
            )
            await message.channel.send(embed=embed)
            return

        # Si SÍ se sancionó → embed rojo
        embed = discord.Embed(
            title="⛔ Sanción aplicada",
            description=f"Usuario: {user.mention}\nAcción: **{action}**\nRazón: Flood",
            color=discord.Color.red()
        )
        await message.channel.send(embed=embed)


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiFlood(bot)) 
