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
# COG ANTI-LINKS
# ============================

class AntiLinksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_antilinks()
        self.user_pages = {}

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
                "manage_role": 0   # NUEVO: rol que puede usar /antilinks
            }
            save_antilinks(self.config)

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

        await self.build_panel(interaction, page=1)


    # ============================
    #  ROL QUE PUEDE USAR /antilinks
    # ============================

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="antilinks_setrole",
        description="Establece el rol que puede usar /antilinks en este servidor"
    )
    @app_commands.describe(
        rol="Rol que podrá usar /antilinks"
    )
    async def antilinks_setrole(self, interaction: discord.Interaction, rol: discord.Role):

        guild_id = str(interaction.guild.id)

        # Crear config si no existe
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

        self.config[guild_id]["manage_role"] = rol.id
        save_antilinks(self.config)

        await interaction.response.send_message(
            f"🔐 El rol {rol.mention} ahora puede usar `/antilinks`.",
            ephemeral=True
        )

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
    # SELECTS (TU SISTEMA)
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
    # BOTONES PRINCIPALES
    # ============================

    def main_buttons(self, guild_id: str, page: int):
        enabled = self.config[guild_id]["enabled"]

        btn_enable = discord.ui.Button(
            label="Desactivar" if enabled else "Activar",
            style=discord.ButtonStyle.green if not enabled else discord.ButtonStyle.red,
            custom_id="toggle_enabled"
        )

        btn_save = discord.ui.Button(
            label="Guardar",
            style=discord.ButtonStyle.blurple,
            custom_id="save_antilinks"
        )

        btn_test = None
        if page == 6:
            btn_test = discord.ui.Button(
                label="Test",
                style=discord.ButtonStyle.gray,
                custom_id="test_antilinks"
            )

        return btn_enable, btn_save, btn_test

    # ============================
    # BOTONES DE NAVEGACIÓN
    # ============================

    def nav_buttons(self, page: int):
        buttons = []

        if page > 1:
            buttons.append(discord.ui.Button(
                label="⬅️",
                style=discord.ButtonStyle.secondary,
                custom_id="prev_page"
            ))

        if page < 6:
            buttons.append(discord.ui.Button(
                label="➡️",
                style=discord.ButtonStyle.secondary,
                custom_id="next_page"
            ))

        return buttons

    # ============================
    # PANEL PRINCIPAL
    # ============================

    async def build_panel(self, interaction: discord.Interaction, page: int):
        guild = interaction.guild
        guild_id = str(guild.id)

        embed = self.embed_page(page)
        view = discord.ui.View(timeout=300)

        # Página 1
        if page == 1:
            view.add_item(self.select_roles_allowed(guild, guild_id))
            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 2
        elif page == 2:
            view.add_item(self.select_whitelist_users(guild, guild_id))
            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 3
        elif page == 3:
            view.add_item(self.select_whitelist_roles(guild, guild_id))
            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 4
        elif page == 4:
            domains = self.config[guild_id]["whitelist_domains"]
            embed.add_field(
                name="Dominios permitidos",
                value="\n".join(domains) if domains else "Ninguno",
                inline=False
            )
            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 5
        elif page == 5:
            allies = self.config[guild_id]["allowed_servers"]
            embed.add_field(
                name="Servidores aliados",
                value="\n".join(allies) if allies else "Ninguno",
                inline=False
            )
            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 6
        elif page == 6:
            config = self.config[guild_id]
            embed.add_field(
                name="Bloquear acortadores",
                value="Sí" if config["block_shorteners"] else "No",
                inline=False
            )
            embed.add_field(
                name="Bloquear enlaces disfrazados",
                value="Sí" if config["block_obfuscated"] else "No",
                inline=False
            )
            btn_enable, btn_save, btn_test = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)
            if btn_test:
                view.add_item(btn_test)

        # Navegación
        for btn in self.nav_buttons(page):
            view.add_item(btn)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ============================
    # LISTENER DE COMPONENTES
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
            current = self.config[guild_id]["enabled"]
            self.config[guild_id]["enabled"] = not current
            save_antilinks(self.config)
            return await self.update_panel(interaction, page)

        # Guardar
        if custom_id == "save_antilinks":
            save_antilinks(self.config)
            return await interaction.response.send_message(
                "💾 Configuración guardada.",
                ephemeral=True
            )

        # Test
        if custom_id == "test_antilinks":
            return await interaction.response.send_message(
                "🧪 Test Anti‑Links enviado.",
                ephemeral=True
            )

        # Select: roles autorizados
        if custom_id == "select_allowed_roles":
            selected = interaction.data.get("values", [])
            self.config[guild_id]["allowed_roles"] = [int(r) for r in selected]
            save_antilinks(self.config)
            return await self.update_panel(interaction, page)

        # Select: whitelist usuarios
        if custom_id == "select_whitelist_users":
            selected = interaction.data.get("values", [])
            self.config[guild_id]["whitelist_users"] = [int(u) for u in selected]
            save_antilinks(self.config)
            return await self.update_panel(interaction, page)

        # Select: whitelist roles
        if custom_id == "select_whitelist_roles":
            selected = interaction.data.get("values", [])
            self.config[guild_id]["whitelist_roles"] = [int(r) for r in selected]
            save_antilinks(self.config)
            return await self.update_panel(interaction, page)

    # ============================
    # ACTUALIZAR PANEL
    # ============================

    async def update_panel(self, interaction: discord.Interaction, page: int):
        guild = interaction.guild
        guild_id = str(guild.id)

        view = discord.ui.View(timeout=300)
        embed = self.embed_page(page)

        # Página 1
        if page == 1:
            view.add_item(self.select_roles_allowed(guild, guild_id))
            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 2
        elif page == 2:
            view.add_item(self.select_whitelist_users(guild, guild_id))
            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 3
        elif page == 3:
            view.add_item(self.select_whitelist_roles(guild, guild_id))
            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 4
        elif page == 4:
            domains = self.config[guild_id]["whitelist_domains"]
            embed.add_field(
                name="Dominios permitidos",
                value="\n".join(domains) if domains else "Ninguno",
                inline=False
            )
            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 5
        elif page == 5:
            allies = self.config[guild_id]["allowed_servers"]
            embed.add_field(
                name="Servidores aliados",
                value="\n".join(allies) if allies else "Ninguno",
                inline=False
            )
            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 6
        elif page == 6:
            config = self.config[guild_id]
            embed.add_field(
                name="Bloquear acortadores",
                value="Sí" if config["block_shorteners"] else "No",
                inline=False
            )
            embed.add_field(
                name="Bloquear enlaces disfrazados",
                value="Sí" if config["block_obfuscated"] else "No",
                inline=False
            )
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
    # DETECCIÓN DE LINKS
    # ============================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author.bot:
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
# SETUP DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(AntiLinksCog(bot))
