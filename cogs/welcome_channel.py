import discord
from discord.ext import commands
from discord import app_commands
import json
import os

WELCOME_FILE = "welcome.json"


# ============================
# JSON LOADER
# ============================

def load_welcome():
    if not os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "w") as f:
            json.dump({}, f, indent=4)

    try:
        with open(WELCOME_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_welcome(data):
    with open(WELCOME_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# COG DE BIENVENIDA + VERIFICACIÓN PRO
# ============================

class WelcomeChannelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.welcome_config = load_welcome()
        self.user_pages: dict[int, int] = {}       # user_id -> page
        self.panel_owner: dict[int, int] = {}      # guild_id -> user_id
        self.panel_message: dict[int, int] = {}    # guild_id -> message_id

    # ============================
    # CONFIG POR SERVIDOR
    # ============================

    def ensure_guild_config(self, guild_id: str):
        if guild_id not in self.welcome_config:
            self.welcome_config[guild_id] = {
                "enabled": False,
                "welcome_channel": None,
                "log_channel": None,
                "verify_give_role": None,
                "verify_remove_role": None,
                "welcome_message": "🎉 Bienvenido {user} a **{server}**! Ahora somos {membercount} miembros.",
                "welcome_image": None,
                # Lista de custom_id que cuentan como verificación/captcha
                "verification_ids": []  # lista de strings
            }
            save_welcome(self.welcome_config)
        return self.welcome_config[guild_id]

    # ============================
    # EMBEDS POR PÁGINA
    # ============================

    def welcome_embed_page(self, guild: discord.Guild, page: int):
        cfg = self.ensure_guild_config(str(guild.id))

        if page == 1:
            ch = guild.get_channel(cfg.get("welcome_channel") or 0)
            log_ch = guild.get_channel(cfg.get("log_channel") or 0)
            give_role = guild.get_role(cfg.get("verify_give_role") or 0)
            rem_role = guild.get_role(cfg.get("verify_remove_role") or 0)

            verif_ids = cfg.get("verification_ids", [])
            verif_text = ", ".join(verif_ids) if verif_ids else "❌ Ninguno configurado"

            embed = discord.Embed(
                title="👋 Bienvenida + Verificación — General",
                description="Activa la bienvenida, elige canal, logs, roles y custom IDs de verificación/captcha.",
                color=discord.Color.blurple()
            )
            embed.add_field(
                name="Estado",
                value="🟢 Activada" if cfg["enabled"] else "🔴 Desactivada",
                inline=False
            )
            embed.add_field(
                name="Canal de bienvenida",
                value=ch.mention if ch else "❌ No configurado",
                inline=False
            )
            embed.add_field(
                name="Canal de logs",
                value=log_ch.mention if log_ch else "❌ No configurado",
                inline=False
            )
            embed.add_field(
                name="Rol que se da al verificar",
                value=give_role.mention if give_role else "❌ No configurado",
                inline=False
            )
            embed.add_field(
                name="Rol que se quita al verificar",
                value=rem_role.mention if rem_role else "❌ No configurado",
                inline=False
            )
            embed.add_field(
                name="Custom IDs de verificación/captcha",
                value=f"```{verif_text}```",
                inline=False
            )
            return embed

        if page == 2:
            embed = discord.Embed(
                title="💬 Mensaje de bienvenida",
                description="Edita el mensaje y revisa la vista previa.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Mensaje actual",
                value=f"```{cfg['welcome_message']}```",
                inline=False
            )
            embed.add_field(
                name="Variables disponibles",
                value="`{user}` — Menciona al usuario\n"
                      "`{server}` — Nombre del servidor\n"
                      "`{membercount}` — Miembros totales",
                inline=False
            )
            return embed

        if page == 3:
            embed = discord.Embed(
                title="🖼 Imagen de bienvenida",
                description="Configura la imagen de bienvenida.",
                color=discord.Color.orange()
            )
            if cfg["welcome_image"]:
                embed.add_field(
                    name="Imagen actual",
                    value=cfg["welcome_image"],
                    inline=False
                )
                embed.set_image(url=cfg["welcome_image"])
            else:
                embed.add_field(
                    name="Imagen actual",
                    value="❌ No configurada",
                    inline=False
                )
            return embed

    # ============================
    # SELECTS
    # ============================

    def select_welcome_channel(self, guild, cfg):
        options = [
            discord.SelectOption(
                label=c.name,
                value=str(c.id),
                default=(cfg["welcome_channel"] == c.id)
            )
            for c in guild.text_channels
        ][:25]

        if not options:
            options = [discord.SelectOption(label="Sin canales", value="none")]

        return discord.ui.Select(
            placeholder="Selecciona canal de bienvenida",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="welcome_select_channel"
        )

    def select_log_channel(self, guild, cfg):
        options = [
            discord.SelectOption(
                label=c.name,
                value=str(c.id),
                default=(cfg["log_channel"] == c.id)
            )
            for c in guild.text_channels
        ][:25]

        if not options:
            options = [discord.SelectOption(label="Sin canales", value="none")]

        return discord.ui.Select(
            placeholder="Selecciona canal de logs",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="welcome_select_log"
        )

    def select_give_role(self, guild, cfg):
        roles = [r for r in guild.roles if r.name != "@everyone"]
        options = [
            discord.SelectOption(
                label=r.name,
                value=str(r.id),
                default=(cfg["verify_give_role"] == r.id)
            )
            for r in roles
        ][:25]

        if not options:
            options = [discord.SelectOption(label="Sin roles", value="none")]

        return discord.ui.Select(
            placeholder="Rol que se dará al verificar",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="welcome_select_give_role"
        )

    def select_remove_role(self, guild, cfg):
        roles = [r for r in guild.roles if r.name != "@everyone"]
        options = [
            discord.SelectOption(
                label=r.name,
                value=str(r.id),
                default=(cfg["verify_remove_role"] == r.id)
            )
            for r in roles
        ][:25]

        if not options:
            options = [discord.SelectOption(label="Sin roles", value="none")]

        return discord.ui.Select(
            placeholder="Rol que se quitará al verificar",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="welcome_select_remove_role"
        )

    # ============================
    # BOTONES
    # ============================

    def welcome_main_buttons(self, cfg):
        btn_enable = discord.ui.Button(
            label="🟢 Activada" if cfg["enabled"] else "🔴 Desactivada",
            style=discord.ButtonStyle.green if cfg["enabled"] else discord.ButtonStyle.red,
            custom_id="welcome_toggle_enabled"
        )

        btn_test = discord.ui.Button(
            label="🧪 Enviar bienvenida de prueba",
            style=discord.ButtonStyle.blurple,
            custom_id="welcome_test"
        )

        btn_msg = discord.ui.Button(
            label="✏️ Editar mensaje",
            style=discord.ButtonStyle.gray,
            custom_id="welcome_edit_message"
        )

        btn_img = discord.ui.Button(
            label="🖼 Cambiar/Quitar imagen",
            style=discord.ButtonStyle.gray,
            custom_id="welcome_edit_image"
        )

        btn_verif_ids = discord.ui.Button(
            label="⚙️ Custom IDs verificación/captcha",
            style=discord.ButtonStyle.gray,
            custom_id="welcome_edit_verification_ids"
        )

        return btn_enable, btn_test, btn_msg, btn_img, btn_verif_ids

    def welcome_nav_buttons(self, page):
        buttons = []

        if page > 1:
            buttons.append(
                discord.ui.Button(
                    label="⬅ Anterior",
                    style=discord.ButtonStyle.secondary,
                    custom_id="welcome_prev_page"
                )
            )

        if page < 3:
            buttons.append(
                discord.ui.Button(
                    label="Siguiente ➡",
                    style=discord.ButtonStyle.secondary,
                    custom_id="welcome_next_page"
                )
            )

        return buttons

    # ============================
    # PANEL BUILDER
    # ============================

    async def welcome_build_panel(self, interaction: discord.Interaction, page: int):
        guild = interaction.guild
        guild_id = str(guild.id)
        cfg = self.ensure_guild_config(guild_id)

        embed = self.welcome_embed_page(guild, page)
        view = discord.ui.View(timeout=None)

        # Página 1 → selects + botones generales
        if page == 1:
            view.add_item(self.select_welcome_channel(guild, cfg))
            view.add_item(self.select_log_channel(guild, cfg))
            view.add_item(self.select_give_role(guild, cfg))
            view.add_item(self.select_remove_role(guild, cfg))

        btn_enable, btn_test, btn_msg, btn_img, btn_verif_ids = self.welcome_main_buttons(cfg)

        if page == 1:
            view.add_item(btn_enable)
            view.add_item(btn_test)
            view.add_item(btn_verif_ids)

        if page == 2:
            view.add_item(btn_msg)

        if page == 3:
            view.add_item(btn_img)

        for b in self.welcome_nav_buttons(page):
            view.add_item(b)

        # Enviar o editar panel (siempre ephemeral)
        if guild_id not in self.panel_message:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            msg = await interaction.original_response()
            self.panel_message[guild_id] = msg.id
        else:
            try:
                msg = await interaction.channel.fetch_message(self.panel_message[guild_id])
                await msg.edit(embed=embed, view=view)
                if not interaction.response.is_done():
                    await interaction.response.defer()
            except:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                msg = await interaction.original_response()
                self.panel_message[guild_id] = msg.id

    async def welcome_update_panel(self, interaction: discord.Interaction, page: int):
        await self.welcome_build_panel(interaction, page)

    # ============================
    # COMANDO PARA ABRIR PANEL
    # ============================

    @app_commands.command(
        name="welcome",
        description="Abrir panel de configuración de bienvenida y verificación"
    )
    async def welcome_cmd(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                "❌ No tienes permisos para usar este comando.",
                ephemeral=True
            )

        guild_id = str(interaction.guild.id)
        self.panel_owner[guild_id] = interaction.user.id
        self.user_pages[interaction.user.id] = 1

        await self.welcome_build_panel(interaction, 1)



# ============================
    # INTERACCIONES DEL PANEL + VERIFICACIÓN
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id")
        if not custom_id:
            return

        guild = interaction.guild
        if not guild:
            return

        guild_id = str(guild.id)
        cfg = self.ensure_guild_config(guild_id)
        user = interaction.user

        # ============================
        # 1) DETECCIÓN DE VERIFICACIÓN (BOTÓN/CAPTCHA CONFIGURABLE)
        # ============================

        if custom_id in cfg.get("verification_ids", []):
            if isinstance(user, discord.Member):
                give_role_id = cfg.get("verify_give_role")
                rem_role_id = cfg.get("verify_remove_role")

                given = None
                removed = None

                try:
                    if give_role_id:
                        role = guild.get_role(int(give_role_id))
                        if role and role not in user.roles:
                            await user.add_roles(role, reason="Verificación (WELCOME PRO)")
                            given = role
                except:
                    pass

                try:
                    if rem_role_id:
                        role = guild.get_role(int(rem_role_id))
                        if role and role in user.roles:
                            await user.remove_roles(role, reason="Verificación (WELCOME PRO)")
                            removed = role
                except:
                    pass

                await self.send_verification_log(
                    member=user,
                    guild=guild,
                    given_role=given,
                    removed_role=removed
                )

                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "✅ Has sido verificado correctamente.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "✅ Has sido verificado correctamente.",
                        ephemeral=True
                    )

            return

        # ============================
        # 2) PANEL DE BIENVENIDA (custom_id que empiezan por welcome_)
        # ============================

        if not custom_id.startswith("welcome_"):
            return

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
        # MODALES
        # ============================

        class WelcomeMessageModal(discord.ui.Modal):
            def __init__(self, cog):
                super().__init__(title="Editar mensaje de bienvenida")
                self.cog = cog
                self.input = discord.ui.TextInput(
                    label="Nuevo mensaje",
                    style=discord.TextStyle.paragraph,
                    required=True,
                    default=cfg["welcome_message"][:4000]
                )
                self.add_item(self.input)

            async def on_submit(self, modal_interaction: discord.Interaction):
                guild_id_local = str(modal_interaction.guild.id)
                self.cog.welcome_config[guild_id_local]["welcome_message"] = str(self.input.value)
                save_welcome(self.cog.welcome_config)
                await modal_interaction.response.send_message(
                    "💾 Mensaje de bienvenida actualizado.",
                    ephemeral=True
                )
                await self.cog.welcome_update_panel(modal_interaction, 2)

        class WelcomeImageModal(discord.ui.Modal):
            def __init__(self, cog):
                super().__init__(title="Cambiar imagen de bienvenida")
                self.cog = cog
                self.input = discord.ui.TextInput(
                    label="URL de la imagen (o deja vacío para quitar)",
                    style=discord.TextStyle.short,
                    required=False
                )
                self.add_item(self.input)

            async def on_submit(self, modal_interaction: discord.Interaction):
                guild_id_local = str(modal_interaction.guild.id)
                url = self.input.value.strip()
                if url:
                    self.cog.welcome_config[guild_id_local]["welcome_image"] = url
                else:
                    self.cog.welcome_config[guild_id_local]["welcome_image"] = None
                save_welcome(self.cog.welcome_config)
                await modal_interaction.response.send_message(
                    "💾 Imagen de bienvenida actualizada.",
                    ephemeral=True
                )
                await self.cog.welcome_update_panel(modal_interaction, 3)

        class VerificationIDsModal(discord.ui.Modal):
            def __init__(self, cog):
                super().__init__(title="Custom IDs de verificación/captcha")
                self.cog = cog
                current = ", ".join(cfg.get("verification_ids", []))
                self.input = discord.ui.TextInput(
                    label="IDs separados por coma (ej: verify_button, captcha_ok)",
                    style=discord.TextStyle.paragraph,
                    required=False,
                    default=current[:4000]
                )
                self.add_item(self.input)

            async def on_submit(self, modal_interaction: discord.Interaction):
                guild_id_local = str(modal_interaction.guild.id)
                raw = self.input.value.strip()
                if raw:
                    ids = [x.strip() for x in raw.split(",") if x.strip()]
                else:
                    ids = []
                self.cog.welcome_config[guild_id_local]["verification_ids"] = ids
                save_welcome(self.cog.welcome_config)
                await modal_interaction.response.send_message(
                    "💾 Custom IDs de verificación/captcha actualizados.",
                    ephemeral=True
                )
                await self.cog.welcome_update_panel(modal_interaction, 1)

        if custom_id == "welcome_edit_message":
            return await interaction.response.send_modal(WelcomeMessageModal(self))

        if custom_id == "welcome_edit_image":
            return await interaction.response.send_modal(WelcomeImageModal(self))

        if custom_id == "welcome_edit_verification_ids":
            return await interaction.response.send_modal(VerificationIDsModal(self))

        # ============================
        # ACCIONES QUE SOLO ACTUALIZAN PANEL
        # ============================

        update_only = {
            "welcome_next_page", "welcome_prev_page",
            "welcome_toggle_enabled",
            "welcome_select_channel",
            "welcome_select_log",
            "welcome_select_give_role",
            "welcome_select_remove_role"
        }

        if custom_id in update_only:

            if not interaction.response.is_done():
                await interaction.response.defer()

            if custom_id == "welcome_next_page":
                page = min(3, page + 1)
                self.user_pages[user.id] = page

            elif custom_id == "welcome_prev_page":
                page = max(1, page - 1)
                self.user_pages[user.id] = page

            elif custom_id == "welcome_toggle_enabled":
                cfg["enabled"] = not cfg["enabled"]

            elif custom_id == "welcome_select_channel":
                values = interaction.data.get("values", [])
                if values and values[0] != "none":
                    cfg["welcome_channel"] = int(values[0])

            elif custom_id == "welcome_select_log":
                values = interaction.data.get("values", [])
                if values and values[0] != "none":
                    cfg["log_channel"] = int(values[0])

            elif custom_id == "welcome_select_give_role":
                values = interaction.data.get("values", [])
                if values and values[0] != "none":
                    cfg["verify_give_role"] = int(values[0])

            elif custom_id == "welcome_select_remove_role":
                values = interaction.data.get("values", [])
                if values and values[0] != "none":
                    cfg["verify_remove_role"] = int(values[0])

            save_welcome(self.welcome_config)
            await self.welcome_update_panel(interaction, page)
            return

        # ============================
        # TEST DE BIENVENIDA
        # ============================

        if custom_id == "welcome_test":
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

            await self.send_welcome_message(
                member=interaction.user,
                guild=interaction.guild,
                test=True
            )

            await interaction.followup.send(
                "🧪 Bienvenida de prueba enviada (si el canal está configurado y la bienvenida está activada).",
                ephemeral=True
            )
            return

    # ============================
    # ENVIAR BIENVENIDA
    # ============================

    async def send_welcome_message(self, member: discord.abc.User | discord.Member,
                                   guild: discord.Guild,
                                   test: bool = False):

        guild_id = str(guild.id)
        cfg = self.ensure_guild_config(guild_id)

        if not cfg["enabled"]:
            return

        channel_id = cfg.get("welcome_channel")
        if not channel_id:
            return

        channel = guild.get_channel(int(channel_id))
        if not channel:
            return

        msg_template = cfg.get(
            "welcome_message",
            "🎉 Bienvenido {user} a **{server}**! Ahora somos {membercount} miembros."
        )

        text = msg_template.replace("{user}", member.mention)
        text = text.replace("{server}", guild.name)
        text = text.replace("{membercount}", str(guild.member_count))

        if test:
            text = "🧪 **[PRUEBA]** " + text

        image_url = cfg.get("welcome_image")

        try:
            if image_url:
                embed = discord.Embed(
                    description=text,
                    color=discord.Color.green()
                )
                embed.set_image(url=image_url)
                await channel.send(embed=embed)
            else:
                await channel.send(text)
        except:
            pass

        await self.send_welcome_log(member, guild, test=test)

    # ============================
    # LOG DE BIENVENIDA
    # ============================

    async def send_welcome_log(self, member: discord.abc.User | discord.Member,
                               guild: discord.Guild,
                               test: bool = False):

        guild_id = str(guild.id)
        cfg = self.ensure_guild_config(guild_id)

        log_channel_id = cfg.get("log_channel")
        if not log_channel_id:
            return

        channel = guild.get_channel(int(log_channel_id))
        if not channel:
            return

        title = "✅ Nuevo usuario" if not test else "🧪 [PRUEBA] Log de bienvenida"
        embed = discord.Embed(
            title=title,
            color=discord.Color.blue()
        )

        embed.add_field(name="👤 Usuario", value=f"{member.mention}", inline=False)
        embed.add_field(name="🆔 ID", value=str(member.id), inline=False)
        embed.add_field(name="🏠 Servidor", value=guild.name, inline=False)
        embed.add_field(name="👥 Miembros totales", value=str(guild.member_count), inline=False)

        if isinstance(member, discord.Member):
            roles = [r.mention for r in member.roles if r.name != "@everyone"]
            if roles:
                embed.add_field(name="🎭 Roles actuales", value=", ".join(roles), inline=False)

        if getattr(member, "avatar", None):
            embed.set_thumbnail(url=member.avatar.url)

        try:
            await channel.send(embed=embed)
        except:
            pass

    # ============================
    # LOG DE VERIFICACIÓN
    # ============================

    async def send_verification_log(self, member: discord.Member,
                                    guild: discord.Guild,
                                    given_role: discord.Role | None,
                                    removed_role: discord.Role | None):

        guild_id = str(guild.id)
        cfg = self.ensure_guild_config(guild_id)

        log_channel_id = cfg.get("log_channel")
        if not log_channel_id:
            return

        channel = guild.get_channel(int(log_channel_id))
        if not channel:
            return

        embed = discord.Embed(
            title="✅ Nuevo usuario Verificado ✅",
            color=discord.Color.green()
        )

        embed.add_field(name="👤 Usuario", value=member.mention, inline=False)
        embed.add_field(name="🆔 ID", value=str(member.id), inline=False)

        if given_role:
            embed.add_field(name="🎭 Rol dado", value=given_role.mention, inline=False)
        else:
            embed.add_field(name="🎭 Rol dado", value="Ninguno / no configurado", inline=False)

        if removed_role:
            embed.add_field(name="❌ Rol quitado", value=removed_role.mention, inline=False)
        else:
            embed.add_field(name="❌ Rol quitado", value="Ninguno / no configurado", inline=False)

        embed.add_field(name="🏠 Servidor", value=guild.name, inline=False)

        if getattr(member, "avatar", None):
            embed.set_thumbnail(url=member.avatar.url)

        try:
            await channel.send(embed=embed)
        except:
            pass

    # ============================
    # EVENTO: on_member_join
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        await self.send_welcome_message(member, guild, test=False)


# ============================
# SETUP DEL COG
# ============================

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeChannelCog(bot))
