import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio


LOGS_FILE = "logs_config.json"


# ============================
# JSON LOADER
# ============================

def load_logs():  # ← FUNCIÓN CORREGIDA
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}

    with open(LOGS_FILE, "r") as f:
        try:
            data = json.load(f)
        except:
            return {}

    # 🔧 AUTOCORRECCIÓN DEL JSON
    # Si algún servidor tiene un valor inválido (int, string, etc),
    # lo repara automáticamente para evitar errores.
    for guild_id, value in list(data.items()):
        if not isinstance(value, dict):
            data[guild_id] = {
                "enabled": False,
                "channel": None,
                "events": {
                    "joins": True,
                    "leaves": True,
                    "bans": True,
                    "unbans": True,
                    "messages_delete": True,
                    "messages_edit": True,
                    "commands": True
                }
            }

    return data


def save_logs(data):  # ← ESTO NO SE TOCA
    with open(LOGS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# COG DE LOGS
# ============================

class LogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logs = load_logs()


    # ============================
    # Embeds por página
    # ============================

    def embed_page(self, page: int):
        if page == 1:
            embed = discord.Embed(
                title="⚙️ Configuración General",
                description="Selecciona el canal de logs y activa/desactiva el sistema.",
                color=discord.Color.blue()
            )
            return embed

        elif page == 2:
            embed = discord.Embed(
                title="🧍 Logs de Usuarios",
                description="Configura entradas, salidas, baneos y unbaneos.",
                color=discord.Color.green()
            )
            return embed

        elif page == 3:
            embed = discord.Embed(
                title="💬 Logs de Mensajes",
                description="Configura mensajes eliminados y editados.",
                color=discord.Color.yellow()
            )
            return embed

        elif page == 4:
            embed = discord.Embed(
                title="🛡️ Logs de Roles",
                description="Configura roles añadidos y eliminados.",
                color=discord.Color.purple()
            )
            return embed

        elif page == 5:
            embed = discord.Embed(
                title="📁 Logs de Canales",
                description="Configura creación, eliminación y renombrado de canales.",
                color=discord.Color.orange()
            )
            return embed

        elif page == 6:
            embed = discord.Embed(
                title="✨ Logs Avanzados",
                description="Configura boosts y comandos usados.",
                color=discord.Color.magenta()
            )
            return embed


    # ============================
    # Select de categorías por página
    # ============================

    def select_events(self, page: int, guild_id: str):

        options = []

        if page == 2:
            options = [
                discord.SelectOption(label="Entradas", value="joins"),
                discord.SelectOption(label="Salidas", value="leaves"),
                discord.SelectOption(label="Baneos", value="bans"),
                discord.SelectOption(label="Unbaneos", value="unbans"),
            ]

        elif page == 3:
            options = [
                discord.SelectOption(label="Mensajes eliminados", value="messages_delete"),
                discord.SelectOption(label="Mensajes editados", value="messages_edit"),
            ]

        elif page == 4:
            options = [
                discord.SelectOption(label="Rol añadido", value="roles_add"),
                discord.SelectOption(label="Rol quitado", value="roles_remove"),
            ]

        elif page == 5:
            options = [
                discord.SelectOption(label="Canal creado", value="channels_create"),
                discord.SelectOption(label="Canal eliminado", value="channels_delete"),
                discord.SelectOption(label="Canal renombrado", value="channels_update"),
            ]

        elif page == 6:
            options = [
                discord.SelectOption(label="Boosts", value="boosts"),
                discord.SelectOption(label="Comandos usados", value="commands"),
            ]

        # Estado actual
        selected = []
        if guild_id in self.logs:
            for event, enabled in self.logs[guild_id]["events"].items():
                if enabled:
                    selected.append(event)

        select = discord.ui.Select(
            placeholder="Selecciona eventos para activar/desactivar",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id=f"select_events_page_{page}"
        )

        return select


    # ============================
    # Botones de navegación
    # ============================

    def nav_buttons(self, page: int):
        buttons = []

        if page > 1:
            buttons.append(discord.ui.Button(
                label="⬅️ Anterior",
                style=discord.ButtonStyle.secondary,
                custom_id="prev_page"
            ))

        if page < 6:
            buttons.append(discord.ui.Button(
                label="➡️ Siguiente",
                style=discord.ButtonStyle.secondary,
                custom_id="next_page"
            ))

        return buttons


    # ============================
    # Botones principales
    # ============================

    def main_buttons(self, guild_id: str, page: int):

        enabled = self.logs.get(guild_id, {}).get("enabled", False)

        btn_enable = discord.ui.Button(
            label="🟢 Activar logs" if not enabled else "🔴 Desactivar logs",
            style=discord.ButtonStyle.green if not enabled else discord.ButtonStyle.red,
            custom_id="toggle_logs"
        )

        btn_save = discord.ui.Button(
            label="🔵 Guardar",
            style=discord.ButtonStyle.blurple,
            custom_id="save_logs"
        )

        btn_test = None
        if page == 6:
            btn_test = discord.ui.Button(
                label="🟣 Test Log",
                style=discord.ButtonStyle.blurple,
                custom_id="test_log"
            )

        return btn_enable, btn_save, btn_test


    # ============================
    # Construcción del panel
    # ============================

    async def build_panel(self, interaction: discord.Interaction, page: int):
        guild_id = str(interaction.guild.id)

        # Crear vista
        view = discord.ui.View(timeout=300)  # 5 minutos

        # Embeds por página
        embed = self.embed_page(page)

        # ============================
        # Página 1: Configuración general
        # ============================
        if page == 1:
            # Selector de canal
            channel_select = discord.ui.ChannelSelect(
                placeholder="Selecciona el canal de logs",
                channel_types=[discord.ChannelType.text],
                custom_id="select_channel"
            )
            view.add_item(channel_select)

            # Botones principales
            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # ============================
        # Páginas 2 a 6: Select de eventos
        # ============================
        else:
            select = self.select_events(page, guild_id)
            view.add_item(select)

            # Botones principales
            btn_enable, btn_save, btn_test = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

            if btn_test:
                view.add_item(btn_test)

        # ============================
        # Botones de navegación
        # ============================
        for btn in self.nav_buttons(page):
            view.add_item(btn)

        # Guardar la página actual en el estado del usuario
        if not hasattr(self, "user_pages"):
            self.user_pages = {}

        self.user_pages[interaction.user.id] = page

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


    # ============================
    # Comando /logs
    # ============================

    @app_commands.command(name="logs", description="Abre el panel de configuración de logs")
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_cmd(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)

        # Crear config si no existe
        if guild_id not in self.logs:
            self.logs[guild_id] = {
                "channel": None,
                "enabled": False,
                "events": {
                    "joins": True,
                    "leaves": True,
                    "bans": True,
                    "unbans": True,
                    "messages_delete": True,
                    "messages_edit": True,
                    "roles_add": True,
                    "roles_remove": True,
                    "channels_create": True,
                    "channels_delete": True,
                    "channels_update": True,
                    "boosts": True,
                    "commands": True
                }
            }
            save_logs(self.logs)

        # Abrir panel en página 1
        await self.build_panel(interaction, page=1)


    # ============================
    # Listener de componentes
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        if not interaction.type == discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id")
        user_id = interaction.user.id

        # Verificar que el usuario tenga una página activa
        if not hasattr(self, "user_pages") or user_id not in self.user_pages:
            return

        page = self.user_pages[user_id]
        guild_id = str(interaction.guild.id)

        # ============================
        # Navegación
        # ============================

        if custom_id == "next_page":
            page = min(6, page + 1)
            self.user_pages[user_id] = page
            return await self.update_panel(interaction, page)

        if custom_id == "prev_page":
            page = max(1, page - 1)
            self.user_pages[user_id] = page
            return await self.update_panel(interaction, page)

        # ============================
        # Activar / Desactivar logs
        # ============================

        if custom_id == "toggle_logs":
            current = self.logs[guild_id]["enabled"]
            self.logs[guild_id]["enabled"] = not current
            save_logs(self.logs)
            return await self.update_panel(interaction, page)

        # ============================
        # Guardar configuración
        # ============================

        if custom_id == "save_logs":
            save_logs(self.logs)
            return await interaction.response.send_message(
                "✅ Configuración guardada correctamente.",
                ephemeral=True
            )

        # ============================
        # Test Log
        # ============================

        if custom_id == "test_log":
            channel_id = self.logs[guild_id].get("channel")
            channel = interaction.guild.get_channel(channel_id)

            if not channel:
                return await interaction.response.send_message(
                    "❌ No hay canal configurado.",
                    ephemeral=True
                )

            embed = discord.Embed(
                title="🟣 Test Log",
                description="Este es un mensaje de prueba.",
                color=discord.Color.magenta()
            )
            await channel.send(embed=embed)

            return await interaction.response.send_message(
                "🟣 Test enviado correctamente.",
                ephemeral=True
            )

        # ============================
        # Selector de canal
        # ============================

        if custom_id == "select_channel":
            channel = interaction.data["values"][0]
            channel_obj = interaction.guild.get_channel(int(channel))

            self.logs[guild_id]["channel"] = channel_obj.id
            save_logs(self.logs)

            return await self.update_panel(interaction, page)

        # ============================
        # Select de eventos
        # ============================

        if custom_id.startswith("select_events_page_"):
            selected = interaction.data.get("values", [])

            # Resetear todos los eventos de esa página
            for event in self.logs[guild_id]["events"]:
                if event in selected:
                    self.logs[guild_id]["events"][event] = True
                else:
                    # Solo desactivar si pertenece a esta página
                    pass

            save_logs(self.logs)
            return await self.update_panel(interaction, page)


    # ============================
    # Actualizar panel sin recrearlo
    # ============================

    async def update_panel(self, interaction: discord.Interaction, page: int):
        embed = self.embed_page(page)
        view = discord.ui.View(timeout=300)

        guild_id = str(interaction.guild.id)

        # Página 1
        if page == 1:
            channel_select = discord.ui.ChannelSelect(
                placeholder="Selecciona el canal de logs",
                channel_types=[discord.ChannelType.text],
                custom_id="select_channel"
            )
            view.add_item(channel_select)

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Páginas 2 a 6
        else:
            select = self.select_events(page, guild_id)
            view.add_item(select)

            btn_enable, btn_save, btn_test = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

            if btn_test:
                view.add_item(btn_test)

        # Navegación
        for btn in self.nav_buttons(page):
            view.add_item(btn)

        await interaction.response.edit_message(embed=embed, view=view)


    # ============================
    # Función para enviar logs
    # ============================

    async def send_log(self, guild: discord.Guild, embed: discord.Embed, event_key: str):
        guild_id = str(guild.id)

        # Si no hay config → no enviar nada
        if guild_id not in self.logs:
            return

        config = self.logs[guild_id]

        # Logs desactivados
        if not config.get("enabled", False):
            return

        # Evento desactivado
        if not config["events"].get(event_key, False):
            return

        # Canal no configurado
        channel_id = config.get("channel")
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
    # EVENTOS DE LOGS
    # ============================

    # --- ENTRADAS ---
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(
            title="🟢 Usuario entró",
            description=f"{member.mention} ha entrado al servidor.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar)
        await self.send_log(member.guild, embed, "joins")


    # --- SALIDAS ---
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = discord.Embed(
            title="🔴 Usuario salió",
            description=f"{member.mention} ha salido del servidor.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.avatar)
        await self.send_log(member.guild, embed, "leaves")


    # --- BAN ---
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        embed = discord.Embed(
            title="🔨 Usuario baneado",
            description=f"{user.mention} fue baneado.",
            color=discord.Color.dark_red()
        )
        await self.send_log(guild, embed, "bans")


    # --- UNBAN ---
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        embed = discord.Embed(
            title="♻️ Usuario desbaneado",
            description=f"{user.mention} fue desbaneado.",
            color=discord.Color.green()
        )
        await self.send_log(guild, embed, "unbans")


    # --- MENSAJE ELIMINADO ---
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild or message.author.bot:
            return

        embed = discord.Embed(
            title="🗑️ Mensaje eliminado",
            color=discord.Color.red()
        )
        embed.add_field(name="Autor", value=message.author.mention)
        embed.add_field(name="Canal", value=message.channel.mention)
        embed.add_field(name="Contenido", value=message.content or "(vacío)", inline=False)

        await self.send_log(message.guild, embed, "messages_delete")


    # --- MENSAJE EDITADO ---
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not before.guild or before.author.bot:
            return
        if before.content == after.content:
            return

        embed = discord.Embed(
            title="✏️ Mensaje editado",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Autor", value=before.author.mention)
        embed.add_field(name="Canal", value=before.channel.mention)
        embed.add_field(name="Antes", value=before.content or "(vacío)", inline=False)
        embed.add_field(name="Después", value=after.content or "(vacío)", inline=False)

        await self.send_log(before.guild, embed, "messages_edit")


    # --- ROLES AÑADIDOS / QUITADOS ---
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Rol añadido
        if len(after.roles) > len(before.roles):
            rol = next(r for r in after.roles if r not in before.roles)

            embed = discord.Embed(
                title="➕ Rol añadido",
                description=f"{after.mention} recibió el rol **{rol.name}**",
                color=discord.Color.green()
            )
            await self.send_log(after.guild, embed, "roles_add")

        # Rol quitado
        elif len(after.roles) < len(before.roles):
            rol = next(r for r in before.roles if r not in after.roles)

            embed = discord.Embed(
                title="➖ Rol quitado",
                description=f"A {after.mention} le quitaron el rol **{rol.name}**",
                color=discord.Color.red()
            )
            await self.send_log(after.guild, embed, "roles_remove")


    # --- CANAL CREADO ---
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        embed = discord.Embed(
            title="📁 Canal creado",
            description=f"Se creó el canal {channel.mention}",
            color=discord.Color.green()
        )
        await self.send_log(channel.guild, embed, "channels_create")


    # --- CANAL ELIMINADO ---
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        embed = discord.Embed(
            title="🗑️ Canal eliminado",
            description=f"Se eliminó el canal **{channel.name}**",
            color=discord.Color.red()
        )
        await self.send_log(channel.guild, embed, "channels_delete")


    # --- CANAL RENOMBRADO ---
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.name != after.name:
            embed = discord.Embed(
                title="✏️ Canal renombrado",
                description=f"**{before.name}** → **{after.name}**",
                color=discord.Color.yellow()
            )
            await self.send_log(after.guild, embed, "channels_update")


    # --- BOOSTS ---
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.premium_subscription_count != after.premium_subscription_count:
            embed = discord.Embed(
                title="💎 Nuevo Boost",
                description=f"El servidor ahora tiene **{after.premium_subscription_count} boosts**",
                color=discord.Color.magenta()
            )
            await self.send_log(after, embed, "boosts")


    # --- COMANDOS USADOS ---
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction, command):
        embed = discord.Embed(
            title="📌 Comando usado",
            description=f"{interaction.user.mention} usó **/{command.name}**",
            color=discord.Color.blue()
        )
        await self.send_log(interaction.guild, embed, "commands")


# ============================
# SETUP DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(LogsCog(bot))