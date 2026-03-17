import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import datetime
from typing import Optional

LOGS_FILE = "logs_config.json"

# ============================
# JSON SEGURO
# ============================

def load_logs():
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}

    try:
        with open(LOGS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_logs(data):
    with open(LOGS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# FORMATEADORES
# ============================

def format_timestamp():
    now = datetime.datetime.now()
    return now.strftime("%d/%m/%Y"), now.strftime("%H:%M:%S")


# ============================
# COLORES E ICONOS
# ============================

EVENT_COLORS = {
    "join": discord.Color.green(),
    "leave": discord.Color.red(),
    "ban": discord.Color.dark_red(),
    "unban": discord.Color.green(),
    "msg_delete": discord.Color.red(),
    "msg_edit": discord.Color.yellow(),
    "role_add": discord.Color.green(),
    "role_remove": discord.Color.red(),
    "channel_create": discord.Color.green(),
    "channel_delete": discord.Color.red(),
    "channel_update": discord.Color.yellow(),
    "boost": discord.Color.magenta(),
    "server_update": discord.Color.blue(),
}

EVENT_ICONS = {
    "join": "🟢",
    "leave": "🔴",
    "ban": "🔨",
    "unban": "♻️",
    "msg_delete": "🗑️",
    "msg_edit": "✏️",
    "role_add": "➕",
    "role_remove": "➖",
    "channel_create": "📁",
    "channel_delete": "🗑️",
    "channel_update": "✏️",
    "boost": "💎",
    "server_update": "🖼️",
}


# ============================
# CATEGORÍAS
# ============================

CATEGORIES = {
    "joins": ["join", "leave", "ban", "unban"],
    "roles": ["role_add", "role_remove"],
    "canales": ["channel_create", "channel_delete", "channel_update"],
    "mensajes": ["msg_delete", "msg_edit"],
    "servidor": ["boost", "server_update"],
}


# ============================
# EMBEDS BASE
# ============================

def create_log_embed(event_key: str, title: str, guild: discord.Guild):
    fecha, hora = format_timestamp()

    embed = discord.Embed(
        title=f"{EVENT_ICONS.get(event_key, '📄')} {title}",
        color=EVENT_COLORS.get(event_key, discord.Color.blurple())
    )

    embed.add_field(name="📅 Fecha", value=fecha, inline=True)
    embed.add_field(name="🕒 Hora", value=hora, inline=True)
    embed.add_field(name="🏠 Servidor", value=f"{guild.name}\nID: `{guild.id}`", inline=False)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    return embed


def add_user_block(embed: discord.Embed, user: discord.abc.User | discord.Member, member: Optional[discord.Member] = None):
    embed.add_field(name="👤 Usuario", value=f"{user.mention}\n`{user}`", inline=False)
    embed.add_field(name="🆔 Usuario ID", value=f"`{user.id}`", inline=True)
    embed.add_field(name="🤖 Bot", value="Sí" if user.bot else "No", inline=True)

    created = user.created_at.strftime("%d/%m/%Y %H:%M:%S")
    embed.add_field(name="📆 Cuenta creada", value=created, inline=False)

    if member is not None:
        joined = member.joined_at.strftime("%d/%m/%Y %H:%M:%S") if member.joined_at else "Desconocido"
        embed.add_field(name="📥 Entró al servidor", value=joined, inline=False)

    if user.avatar:
        embed.set_author(name=str(user), icon_url=user.avatar.url)


def add_message_block(embed: discord.Embed, message: discord.Message, deleted: bool = False):
    embed.add_field(
        name="💬 Contenido",
        value=message.content if message.content else "*Sin contenido de texto*",
        inline=False
    )
    embed.add_field(
        name="📨 Mensaje ID",
        value=f"`{message.id}`",
        inline=True
    )
    embed.add_field(
        name="📺 Canal",
        value=f"{message.channel.mention}\nID: `{message.channel.id}`",
        inline=True
    )

    if message.attachments:
        atts = "\n".join(f"- {a.filename} ({a.url})" for a in message.attachments)
        embed.add_field(name="📎 Adjuntos", value=atts[:1024], inline=False)

    if deleted:
        embed.set_footer(text="Mensaje eliminado")


# ============================
# COG PRINCIPAL
# ============================

class UltraLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logs = load_logs()

    # ============================
    # Enviar log
    # ============================

    async def send_log(self, guild: discord.Guild, embed: discord.Embed, event_key: str):
        gid = str(guild.id)

        if gid not in self.logs:
            return

        cfg = self.logs[gid]

        if not cfg.get("enabled", False):
            return

        for cat, events in CATEGORIES.items():
            if event_key in events:
                if not cfg["categories"].get(cat, True):
                    return

        channel_id = cfg.get("channel")
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            return

        try:
            await channel.send(embed=embed)
        except:
            pass

    # ============================
    # COMANDO ÚNICO /logs
    # ============================

    @app_commands.command(name="logs", description="Configura el sistema de logs completo")
    @app_commands.describe(
        estado="Activar o desactivar todos los logs",
        canal="Canal donde se enviarán los logs",
        joins="Logs de entradas, salidas, baneos y desbaneos",
        roles="Logs de roles añadidos/quitados",
        canales="Logs de canales creados/eliminados/actualizados",
        mensajes="Logs de mensajes eliminados/editados",
        servidor="Logs de boosts y cambios del servidor"
    )
    @app_commands.choices(
        estado=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ],
        joins=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ],
        roles=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ],
        canales=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ],
        mensajes=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ],
        servidor=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ]
    )
    async def logs_cmd(
        self,
        interaction: discord.Interaction,
        estado: Optional[app_commands.Choice[str]] = None,
        canal: Optional[discord.TextChannel] = None,
        joins: Optional[app_commands.Choice[str]] = None,
        roles: Optional[app_commands.Choice[str]] = None,
        canales: Optional[app_commands.Choice[str]] = None,
        mensajes: Optional[app_commands.Choice[str]] = None,
        servidor: Optional[app_commands.Choice[str]] = None
    ):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Solo administradores pueden usar este comando.",
                ephemeral=True
            )

        gid = str(interaction.guild.id)

        if gid not in self.logs:
            self.logs[gid] = {
                "enabled": False,
                "channel": None,
                "categories": {
                    "joins": True,
                    "roles": True,
                    "canales": True,
                    "mensajes": True,
                    "servidor": True
                }
            }

        cfg = self.logs[gid]
        changed = []

        if estado is not None:
            cfg["enabled"] = (estado.value == "activar")
            changed.append(f"Estado: **{estado.value.upper()}**")

        if canal is not None:
            cfg["channel"] = canal.id
            changed.append(f"Canal: {canal.mention}")

        if joins is not None:
            cfg["categories"]["joins"] = (joins.value == "activar")
            changed.append(f"Joins: **{joins.value.upper()}**")

        if roles is not None:
            cfg["categories"]["roles"] = (roles.value == "activar")
            changed.append(f"Roles: **{roles.value.upper()}**")

        if canales is not None:
            cfg["categories"]["canales"] = (canales.value == "activar")
            changed.append(f"Canales: **{canales.value.upper()}**")

        if mensajes is not None:
            cfg["categories"]["mensajes"] = (mensajes.value == "activar")
            changed.append(f"Mensajes: **{mensajes.value.upper()}**")

        if servidor is not None:
            cfg["categories"]["servidor"] = (servidor.value == "activar")
            changed.append(f"Servidor: **{servidor.value.upper()}**")

        save_logs(self.logs)

        if not changed:
            cfg_cat = cfg["categories"]
            resumen = (
                f"🟢 Estado: **{'ACTIVADO' if cfg['enabled'] else 'DESACTIVADO'}**\n"
                f"📌 Canal: {interaction.guild.get_channel(cfg['channel']).mention if cfg['channel'] else 'No configurado'}\n"
                f"📂 Joins: **{'ON' if cfg_cat.get('joins', True) else 'OFF'}**\n"
                f"📂 Roles: **{'ON' if cfg_cat.get('roles', True) else 'OFF'}**\n"
                f"📂 Canales: **{'ON' if cfg_cat.get('canales', True) else 'OFF'}**\n"
                f"📂 Mensajes: **{'ON' if cfg_cat.get('mensajes', True) else 'OFF'}**\n"
                f"📂 Servidor: **{'ON' if cfg_cat.get('servidor', True) else 'OFF'}**"
            )
            return await interaction.response.send_message(
                f"⚙️ Configuración actual de logs:\n{resumen}",
                ephemeral=True
            )

        texto = "✅ Configuración de logs actualizada:\n" + "\n".join(f"• {c}" for c in changed)
        await interaction.response.send_message(texto, ephemeral=True)

    # ============================
    # EVENTOS
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        embed = create_log_embed("join", "Usuario Entró", guild)
        add_user_block(embed, member, member)
        await self.send_log(guild, embed, "join")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        embed = create_log_embed("leave", "Usuario Salió", guild)
        add_user_block(embed, member, member)
        await self.send_log(guild, embed, "leave")

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        embed = create_log_embed("ban", "Usuario Baneado", guild)
        add_user_block(embed, user, None)
        await self.send_log(guild, embed, "ban")

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        embed = create_log_embed("unban", "Usuario Desbaneado", guild)
        add_user_block(embed, user, None)
        await self.send_log(guild, embed, "unban")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        guild = message.guild
        embed = create_log_embed("msg_delete", "Mensaje Eliminado", guild)
        add_user_block(embed, message.author, message.author if isinstance(message.author, discord.Member) else None)
        add_message_block(embed, message, deleted=True)
        await self.send_log(guild, embed, "msg_delete")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot:
            return
        if before.content == after.content and not before.attachments and not after.attachments:
            return

        guild = before.guild
        embed = create_log_embed("msg_edit", "Mensaje Editado", guild)
        add_user_block(embed, before.author, before.author if isinstance(before.author, discord.Member) else None)

        embed.add_field(name="📨 Mensaje ID", value=f"`{before.id}`", inline=True)
        embed.add_field(
            name="📺 Canal",
            value=f"{before.channel.mention}\nID: `{before.channel.id}`",
            inline=True
        )

        before_text = before.content if before.content else "*Sin contenido*"
        after_text = after.content if after.content else "*Sin contenido*"

        embed.add_field(name="✏️ Antes", value=before_text[:1024], inline=False)
        embed.add_field(name="✏️ Después", value=after_text[:1024], inline=False)

        await self.send_log(guild, embed, "msg_edit")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild

        if len(after.roles) > len(before.roles):
            role = next(r for r in after.roles if r not in before.roles)
            embed = create_log_embed("role_add", "Rol Añadido", guild)
            add_user_block(embed, after, after)
            embed.add_field(name="➕ Rol añadido", value=f"{role.mention}\nID: `{role.id}`", inline=False)
            await self.send_log(guild, embed, "role_add")

        elif len(after.roles) < len(before.roles):
            role = next(r for r in before.roles if r not in after.roles)
            embed = create_log_embed("role_remove", "Rol Quitado", guild)
            add_user_block(embed, after, after)
            embed.add_field(name="➖ Rol quitado", value=f"{role.mention}\nID: `{role.id}`", inline=False)
            await self.send_log(guild, embed, "role_remove")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        embed = create_log_embed("channel_create", "Canal Creado", guild)
        embed.add_field(name="📁 Canal", value=f"{getattr(channel, 'mention', '`Sin mención`')}\n`{channel.name}`", inline=False)
        embed.add_field(name="🆔 Canal ID", value=f"`{channel.id}`", inline=True)
        if channel.category:
            embed.add_field(name="📂 Categoría", value=f"{channel.category.name}\nID: `{channel.category.id}`", inline=True)
        await self.send_log(guild, embed, "channel_create")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        embed = create_log_embed("channel_delete", "Canal Eliminado", guild)
        embed.add_field(name="🗑️ Canal", value=f"`{channel.name}`", inline=False)
        embed.add_field(name="🆔 Canal ID", value=f"`{channel.id}`", inline=True)
        await self.send_log(guild, embed, "channel_delete")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        guild = after.guild
        cambios = []

        if before.name != after.name:
            cambios.append(f"Nombre: `{before.name}` → `{after.name}`")

        if getattr(before, "category", None) != getattr(after, "category", None):
            antes_cat = before.category.name if before.category else "Ninguna"
            despues_cat = after.category.name if after.category else "Ninguna"
            cambios.append(f"Categoría: `{antes_cat}` → `{despues_cat}`")

        if not cambios:
            return

        embed = create_log_embed("channel_update", "Canal Actualizado", guild)
        embed.add_field(
            name="📺 Canal",
            value=f"{getattr(after, 'mention', '`Sin mención`')}\n`{after.name}`\nID: `{after.id}`",
            inline=False
        )
        embed.add_field(
            name="✏️ Cambios",
            value="\n".join(f"• {c}" for c in cambios)[:1024],
            inline=False
        )
        await self.send_log(guild, embed, "channel_update")

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        cambios = []
        if before.name != after.name:
            cambios.append(f"Nombre: `{before.name}` → `{after.name}`")
        if before.icon != after.icon:
            cambios.append("Icono del servidor cambiado")
        if before.premium_subscription_count != after.premium_subscription_count:
            cambios.append(
                f"Boosts: `{before.premium_subscription_count}` → `{after.premium_subscription_count}`"
            )

        if not cambios:
            return

        embed = create_log_embed("server_update", "Servidor Actualizado", after)
        embed.add_field(
            name="✏️ Cambios",
            value="\n".join(f"• {c}" for c in cambios)[:1024],
            inline=False
        )
        await self.send_log(after, embed, "server_update")


async def setup(bot):
    await bot.add_cog(UltraLogs(bot)) 
