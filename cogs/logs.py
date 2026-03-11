import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import datetime


LOGS_FILE = "logs_config.json"


# ============================
# JSON SEGURO Y AUTOCORREGIDO
# ============================

def load_logs():
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}

    try:
        with open(LOGS_FILE, "r") as f:
            data = json.load(f)
    except:
        with open(LOGS_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}

    for guild_id, cfg in list(data.items()):
        if not isinstance(cfg, dict):
            data[guild_id] = {}

        cfg.setdefault("enabled", False)
        cfg.setdefault("channel", None)
        cfg.setdefault("events", {})

    return data


def save_logs(data):
    with open(LOGS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# FORMATEADORES PROFESIONALES
# ============================

def format_timestamp():
    now = datetime.datetime.now()
    fecha = now.strftime("%d/%m/%Y")
    hora = now.strftime("%H:%M:%S")
    return fecha, hora


def format_id(obj):
    return f"`{obj.id}`" if obj else "`N/A`"


def safe_name(obj):
    return obj.name if obj else "Desconocido"


def safe_mention(obj):
    try:
        return obj.mention
    except:
        return "N/A"


# ============================
# SISTEMA DE COLORES POR EVENTO
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
    "command": discord.Color.blue(),
    "emoji_add": discord.Color.green(),
    "emoji_remove": discord.Color.red(),
    "emoji_update": discord.Color.yellow(),
    "invite_create": discord.Color.green(),
    "invite_delete": discord.Color.red(),
    "thread_create": discord.Color.green(),
    "thread_update": discord.Color.yellow(),
}


# ============================
# ICONOS PROFESIONALES
# ============================

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
    "command": "📌",
    "emoji_add": "😃",
    "emoji_remove": "❌",
    "emoji_update": "✏️",
    "invite_create": "🔗",
    "invite_delete": "❌",
    "thread_create": "🧵",
    "thread_update": "✏️",
}


# ============================
# GENERADOR DE EMBEDS ULTRA PRO
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
# COG BASE
# ============================

class UltraLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logs = load_logs()

        # 🔥 YA NO SE MEZCLA CON ANTI-LINKS
        self.ulog_pages = {}   # antes era user_pages


    # ============================
    # Enviar log
    # ============================

    async def send_log(self, guild: discord.Guild, embed: discord.Embed, event_key: str):
        guild_id = str(guild.id)

        if guild_id not in self.logs:
            return

        cfg = self.logs[guild_id]

        if not cfg.get("enabled", False):
            return

        if not cfg["events"].get(event_key, True):
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
    # EMBEDS DEL PANEL
    # ============================

    def panel_embed(self, page: int):
        titles = {
            1: "⚙️ Configuración General",
            2: "🧍 Eventos de Usuarios",
            3: "💬 Eventos de Mensajes",
            4: "🛡️ Eventos de Roles",
            5: "📁 Eventos de Canales",
            6: "✨ Eventos Avanzados"
        }

        descriptions = {
            1: "Selecciona el canal de logs y activa/desactiva el sistema.",
            2: "Configura entradas, salidas, baneos, unbaneos y cambios de usuario.",
            3: "Configura mensajes eliminados, editados, con archivos, stickers, etc.",
            4: "Configura creación, eliminación y cambios de roles.",
            5: "Configura creación, eliminación y cambios de canales.",
            6: "Configura boosts, invites, threads, emojis y comandos."
        }

        embed = discord.Embed(
            title=titles.get(page, "Panel"),
            description=descriptions.get(page, ""),
            color=discord.Color.blurple()
        )

        embed.set_footer(text=f"Página {page}/6")
        return embed


    # ============================
    # SELECT DE EVENTOS POR PÁGINA
    # ============================

    def event_options(self, page: int):
        if page == 2:
            return [
                ("joins", "Entradas"),
                ("leaves", "Salidas"),
                ("bans", "Baneos"),
                ("unbans", "Unbaneos"),
                ("nick_change", "Cambio de nick"),
                ("avatar_change", "Cambio de avatar"),
            ]

        if page == 3:
            return [
                ("messages_delete", "Mensajes eliminados"),
                ("messages_edit", "Mensajes editados"),
                ("messages_files", "Mensajes con archivos"),
                ("messages_stickers", "Mensajes con stickers"),
                ("messages_links", "Mensajes con links"),
            ]

        if page == 4:
            return [
                ("roles_add", "Rol añadido"),
                ("roles_remove", "Rol quitado"),
                ("roles_create", "Rol creado"),
                ("roles_delete", "Rol eliminado"),
                ("roles_update", "Rol actualizado"),
            ]

        if page == 5:
            return [
                ("channels_create", "Canal creado"),
                ("channels_delete", "Canal eliminado"),
                ("channels_update", "Canal actualizado"),
                ("channels_perms", "Permisos cambiados"),
            ]

        if page == 6:
            return [
                ("boosts", "Boosts"),
                ("invites_create", "Invitación creada"),
                ("invites_delete", "Invitación eliminada"),
                ("threads_create", "Thread creado"),
                ("threads_update", "Thread actualizado"),
                ("emoji_add", "Emoji añadido"),
                ("emoji_remove", "Emoji eliminado"),
                ("emoji_update", "Emoji actualizado"),
                ("commands", "Comandos usados"),
            ]

        return []


    def build_event_select(self, guild_id: str, page: int):
        options = []
        current = self.logs[guild_id]["events"]

        for key, label in self.event_options(page):
            options.append(
                discord.SelectOption(
                    label=label,
                    value=key,
                    default=current.get(key, True)
                )
            )

        return discord.ui.Select(
            placeholder="Selecciona eventos para activar/desactivar",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id=f"ulog_events_page_{page}"   # 🔥 ID único
        )


    # ============================
    # BOTONES PRINCIPALES
    # ============================

    def main_buttons(self, guild_id: str):
        enabled = self.logs[guild_id]["enabled"]

        btn_toggle = discord.ui.Button(
            label="🟢 Activar Logs" if not enabled else "🔴 Desactivar Logs",
            style=discord.ButtonStyle.green if not enabled else discord.ButtonStyle.red,
            custom_id="ulog_toggle"   # 🔥 ID único
        )

        btn_save = discord.ui.Button(
            label="💾 Guardar",
            style=discord.ButtonStyle.blurple,
            custom_id="ulog_save"     # 🔥 ID único
        )

        return btn_toggle, btn_save


    # ============================
    # BOTONES DE NAVEGACIÓN
    # ============================

    def nav_buttons(self, page: int):
        buttons = []

        if page > 1:
            buttons.append(discord.ui.Button(
                label="⬅️ Anterior",
                style=discord.ButtonStyle.secondary,
                custom_id="ulog_prev_page"   # 🔥 ID único
            ))

        if page < 6:
            buttons.append(discord.ui.Button(
                label="➡️ Siguiente",
                style=discord.ButtonStyle.secondary,
                custom_id="ulog_next_page"   # 🔥 ID único
            ))

        return buttons


    # ============================
    # PANEL PRINCIPAL
    # ============================

    async def open_panel(self, interaction: discord.Interaction, page: int = 1):
        guild_id = str(interaction.guild.id)

        embed = self.panel_embed(page)
        view = discord.ui.View(timeout=300)

        if page == 1:
            channel_select = discord.ui.ChannelSelect(
                placeholder="Selecciona el canal de logs",
                channel_types=[discord.ChannelType.text],
                custom_id="ulog_select_channel"   # 🔥 ID único
            )
            view.add_item(channel_select)

        else:
            view.add_item(self.build_event_select(guild_id, page))

        btn_toggle, btn_save = self.main_buttons(guild_id)
        view.add_item(btn_toggle)
        view.add_item(btn_save)

        for btn in self.nav_buttons(page):
            view.add_item(btn)

        self.ulog_pages[interaction.user.id] = page

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


    # ============================
    # COMANDO /logs
    # ============================

    @app_commands.command(name="logs", description="Abre el panel de configuración de logs")
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_cmd(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)

        if guild_id not in self.logs:
            self.logs[guild_id] = {
                "enabled": False,
                "channel": None,
                "events": {}
            }
            save_logs(self.logs)

        await self.open_panel(interaction, page=1) 



        
# ============================
    # LISTENER DE COMPONENTES
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        if interaction.type != discord.InteractionType.component:
            return

        custom = interaction.data.get("custom_id")
        user_id = interaction.user.id

        # 🔥 Solo responder si pertenece al panel de logs
        if user_id not in self.ulog_pages:
            return

        page = self.ulog_pages[user_id]
        guild_id = str(interaction.guild.id)

        # Navegación
        if custom == "ulog_next_page":
            page = min(6, page + 1)
            self.ulog_pages[user_id] = page
            return await self.update_panel(interaction, page)

        if custom == "ulog_prev_page":
            page = max(1, page - 1)
            self.ulog_pages[user_id] = page
            return await self.update_panel(interaction, page)

        # Activar / desactivar logs
        if custom == "ulog_toggle":
            self.logs[guild_id]["enabled"] = not self.logs[guild_id]["enabled"]
            save_logs(self.logs)
            return await self.update_panel(interaction, page)

        # Guardar
        if custom == "ulog_save":
            save_logs(self.logs)
            return await interaction.response.send_message(
                "💾 Configuración guardada.",
                ephemeral=True
            )

        # Selección de canal
        if custom == "ulog_select_channel":
            channel_id = int(interaction.data["values"][0])
            self.logs[guild_id]["channel"] = channel_id
            save_logs(self.logs)
            return await self.update_panel(interaction, page)

        # Selección de eventos
        if custom.startswith("ulog_events_page_"):
            selected = interaction.data.get("values", [])
            all_events = [key for key, _ in self.event_options(page)]

            for ev in all_events:
                self.logs[guild_id]["events"][ev] = ev in selected

            save_logs(self.logs)
            return await self.update_panel(interaction, page)


    # ============================
    # ACTUALIZAR PANEL
    # ============================

    async def update_panel(self, interaction: discord.Interaction, page: int):
        embed = self.panel_embed(page)
        view = discord.ui.View(timeout=300)

        guild_id = str(interaction.guild.id)

        if page == 1:
            channel_select = discord.ui.ChannelSelect(
                placeholder="Selecciona el canal de logs",
                channel_types=[discord.ChannelType.text],
                custom_id="ulog_select_channel"
            )
            view.add_item(channel_select)
        else:
            view.add_item(self.build_event_select(guild_id, page))

        btn_toggle, btn_save = self.main_buttons(guild_id)
        view.add_item(btn_toggle)
        view.add_item(btn_save)

        for btn in self.nav_buttons(page):
            view.add_item(btn)

        await interaction.response.edit_message(embed=embed, view=view)


    # ============================
    # EVENTOS — USUARIOS
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild

        fecha_creacion = member.created_at.strftime("%d/%m/%Y — %H:%M:%S")
        antiguedad = (discord.utils.utcnow() - member.created_at).days

        desc = (
            f"👤 **Usuario:** {member.mention}\n"
            f"🆔 **ID:** `{member.id}`\n\n"
            f"📅 **Cuenta creada:** {fecha_creacion}\n"
            f"📌 **Antigüedad:** {antiguedad} días"
        )

        embed = create_log_embed("join", "Usuario Entró", desc, guild)
        await self.send_log(guild, embed, "joins")


    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild

        desc = (
            f"👤 **Usuario:** {member.mention}\n"
            f"🆔 **ID:** `{member.id}`"
        )

        embed = create_log_embed("leave", "Usuario Salió", desc, guild)
        await self.send_log(guild, embed, "leaves")


    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        desc = (
            f"👤 **Usuario:** {user.mention}\n"
            f"🆔 **ID:** `{user.id}`"
        )

        embed = create_log_embed("ban", "Usuario Baneado", desc, guild)
        await self.send_log(guild, embed, "bans")


    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        desc = (
            f"👤 **Usuario:** {user.mention}\n"
            f"🆔 **ID:** `{user.id}`"
        )

        embed = create_log_embed("unban", "Usuario Desbaneado", desc, guild)
        await self.send_log(guild, embed, "unbans")


    # ============================
    # CAMBIO DE NICK / AVATAR
    # ============================

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        guild = after.guild

        # Cambio de nick
        if before.nick != after.nick:
            desc = (
                f"👤 **Usuario:** {after.mention}\n"
                f"🆔 **ID:** `{after.id}`\n\n"
                f"✏️ **Antes:** `{before.nick}`\n"
                f"✏️ **Después:** `{after.nick}`"
            )
            embed = create_log_embed("nick_change", "Cambio de Nick", desc, guild)
            await self.send_log(guild, embed, "nick_change")

        # Cambio de avatar
        if before.avatar != after.avatar:
            desc = (
                f"👤 **Usuario:** {after.mention}\n"
                f"🆔 **ID:** `{after.id}`\n\n"
                f"🖼️ **Avatar cambiado**"
            )
            embed = create_log_embed("avatar_change", "Cambio de Avatar", desc, guild)

            if after.avatar:
                embed.set_thumbnail(url=after.avatar.url)

            await self.send_log(guild, embed, "avatar_change")


    # ============================
    # EVENTOS — ROLES
    # ============================

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        guild = after.guild

        # ROLES AÑADIDOS
        if len(after.roles) > len(before.roles):
            role = next(r for r in after.roles if r not in before.roles)

            desc = (
                f"👤 **Usuario:** {after.mention}\n"
                f"🆔 **ID:** `{after.id}`\n\n"
                f"➕ **Rol añadido:** {role.mention}\n"
                f"🆔 **ID del rol:** `{role.id}`"
            )

            embed = create_log_embed("role_add", "Rol Añadido", desc, guild)
            await self.send_log(guild, embed, "roles_add")

        # ROLES QUITADOS
        elif len(after.roles) < len(before.roles):
            role = next(r for r in before.roles if r not in after.roles)

            desc = (
                f"👤 **Usuario:** {after.mention}\n"
                f"🆔 **ID:** `{after.id}`\n\n"
                f"➖ **Rol quitado:** {role.mention}\n"
                f"🆔 **ID del rol:** `{role.id}`"
            )

            embed = create_log_embed("role_remove", "Rol Quitado", desc, guild)
            await self.send_log(guild, embed, "roles_remove")




# ============================
    # EVENTOS — MENSAJES
    # ============================

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):

        if not message.guild or message.author.bot:
            return

        guild = message.guild

        desc = (
            f"👤 **Autor:** {message.author.mention}\n"
            f"🆔 **ID:** `{message.author.id}`\n\n"
            f"💬 **Mensaje ID:** `{message.id}`\n"
            f"📍 **Canal:** {message.channel.mention} (`{message.channel.id}`)\n\n"
            f"📄 **Contenido:**\n{message.content or '*Vacío*'}"
        )

        embed = create_log_embed("msg_delete", "Mensaje Eliminado", desc, guild)

        await self.send_log(guild, embed, "messages_delete")


    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):

        if not before.guild or before.author.bot:
            return

        if before.content == after.content:
            return

        guild = before.guild

        desc = (
            f"👤 **Autor:** {before.author.mention}\n"
            f"🆔 **ID:** `{before.author.id}`\n\n"
            f"💬 **Mensaje ID:** `{before.id}`\n"
            f"📍 **Canal:** {before.channel.mention} (`{before.channel.id}`)\n\n"
            f"✏️ **Antes:**\n{before.content or '*Vacío*'}\n\n"
            f"✏️ **Después:**\n{after.content or '*Vacío*'}"
        )

        embed = create_log_embed("msg_edit", "Mensaje Editado", desc, guild)

        await self.send_log(guild, embed, "messages_edit")


    # ============================
    # EVENTOS — CANALES
    # ============================

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild

        desc = (
            f"📁 **Canal creado**\n\n"
            f"📌 **Nombre:** `{channel.name}`\n"
            f"🆔 **ID:** `{channel.id}`\n"
            f"📂 **Categoría:** {channel.category.name if channel.category else 'Ninguna'}"
        )

        embed = create_log_embed("channel_create", "Canal Creado", desc, guild)
        await self.send_log(guild, embed, "channels_create")


    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild

        desc = (
            f"🗑️ **Canal eliminado**\n\n"
            f"📌 **Nombre:** `{channel.name}`\n"
            f"🆔 **ID:** `{channel.id}`"
        )

        embed = create_log_embed("channel_delete", "Canal Eliminado", desc, guild)
        await self.send_log(guild, embed, "channels_delete")


    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        guild = after.guild

        # Renombrado
        if before.name != after.name:
            desc = (
                f"✏️ **Canal renombrado**\n\n"
                f"📌 **Antes:** `{before.name}`\n"
                f"📌 **Después:** `{after.name}`\n"
                f"🆔 **ID:** `{after.id}`"
            )
            embed = create_log_embed("channel_update", "Canal Renombrado", desc, guild)
            await self.send_log(guild, embed, "channels_update")

        # Cambio de categoría
        if before.category != after.category:
            desc = (
                f"📂 **Cambio de categoría**\n\n"
                f"📌 **Canal:** `{after.name}` (`{after.id}`)\n"
                f"📁 **Antes:** {before.category.name if before.category else 'Ninguna'}\n"
                f"📁 **Después:** {after.category.name if after.category else 'Ninguna'}"
            )
            embed = create_log_embed("channel_update", "Categoría Cambiada", desc, guild)
            await self.send_log(guild, embed, "channels_update")


    # ============================
    # EVENTOS — SERVIDOR
    # ============================

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):

        # Boosts
        if before.premium_subscription_count != after.premium_subscription_count:
            desc = (
                f"💎 **Boost actualizado**\n\n"
                f"📌 **Antes:** {before.premium_subscription_count}\n"
                f"📌 **Después:** {after.premium_subscription_count}"
            )
            embed = create_log_embed("boost", "Boost del Servidor", desc, after)
            await self.send_log(after, embed, "boosts")

        # Nombre del servidor
        if before.name != after.name:
            desc = (
                f"🏷️ **Nombre cambiado**\n\n"
                f"📌 **Antes:** `{before.name}`\n"
                f"📌 **Después:** `{after.name}`"
            )
            embed = create_log_embed("server_update", "Nombre del Servidor Cambiado", desc, after)
            await self.send_log(after, embed, "server_update")

        # Icono
        if before.icon != after.icon:
            desc = (
                f"🖼️ **Icono cambiado**\n\n"
                f"📌 **Servidor:** `{after.name}`"
            )
            embed = create_log_embed("server_update", "Icono del Servidor Cambiado", desc, after)
            if after.icon:
                embed.set_thumbnail(url=after.icon.url)
            await self.send_log(after, embed, "server_update")

        # Banner
        if before.banner != after.banner:
            desc = (
                f"🖼️ **Banner cambiado**\n\n"
                f"📌 **Servidor:** `{after.name}`"
            )
            embed = create_log_embed("server_update", "Banner del Servidor Cambiado", desc, after)
            await self.send_log(after, embed, "server_update")


    # ============================
    # EVENTOS — EMOJIS
    # ============================

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):

        before_ids = {e.id: e for e in before}
        after_ids = {e.id: e for e in after}

        # Emoji añadido
        for emoji in after:
            if emoji.id not in before_ids:
                desc = (
                    f"😃 **Emoji añadido**\n\n"
                    f"📌 **Nombre:** `{emoji.name}`\n"
                    f"🆔 **ID:** `{emoji.id}`"
                )
                embed = create_log_embed("emoji_add", "Emoji Añadido", desc, guild)
                await self.send_log(guild, embed, "emoji_add")

        # Emoji eliminado
        for emoji in before:
            if emoji.id not in after_ids:
                desc = (
                    f"❌ **Emoji eliminado**\n\n"
                    f"📌 **Nombre:** `{emoji.name}`\n"
                    f"🆔 **ID:** `{emoji.id}`"
                )
                embed = create_log_embed("emoji_remove", "Emoji Eliminado", desc, guild)
                await self.send_log(guild, embed, "emoji_remove")

        # Emoji actualizado
        for emoji in after:
            if emoji.id in before_ids and emoji.name != before_ids[emoji.id].name:
                desc = (
                    f"✏️ **Emoji actualizado**\n\n"
                    f"📌 **Antes:** `{before_ids[emoji.id].name}`\n"
                    f"📌 **Después:** `{emoji.name}`"
                )
                embed = create_log_embed("emoji_update", "Emoji Actualizado", desc, guild)
                await self.send_log(guild, embed, "emoji_update")


    # ============================
    # EVENTOS — INVITACIONES
    # ============================

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        guild = invite.guild

        desc = (
            f"🔗 **Invitación creada**\n\n"
            f"📌 **Código:** `{invite.code}`\n"
            f"📍 **Canal:** {invite.channel.mention}\n"
            f"👤 **Creador:** {invite.inviter.mention if invite.inviter else 'Desconocido'}"
        )

        embed = create_log_embed("invite_create", "Invitación Creada", desc, guild)
        await self.send_log(guild, embed, "invites_create")


    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        guild = invite.guild

        desc = (
            f"❌ **Invitación eliminada**\n\n"
            f"📌 **Código:** `{invite.code}`\n"
            f"📍 **Canal:** {invite.channel.mention}"
        )

        embed = create_log_embed("invite_delete", "Invitación Eliminada", desc, guild)
        await self.send_log(guild, embed, "invites_delete")


    # ============================
    # EVENTOS — THREADS
    # ============================

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        guild = thread.guild

        desc = (
            f"🧵 **Thread creado**\n\n"
            f"📌 **Nombre:** `{thread.name}`\n"
            f"🆔 **ID:** `{thread.id}`\n"
            f"📍 **Canal padre:** {thread.parent.mention}"
        )

        embed = create_log_embed("thread_create", "Thread Creado", desc, guild)
        await self.send_log(guild, embed, "threads_create")


    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        guild = after.guild

        if before.archived != after.archived:
            estado = "Archivado" if after.archived else "Desarchivado"

            desc = (
                f"📌 **Thread:** `{after.name}` (`{after.id}`)\n"
                f"📁 **Estado:** {estado}"
            )

            embed = create_log_embed("thread_update", "Thread Actualizado", desc, guild)
            await self.send_log(guild, embed, "threads_update")


    # ============================
    # EVENTOS — COMANDOS USADOS
    # ============================

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command):

        guild = interaction.guild
        if not guild:
            return

        fecha, hora = format_timestamp()

        desc = (
            f"📌 **Comando usado:** `/{command.name}`\n\n"
            f"👤 **Usuario:** {interaction.user.mention}\n"
            f"🆔 **ID:** `{interaction.user.id}`\n"
            f"📍 **Canal:** {interaction.channel.mention} (`{interaction.channel.id}`)\n\n"
            f"📅 **Fecha**\n{fecha}\n\n"
            f"🕒 **Hora**\n{hora}\n\n"
            f"🏠 **Servidor**\n{guild.name}\n"
            f"ID: `{guild.id}`"
        )

        embed = discord.Embed(
            title="📌 Comando Usado",
            description=desc,
            color=discord.Color.blue()
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await self.send_log(guild, embed, "commands")

# ============================
# SETUP DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(UltraLogs(bot))
