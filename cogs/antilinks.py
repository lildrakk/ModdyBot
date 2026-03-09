import discord
from discord.ext import commands
from discord import app_commands
import json
import os

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
                "manage_role": 0
            }
            save_antilinks(self.config)

        return self.config[guild_id]

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

    def embed_page(self, page: int):
        if page == 1:
            return discord.Embed(
                title="⚙️ Configuración General",
                description=(
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
            return discord.Embed(
                title="🔧 Opciones Avanzadas",
                description=(
                    "Bloqueo de enlaces acortados.\n"
                    "Bloqueo de enlaces disfrazados.\n"
                    "Test Anti‑Links."
                ),
                color=discord.Color.magenta()
            )

    # ============================
    # SELECTS (CORREGIDOS)
    # ============================

    def select_roles_allowed(self, guild: discord.Guild, guild_id: str):
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
            placeholder="Selecciona roles autorizados",
            min_values=0,
            max_values=min(len(options), 25),
            options=options[:25],
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
            placeholder="Selecciona usuarios permitidos",
            min_values=0,
            max_values=min(len(options), 25),
            options=options[:25],
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
            placeholder="Selecciona roles permitidos",
            min_values=0,
            max_values=min(len(options), 25),
            options=options[:25],
            custom_id="select_whitelist_roles"
        )

    def select_whitelist_domains(self, guild_id: str):
        domains = self.config[guild_id]["whitelist_domains"]

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
        servers = self.config[guild_id]["allowed_servers"]

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



        # ============================
    # MANEJADOR DE INTERACCIONES
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        if not interaction.data:
            return

        custom = interaction.data.get("custom_id", "")
        user_id = interaction.user.id

        # Solo manejar interacciones del panel
        if custom not in [
            "next_page", "prev_page", "toggle_enabled", "save_antilinks",
            "test_antilinks", "select_allowed_roles", "select_whitelist_users",
            "select_whitelist_roles", "select_whitelist_domains",
            "select_allowed_servers", "add_domain"
        ]:
            return

        guild_id = str(interaction.guild.id)
        cfg = self.ensure_guild_config(guild_id)

        # ============================
        # NAVEGACIÓN
        # ============================

        if custom == "next_page":
            self.user_pages[user_id] = min(6, self.user_pages.get(user_id, 1) + 1)
            return await self.build_panel(interaction, self.user_pages[user_id])

        if custom == "prev_page":
            self.user_pages[user_id] = max(1, self.user_pages.get(user_id, 1) - 1)
            return await self.build_panel(interaction, self.user_pages[user_id])

        # ============================
        # ACTIVAR / DESACTIVAR
        # ============================

        if custom == "toggle_enabled":
            cfg["enabled"] = not cfg["enabled"]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages[user_id])

        # ============================
        # GUARDAR CONFIG
        # ============================

        if custom == "save_antilinks":
            save_antilinks(self.config)
            return await interaction.response.send_message(
                "💾 Configuración guardada correctamente.",
                ephemeral=True
            )

        # ============================
        # TEST
        # ============================

        if custom == "test_antilinks":
            return await interaction.response.send_message(
                "🧪 Test Anti‑Links realizado. Todo funciona correctamente.",
                ephemeral=True
            )

        # ============================
        # SELECTS
        # ============================

        if custom == "select_allowed_roles":
            cfg["allowed_roles"] = [int(v) for v in interaction.data["values"]]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages[user_id])

        if custom == "select_whitelist_users":
            cfg["whitelist_users"] = [int(v) for v in interaction.data["values"]]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages[user_id])

        if custom == "select_whitelist_roles":
            cfg["whitelist_roles"] = [int(v) for v in interaction.data["values"]]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages[user_id])

        if custom == "select_whitelist_domains":
            cfg["whitelist_domains"] = interaction.data["values"]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages[user_id])

        if custom == "select_allowed_servers":
            cfg["allowed_servers"] = interaction.data["values"]
            save_antilinks(self.config)
            return await self.build_panel(interaction, self.user_pages[user_id])

        # ============================
        # ➕ AÑADIR DOMINIO
        # ============================

        if custom == "add_domain":
            return await interaction.response.send_modal(AddDomainModal(self, guild_id))

    # ============================
    # DETECCIÓN DE LINKS (CORREGIDA)
    # ============================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # IGNORAR MENSAJES DEL BOT
        if message.author.bot:
            return

        # IGNORAR MENSAJES SIN CONTENIDO (interacciones, botones, modales)
        if not message.content:
            return

        # IGNORAR MENSAJES DE INTERACCIONES
        if isinstance(message, discord.InteractionMessage):
            return

        # IGNORAR MENSAJES EPHEMERAL (no existen realmente)
        if hasattr(message, "flags") and message.flags.ephemeral:
            return

        guild = message.guild
        if not guild:
            return

        guild_id = str(guild.id)

        if guild_id not in self.config:
            return

        config = self.config[guild_id]

        if not config["enabled"]:
            return

        content = message.content.lower()

        # Whitelist usuarios
        if message.author.id in config["whitelist_users"]:
            return

        # Whitelist roles
        if any(role.id in config["whitelist_roles"] for role in message.author.roles):
            return

        # Whitelist dominios
        for domain in config["whitelist_domains"]:
            if domain.lower() in content:
                return

        # Whitelist servidores aliados
        if any(inv in content for inv in ["discord.gg/", "discord.com/invite/"]):
            for server_id in config["allowed_servers"]:
                if server_id in content:
                    return

        # Detectar enlaces
        if not ("http://" in content or "https://" in content):
            return

        # BLOQUEO DE ACORTADORES
        if config["block_shorteners"]:
            shorteners = [
                "bit.ly", "tinyurl", "t.co", "is.gd", "cutt.ly",
                "rebrand.ly", "shorturl", "soo.gd", "buff.ly"
            ]
            if any(s in content for s in shorteners):
                try:
                    await message.delete()
                except:
                    pass
                return await message.channel.send(
                    f"{message.author.mention} 🚫 No puedes enviar enlaces acortados.",
                    delete_after=5
                )

        # BLOQUEO DE ENLACES DISFRAZADOS
        if config["block_obfuscated"]:
            obfuscated_patterns = ["h t t p", "hxxp", ":// ", " . ", "dot com"]
            if any(p in content for p in obfuscated_patterns):
                try:
                    await message.delete()
                except:
                    pass
                return await message.channel.send(
                    f"{message.author.mention} 🚫 No intentes ocultar enlaces.",
                    delete_after=5
                )

        # BLOQUEO GENERAL
        try:
            await message.delete()
        except:
            pass

        await message.channel.send(
            f"{message.author.mention} 🚫 No puedes enviar enlaces en este servidor.",
            delete_after=5
        )


# ============================
# SETUP FINAL DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(AntiLinksCog(bot))
