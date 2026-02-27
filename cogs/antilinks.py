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

        options = options[:25]

        return discord.ui.Select(
            placeholder="Selecciona roles autorizados",
            min_values=0,
            max_values=min(len(options), 25),
            options=options,
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

        options = options[:25]

        return discord.ui.Select(
            placeholder="Selecciona usuarios permitidos",
            min_values=0,
            max_values=min(len(options), 25),
            options=options,
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

        options = options[:25]

        return discord.ui.Select(
            placeholder="Selecciona roles permitidos",
            min_values=0,
            max_values=min(len(options), 25),
            options=options,
            custom_id="select_whitelist_roles"
        )


    # ============================
    # Botones principales
    # ============================

    def main_buttons(self, guild_id: str, page: int):
        enabled = self.config[guild_id]["enabled"]

        btn_enable = discord.ui.Button(
            label="🟢 Activar Anti‑Links" if not enabled else "🔴 Desactivar Anti‑Links",
            style=discord.ButtonStyle.green if not enabled else discord.ButtonStyle.red,
            custom_id="toggle_enabled"
        )

        btn_save = discord.ui.Button(
            label="💾 Guardar",
            style=discord.ButtonStyle.blurple,
            custom_id="save_antilinks"
        )

        btn_test = None
        if page == 6:
            btn_test = discord.ui.Button(
                label="🧪 Test Anti‑Links",
                style=discord.ButtonStyle.blurple,
                custom_id="test_antilinks"
            )

        return btn_enable, btn_save, btn_test

    # ============================
    # Botones de navegación
    # ============================

    def nav_buttons(self, page: int):
        btn_prev = discord.ui.Button(
            label="⬅️ Anterior",
            style=discord.ButtonStyle.gray,
            custom_id="prev_page",
            disabled=(page == 1)
        )

        btn_next = discord.ui.Button(
            label="➡️ Siguiente",
            style=discord.ButtonStyle.gray,
            custom_id="next_page",
            disabled=(page == 6)
        )

        return [btn_prev, btn_next]

    # ============================
    # Construcción del panel
    # ============================

    async def build_panel(self, interaction: discord.Interaction, page: int):
        guild = interaction.guild
        guild_id = str(guild.id)

        self.user_pages[interaction.user.id] = page

        embed = self.embed_page(page)
        view = discord.ui.View(timeout=300)

        # Página 1 — Configuración general
        if page == 1:
            select_roles = self.select_roles_allowed(guild, guild_id)
            view.add_item(select_roles)

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 2 — Whitelist usuarios
        elif page == 2:
            select_users = self.select_whitelist_users(guild, guild_id)
            view.add_item(select_users)

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 3 — Whitelist roles
        elif page == 3:
            select_roles = self.select_whitelist_roles(guild, guild_id)
            view.add_item(select_roles)

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 4 — Dominios permitidos
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

        # Página 5 — Servidores aliados
        elif page == 5:
            allies = self.config[guild_id]["allowed_servers"]
            embed.add_field(
                name="Servidores aliados (IDs)",
                value="\n".join(allies) if allies else "Ninguno",
                inline=False
            )

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 6 — Opciones avanzadas
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

        # Botones de navegación
        for btn in self.nav_buttons(page):
            view.add_item(btn)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ============================
    # Comando /antilinks
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
                "allow_discord_invites": False,
                "allowed_roles": [],
                "whitelist_users": [],
                "whitelist_roles": [],
                "whitelist_domains": [],
                "allowed_servers": [],
                "block_shorteners": True,
                "block_obfuscated": True
            }
            save_antilinks(self.config)

        # Verificar permisos
        allowed_roles = self.config[guild_id]["allowed_roles"]

        if allowed_roles:
            if not any(role.id in allowed_roles for role in interaction.user.roles):
                return await interaction.response.send_message(
                    "❌ No tienes permiso para usar este comando.",
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
    # Actualizar panel sin recrearlo
    # ============================

    async def update_panel(self, interaction: discord.Interaction, page: int):
        guild = interaction.guild
        guild_id = str(guild.id)

        view = discord.ui.View(timeout=300)
        embed = self.embed_page(page)

        # Página 1
        if page == 1:
            select_roles = self.select_roles_allowed(guild, guild_id)
            view.add_item(select_roles)

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 2
        elif page == 2:
            select_users = self.select_whitelist_users(guild, guild_id)
            view.add_item(select_users)

            btn_enable, btn_save, _ = self.main_buttons(guild_id, page)
            view.add_item(btn_enable)
            view.add_item(btn_save)

        # Página 3
        elif page == 3:
            select_roles = self.select_whitelist_roles(guild, guild_id)
            view.add_item(select_roles)

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

        # Whitelist servidores aliados (solo invitaciones)
        if any(inv in content for inv in ["discord.gg/", "discord.com/invite/"]):
            for server_id in config["allowed_servers"]:
                if server_id in content:
                    return

        # Detectar enlaces
        if "http://" in content or "https://" in content:
            pass
        else:
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
