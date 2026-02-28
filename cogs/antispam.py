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
    # CONFIG
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
                "cooldown": 3
            }
            save_antispam(self.config)
        return self.config[guild_id]

    # ============================
    # EMBEDS POR PÁGINA
    # ============================

    def embed_page(self, page: int):
        if page == 1:
            return discord.Embed(
                title="⚙️ Configuración General",
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
            description="Cooldown, modo progresivo y test Anti‑Spam.",
            color=discord.Color.magenta()
        )

    # ============================
    # SELECTS
    # ============================

    def select_allowed_roles(self, guild, guild_id):
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
            custom_id="select_allowed_roles"
        )

    def select_whitelist_users(self, guild, guild_id):
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
            custom_id="select_whitelist_users"
        )

    def select_whitelist_roles(self, guild, guild_id):
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
            custom_id="select_whitelist_roles"
        )

    def select_whitelist_channels(self, guild, guild_id):
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
            custom_id="select_whitelist_channels"
        )

    # ============================
    # BOTONES
    # ============================

    def main_buttons(self, guild_id, page):
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

    def nav_buttons(self, page):
        buttons = []
        if page > 1:
            buttons.append(discord.ui.Button(label="⬅️ Anterior", style=discord.ButtonStyle.secondary, custom_id="prev_page"))
        if page < 6:
            buttons.append(discord.ui.Button(label="➡️ Siguiente", style=discord.ButtonStyle.secondary, custom_id="next_page"))
        return buttons

    # ============================
    # PANEL
    # ============================

    async def build_panel(self, interaction, page):
        guild = interaction.guild
        guild_id = str(guild.id)
        cfg = self.ensure_guild_config(guild_id)
        self.user_pages[interaction.user.id] = page

        embed = self.embed_page(page)
        view = discord.ui.View(timeout=300)

        # Botón cerrar panel
        view.add_item(discord.ui.Button(label="🔒 Cerrar panel", style=discord.ButtonStyle.red, custom_id="close_panel"))

        # Página 1
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
            embed.add_field(name="Máx. mensajes", value=str(cfg["flood"]["max_messages"]), inline=False)
            embed.add_field(name="Intervalo (s)", value=str(cfg["flood"]["interval"]), inline=False)

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
            embed.add_field(name="Máx. repeticiones", value=str(cfg["repeat"]["max_repeat"]), inline=False)

            view.add_item(discord.ui.Button(label="Toggle repetición", style=discord.ButtonStyle.gray, custom_id="toggle_repeat"))
            view.add_item(discord.ui.Button(label="Cambiar repeticiones", style=discord.ButtonStyle.blurple, custom_id="change_repeat_max"))

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 5 — Whitelist
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

        # Crear o editar panel
        if guild_id not in self.panel_message:
            sent = await interaction.channel.send(
                "**Panel Anti‑Spam — Configuración del servidor**",
                embed=embed,
                view=view
            )
            self.panel_message[guild_id] = sent.id
            self.panel_owner[guild_id] = interaction.user.id
        else:
            try:
                msg = await interaction.channel.fetch_message(self.panel_message[guild_id])
                await msg.edit(embed=embed, view=view)
            except discord.NotFound:
                sent = await interaction.channel.send(
                    "**Panel Anti‑Spam — Configuración del servidor**",
                    embed=embed,
                    view=view
                )
                self.panel_message[guild_id] = sent.id
                self.panel_owner[guild_id] = interaction.user.id

    async def update_panel(self, interaction, page):
        await self.build_panel(interaction, page)

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
    cfg = self.ensure_guild_config(guild_id)

    # ============================
    # ✔ Comprobación de permisos
    # ============================

    # Si es administrador → acceso total
    if interaction.user.guild_permissions.administrator:
        pass

    # Si NO es admin → debe tener manage_guild
    elif not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message(
            "❌ No tienes permiso para usar este comando.",
            ephemeral=True
        )

    # Si NO es admin y NO tiene manage_guild → comprobar roles permitidos
    elif cfg["allowed_roles"]:
        if not any(r.id in cfg["allowed_roles"] for r in interaction.user.roles):
            return await interaction.response.send_message(
                "❌ No tienes permisos para usar este panel.",
                ephemeral=True
            )

    # ============================
    # Abrir panel
    # ============================

    await interaction.response.send_message(
        "✅ Panel Anti‑Spam abierto en este canal.",
        ephemeral=True
    )

    self.panel_owner[guild_id] = interaction.user.id
    self.user_pages[interaction.user.id] = 1
    await self.build_panel(interaction, 1)

        

    # ============================
    # INTERACCIONES
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.type != discord.InteractionType.component:
            return

        guild = interaction.guild
        guild_id = str(guild.id)
        user = interaction.user

        custom_id = interaction.data.get("custom_id")
        if not custom_id:
            return

        # Solo el dueño del panel
        if guild_id in self.panel_owner and user.id != self.panel_owner[guild_id]:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Solo quien abrió el panel puede usarlo.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Solo quien abrió el panel puede usarlo.", ephemeral=True)
            return

        page = self.user_pages.get(user.id, 1)
        cfg = self.ensure_guild_config(guild_id)

        # ============================
        # CERRAR PANEL
        # ============================

        if custom_id == "close_panel":
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
        # MODALS
        # ============================

        class SimpleModal(discord.ui.Modal):
            def __init__(self, outer, title, label, cb):
                super().__init__(title=title)
                self.outer = outer
                self.cb = cb
                self.input = discord.ui.TextInput(label=label, required=True)
                self.add_item(self.input)

            async def on_submit(self, modal_interaction):
                await self.cb(modal_interaction, self.input.value)

        # Modals
        if custom_id == "change_action":
            async def cb(i, value):
                cfg["action"] = value.lower()
                save_antispam(self.outer.config)
                await i.response.send_message("💾 Acción actualizada.", ephemeral=True)
                await self.outer.update_panel(i, page)

            return await interaction.response.send_modal(
                SimpleModal(self, "Cambiar acción", "Acción:", cb)
            )

        if custom_id == "change_mute_time":
            async def cb(i, value):
                cfg["mute_time"] = max(1, int(value))
                save_antispam(self.outer.config)
                await i.response.send_message("💾 Tiempo mute actualizado.", ephemeral=True)
                await self.outer.update_panel(i, page)

            return await interaction.response.send_modal(
                SimpleModal(self, "Cambiar tiempo mute", "Segundos:", cb)
            )

        if custom_id == "change_flood_max":
            async def cb(i, value):
                cfg["flood"]["max_messages"] = max(1, int(value))
                save_antispam(self.outer.config)
                await i.response.send_message("💾 Máx. mensajes actualizado.", ephemeral=True)
                await self.outer.update_panel(i, page)

            return await interaction.response.send_modal(
                SimpleModal(self, "Cambiar máx. mensajes", "Cantidad:", cb)
            )

        if custom_id == "change_flood_interval":
            async def cb(i, value):
                cfg["flood"]["interval"] = max(1, int(value))
                save_antispam(self.outer.config)
                await i.response.send_message("💾 Intervalo actualizado.", ephemeral=True)
                await self.outer.update_panel(i, page)

            return await interaction.response.send_modal(
                SimpleModal(self, "Cambiar intervalo", "Segundos:", cb)
            )

        if custom_id == "change_caps_max":
            async def cb(i, value):
                cfg["caps"]["max_caps"] = max(1, int(value))
                save_antispam(self.outer.config)
                await i.response.send_message("💾 % máximo actualizado.", ephemeral=True)
                await self.outer.update_panel(i, page)

            return await interaction.response.send_modal(
                SimpleModal(self, "Cambiar % máximo", "Porcentaje:", cb)
            )

        if custom_id == "change_repeat_max":
            async def cb(i, value):
                cfg["repeat"]["max_repeat"] = max(1, int(value))
                save_antispam(self.outer.config)
                await i.response.send_message("💾 Repeticiones actualizadas.", ephemeral=True)
                await self.outer.update_panel(i, page)

            return await interaction.response.send_modal(
                SimpleModal(self, "Cambiar repeticiones", "Cantidad:", cb)
            )

        if custom_id == "change_cooldown":
            async def cb(i, value):
                cfg["cooldown"] = max(0, int(value))
                save_antispam(self.outer.config)
                await i.response.send_message("💾 Cooldown actualizado.", ephemeral=True)
                await self.outer.update_panel(i, page)

            return await interaction.response.send_modal(
                SimpleModal(self, "Cambiar cooldown", "Segundos:", cb)
            )

        # ============================
        # ACCIONES QUE SOLO ACTUALIZAN PANEL
        # ============================

        update_only = {
            "next_page", "prev_page",
            "toggle_enabled", "toggle_progressive",
            "toggle_caps", "toggle_repeat",
            "select_allowed_roles",
            "select_whitelist_users",
            "select_whitelist_roles",
            "select_whitelist_channels",
        }

        if custom_id in update_only:
            if not interaction.response.is_done():
                await interaction.response.defer()

            if custom_id == "next_page":
                page = min(6, page + 1)
                self.user_pages[user.id] = page

            elif custom_id == "prev_page":
                page = max(1, page - 1)
                self.user_pages[user.id] = page

            elif custom_id == "toggle_enabled":
                cfg["enabled"] = not cfg["enabled"]
                save_antispam(self.config)

            elif custom_id == "toggle_progressive":
                cfg["progressive"] = not cfg["progressive"]
                save_antispam(self.config)

            elif custom_id == "toggle_caps":
                cfg["caps"]["enabled"] = not cfg["caps"]["enabled"]
                save_antispam(self.config)

            elif custom_id == "toggle_repeat":
                cfg["repeat"]["enabled"] = not cfg["repeat"]["enabled"]
                save_antispam(self.config)

            elif custom_id == "select_allowed_roles":
                cfg["allowed_roles"] = [int(v) for v in interaction.data.get("values", []) if v != "none"]
                save_antispam(self.config)

            elif custom_id == "select_whitelist_users":
                cfg["whitelist_users"] = [int(v) for v in interaction.data.get("values", []) if v != "none"]
                save_antispam(self.config)

            elif custom_id == "select_whitelist_roles":
                cfg["whitelist_roles"] = [int(v) for v in interaction.data.get("values", []) if v != "none"]
                save_antispam(self.config)

            elif custom_id == "select_whitelist_channels":
                cfg["whitelist_channels"] = [int(v) for v in interaction.data.get("values", []) if v != "none"]
                save_antispam(self.config)

            await self.update_panel(interaction, page)
            return

        # ============================
        # GUARDAR / TEST
        # ============================

        if custom_id == "save_antispam":
            save_antispam(self.config)
            if not interaction.response.is_done():
                await interaction.response.send_message("💾 Configuración guardada.", ephemeral=True)
            else:
                await interaction.followup.send("💾 Configuración guardada.", ephemeral=True)
            return

        if custom_id == "test_antispam":
            if not interaction.response.is_done():
                await interaction.response.send_message("🧪 Test Anti‑Spam activado.", ephemeral=True)
            else:
                await interaction.followup.send("🧪 Test Anti‑Spam activado.", ephemeral=True)
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

        # Whitelist
        if user.id in cfg["whitelist_users"]:
            return
        if any(r.id in cfg["whitelist_roles"] for r in user.roles):
            return
        if message.channel.id in cfg["whitelist_channels"]:
            return

        # Cooldown
        if user.id in self.cooldowns and now - self.cooldowns[user.id] < cfg["cooldown"]:
            return
        self.cooldowns[user.id] = now

        # Flood tracking
        if user.id not in self.user_messages:
            self.user_messages[user.id] = []

        self.user_messages[user.id].append((now, content))

        interval = cfg["flood"]["interval"]
        self.user_messages[user.id] = [(t, msg) for t, msg in self.user_messages[user.id] if now - t <= interval]

        # Flood detectado
        if len(self.user_messages[user.id]) >= cfg["flood"]["max_messages"]:
            if user.id not in self.warned or now - self.warned[user.id] > interval:
                self.warned[user.id] = now
                await message.channel.send(
                    f"{user.mention} ⚠️ Si continúas haciendo spam recibirás: **{cfg['action']}**",
                    delete_after=5
                )
                return
            return await self.apply_action(message, "flood")

        # Repetición
        if cfg["repeat"]["enabled"]:
            msgs = [msg for _, msg in self.user_messages[user.id]]
            if len(msgs) >= cfg["repeat"]["max_repeat"]:
                last_n = msgs[-cfg["repeat"]["max_repeat"]:]
                if len(set(last_n)) == 1:
                    if user.id not in self.warned or now - self.warned[user.id] > interval:
                        self.warned[user.id] = now
                        await message.channel.send(
                            f"{user.mention} ⚠️ Si continúas repitiendo mensajes recibirás: **{cfg['action']}**",
                            delete_after=5
                        )
                        return
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
                        await message.channel.send(
                            f"{user.mention} ⚠️ Si continúas usando mayúsculas recibirás: **{cfg['action']}**",
                            delete_after=5
                        )
                        return
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
            await message.channel.send(
                f"{user.mention} ⚠️ Evita hacer spam ({reason}).",
                delete_after=5
            )
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

        # Mute (timeout)
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

            await message.channel.send(
                f"{user.mention} ⛔ Has sido muteado por **{duration} segundos** por spam.",
                delete_after=5
            )
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiSpamCog(bot))
