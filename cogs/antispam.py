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
        self.warned = {}  # NUEVO: guarda advertencias por usuario

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
    # Selects dinámicos
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
        ]

        return discord.ui.Select(
            placeholder="Roles autorizados para usar /antispam",
            min_values=0,
            max_values=len(options) if options else 1,
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
        ]

        return discord.ui.Select(
            placeholder="Usuarios permitidos",
            min_values=0,
            max_values=len(options) if options else 1,
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
        ]

        return discord.ui.Select(
            placeholder="Roles permitidos",
            min_values=0,
            max_values=len(options) if options else 1,
            options=options or [discord.SelectOption(label="Sin roles", value="none", default=True)],
            custom_id="select_whitelist_roles"
        )

    def select_whitelist_channels(self, guild: discord.Guild, guild_id: str):
        allowed = self.config[guild[guild_id]]["whitelist_channels"]

        options = [
            discord.SelectOption(
                label=channel.name,
                value=str(channel.id),
                default=(channel.id in allowed)
            )
            for channel in guild.text_channels
        ]

        return discord.ui.Select(
            placeholder="Canales permitidos",
            min_values=0,
            max_values=len(options) if options else 1,
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

        # Crear config si no existe
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

        self.user_pages[interaction.user.id] = page
        cfg = self.config[guild_id]

        embed = self.embed_page(page)
        view = discord.ui.View(timeout=300)

        # ============================
        # Página 1 — Configuración general
        # ============================
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


    # ============================
        # Página 2 — Flood
        # ============================
        elif page == 2:
            embed.add_field(name="Máx. mensajes", value=cfg["flood"]["max_messages"], inline=False)
            embed.add_field(name="Intervalo (s)", value=cfg["flood"]["interval"], inline=False)

            view.add_item(discord.ui.Button(label="Cambiar máx. mensajes", style=discord.ButtonStyle.blurple, custom_id="change_flood_max"))
            view.add_item(discord.ui.Button(label="Cambiar intervalo", style=discord.ButtonStyle.blurple, custom_id="change_flood_interval"))

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # ============================
        # Página 3 — Mayúsculas
        # ============================
        elif page == 3:
            embed.add_field(name="Detectar mayúsculas", value="Sí" if cfg["caps"]["enabled"] else "No", inline=False)
            embed.add_field(name="Máx. % permitido", value=f"{cfg['caps']['max_caps']}%", inline=False)

            view.add_item(discord.ui.Button(label="Toggle mayúsculas", style=discord.ButtonStyle.gray, custom_id="toggle_caps"))
            view.add_item(discord.ui.Button(label="Cambiar % máximo", style=discord.ButtonStyle.blurple, custom_id="change_caps_max"))

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # ============================
        # Página 4 — Repetición
        # ============================
        elif page == 4:
            embed.add_field(name="Detectar repetición", value="Sí" if cfg["repeat"]["enabled"] else "No", inline=False)
            embed.add_field(name="Máx. repeticiones", value=cfg["repeat"]["max_repeat"], inline=False)

            view.add_item(discord.ui.Button(label="Toggle repetición", style=discord.ButtonStyle.gray, custom_id="toggle_repeat"))
            view.add_item(discord.ui.Button(label="Cambiar repeticiones", style=discord.ButtonStyle.blurple, custom_id="change_repeat_max"))

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # ============================
        # Página 5 — Whitelist
        # ============================
        elif page == 5:
            embed.add_field(
                name="Usuarios permitidos",
                value=", ".join([f"<@{u}>" for u in cfg["whitelist_users"]]) or "Ninguno",
                inline=False
            )
            embed.add_field(
                name="Roles permitidos",
                value=", ".join([f"<@&{r}>" for r in cfg["whitelist_roles"]]) or "Ninguno",
                inline=False
            )
            embed.add_field(
                name="Canales permitidos",
                value=", ".join([f"<#{c}>" for c in cfg["whitelist_channels"]]) or "Ninguno",
                inline=False
            )

            view.add_item(self.select_whitelist_users(guild, guild_id))
            view.add_item(self.select_whitelist_roles(guild, guild_id))
            view.add_item(self.select_whitelist_channels(guild, guild_id))

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # ============================
        # Página 6 — Opciones avanzadas
        # ============================
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

        # Respuesta segura (evita "la aplicación no ha respondido")
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ============================
    # UPDATE PANEL
    # ============================

    async def update_panel(self, interaction: discord.Interaction, page: int):
        guild = interaction.guild
        guild_id = str(guild.id)

        embed = self.embed_page(page)
        view = discord.ui.View(timeout=300)

        # reconstruye el panel reutilizando build_panel
        await self.build_panel(interaction, page)

    # ============================
    # Comando /antispam
    # ============================

    @app_commands.command(name="antispam", description="Abre el panel Anti‑Spam")
    async def antispam_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        guild_id = str(guild.id)

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

        allowed_roles = self.config[guild_id]["allowed_roles"]
        if allowed_roles:
            if not any(role.id in allowed_roles for role in interaction.user.roles):
                return await interaction.response.send_message(
                    "❌ No tienes permiso para usar este panel.",
                    ephemeral=True
                )

        await self.build_panel(interaction, page=1)


    # ============================
# MODALS (inputs)
# ============================

class AntiSpamActionModal(discord.ui.Modal, title="Cambiar acción"):
    action = discord.ui.TextInput(label="Acción (mute/kick/ban/delete/warn)", placeholder="mute")

    def __init__(self, cog, guild_id, page):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.page = page

    async def on_submit(self, interaction: discord.Interaction):
        value = self.action.value.lower()
        if value not in ["mute", "kick", "ban", "delete", "warn"]:
            return await interaction.response.send_message("❌ Acción inválida.", ephemeral=True)

        self.cog.config[self.guild_id]["action"] = value
        save_antispam(self.cog.config)
        await self.cog.update_panel(interaction, self.page)


class AntiSpamMuteTimeModal(discord.ui.Modal, title="Cambiar tiempo de mute"):
    time = discord.ui.TextInput(label="Tiempo en segundos", placeholder="600")

    def __init__(self, cog, guild_id, page):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.page = page

    async def on_submit(self, interaction: discord.Interaction):
        try:
            t = int(self.time.value)
        except:
            return await interaction.response.send_message("❌ Debe ser un número.", ephemeral=True)

        self.cog.config[self.guild_id]["mute_time"] = t
        save_antispam(self.cog.config)
        await self.cog.update_panel(interaction, self.page)


class AntiSpamFloodMaxModal(discord.ui.Modal, title="Cambiar máximo de mensajes"):
    value = discord.ui.TextInput(label="Máximo de mensajes", placeholder="5")

    def __init__(self, cog, guild_id, page):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.page = page

    async def on_submit(self, interaction: discord.Interaction):
        try:
            v = int(self.value.value)
        except:
            return await interaction.response.send_message("❌ Debe ser un número.", ephemeral=True)

        self.cog.config[self.guild_id]["flood"]["max_messages"] = v
        save_antispam(self.cog.config)
        await self.cog.update_panel(interaction, self.page)


class AntiSpamFloodIntervalModal(discord.ui.Modal, title="Cambiar intervalo"):
    value = discord.ui.TextInput(label="Intervalo en segundos", placeholder="4")

    def __init__(self, cog, guild_id, page):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.page = page

    async def on_submit(self, interaction: discord.Interaction):
        try:
            v = int(self.value.value)
        except:
            return await interaction.response.send_message("❌ Debe ser un número.", ephemeral=True)

        self.cog.config[self.guild_id]["flood"]["interval"] = v
        save_antispam(self.cog.config)
        await self.cog.update_panel(interaction, self.page)


class AntiSpamCapsMaxModal(discord.ui.Modal, title="Cambiar % máximo de mayúsculas"):
    value = discord.ui.TextInput(label="Porcentaje máximo", placeholder="70")

    def __init__(self, cog, guild_id, page):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.page = page

    async def on_submit(self, interaction: discord.Interaction):
        try:
            v = int(self.value.value)
        except:
            return await interaction.response.send_message("❌ Debe ser un número.", ephemeral=True)

        self.cog.config[self.guild_id]["caps"]["max_caps"] = v
        save_antispam(self.cog.config)
        await self.cog.update_panel(interaction, self.page)


class AntiSpamRepeatMaxModal(discord.ui.Modal, title="Cambiar repeticiones máximas"):
    value = discord.ui.TextInput(label="Máx. repeticiones", placeholder="2")

    def __init__(self, cog, guild_id, page):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.page = page

    async def on_submit(self, interaction: discord.Interaction):
        try:
            v = int(self.value.value)
        except:
            return await interaction.response.send_message("❌ Debe ser un número.", ephemeral=True)

        self.cog.config[self.guild_id]["repeat"]["max_repeat"] = v
        save_antispam(self.cog.config)
        await self.cog.update_panel(interaction, self.page)


class AntiSpamCooldownModal(discord.ui.Modal, title="Cambiar cooldown"):
    value = discord.ui.TextInput(label="Cooldown en segundos", placeholder="3")

    def __init__(self, cog, guild_id, page):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.page = page

    async def on_submit(self, interaction: discord.Interaction):
        try:
            v = int(self.value.value)
        except:
            return await interaction.response.send_message("❌ Debe ser un número.", ephemeral=True)

        self.cog.config[self.guild_id]["cooldown"] = v
        save_antispam(self.cog.config)
        await self.cog.update_panel(interaction, self.page)


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
