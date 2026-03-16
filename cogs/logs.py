import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import datetime

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
# EMBEDS PRO
# ============================

def create_log_embed(event_key: str, title: str, description: str, guild: discord.Guild):
    fecha, hora = format_timestamp()

    embed = discord.Embed(
        title=f"{EVENT_ICONS.get(event_key, '📄')} {title}",
        description=description,
        color=EVENT_COLORS.get(event_key, discord.Color.blurple())
    )

    embed.add_field(name="📅 Fecha", value=fecha, inline=True)
    embed.add_field(name="🕒 Hora", value=hora, inline=True)
    embed.add_field(name="🏠 Servidor", value=f"{guild.name}\nID: `{guild.id}`", inline=False)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    return embed


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

        # Buscar categoría del evento
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
    # COMANDOS
    # ============================

    @app_commands.command(name="logs", description="Configura el sistema de logs")
    async def logs_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Usa los subcomandos:\n"
            "`/logs estado activar/desactivar`\n"
            "`/logs canal #canal`\n"
            "`/logs categoria <joins/roles/canales/mensajes/servidor> activar/desactivar`",
            ephemeral=True
        )

    # ESTADO
    @app_commands.command(name="logs_estado", description="Activa o desactiva los logs")
    async def logs_estado(self, interaction: discord.Interaction, estado: str):

        gid = str(interaction.guild.id)

        if gid not in self.logs:
            self.logs[gid] = {"enabled": False, "channel": None, "categories": {}}

        estado = estado.lower()
        if estado not in ["activar", "desactivar"]:
            return await interaction.response.send_message("Usa: activar / desactivar", ephemeral=True)

        self.logs[gid]["enabled"] = (estado == "activar")
        save_logs(self.logs)

        await interaction.response.send_message(
            f"🟢 Logs **{estado.upper()}**.",
            ephemeral=True
        )

    # CANAL
    @app_commands.command(name="logs_canal", description="Establece el canal de logs")
    async def logs_canal(self, interaction: discord.Interaction, canal: discord.TextChannel):

        gid = str(interaction.guild.id)

        if gid not in self.logs:
            self.logs[gid] = {"enabled": False, "channel": None, "categories": {}}

        self.logs[gid]["channel"] = canal.id
        save_logs(self.logs)

        await interaction.response.send_message(
            f"📌 Canal de logs establecido en {canal.mention}",
            ephemeral=True
        )

    # CATEGORÍAS
    @app_commands.command(name="logs_categoria", description="Activa o desactiva una categoría de logs")
    async def logs_categoria(self, interaction: discord.Interaction, categoria: str, estado: str):

        categoria = categoria.lower()
        estado = estado.lower()

        if categoria not in CATEGORIES:
            return await interaction.response.send_message(
                f"Categorías válidas: {', '.join(CATEGORIES.keys())}",
                ephemeral=True
            )

        if estado not in ["activar", "desactivar"]:
            return await interaction.response.send_message("Usa: activar / desactivar", ephemeral=True)

        gid = str(interaction.guild.id)

        if gid not in self.logs:
            self.logs[gid] = {"enabled": False, "channel": None, "categories": {}}

        self.logs[gid]["categories"][categoria] = (estado == "activar")
        save_logs(self.logs)

        await interaction.response.send_message(
            f"📁 Categoría **{categoria}** {estado.upper()}",
            ephemeral=True
        )


    # ============================
    # EVENTOS (SE MANTIENEN IGUAL)
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member):
        desc = f"👤 Usuario: {member.mention}\n🆔 `{member.id}`"
        embed = create_log_embed("join", "Usuario Entró", desc, member.guild)
        await self.send_log(member.guild, embed, "join")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        desc = f"👤 Usuario: {member.mention}\n🆔 `{member.id}`"
        embed = create_log_embed("leave", "Usuario Salió", desc, member.guild)
        await self.send_log(member.guild, embed, "leave")

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        desc = f"👤 Usuario: {user.mention}\n🆔 `{user.id}`"
        embed = create_log_embed("ban", "Usuario Baneado", desc, guild)
        await self.send_log(guild, embed, "ban")

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        desc = f"👤 Usuario: {user.mention}\n🆔 `{user.id}`"
        embed = create_log_embed("unban", "Usuario Desbaneado", desc, guild)
        await self.send_log(guild, embed, "unban")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild or message.author.bot:
            return
        desc = f"👤 Autor: {message.author.mention}\n💬 Contenido:\n{message.content}"
        embed = create_log_embed("msg_delete", "Mensaje Eliminado", desc, message.guild)
        await self.send_log(message.guild, embed, "msg_delete")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not before.guild or before.author.bot:
            return
        if before.content == after.content:
            return
        desc = f"✏️ Antes:\n{before.content}\n\n✏️ Después:\n{after.content}"
        embed = create_log_embed("msg_edit", "Mensaje Editado", desc, before.guild)
        await self.send_log(before.guild, embed, "msg_edit")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        guild = after.guild

        # Rol añadido
        if len(after.roles) > len(before.roles):
            role = next(r for r in after.roles if r not in before.roles)
            desc = f"➕ Rol añadido: {role.mention}"
            embed = create_log_embed("role_add", "Rol Añadido", desc, guild)
            await self.send_log(guild, embed, "role_add")

        # Rol quitado
        elif len(after.roles) < len(before.roles):
            role = next(r for r in before.roles if r not in after.roles)
            desc = f"➖ Rol quitado: {role.mention}"
            embed = create_log_embed("role_remove", "Rol Quitado", desc, guild)
            await self.send_log(guild, embed, "role_remove")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        desc = f"📁 Canal creado: `{channel.name}`"
        embed = create_log_embed("channel_create", "Canal Creado", desc, channel.guild)
        await self.send_log(channel.guild, embed, "channel_create")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        desc = f"🗑️ Canal eliminado: `{channel.name}`"
        embed = create_log_embed("channel_delete", "Canal Eliminado", desc, channel.guild)
        await self.send_log(channel.guild, embed, "channel_delete")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.name != after.name:
            desc = f"✏️ Renombrado: `{before.name}` → `{after.name}`"
            embed = create_log_embed("channel_update", "Canal Renombrado", desc, after.guild)
            await self.send_log(after.guild, embed, "channel_update")

        if before.category != after.category:
            desc = f"📂 Categoría cambiada"
            embed = create_log_embed("channel_update", "Categoría Cambiada", desc, after.guild)
            await self.send_log(after.guild, embed, "channel_update")

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.premium_subscription_count != after.premium_subscription_count:
            desc = f"💎 Boost cambiado"
            embed = create_log_embed("boost", "Boost del Servidor", desc, after)
            await self.send_log(after, embed, "boost")

        if before.name != after.name:
            desc = f"🏷️ Nombre cambiado"
            embed = create_log_embed("server_update", "Nombre del Servidor Cambiado", desc, after)
            await self.send_log(after, embed, "server_update")

        if before.icon != after.icon:
            desc = f"🖼️ Icono cambiado"
            embed = create_log_embed("server_update", "Icono del Servidor Cambiado", desc, after)
            await self.send_log(after, embed, "server_update")


async def setup(bot):
    await bot.add_cog(UltraLogs(bot))
