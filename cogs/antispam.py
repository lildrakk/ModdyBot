import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time
from datetime import timedelta

ANTISPAM_FILE = "antispam.json"

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


class AntiSpamCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = load_antispam()
        self.user_pages = {}
        self.user_messages = {}
        self.cooldowns = {}
        self.warned = {}
        self.panel_owner = {}
        self.panel_message = {}

    # ============================
    # CONFIG POR SERVIDOR
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
                "repeat": {"enabled": True, "max_repeat": 3},

                "cooldown": 3,

                # NUEVO: canal de logs Anti‑Spam
                "log_channel": None
            }
            save_antispam(self.config)
        return self.config[guild_id]

    # ============================
    # EMBEDS POR PÁGINA
    # ============================

    def spam_embed_page(self, page: int):
        if page == 1:
            return discord.Embed(
                title="⚙️ Configuración General (Anti‑Spam)",
                description="Activa/desactiva el Anti‑Spam y ajusta opciones principales.",
                color=discord.Color.blue()
            )
        if page == 2:
            return discord.Embed(
                title="💬 Flood",
                description="Mensajes por segundo permitidos.",
                color=discord.Color.green()
            )
        if page == 3:
            return discord.Embed(
                title="🔠 Mayúsculas",
                description="Control del abuso de mayúsculas.",
                color=discord.Color.orange()
            )
        if page == 4:
            return discord.Embed(
                title="🔁 Repetición",
                description="Mensajes repetidos detectados.",
                color=discord.Color.purple()
            )
        if page == 5:
            return discord.Embed(
                title="🛡️ Whitelist",
                description="Usuarios, roles y canales permitidos.",
                color=discord.Color.teal()
            )
        return discord.Embed(
            title="🔧 Opciones avanzadas",
            description="Cooldown, modo progresivo, logs y test Anti‑Spam.",
            color=discord.Color.magenta()
        )

    # ============================
    # SELECTS
    # ============================

    def spam_select_allowed_roles(self, guild, guild_id):
        allowed = self.config[guild_id]["allowed_roles"]
        options = [
            discord.SelectOption(label=r.name, value=str(r.id), default=(r.id in allowed))
            for r in guild.roles if r.name != "@everyone"
        ][:25]
        return discord.ui.Select(
            placeholder="Roles autorizados",
            min_values=0,
            max_values=len(options) or 1,
            options=options or [discord.SelectOption(label="Sin roles", value="none")],
            custom_id="spam_select_allowed_roles"
        )

    def spam_select_whitelist_users(self, guild, guild_id):
        allowed = self.config[guild_id]["whitelist_users"]
        options = [
            discord.SelectOption(label=m.name, value=str(m.id), default=(m.id in allowed))
            for m in guild.members
        ][:25]
        return discord.ui.Select(
            placeholder="Usuarios permitidos",
            min_values=0,
            max_values=len(options) or 1,
            options=options or [discord.SelectOption(label="Sin usuarios", value="none")],
            custom_id="spam_select_whitelist_users"
        )

    def spam_select_whitelist_roles(self, guild, guild_id):
        allowed = self.config[guild_id]["whitelist_roles"]
        options = [
            discord.SelectOption(label=r.name, value=str(r.id), default=(r.id in allowed))
            for r in guild.roles if r.name != "@everyone"
        ][:25]
        return discord.ui.Select(
            placeholder="Roles permitidos",
            min_values=0,
            max_values=len(options) or 1,
            options=options or [discord.SelectOption(label="Sin roles", value="none")],
            custom_id="spam_select_whitelist_roles"
        )

    def spam_select_whitelist_channels(self, guild, guild_id):
        allowed = self.config[guild_id]["whitelist_channels"]
        options = [
            discord.SelectOption(label=c.name, value=str(c.id), default=(c.id in allowed))
            for c in guild.text_channels
        ][:25]
        return discord.ui.Select(
            placeholder="Canales permitidos",
            min_values=0,
            max_values=len(options) or 1,
            options=options or [discord.SelectOption(label="Sin canales", value="none")],
            custom_id="spam_select_whitelist_channels"
        )

    # NUEVO: SELECT DE CANAL DE LOGS
    def spam_select_log_channel(self, guild, guild_id):
        current = self.config[guild_id]["log_channel"]
        options = [
            discord.SelectOption(
                label=c.name,
                value=str(c.id),
                default=(c.id == current)
            )
            for c in guild.text_channels
        ][:25]

        return discord.ui.Select(
            placeholder="Selecciona canal de logs Anti‑Spam",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="spam_select_log_channel"
        )

    # ============================
    # BOTONES PRINCIPALES
    # ============================

    def spam_main_buttons(self, guild_id: str, page: int):
        cfg = self.config[guild_id]

        btn_enable = discord.ui.Button(
            label="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado",
            style=discord.ButtonStyle.green if cfg["enabled"] else discord.ButtonStyle.red,
            custom_id="spam_toggle_enabled"
        )

        btn_save = discord.ui.Button(
            label="💾 Guardar",
            style=discord.ButtonStyle.blurple,
            custom_id="spam_save_antispam"
        )

        btn_test = None
        if page == 6:
            btn_test = discord.ui.Button(
                label="🧪 Test Anti‑Spam",
                style=discord.ButtonStyle.gray,
                custom_id="spam_test_antispam"
            )

        return btn_enable, btn_save, btn_test

    # ============================
    # BOTONES DE NAVEGACIÓN
    # ============================

    def spam_nav_buttons(self, page: int):
        buttons = []

        if page > 1:
            buttons.append(
                discord.ui.Button(
                    label="⬅ Anterior",
                    style=discord.ButtonStyle.secondary,
                    custom_id="spam_prev_page"
                )
            )

        if page < 6:
            buttons.append(
                discord.ui.Button(
                    label="Siguiente ➡",
                    style=discord.ButtonStyle.secondary,
                    custom_id="spam_next_page"
                )
            )

        return buttons



# ============================
    # ACTUALIZAR PANEL
    # ============================

    async def spam_update_panel(self, interaction, page):
        await self.spam_build_panel(interaction, page)

    # ============================
    # SLASH COMMAND
    # ============================

    @app_commands.command(
        name="antispam",
        description="Abrir panel de configuración Anti‑Spam"
    )
    async def antispam_cmd(self, interaction: discord.Interaction):

        guild = interaction.guild
        guild_id = str(guild.id)
        self.ensure_guild_config(guild_id)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Solo administradores pueden usar este comando.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "✅ Panel Anti‑Spam abierto en este canal.",
            ephemeral=True
        )

        self.panel_owner[guild_id] = interaction.user.id
        self.user_pages[interaction.user.id] = 1
        await self.spam_build_panel(interaction, 1)

    # ============================
    # INTERACCIONES DEL PANEL
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id")
        if not custom_id or not custom_id.startswith("spam_"):
            return

        guild = interaction.guild
        guild_id = str(guild.id)
        user = interaction.user
        cfg = self.ensure_guild_config(guild_id)

        # Protección del panel
        if guild_id in self.panel_owner and user.id != self.panel_owner[guild_id]:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Solo quien abrió el panel puede usarlo.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Solo quien abrió el panel puede usarlo.",
                    ephemeral=True
                )
            return

        page = self.user_pages.get(user.id, 1)

        # ============================
        # CERRAR PANEL
        # ============================

        if custom_id == "spam_close_panel":
            if not interaction.response.is_done():
                await interaction.response.send_message("🔒 Panel cerrado.", ephemeral=True)
            else:
                await interaction.followup.send("🔒 Panel cerrado.", ephemeral=True)

            try:
                msg = await interaction.channel.fetch_message(self.panel_message[guild_id])
                await msg.delete()
                del self.panel_message[guild_id]
            except:
                pass
            return

        # ============================
        # MODALES
        # ============================

        class SpamModal(discord.ui.Modal):
            def __init__(self, cog, title, label, cb):
                super().__init__(title=title)
                self.cog = cog
                self.cb = cb
                self.input = discord.ui.TextInput(label=label, required=True)
                self.add_item(self.input)

            async def on_submit(self, modal_interaction):
                await self.cb(modal_interaction, self.input.value)

        # Cambiar acción
        if custom_id == "spam_change_action":
            async def cb(i, value):
                cfg["action"] = value.lower()
                save_antispam(self.cog.config)
                await i.response.send_message("💾 Acción actualizada.", ephemeral=True)
                await self.cog.spam_update_panel(i, page)

            return await interaction.response.send_modal(
                SpamModal(self, "Cambiar acción", "Acción:", cb)
            )

        # Cambiar mute time
        if custom_id == "spam_change_mute_time":
            async def cb(i, value):
                cfg["mute_time"] = max(1, int(value))
                save_antispam(self.cog.config)
                await i.response.send_message("💾 Tiempo mute actualizado.", ephemeral=True)
                await self.cog.spam_update_panel(i, page)

            return await interaction.response.send_modal(
                SpamModal(self, "Cambiar tiempo mute", "Segundos:", cb)
            )

        # Flood max
        if custom_id == "spam_change_flood_max":
            async def cb(i, value):
                cfg["flood"]["max_messages"] = max(1, int(value))
                save_antispam(self.cog.config)
                await i.response.send_message("💾 Máx. mensajes actualizado.", ephemeral=True)
                await self.cog.spam_update_panel(i, page)

            return await interaction.response.send_modal(
                SpamModal(self, "Cambiar máx. mensajes", "Cantidad:", cb)
            )

        # Flood interval
        if custom_id == "spam_change_flood_interval":
            async def cb(i, value):
                cfg["flood"]["interval"] = max(1, int(value))
                save_antispam(self.cog.config)
                await i.response.send_message("💾 Intervalo actualizado.", ephemeral=True)
                await self.cog.spam_update_panel(i, page)

            return await interaction.response.send_modal(
                SpamModal(self, "Cambiar intervalo", "Segundos:", cb)
            )

        # Caps max
        if custom_id == "spam_change_caps_max":
            async def cb(i, value):
                cfg["caps"]["max_caps"] = max(1, int(value))
                save_antispam(self.cog.config)
                await i.response.send_message("💾 % máximo actualizado.", ephemeral=True)
                await self.cog.spam_update_panel(i, page)

            return await interaction.response.send_modal(
                SpamModal(self, "Cambiar % máximo", "Porcentaje:", cb)
            )

        # Repeat max
        if custom_id == "spam_change_repeat_max":
            async def cb(i, value):
                cfg["repeat"]["max_repeat"] = max(1, int(value))
                save_antispam(self.cog.config)
                await i.response.send_message("💾 Repeticiones actualizadas.", ephemeral=True)
                await self.cog.spam_update_panel(i, page)

            return await interaction.response.send_modal(
                SpamModal(self, "Cambiar repeticiones", "Cantidad:", cb)
            )

        # Cooldown
        if custom_id == "spam_change_cooldown":
            async def cb(i, value):
                cfg["cooldown"] = max(0, int(value))
                save_antispam(self.cog.config)
                await i.response.send_message("💾 Cooldown actualizado.", ephemeral=True)
                await self.cog.spam_update_panel(i, page)

            return await interaction.response.send_modal(
                SpamModal(self, "Cambiar cooldown", "Segundos:", cb)
            )

        # ============================
        # ACCIONES QUE SOLO ACTUALIZAN PANEL
        # ============================

        update_only = {
            "spam_next_page", "spam_prev_page",
            "spam_toggle_enabled", "spam_toggle_progressive",
            "spam_toggle_caps", "spam_toggle_repeat",
            "spam_select_allowed_roles",
            "spam_select_whitelist_users",
            "spam_select_whitelist_roles",
            "spam_select_whitelist_channels",
            "spam_select_log_channel"
        }

        if custom_id in update_only:

            if not interaction.response.is_done():
                await interaction.response.defer()

            # Navegación
            if custom_id == "spam_next_page":
                page = min(6, page + 1)
                self.user_pages[user.id] = page

            elif custom_id == "spam_prev_page":
                page = max(1, page - 1)
                self.user_pages[user.id] = page

            # Toggles
            elif custom_id == "spam_toggle_enabled":
                cfg["enabled"] = not cfg["enabled"]

            elif custom_id == "spam_toggle_progressive":
                cfg["progressive"] = not cfg["progressive"]

            elif custom_id == "spam_toggle_caps":
                cfg["caps"]["enabled"] = not cfg["caps"]["enabled"]

            elif custom_id == "spam_toggle_repeat":
                cfg["repeat"]["enabled"] = not cfg["repeat"]["enabled"]

            # Selects
            elif custom_id == "spam_select_allowed_roles":
                cfg["allowed_roles"] = [int(v) for v in interaction.data.get("values", [])]

            elif custom_id == "spam_select_whitelist_users":
                cfg["whitelist_users"] = [int(v) for v in interaction.data.get("values", [])]

            elif custom_id == "spam_select_whitelist_roles":
                cfg["whitelist_roles"] = [int(v) for v in interaction.data.get("values", [])]

            elif custom_id == "spam_select_whitelist_channels":
                cfg["whitelist_channels"] = [int(v) for v in interaction.data.get("values", [])]

            # NUEVO: canal de logs
            elif custom_id == "spam_select_log_channel":
                selected = interaction.data.get("values", [])
                cfg["log_channel"] = int(selected[0]) if selected else None

            save_antispam(self.config)
            await self.spam_update_panel(interaction, page)
            return

        # ============================
        # GUARDAR / TEST
        # ============================

        if custom_id == "spam_save_antispam":
            save_antispam(self.config)
            await interaction.response.send_message("💾 Configuración guardada.", ephemeral=True)
            return

        if custom_id == "spam_test_antispam":
            await interaction.response.send_message("🧪 Test Anti‑Spam activado.", ephemeral=True)
            return


# ============================
    # DETECCIÓN DE SPAM
    # ============================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild_id = str(message.guild.id)
        if guild_id not in self.config:
            return

        cfg = self.config[guild_id]
        if not cfg["enabled"]:
            return

        user = message.author
        content = message.content
        now = time.time()

        # ============================
        # WHITELIST
        # ============================

        if user.id in cfg["whitelist_users"]:
            return
        if any(r.id in cfg["whitelist_roles"] for r in user.roles):
            return
        if message.channel.id in cfg["whitelist_channels"]:
            return

        # ============================
        # COOLDOWN
        # ============================

        if user.id in self.cooldowns and now - self.cooldowns[user.id] < cfg["cooldown"]:
            return
        self.cooldowns[user.id] = now

        # ============================
        # HISTORIAL DE MENSAJES
        # ============================

        if user.id not in self.user_messages:
            self.user_messages[user.id] = []

        self.user_messages[user.id].append((now, content))

        interval = cfg["flood"]["interval"]

        # Limpieza de mensajes viejos
        self.user_messages[user.id] = [
            (t, msg) for t, msg in self.user_messages[user.id]
            if now - t <= interval
        ]

        # ============================
        # FLOOD REAL
        # ============================

        if len(self.user_messages[user.id]) >= cfg["flood"]["max_messages"]:
            if user.id not in self.warned or now - self.warned[user.id] > interval:
                self.warned[user.id] = now

                embed = discord.Embed(
                    title="⚠️ Aviso de flood",
                    description=f"{user.mention}, estás enviando mensajes demasiado rápido.",
                    color=discord.Color.orange()
                )

                await message.channel.send(embed=embed)
                await self.send_log(message.guild, embed)
                return

            return await self.apply_action(message, "flood")

        # ============================
        # REPETICIÓN INTELIGENTE
        # ============================

        if cfg["repeat"]["enabled"]:
            msgs = [msg for _, msg in self.user_messages[user.id]]

            if len(msgs) >= cfg["repeat"]["max_repeat"]:
                last_n = msgs[-cfg["repeat"]["max_repeat"]:]

                # Normalización
                normalized = [m.lower().strip() for m in last_n]

                if len(set(normalized)) == 1:

                    if user.id not in self.warned or now - self.warned[user.id] > interval:
                        self.warned[user.id] = now

                        embed = discord.Embed(
                            title="⚠️ Aviso de repetición",
                            description=f"{user.mention}, estás repitiendo mensajes.",
                            color=discord.Color.orange()
                        )

                        await message.channel.send(embed=embed)
                        await self.send_log(message.guild, embed)
                        return

                    return await self.apply_action(message, "repetición")

        # ============================
        # MAYÚSCULAS REAL
        # ============================

        if cfg["caps"]["enabled"]:
            letters = [c for c in content if c.isalpha()]

            if letters:
                caps = sum(1 for c in letters if c.isupper())
                percent = (caps / len(letters)) * 100

                if percent >= cfg["caps"]["max_caps"]:

                    if user.id not in self.warned or now - self.warned[user.id] > interval:
                        self.warned[user.id] = now

                        embed = discord.Embed(
                            title="⚠️ Aviso de mayúsculas",
                            description=f"{user.mention}, estás usando demasiadas mayúsculas.",
                            color=discord.Color.orange()
                        )

                        await message.channel.send(embed=embed)
                        await self.send_log(message.guild, embed)
                        return

                    return await self.apply_action(message, "mayúsculas")

    # ============================
    # ENVIAR LOGS
    # ============================

    async def send_log(self, guild: discord.Guild, embed: discord.Embed):
        guild_id = str(guild.id)
        cfg = self.config[guild_id]

        log_channel_id = cfg.get("log_channel")
        if not log_channel_id:
            return

        channel = guild.get_channel(log_channel_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except:
                pass

    # ============================
    # APLICAR ACCIÓN
    # ============================

    async def apply_action(self, message: discord.Message, reason: str):
        guild = message.guild
        guild_id = str(guild.id)
        cfg = self.config[guild_id]
        action = cfg["action"]
        user = message.author

        # Embed de acción
        embed = discord.Embed(
            title="⛔ Acción aplicada",
            description=f"**{user.mention} ha recibido `{action}` por spam ({reason}).**",
            color=discord.Color.red()
        )

        # Enviar al canal donde ocurrió
        await message.channel.send(embed=embed)

        # Enviar a logs
        await self.send_log(guild, embed)

        # ============================
        # ACCIONES
        # ============================

        # Warn
        if action == "warn":
            return

        # Kick
        if action == "kick":
            try:
                await user.kick(reason=f"Anti‑Spam ({reason})")
            except:
                pass
            return

        # Ban
        if action == "ban":
            try:
                await user.ban(reason=f"Anti‑Spam ({reason})")
            except:
                pass
            return

        # Mute
        if action == "mute":
            duration = cfg["mute_time"]

            if cfg["progressive"]:
                duration = min(duration * 2, 3600)

            try:
                await user.timeout(
                    discord.utils.utcnow() + timedelta(seconds=duration),
                    reason=f"Anti‑Spam ({reason})"
                )
            except:
                pass

            return

# ============================
# SETUP DEL COG
# ============================

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiSpamCog(bot))
