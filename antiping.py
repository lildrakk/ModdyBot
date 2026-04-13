import discord
from discord.ext import commands
from discord import app_commands
import json, time
from datetime import timedelta

CONFIG_FILE = "antiping.json"

# ============================
# CONFIG PERSISTENTE
# ============================

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ============================
# COG ANTIPING PRO
# ============================

class AntiPing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.warns = {}  # user_id -> timestamps

    # Crear config por servidor
    def ensure_guild(self, guild_id: int):
        gid = str(guild_id)
        if gid not in self.config:
            self.config[gid] = {
                "enabled": False,
                "accion": "mute",
                "mute_time": 600,
                "protected_users": [],
                "protected_roles": [],
                "whitelist_users": [],
                "whitelist_roles": [],
                "log_channel": None
            }
            save_config(self.config)
        return self.config[gid]

    # Enviar logs
    async def send_log(self, guild, cfg, embed):
        if cfg["log_channel"]:
            canal = guild.get_channel(cfg["log_channel"])
            if canal:
                try:
                    await canal.send(embed=embed)
                except:
                    pass

    # ============================
    # COMANDO PRINCIPAL /antiping
    # ============================

    @app_commands.command(
        name="antiping",
        description="Configura el Anti‑Ping (SOLO el dueño del servidor puede usarlo)."
    )
    @app_commands.describe(
        activar="Activa o desactiva el Anti‑Ping.",
        accion="Acción al detectar un ping prohibido (warn/mute/kick/ban).",
        mute_time="Tiempo de mute si la acción es 'mute'.",
        log_channel="Canal donde se enviarán los logs del Anti‑Ping."
    )
    @app_commands.choices(
        accion=[
            app_commands.Choice(name="Warn", value="warn"),
            app_commands.Choice(name="Mute", value="mute"),
            app_commands.Choice(name="Kick", value="kick"),
            app_commands.Choice(name="Ban", value="ban")
        ]
    )
    async def antiping_cmd(
        self,
        interaction: discord.Interaction,
        activar: bool = None,
        accion: str = None,
        mute_time: int = None,
        log_channel: discord.TextChannel = None
    ):
        guild = interaction.guild

        # SOLO EL OWNER
        if guild.owner_id != interaction.user.id:
            return await interaction.response.send_message(
                "❌ Solo el **dueño del servidor** puede usar este comando.",
                ephemeral=True
            )

        cfg = self.ensure_guild(guild.id)

        if activar is not None:
            cfg["enabled"] = activar
        if accion is not None:
            cfg["accion"] = accion
        if mute_time is not None:
            cfg["mute_time"] = max(1, mute_time)
        if log_channel is not None:
            cfg["log_channel"] = log_channel.id

        save_config(self.config)

        embed = discord.Embed(
            title="<:warnnormal:1491858539222925364> Configuración Anti‑Ping actualizada",
            color=discord.Color(0x0A3D62)
        )
        embed.add_field(name="Estado", value="Activado" if cfg["enabled"] else "Desactivado", inline=False)
        embed.add_field(name="Acción", value=cfg["accion"], inline=True)
        embed.add_field(name="Mute time", value=f"{cfg['mute_time']}s", inline=True)
        embed.add_field(
            name="Canal de logs",
            value=f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "No configurado",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ============================
    # AÑADIR / QUITAR OBJETIVOS PROTEGIDOS
    # ============================

    @app_commands.command(
        name="antiping_objetivo",
        description="Añade o elimina un usuario o rol que NO podrá ser mencionado."
    )
    @app_commands.describe(
        accion="Añadir o eliminar.",
        usuario="Usuario que NO podrá ser mencionado (solo uno por comando).",
        rol="Rol que NO podrá ser mencionado (solo uno por comando)."
    )
    @app_commands.choices(
        accion=[
            app_commands.Choice(name="Añadir", value="add"),
            app_commands.Choice(name="Eliminar", value="remove")
        ]
    )
    async def antiping_objetivo(
        self,
        interaction: discord.Interaction,
        accion: str,
        usuario: discord.Member = None,
        rol: discord.Role = None
    ):
        guild = interaction.guild

        # SOLO OWNER
        if guild.owner_id != interaction.user.id:
            return await interaction.response.send_message(
                "❌ Solo el **dueño del servidor** puede usar este comando.",
                ephemeral=True
            )

        cfg = self.ensure_guild(guild.id)

        if usuario and rol:
            return await interaction.response.send_message(
                "❌ Solo puedes añadir **un usuario o un rol**, no ambos.",
                ephemeral=True
            )

        if not usuario and not rol:
            return await interaction.response.send_message(
                "❌ Debes seleccionar **un usuario o un rol**.",
                ephemeral=True
            )

        if usuario:
            lista = cfg["protected_users"]
            objetivo = usuario.id
            tipo = "usuario"
        else:
            lista = cfg["protected_roles"]
            objetivo = rol.id
            tipo = "rol"

        if accion == "add":
            if objetivo not in lista:
                lista.append(objetivo)
                msg = f"<a:ao_Tick:1485072554879357089> {tipo.capitalize()} añadido como protegido."
            else:
                msg = f"<:warnnormal:1491858539222925364> Ese {tipo} ya está protegido."
        else:
            if objetivo in lista:
                lista.remove(objetivo)
                msg = f"<a:ao_Tick:1485072554879357089> {tipo.capitalize()} eliminado de protegidos."
            else:
                msg = f"<:warnnormal:1491858539222925364> Ese {tipo} no estaba protegido."

        save_config(self.config)

        await interaction.response.send_message(msg, ephemeral=True)

    # ============================
    # WHITELIST
    # ============================

    @app_commands.command(
        name="antiping_whitelist",
        description="Añade o elimina usuarios o roles que podrán mencionar sin restricciones."
    )
    @app_commands.describe(
        accion="Añadir o eliminar.",
        usuario="Usuario que podrá mencionar sin restricciones.",
        rol="Rol que podrá mencionar sin restricciones."
    )
    @app_commands.choices(
        accion=[
            app_commands.Choice(name="Añadir", value="add"),
            app_commands.Choice(name="Eliminar", value="remove")
        ]
    )
    async def antiping_whitelist(
        self,
        interaction: discord.Interaction,
        accion: str,
        usuario: discord.Member = None,
        rol: discord.Role = None
    ):
        guild = interaction.guild

        # SOLO OWNER
        if guild.owner_id != interaction.user.id:
            return await interaction.response.send_message(
                "❌ Solo el **dueño del servidor** puede usar este comando.",
                ephemeral=True
            )

        cfg = self.ensure_guild(guild.id)

        if usuario and rol:
            return await interaction.response.send_message(
                "❌ Solo puedes añadir **un usuario o un rol**, no ambos.",
                ephemeral=True
            )

        if not usuario and not rol:
            return await interaction.response.send_message(
                "❌ Debes seleccionar **un usuario o un rol**.",
                ephemeral=True
            )

        if usuario:
            lista = cfg["whitelist_users"]
            objetivo = usuario.id
            tipo = "usuario"
        else:
            lista = cfg["whitelist_roles"]
            objetivo = rol.id
            tipo = "rol"

        if accion == "add":
            if objetivo not in lista:
                lista.append(objetivo)
                msg = f"<a:ao_Tick:1485072554879357089> {tipo.capitalize()} añadido a la whitelist."
            else:
                msg = f"<:warnnormal:1491858539222925364> Ese {tipo} ya está en la whitelist."
        else:
            if objetivo in lista:
                lista.remove(objetivo)
                msg = f"<a:ao_Tick:1485072554879357089> {tipo.capitalize()} eliminado de la whitelist."
            else:
                msg = f"<:warnnormal:1491858539222925364> Ese {tipo} no estaba en la whitelist."

        save_config(self.config)

        await interaction.response.send_message(msg, ephemeral=True)

    # ============================
    # DETECCIÓN DE PINGS PROHIBIDOS
    # ============================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild = message.guild
        cfg = self.ensure_guild(guild.id)
        user = message.author

        if not cfg["enabled"]:
            return

        # WHITELIST
        if user.id in cfg["whitelist_users"]:
            return
        if any(r.id in cfg["whitelist_roles"] for r in user.roles):
            return

        # DETECTAR PINGS
        mentioned_users = [u.id for u in message.mentions]
        mentioned_roles = [r.id for r in message.role_mentions]

        # ¿Mencionó a un objetivo protegido?
        hit_user = any(uid in cfg["protected_users"] for uid in mentioned_users)
        hit_role = any(rid in cfg["protected_roles"] for rid in mentioned_roles)

        if not hit_user and not hit_role:
            return

        # ELIMINAR MENSAJE
        try:
            await message.delete()
        except:
            pass

        # SISTEMA DE ADVERTENCIAS
        uid = user.id
        now = time.time()

        if uid not in self.warns:
            self.warns[uid] = []

        self.warns[uid].append(now)
        self.warns[uid] = [t for t in self.warns[uid] if now - t <= 300]
        warn_count = len(self.warns[uid])

        # PRIMERA ADVERTENCIA
        if warn_count == 1:
            embed = discord.Embed(
                title="<:warnnormal:1491858539222925364> Ping no permitido",
                description=f"{user.mention}, has mencionado a un usuario/rol protegido.\nEvita repetirlo.",
                color=discord.Color(0x0A3D62)
            )
            await message.channel.send(embed=embed)

            log = discord.Embed(
                title="<:warnnormal:1491858539222925364> Anti‑Ping | Advertencia 1/2",
                description=f"Usuario: {user.mention}\nCanal: {message.channel.mention}",
                color=discord.Color(0x0A3D62)
            )
            await self.send_log(guild, cfg, log)
            return

        # SEGUNDA VEZ → SANCIÓN
        await self.apply_action(message, cfg)

    # ============================
    # APLICAR SANCIÓN
    # ============================

    async def apply_action(self, message: discord.Message, cfg):
        user = message.author
        guild = message.guild
        action = cfg["accion"]

        sancionado = False

        try:
            if action == "ban":
                await guild.ban(user, reason="Anti‑Ping")
            elif action == "kick":
                await guild.kick(user, reason="Anti‑Ping")
            elif action == "mute":
                duration = cfg["mute_time"]
                await user.timeout(discord.utils.utcnow() + timedelta(seconds=duration), reason="Anti‑Ping")
            sancionado = True
        except:
            sancionado = False

        # LOG Y MENSAJE
        if sancionado:
            embed = discord.Embed(
                title="<a:advertencia:1483506898509758690> Sanción aplicada",
                description=f"Usuario: {user.mention}\nAcción: **{action}**\nRazón: Ping prohibido",
                color=discord.Color(0x0A3D62) 
            )
        else:
            embed = discord.Embed(
                title="<:warnnormal:1491858539222925364> No se pudo sancionar",
                description=f"Detecté un ping prohibido de {user.mention}, pero no tengo permisos.",
                color=discord.Color(0x0A3D62)
            )

        await message.channel.send(embed=embed)
        await self.send_log(guild, cfg, embed)

# ============================
# SETUP
# ============================

async def setup(bot):
    await bot.add_cog(AntiPing(bot))
