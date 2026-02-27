import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time
from datetime import timedelta

ANTISPAM_FILE = "antispam.json"

# ============================
# JSON LOADER
# ============================

def load_antispam():
    if not os.path.exists(ANTISPAM_FILE):
        with open(ANTISPAM_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}

    with open(ANTISPAM_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_antispam(data):
    with open(ANTISPAM_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ============================
# COG ANTI-SPAM
# ============================

class AntiSpamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_antispam()
        self.user_pages = {}
        self.user_messages = {}
        self.cooldowns = {}
        self.warned = {}  # usuario -> timestamp de última advertencia

    # ============================
    # Embeds por página
    # ============================

    def embed_page(self, page: int):
        if page == 1:
            return discord.Embed(
                title="⚙️ Configuración General",
                description=(
                    "Activa o desactiva el Anti‑Spam.\n"
                    "Configura la acción (mute/kick/ban/delete/warn).\n"
                    "Configura el tiempo del mute.\n"
                    "Configura roles autorizados para usar `/antispam`."
                ),
                color=discord.Color.blue()
            )

        elif page == 2:
            return discord.Embed(
                title="💬 Flood (Mensajes por segundo)",
                description="Controla cuántos mensajes se permiten en un intervalo.",
                color=discord.Color.green()
            )

        elif page == 3:
            return discord.Embed(
                title="🔠 Mayúsculas",
                description="Detecta abuso de mayúsculas.",
                color=discord.Color.orange()
            )

        elif page == 4:
            return discord.Embed(
                title="🔁 Mensajes repetidos",
                description="Detecta cuando un usuario repite mensajes.",
                color=discord.Color.purple()
            )

        elif page == 5:
            return discord.Embed(
                title="🛡️ Whitelist",
                description="Usuarios, roles y canales permitidos.",
                color=discord.Color.teal()
            )

        elif page == 6:
            return discord.Embed(
                title="🔧 Opciones avanzadas",
                description=(
                    "Cooldown por usuario.\n"
                    "Modo progresivo.\n"
                    "Test Anti‑Spam."
                ),
                color=discord.Color.magenta()
            )

    # ============================
    # Helper config
    # ============================

    def ensure_guild_config(self, guild_id: str):
        if guild_id not in self.config:
            self.config[guild_id] = {
                "enabled": False,
                "action": "mute",
                "mute_time": 600,
                "progressive": False,
                "allowed_roles": [],
                "whitelist_users": [],
                "whitelist_roles": [],
                "whitelist_channels": [],
                "flood": {"max_messages": 5, "interval": 4},
                "caps": {"enabled": True, "max_caps": 70},
                "repeat": {"enabled": True, "max_repeat": 2},
                "cooldown": 3
            }
            save_antispam(self.config)
        return self.config[guild_id]

    # ============================
    # Selects dinámicos (limitados a 25 opciones)
    # ============================

    def select_allowed_roles(self, guild: discord.Guild, guild_id: str):
        allowed = self.config[guild_id]["allowed_roles"]

        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id),
                default=(role.id in allowed)
            )
            for role in guild.roles if role.name != "@everyone"
        ][:25]

        max_values = len(options) if options else 1

        return discord.ui.Select(
            placeholder="Roles autorizados para usar /antispam",
            min_values=0,
            max_values=max_values,
            options=options or [discord.SelectOption(label="Sin roles", value="none", default=True)],
            custom_id="select_allowed_roles"
        )

    def select_whitelist_users(self, guild: discord.Guild, guild_id: str):
        allowed = self.config[guild_id]["whitelist_users"]

        options = [
            discord.SelectOption(
                label=member.name,
                value=str(member.id),
                default=(member.id in allowed)
            )
            for member in guild.members
        ][:25]

        max_values = len(options) if options else 1

        return discord.ui.Select(
            placeholder="Usuarios permitidos",
            min_values=0,
            max_values=max_values,
            options=options or [discord.SelectOption(label="Sin usuarios", value="none", default=True)],
            custom_id="select_whitelist_users"
        )

    def select_whitelist_roles(self, guild: discord.Guild, guild_id: str):
        allowed = self.config[guild_id]["whitelist_roles"]

        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id),
                default=(role.id in allowed)
            )
            for role in guild.roles if role.name != "@everyone"
        ][:25]

        max_values = len(options) if options else 1

        return discord.ui.Select(
            placeholder="Roles permitidos",
            min_values=0,
            max_values=max_values,
            options=options or [discord.SelectOption(label="Sin roles", value="none", default=True)],
            custom_id="select_whitelist_roles"
        )

    def select_whitelist_channels(self, guild: discord.Guild, guild_id: str):
        allowed = self.config[guild_id]["whitelist_channels"]

        options = [
            discord.SelectOption(
                label=channel.name,
                value=str(channel.id),
                default=(channel.id in allowed)
            )
            for channel in guild.text_channels
        ][:25]

        max_values = len(options) if options else 1

        return discord.ui.Select(
            placeholder="Canales permitidos",
            min_values=0,
            max_values=max_values,
            options=options or [discord.SelectOption(label="Sin canales", value="none", default=True)],
            custom_id="select_whitelist_channels"
        )

    # ============================
    # Botones principales
    # ============================

    def main_buttons(self, guild_id: str, page: int):
        enabled = self.config[guild_id]["enabled"]

        btn_enable = discord.ui.Button(
            label="🟢 Activar Anti‑Spam" if not enabled else "🔴 Desactivar Anti‑Spam",
            style=discord.ButtonStyle.green if not enabled else discord.ButtonStyle.red,
            custom_id="toggle_enabled"
        )

        btn_save = discord.ui.Button(
            label="💾 Guardar",
            style=discord.ButtonStyle.blurple,
            custom_id="save_antispam"
        )

        btn_test = None
        if page == 6:
            btn_test = discord.ui.Button(
                label="🧪 Test Anti‑Spam",
                style=discord.ButtonStyle.blurple,
                custom_id="test_antispam"
            )

        return btn_enable, btn_save, btn_test

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
    # Construcción del panel
    # ============================

    async def build_panel(self, interaction: discord.Interaction, page: int):
        guild = interaction.guild
        guild_id = str(guild.id)

        cfg = self.ensure_guild_config(guild_id)
        self.user_pages[interaction.user.id] = page

        embed = self.embed_page(page)
        view = discord.ui.View(timeout=300)

        # Página 1 — Configuración general
        if page == 1:
            embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)
            embed.add_field(name="Acción", value=cfg["action"], inline=False)
            embed.add_field(name="Tiempo de mute", value=f"{cfg['mute_time']}s", inline=False)
            embed.add_field(name="Modo progresivo", value="Sí" if cfg["progressive"] else "No", inline=False)

            view.add_item(self.select_allowed_roles(guild, guild_id))

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)

            view.add_item(discord.ui.Button(label="Cambiar acción", style=discord.ButtonStyle.blurple, custom_id="change_action"))
            view.add_item(discord.ui.Button(label="Cambiar tiempo mute", style=discord.ButtonStyle.blurple, custom_id="change_mute_time"))
            view.add_item(discord.ui.Button(label="Modo progresivo", style=discord.ButtonStyle.gray, custom_id="toggle_progressive"))

            view.add_item(btn_save)

        # Página 2 — Flood
        elif page == 2:
            embed.add_field(name="Máx. mensajes", value=cfg["flood"]["max_messages"], inline=False)
            embed.add_field(name="Intervalo (s)", value=cfg["flood"]["interval"], inline=False)

            view.add_item(discord.ui.Button(label="Cambiar máx. mensajes", style=discord.ButtonStyle.blurple, custom_id="change_flood_max"))
            view.add_item(discord.ui.Button(label="Cambiar intervalo", style=discord.ButtonStyle.blurple, custom_id="change_flood_interval"))

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 3 — Mayúsculas
        elif page == 3:
            embed.add_field(name="Detectar mayúsculas", value="Sí" if cfg["caps"]["enabled"] else "No", inline=False)
            embed.add_field(name="Máx. % permitido", value=f"{cfg['caps']['max_caps']}%", inline=False)

            view.add_item(discord.ui.Button(label="Toggle mayúsculas", style=discord.ButtonStyle.gray, custom_id="toggle_caps"))
            view.add_item(discord.ui.Button(label="Cambiar % máximo", style=discord.ButtonStyle.blurple, custom_id="change_caps_max"))

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 4 — Repetición
        elif page == 4:
            embed.add_field(name="Detectar repetición", value="Sí" if cfg["repeat"]["enabled"] else "No", inline=False)
            embed.add_field(name="Máx. repeticiones" if cfg["repeat"]["enabled"] else "No", inline=False)
            embed.add_field(name="Máx. repeticiones", value=cfg["repeat"]["max_repeat"], inline=False)

            view.add_item(discord.ui.Button(label="Toggle repetición", style=discord.ButtonStyle.gray, custom_id="toggle_repeat"))
            view.add_item(discord.ui.Button(label="Cambiar repeticiones", style=discord.ButtonStyle.blurple, custom_id="change_repeat_max"))

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 5 — Whitelist
        elif page == 5:
            embed.add_field(
                name="Usuarios permitidos",
                value=", ".join([f"<@{u}>" for u in cfg['whitelist_users']]) or "Ninguno",
                inline=False
            )
            embed.add_field(
                name="Roles permitidos",
                value=", ".join([f"<@&{r}>" for r in cfg['whitelist_roles']]) or "Ninguno",
                inline=False
            )
            embed.add_field(
                name="Canales permitidos",
                value=", ".join([f"<#{c}>" for c in cfg['whitelist_channels']]) or "Ninguno",
                inline=False
            )

            view.add_item(self.select_whitelist_users(guild, guild_id))
            view.add_item(self.select_whitelist_roles(guild, guild_id))
            view.add_item(self.select_whitelist_channels(guild, guild_id))

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 6 — Opciones avanzadas
        elif page == 6:
            embed.add_field(name="Cooldown por usuario", value=f"{cfg['cooldown']}s", inline=False)
            embed.add_field(name="Modo progresivo", value="Sí" if cfg["progressive"] else "No", inline=False)

            view.add_item(discord.ui.Button(label="Cambiar cooldown", style=discord.ButtonStyle.blurple, custom_id="change_cooldown"))
            view.add_item(discord.ui.Button(label="Modo progresivo", style=discord.ButtonStyle.gray, custom_id="toggle_progressive"))

            btn_enable, btn_save, btn_test = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)
            if btn_test:
                view.add_item(btn_test)

        # Navegación
        for btn in self.nav_buttons(page):
            view.add_item(btn)

        # Respuesta segura
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ============================
    # UPDATE PANEL
    # ============================

    async def update_panel(self, interaction: discord.Interaction, page: int):
        await self.build_panel(interaction, page)

    # ============================
    # Comando /antispam
    # ============================

    @app_commands.command(name="antispam", description="Abre el panel Anti‑Spam")
    async def antispam_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        guild_id = str(guild.id)

        self.ensure_guild_config(guild_id)

        allowed_roles = self.config[guild_id]["allowed_roles"]
        if allowed_roles:
            if not any(role.id in allowed_roles for role in interaction.user.roles):
                return await interaction.response.send_message(
                    "❌ No tienes permiso para usar este panel.",
                    ephemeral=True
                )

        await self.build_panel(interaction, page=1)

    # ============================
    # Listener de componentes
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id")
        user_id = interaction_guild_config(guild_id)

        allowed_roles = self.config[guild_id]["allowed_roles"]
        if allowed_roles:
            if not any(role.id in allowed_roles for role in interaction.user.roles):
                return await interaction.response.send_message(
                    "❌ No tienes permiso para usar este panel.",
                    ephemeral=True
                )

        await self.build_panel(interaction, page=1)

    # ============================
    # Listener de componentes
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id")
        user_id = interaction.user.id

        if user_id not in self.user_pages:
            return

        page = self.user_pages[user_id]
        guild_id = str(interaction.guild.id)
        cfg = self.config[guild_id]

        # Navegación
        if custom_id == "next_page":
            page = min(6, page + 1)
            self.user_pages[user_id] = page
            return await self.update_panel(interaction, page)

        if custom_id == "prev_page":
            page = max(1, page - 1)
            self.user_pages[user_id] = page
            return await self.update_panel(interaction, page)

        # Activar / Desactivar
        if custom_id == "toggle_enabled":
            cfg["enabled"] = not cfg["enabled"]
            save_antispam(self.config)
            return await self.update_panel(interaction, page)

        # Guardar
        if custom_id == "save_antispam":
            save_antispam(self.config)
            return await interaction.response.send_message(
                "💾 Configuración guardada.",
                ephemeral=True
            )

        # Acción
        if custom_id == "change_action":
            modal = AntiSpamActionModal(self, guild_id, page)
            return await interaction.response.send_modal(modal)

        # Tiempo de mute
        if custom_id == "change_mute_time":
            modal = AntiSpamMuteTimeModal(self, guild_id, page)
            return await interaction.response.send_modal(modal)

        # Flood
        if custom_id == "change_flood_max":
            modal = AntiSpamFloodMaxModal(self, guild_id, page)
            return await interaction.response.send_modal(modal)

        if custom_id == "change_flood_interval":
            modal = AntiSpamFloodIntervalModal(self, guild_id, page)
            return await interaction.response.send_modal(modal)

        # Caps
        if custom_id == "toggle_caps":
            cfg["caps"]["enabled"] = not cfg["caps"]["enabled"]
            save_antispam(self.config)
            return await self.update_panel(interaction, page)

        if custom_id == "change_caps_max":
            modal = AntiSpamCapsMaxModal(self, guild_id, page)
            return await interaction.response.send_modal(modal)

        # Repetición
        if custom_id == "toggle_repeat":
            cfg["repeat"]["enabled"] = not cfg["repeat"]["enabled"]
            save_antispam(self.config)
            return await self.update_panel(interaction, page)

        if custom_id == "change_repeat_max":
            modal = AntiSpamRepeatMaxModal(self, guild_id, page)
            return await interaction.response.send_modal(modal)

        # Cooldown
        if custom_id == "change_cooldown":
            modal = AntiSpamCooldownModal(self, guild_id, page)
            return await interaction.response.send_modal(modal)

        # Modo progresivo
        if custom_id == "toggle_progressive":
            cfg["progressive"] = not cfg["progressive"]
            save_antispam(self.config)
            return await self.update_panel(interaction, page)

        # Test Anti-Spam
        if custom_id == "test_antispam":
            return await interaction.response.send_message(
                "🧪 Test Anti‑Spam activado.\nEscribe 5 mensajes rápidos para probarlo.",
                ephemeral=True
            )

        # Selects
        if custom_id == "select_allowed_roles":
            values = interaction.data.get("values", [])
            cfg["allowed_roles"] = [int(r) for r in values if r != "none"]
            save_antispam(self.config)
            return await self.update_panel(interaction, page)

        if custom_id == "select_whitelist_users":
            values = interaction.data.get("values", [])
            cfg["whitelist_users"] = [int(u) for u in values if u != "none"]
            save_antispam(self.config)
            return await self.update_panel(interaction, page)

        if custom_id == "select_whitelist_roles":
            values = interaction.data.get("values", [])
            cfg["whitelist_roles"] = [int(r) for r in values if r != "none"]
            save_antispam(self.config)
            return await self.update_panel(interaction, page)

        if custom_id == "select_whitelist_channels":
            values = interaction.data.get("values", [])
            cfg["whitelist_channels"] = [int(c) for c in values if c != "none"]
            save_antispam(self.config)
            return await self.update_panel(interaction, page)

    # ============================
    # DETECCIÓN DE SPAM
    # ============================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if not message.guild:
            return
        if message.author.bot:
            return

        guild_id = str(message.guild.id)

        if guild_id not in self.config or not self.config[guild_id]["enabled"]:
            return

        cfg = self.config[guild_id]
        user = message.author
        content = message.content

        # Whitelist
        if user.id in cfg["whitelist_users"]:
            return
        if any(role.id in cfg["whitelist_roles"] for role in user.roles):
            return
        if message.channel.id in cfg["whitelist_channels"]:
            return

        now = time.time()

        # Cooldown
        if user.id in self.cooldowns:
            if now - self.cooldowns[user.id] < cfg["cooldown"]:
                return
        self.cooldowns[user.id] = now

        # Flood tracking
        if user.id not in self.user_messages:
            self.user_messages[user.id] = []

        self.user_messages[user.id].append((now, content))

        # Limpiar mensajes antiguos
        interval = cfg["flood"]["interval"]
        self.user_messages[user.id] = [
            (t, msg) for t, msg in self.user_messages[user.id] if now - t <= interval
        ]

        # Flood detectado
        if len(self.user_messages[user.id]) >= cfg["flood"]["max_messages"]:

            # Si NO ha sido advertido → advertencia
            if user.id not in self.warned or now - self.warned[user.id] > interval:
                self.warned[user.id] = now
                return await message.channel.send(
                    f"{user.mention} ⚠️ Si continúas haciendo spam recibirás: **{cfg['action']}**",
                    delete_after=5
                )

            # Si YA fue advertido → aplicar acción
            return await self.apply_action(message, "flood")

        # Repetición
        if cfg["repeat"]["enabled"]:
            msgs = [msg for _, msg in self.user_messages[user.id]]
            if len(msgs) >= cfg["repeat"]["max_repeat"]:
                if all(m == msgs[-1] for m in msgs[-cfg["repeat"]["max_repeat"]:]):

                    if user.id not in self.warned or now - self.warned[user.id] > interval:
                        self.warned[user.id] = now
                        return await message.channel.send(
                            f"{user.mention} ⚠️ Si continúas repitiendo mensajes recibirás: **{cfg['action']}**",
                            delete_after=5
                        )

                    return await self.apply_action(message, "repeat")

        # Mayúsculas
        if cfg["caps"]["enabled"]:
            letters = [c for c in content if c.isalpha()]
            if letters:
                caps = sum(1 for c in letters if c.isupper())
                percent = (caps / len(letters)) * 100
                if percent >= cfg["caps"]["max_caps"]:

                    if user.id not in self.warned or now - self.warned[user.id] > interval:
                        self.warned[user.id] = now
                        return await message.channel.send(
                            f"{user.mention} ⚠️ Si continúas usando mayúsculas recibirás: **{cfg['action']}**",
                            delete_after=5
                        )

                    return await self.apply_action(message, "caps")

    # ============================
    # APLICAR ACCIÓN
    # ============================

    async def apply_action(self, message: discord.Message, reason: str):
        guild_id = str(message.guild.id)
        cfg = self.config[guild_id]
        action = cfg["action"]
        user = message.author

        # Borrar mensaje
        try:
            await message.delete()
        except:
            pass

        # Acción delete
        if action == "delete":
            return

        # Warn
        if action == "warn":
            return await message.channel.send(
                f"{user.mention} ⚠️ Evita hacer spam ({reason}).",
                delete_after=5
            )

        # Kick
        if action == "kick":
            try:
                await user.kick(reason="Anti-Spam")
            except:
                pass
            return

        # Ban
        if action == "ban":
            try:
                await user.ban(reason="Anti-Spam")
            except:
                pass
            return

        # Mute (timeout oficial)
        if action == "mute":
            duration = cfg["mute_time"]

            # Modo progresivo
            if cfg["progressive"]:
                duration = min(duration * 2, 3600)

            try:
                await user.timeout(discord.utils.utcnow() + timedelta(seconds=duration))
            except:
                pass

            return await message.channel.send(
                f"{user.mention} ⛔ Has sido muteado por **{duration} segundos** por spam.",
                delete_after=5
            )

# ============================
# SETUP DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(AntiSpamCog(bot))
