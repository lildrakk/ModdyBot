import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time

ANTILINKS_FILE = "antilinks.json"

# ============================
# JSON LOADER
# ============================

def load_antilinks():
    if not os.path.exists(ANTILINKS_FILE):
        with open(ANTILINKS_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}

    with open(ANTILINKS_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_antilinks(data):
    with open(ANTILINKS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# MODAL PARA AÑADIR DOMINIOS
# ============================

class AddDomainModal(discord.ui.Modal):
    def __init__(self, cog, guild_id):
        super().__init__(title="Añadir dominio permitido")
        self.cog = cog
        self.guild_id = guild_id

        self.dominio = discord.ui.TextInput(
            label="Dominio (ej: youtube.com)",
            placeholder="sin https:// ni www",
            required=True,
            max_length=100
        )
        self.add_item(self.dominio)

    async def on_submit(self, interaction: discord.Interaction):
        dominio = self.dominio.value.lower().strip()

        cfg = self.cog.ensure_guild_config(self.guild_id)

        if dominio not in cfg["whitelist_domains"]:
            cfg["whitelist_domains"].append(dominio)
            save_antilinks(self.cog.config)

        await interaction.response.send_message(
            f"✅ Dominio **{dominio}** añadido a la whitelist.",
            ephemeral=True
        )


# ============================
# MODAL OPCIONES AVANZADAS (WARN / TIEMPO / MUTE)
# ============================

class AdvancedSettingsModal(discord.ui.Modal):
    def __init__(self, cog, guild_id):
        super().__init__(title="Opciones avanzadas Anti‑Links")
        self.cog = cog
        self.guild_id = guild_id

        cfg = self.cog.ensure_guild_config(guild_id)

        self.warn_limit = discord.ui.TextInput(
            label="Avisos necesarios (ej: 3, 6...)",
            placeholder="Número de avisos antes de sancionar",
            default=str(cfg.get("warn_limit", 3)),
            required=True,
            max_length=3
        )
        self.warn_window = discord.ui.TextInput(
            label="Ventana en minutos (ej: 5, 10...)",
            placeholder="Tiempo para contar avisos",
            default=str(cfg.get("warn_window_minutes", 5)),
            required=True,
            max_length=3
        )
        self.mute_minutes = discord.ui.TextInput(
            label="Duración del mute en minutos",
            placeholder="Solo si la acción es mute",
            default=str(cfg.get("auto_punish_mute_minutes", 10)),
            required=True,
            max_length=4
        )

        self.add_item(self.warn_limit)
        self.add_item(self.warn_window)
        self.add_item(self.mute_minutes)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = self.cog.ensure_guild_config(self.guild_id)

        try:
            warn_limit = int(self.warn_limit.value)
            warn_window = int(self.warn_window.value)
            mute_minutes = int(self.mute_minutes.value)

            if warn_limit < 1:
                warn_limit = 1
            if warn_window < 1:
                warn_window = 1
            if mute_minutes < 1:
                mute_minutes = 1

            cfg["warn_limit"] = warn_limit
            cfg["warn_window_minutes"] = warn_window
            cfg["auto_punish_mute_minutes"] = mute_minutes

            save_antilinks(self.cog.config)

            await interaction.response.send_message(
                f"✅ Opciones avanzadas actualizadas:\n"
                f"- Avisos necesarios: **{warn_limit}**\n"
                f"- Ventana: **{warn_window}** minutos\n"
                f"- Mute: **{mute_minutes}** minutos",
                ephemeral=True
            )
        except:
            await interaction.response.send_message(
                "❌ Valores inválidos. Usa solo números enteros.",
                ephemeral=True
            )


# ============================
# COG ANTI-LINKS
# ============================

class AntiLinksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_antilinks()
        self.user_pages = {}

    # ============================
    # ASEGURAR CONFIG POR SERVIDOR
    # ============================

    def ensure_guild_config(self, guild_id: str):
        if guild_id not in self.config:
            self.config[guild_id] = {
                "enabled": False,
                "allowed_roles": [],
                "whitelist_users": [],
                "whitelist_roles": [],
                "whitelist_domains": [],
                "allowed_servers": [],
                "block_shorteners": True,
                "block_obfuscated": True,
                "manage_role": 0,

                "log_channel": 0,

                "auto_punish_enabled": True,
                "auto_punish_action": "mute",  # mute / kick / ban / none
                "auto_punish_mute_minutes": 10,

                "warn_limit": 3,
                "warn_window_minutes": 5,

                "warns": {}
            }
            save_antilinks(self.config)

        # Asegurar claves nuevas en servidores antiguos
        cfg = self.config[guild_id]
        cfg.setdefault("log_channel", 0)
        cfg.setdefault("auto_punish_enabled", True)
        cfg.setdefault("auto_punish_action", "mute")
        cfg.setdefault("auto_punish_mute_minutes", 10)
        cfg.setdefault("warn_limit", 3)
        cfg.setdefault("warn_window_minutes", 5)
        cfg.setdefault("warns", {})

        return cfg

    # ============================
    # COMANDO PRINCIPAL /antilinks
    # ============================

    @app_commands.command(
        name="antilinks",
        description="Abre el panel de configuración Anti‑Links"
    )
    async def antilinks_cmd(self, interaction: discord.Interaction):

        guild = interaction.guild
        guild_id = str(guild.id)

        # Crear config si no existe
        self.ensure_guild_config(guild_id)

        # PERMISOS
        manage_role = self.config[guild_id].get("manage_role", 0)

        es_admin = interaction.user.guild_permissions.administrator
        tiene_rol = any(role.id == manage_role for role in interaction.user.roles)

        if not es_admin and not tiene_rol:
            return await interaction.response.send_message(
                "❌ No tienes permisos para usar este comando.",
                ephemeral=True
            )

        # Guardar página del usuario
        self.user_pages[interaction.user.id] = 1

        # Panel inicial
        await self.build_panel(interaction, page=1, initial=True)

    # ============================
    # Embeds por página
    # ============================

    def embed_page(self, guild: discord.Guild, guild_id: str, page: int):
        cfg = self.ensure_guild_config(guild_id)

        if page == 1:
            estado = "✅ Activado" if cfg["enabled"] else "❌ Desactivado"
            return discord.Embed(
                title="⚙️ Configuración General",
                description=(
                    f"Estado del sistema: **{estado}**\n\n"
                    "Activa o desactiva el Anti‑Links.\n"
                    "Configura roles autorizados para usar `/antilinks`.\n"
                    "Controla si se permiten invitaciones de Discord."
                ),
                color=discord.Color.blue()
            )

        elif page == 2:
            return discord.Embed(
                title="👤 Whitelist de Usuarios",
                description="Usuarios que pueden enviar enlaces sin restricciones.",
                color=discord.Color.green()
            )

        elif page == 3:
            return discord.Embed(
                title="🛡️ Whitelist de Roles",
                description="Roles que pueden enviar enlaces sin restricciones.",
                color=discord.Color.purple()
            )

        elif page == 4:
            return discord.Embed(
                title="🌐 Whitelist de Dominios",
                description="Dominios permitidos (ej: `youtube.com`).",
                color=discord.Color.orange()
            )

        elif page == 5:
            return discord.Embed(
                title="🤝 Servidores Aliados",
                description="IDs de servidores aliados permitidos.",
                color=discord.Color.teal()
            )

        elif page == 6:
            log_channel_id = cfg.get("log_channel", 0)
            log_channel = guild.get_channel(log_channel_id) if log_channel_id else None

            auto_enabled = "✅ Activadas" if cfg["auto_punish_enabled"] else "❌ Desactivadas"
            action = cfg.get("auto_punish_action", "mute").upper()
            warn_limit = cfg.get("warn_limit", 3)
            warn_window = cfg.get("warn_window_minutes", 5)
            mute_minutes = cfg.get("auto_punish_mute_minutes", 10)

            desc = (
                f"**Sanciones automáticas:** {auto_enabled}\n"
                f"**Acción:** `{action}`\n"
                f"**Avisos necesarios:** `{warn_limit}`\n"
                f"**Ventana:** `{warn_window}` minutos\n"
                f"**Mute:** `{mute_minutes}` minutos\n"
                f"**Canal de logs:** {log_channel.mention if log_channel else 'No configurado'}\n\n"
                "Configura avisos, tiempo, sanciones y canal de logs."
            )

            return discord.Embed(
                title="🔧 Opciones Avanzadas",
                description=desc,
                color=discord.Color.magenta()
            )

    # ============================
    # SELECTS
    # ============================

    def select_roles_allowed(self, guild: discord.Guild, guild_id: str):
        cfg = self.ensure_guild_config(guild_id)
        allowed = cfg["allowed_roles"]

        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id),
                default=(role.id in allowed)
            )
            for role in guild.roles if role.name != "@everyone"
        ]

        return discord.ui.Select(
            placeholder="Selecciona roles autorizados",
            min_values=0,
            max_values=min(len(options), 25),
            options=options[:25],
            custom_id="select_allowed_roles"
        )

    def select_whitelist_users(self, guild: discord.Guild, guild_id: str):
        cfg = self.ensure_guild_config(guild_id)
        allowed = cfg["whitelist_users"]

        options = [
            discord.SelectOption(
                label=member.name,
                value=str(member.id),
                default=(member.id in allowed)
            )
            for member in guild.members
        ]

        return discord.ui.Select(
            placeholder="Selecciona usuarios permitidos",
            min_values=0,
            max_values=min(len(options), 25),
            options=options[:25],
            custom_id="select_whitelist_users"
        )

    def select_whitelist_roles(self, guild: discord.Guild, guild_id: str):
        cfg = self.ensure_guild_config(guild_id)
        allowed = cfg["whitelist_roles"]

        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id),
                default=(role.id in allowed)
            )
            for role in guild.roles if role.name != "@everyone"
        ]

        return discord.ui.Select(
            placeholder="Selecciona roles permitidos",
            min_values=0,
            max_values=min(len(options), 25),
            options=options[:25],
            custom_id="select_whitelist_roles"
        )

    def select_whitelist_domains(self, guild_id: str):
        cfg = self.ensure_guild_config(guild_id)
        domains = cfg["whitelist_domains"]

        options = [
            discord.SelectOption(
                label=domain,
                value=domain,
                default=True
            )
            for domain in domains
        ]

        return discord.ui.Select(
            placeholder="Selecciona dominios permitidos",
            min_values=0,
            max_values=min(len(options), 25),
            options=options[:25],
            custom_id="select_whitelist_domains"
        )

    def select_allowed_servers(self, guild_id: str):
        cfg = self.ensure_guild_config(guild_id)
        servers = cfg["allowed_servers"]

        options = [
            discord.SelectOption(
                label=server_id,
                value=server_id,
                default=True
            )
            for server_id in servers
        ]

        return discord.ui.Select(
            placeholder="Selecciona servidores aliados",
            min_values=0,
            max_values=min(len(options), 25),
            options=options[:25],
            custom_id="select_allowed_servers"
        )

    def select_log_channel(self, guild: discord.Guild, guild_id: str):
        cfg = self.ensure_guild_config(guild_id)
        current = cfg.get("log_channel", 0)

        options = []
        for ch in guild.text_channels:
            options.append(
                discord.SelectOption(
                    label=ch.name,
                    value=str(ch.id),
                    default=(ch.id == current)
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="No hay canales de texto",
                    value="0",
                    default=True
                )
            )

        return discord.ui.Select(
            placeholder="Selecciona canal de logs",
            min_values=0,
            max_values=1,
            options=options[:25],
            custom_id="select_log_channel"
        )

    def select_auto_action(self, guild_id: str):
        cfg = self.ensure_guild_config(guild_id)
        current = cfg.get("auto_punish_action", "mute")

        actions = [
            ("none", "Sin sanción (solo warn)"),
            ("mute", "Mute"),
            ("kick", "Kick"),
            ("ban", "Ban")
        ]

        options = [
            discord.SelectOption(
                label=label,
                value=value,
                default=(value == current)
            )
            for value, label in actions
        ]

        return discord.ui.Select(
            placeholder="Selecciona acción automática",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="select_auto_action"
        )

    # ============================
    # PANEL PRINCIPAL
    # ============================

    async def build_panel(self, interaction: discord.Interaction, page: int = 1, initial: bool = False):

        guild = interaction.guild
        guild_id = str(guild.id)
        cfg = self.ensure_guild_config(guild_id)

        # Guardar página del usuario
        self.user_pages[interaction.user.id] = page

        embed = self.embed_page(guild, guild_id, page)
        parent = self

        class PanelView(discord.ui.View):
            def __init__(self, parent, page):
                super().__init__(timeout=180)
                self.parent = parent
                self.page = page

            @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary, custom_id="prev_page")
            async def prev(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                await interaction_btn.response.defer()
                new_page = max(1, parent.user_pages.get(interaction_btn.user.id, 1) - 1)
                await parent.build_panel(interaction_btn, new_page)

            @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary, custom_id="next_page")
            async def next(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                await interaction_btn.response.defer()
                new_page = min(6, parent.user_pages.get(interaction_btn.user.id, 1) + 1)
                await parent.build_panel(interaction_btn, new_page)

            @discord.ui.button(label="💾 Guardar", style=discord.ButtonStyle.success, custom_id="save_antilinks")
            async def save(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                save_antilinks(parent.config)
                await interaction_btn.response.send_message(
                    "💾 Configuración guardada correctamente.",
                    ephemeral=True
                )

            @discord.ui.button(label="🧪 Test", style=discord.ButtonStyle.primary, custom_id="test_antilinks")
            async def test(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                await interaction_btn.response.send_message(
                    "🧪 Test Anti‑Links realizado. Todo funciona correctamente.",
                    ephemeral=True
                )

        view = PanelView(self, page)

        # CONTENIDO SEGÚN PÁGINA
        if page == 1:
            toggle_label = "Desactivar Anti‑Links" if cfg["enabled"] else "Activar Anti‑Links"

            toggle_button = discord.ui.Button(
                label=toggle_label,
                style=discord.ButtonStyle.danger,
                custom_id="toggle_enabled"
            )
            view.add_item(toggle_button)
            view.add_item(self.select_roles_allowed(guild, guild_id))

        elif page == 2:
            view.add_item(self.select_whitelist_users(guild, guild_id))

        elif page == 3:
            view.add_item(self.select_whitelist_roles(guild, guild_id))

        elif page == 4:
            view.add_item(self.select_whitelist_domains(guild_id))
            add_domain_button = discord.ui.Button(
                label="➕ Añadir dominio",
                style=discord.ButtonStyle.success,
                custom_id="add_domain"
            )
            view.add_item(add_domain_button)

        elif page == 5:
            view.add_item(self.select_allowed_servers(guild_id))

        elif page == 6:
            view.add_item(self.select_auto_action(guild_id))
            view.add_item(self.select_log_channel(guild, guild_id))

            toggle_auto = discord.ui.Button(
                label="Activar/Desactivar sanciones automáticas",
                style=discord.ButtonStyle.danger,
                custom_id="toggle_auto_punish"
            )
            adv_button = discord.ui.Button(
                label="⚙️ Configurar avisos/tiempos/mute",
                style=discord.ButtonStyle.secondary,
                custom_id="open_advanced_settings"
            )
            clear_warns = discord.ui.Button(
                label="🧹 Limpiar avisos",
                style=discord.ButtonStyle.secondary,
                custom_id="clear_warns"
            )

            view.add_item(toggle_auto)
            view.add_item(adv_button)
            view.add_item(clear_warns)

        if initial:
            await interaction.response.send_message(embed=embed, view=view)
        else:
            await interaction.edit_original_response(embed=embed, view=view)



# ============================
    # MANEJADOR DE INTERACCIONES
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        if not interaction.data:
            return

        custom = interaction.data.get("custom_id", "")
        user_id = interaction.user.id

        if custom not in [
            "next_page", "prev_page", "toggle_enabled", "save_antilinks",
            "test_antilinks", "select_allowed_roles", "select_whitelist_users",
            "select_whitelist_roles", "select_whitelist_domains",
            "select_allowed_servers", "add_domain",
            "select_log_channel", "select_auto_action",
            "toggle_auto_punish", "open_advanced_settings",
            "clear_warns"
        ]:
            return

        guild = interaction.guild
        if not guild:
            return

        guild_id = str(guild.id)
        cfg = self.ensure_guild_config(guild_id)

        # NAVEGACIÓN
        if custom == "next_page":
            self.user_pages[user_id] = min(6, self.user_pages.get(user_id, 1) + 1)
            return await self.build_panel(interaction, self.user_pages[user_id])

        if custom == "prev_page":
            self.user_pages[user_id] = max(1, self.user_pages.get(user_id, 1) - 1)
            return await self.build_panel(interaction, self.user_pages[user_id])

        # ACTIVAR / DESACTIVAR SISTEMA
        if custom == "toggle_enabled":
            cfg["enabled"] = not cfg["enabled"]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages.get(user_id, 1))

        # GUARDAR CONFIG
        if custom == "save_antilinks":
            save_antilinks(self.config)
            return await interaction.response.send_message(
                "💾 Configuración guardada correctamente.",
                ephemeral=True
            )

        # TEST
        if custom == "test_antilinks":
            return await interaction.response.send_message(
                "🧪 Test Anti‑Links realizado. Todo funciona correctamente.",
                ephemeral=True
            )

        # SELECTS
        if custom == "select_allowed_roles":
            cfg["allowed_roles"] = [int(v) for v in interaction.data.get("values", [])]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages.get(user_id, 1))

        if custom == "select_whitelist_users":
            cfg["whitelist_users"] = [int(v) for v in interaction.data.get("values", [])]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages.get(user_id, 1))

        if custom == "select_whitelist_roles":
            cfg["whitelist_roles"] = [int(v) for v in interaction.data.get("values", [])]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages.get(user_id, 1))

        if custom == "select_whitelist_domains":
            cfg["whitelist_domains"] = interaction.data.get("values", [])
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages.get(user_id, 1))

        if custom == "select_allowed_servers":
            cfg["allowed_servers"] = interaction.data.get("values", [])
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages.get(user_id, 1))

        if custom == "select_log_channel":
            values = interaction.data.get("values", [])
            cfg["log_channel"] = int(values[0]) if values else 0
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages.get(user_id, 1))

        if custom == "select_auto_action":
            values = interaction.data.get("values", [])
            if values:
                cfg["auto_punish_action"] = values[0]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages.get(user_id, 1))

        # BOTONES AVANZADOS
        if custom == "toggle_auto_punish":
            cfg["auto_punish_enabled"] = not cfg["auto_punish_enabled"]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages.get(user_id, 1))

        if custom == "open_advanced_settings":
            return await interaction.response.send_modal(AdvancedSettingsModal(self, guild_id))

        if custom == "clear_warns":
            cfg["warns"] = {}
            save_antilinks(self.config)
            return await interaction.response.send_message(
                "🧹 Todos los avisos han sido limpiados.",
                ephemeral=True
            )

        if custom == "add_domain":
            return await interaction.response.send_modal(AddDomainModal(self, guild_id))


    # ============================
    # SISTEMA DE WARNS (ASYNC)
    # ============================

    async def register_warn(self, guild_id: str, user_id: int):
        cfg = self.ensure_guild_config(guild_id)

        now = int(time.time())
        window = cfg.get("warn_window_minutes", 5) * 60
        limit = cfg.get("warn_limit", 3)

        if str(user_id) not in cfg["warns"]:
            cfg["warns"][str(user_id)] = []

        # Añadir nuevo aviso
        cfg["warns"][str(user_id)].append(now)

        # Limpiar avisos antiguos
        cfg["warns"][str(user_id)] = [
            t for t in cfg["warns"][str(user_id)] if now - t <= window
        ]

        save_antilinks(self.config)

        warn_count = len(cfg["warns"][str(user_id)])

        # ¿Supera el límite?
        if warn_count >= limit and cfg["auto_punish_enabled"]:
            action = await self.apply_punishment(guild_id, user_id)
            return warn_count, action
        else:
            return warn_count, "Warn"


    # ============================
    # APLICAR SANCIÓN (ASYNC)
    # ============================

    async def apply_punishment(self, guild_id: str, user_id: int):
        cfg = self.ensure_guild_config(guild_id)
        action = cfg.get("auto_punish_action", "mute")

        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return "Error"

        member = guild.get_member(user_id)
        if not member:
            return "Error"

        # MUTE
        if action == "mute":
            mute_minutes = cfg.get("auto_punish_mute_minutes", 10)
            try:
                mute_role = discord.utils.get(guild.roles, name="Muted")
                if not mute_role:
                    mute_role = await guild.create_role(name="Muted")
                    for channel in guild.channels:
                        await channel.set_permissions(mute_role, send_messages=False)

                await member.add_roles(mute_role, reason="Anti‑Links Auto‑Mute")
                return f"Mute ({mute_minutes} min)"
            except:
                return "Error"

        # KICK
        if action == "kick":
            try:
                await member.kick(reason="Anti‑Links Auto‑Kick")
                return "Kick"
            except:
                return "Error"

        # BAN
        if action == "ban":
            try:
                await member.ban(reason="Anti‑Links Auto‑Ban")
                return "Ban"
            except:
                return "Error"

        # SIN SANCIÓN
        return "Warn"



    # ============================
    # ENVIAR LOGS
    # ============================

    async def send_log(self, guild: discord.Guild, cfg: dict, user: discord.Member, content: str, warn_count: int, action: str):
        log_channel_id = cfg.get("log_channel", 0)
        if not log_channel_id:
            return

        channel = guild.get_channel(log_channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="🚨 Anti‑Links — Enlace Detectado",
            color=discord.Color.red()
        )
        embed.add_field(name="👤 Usuario", value=f"{user.mention} (`{user.id}`)", inline=False)
        embed.add_field(name="🔗 Mensaje", value=content[:1000], inline=False)
        embed.add_field(name="⚠ Avisos", value=f"{warn_count}/{cfg.get('warn_limit', 3)}", inline=True)
        embed.add_field(name="🛠 Acción tomada", value=action, inline=True)
        embed.timestamp = discord.utils.utcnow()

        await channel.send(embed=embed)

    # ============================
    # DETECCIÓN DE LINKS
    # ============================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author.bot:
            return

        if not message.content:
            return

        guild = message.guild
        if not guild:
            return

        guild_id = str(guild.id)
        cfg = self.ensure_guild_config(guild_id)

        if not cfg["enabled"]:
            return

        content = message.content.lower()

        # Whitelist usuarios
        if message.author.id in cfg["whitelist_users"]:
            return

        # Whitelist roles
        if any(role.id in cfg["whitelist_roles"] for role in message.author.roles):
            return

        # Whitelist dominios
        for domain in cfg["whitelist_domains"]:
            if domain.lower() in content:
                return

        # Whitelist servidores aliados
        if any(inv in content for inv in ["discord.gg/", "discord.com/invite/"]):
            for server_id in cfg["allowed_servers"]:
                if server_id in content:
                    return

        # Detectar enlaces
        if not ("http://" in content or "https://" in content):
            return

        # BLOQUEO DE ACORTADORES
        if cfg["block_shorteners"]:
            shorteners = [
                "bit.ly", "tinyurl", "t.co", "is.gd", "cutt.ly",
                "rebrand.ly", "shorturl", "soo.gd", "buff.ly"
            ]
            if any(s in content for s in shorteners):
                try:
                    await message.delete()
                except:
                    pass

                warn_count, action = self.register_warn(guild_id, message.author.id)
                await self.send_log(guild, cfg, message.author, content, warn_count, action)

                if action == "Warn":
                    await message.channel.send(
                        f"{message.author.mention} ⚠ Advertencia por enviar enlaces acortados.",
                        delete_after=5
                    )
                return

        # BLOQUEO DE ENLACES DISFRAZADOS
        if cfg["block_obfuscated"]:
            obfuscated_patterns = ["h t t p", "hxxp", ":// ", " . ", "dot com"]
            if any(p in content for p in obfuscated_patterns):
                try:
                    await message.delete()
                except:
                    pass

                warn_count, action = self.register_warn(guild_id, message.author.id)
                await self.send_log(guild, cfg, message.author, content, warn_count, action)

                if action == "Warn":
                    await message.channel.send(
                        f"{message.author.mention} ⚠ Advertencia por intentar ocultar enlaces.",
                        delete_after=5
                    )
                return

        # BLOQUEO GENERAL
        try:
            await message.delete()
        except:
            pass

        warn_count, action = self.register_warn(guild_id, message.author.id)
        await self.send_log(guild, cfg, message.author, content, warn_count, action)

        if action == "Warn":
            await message.channel.send(
                f"{message.author.mention} ⚠ No puedes enviar enlaces en este servidor.",
                delete_after=5
            )
        else:
            await message.channel.send(
                f"{message.author.mention} 🚫 Acción aplicada: **{action}**",
                delete_after=5
            )

# ============================
# SETUP FINAL DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(AntiLinksCog(bot))

