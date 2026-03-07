import discord
from discord.ext import commands
from discord import app_commands
import json
import os

ANTIMENTION_FILE = "antimention.json"

# ============================
# JSON LOADER
# ============================

def load_antimention():
    if not os.path.exists(ANTIMENTION_FILE):
        with open(ANTIMENTION_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}

    with open(ANTIMENTION_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_antimention(data):
    with open(ANTIMENTION_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# COG ANTI-MENTION PRO
# ============================

class AntiMentionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_antimention()
        self.user_pages = {}

    # ============================
    # CONFIG POR SERVIDOR
    # ============================

    def ensure_guild_config(self, guild_id: str):
        if guild_id not in self.config:
            self.config[guild_id] = {
                "enabled": False,
                "action": "warn",
                "mute_time": 600,
                "progressive": False,
                "logs_channel": None,

                "everyone": {
                    "enabled": True,
                    "max_mentions": 1
                },

                "user_mentions": {
                    "enabled": True,
                    "max_mentions": 3,
                    "max_repeat": 2
                },

                "role_mentions": {
                    "enabled": True,
                    "max_mentions": 3,
                    "max_repeat": 2
                },

                "whitelist_users": [],
                "whitelist_roles": [],
                "whitelist_channels": [],

                "cooldown": 3
            }
            save_antimention(self.config)

        return self.config[guild_id]

    # ============================
    # EMBEDS POR PÁGINA
    # ============================

    def mention_embed_page(self, page: int):
        pages = {
            1: ("⚙️ Configuración General", "Opciones principales del Anti‑Mention."),
            2: ("📣 Control de @everyone", "Permisos y límites de @everyone/@here."),
            3: ("👤 Menciones a Usuarios", "Límites y repetición de menciones."),
            4: ("🛡️ Menciones a Roles", "Control de menciones a roles."),
            5: ("📝 Whitelist", "Usuarios, roles y canales permitidos."),
            6: ("🔧 Opciones Avanzadas", "Cooldown, logs y modo progresivo.")
        }

        title, desc = pages.get(page, ("Anti‑Mention", "Panel de configuración"))
        return discord.Embed(title=title, description=desc, color=discord.Color.blurple())

    # ============================
    # SELECT MENÚ PARA LOGS
    # ============================

    def select_logs_channel(self, guild, cfg):
        options = [
            discord.SelectOption(label=c.name, value=str(c.id), default=(cfg["logs_channel"] == c.id))
            for c in guild.text_channels
        ][:25]

        return discord.ui.Select(
            placeholder="Selecciona canal de logs",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="mention_select_logs_channel"
        )

    # ============================
    # SELECTS WHITELIST
    # ============================

    def select_whitelist_users(self, guild, cfg):
        options = [
            discord.SelectOption(label=m.name, value=str(m.id), default=(m.id in cfg["whitelist_users"]))
            for m in guild.members
        ][:25]

        return discord.ui.Select(
            placeholder="Usuarios permitidos",
            min_values=0,
            max_values=len(options) or 1,
            options=options or [discord.SelectOption(label="Sin usuarios", value="none")],
            custom_id="mention_select_whitelist_users"
        )

    def select_whitelist_roles(self, guild, cfg):
        options = [
            discord.SelectOption(label=r.name, value=str(r.id), default=(r.id in cfg["whitelist_roles"]))
            for r in guild.roles if r.name != "@everyone"
        ][:25]

        return discord.ui.Select(
            placeholder="Roles permitidos",
            min_values=0,
            max_values=len(options) or 1,
            options=options or [discord.SelectOption(label="Sin roles", value="none")],
            custom_id="mention_select_whitelist_roles"
        )

    def select_whitelist_channels(self, guild, cfg):
        options = [
            discord.SelectOption(label=c.name, value=str(c.id), default=(c.id in cfg["whitelist_channels"]))
            for c in guild.text_channels
        ][:25]

        return discord.ui.Select(
            placeholder="Canales permitidos",
            min_values=0,
            max_values=len(options) or 1,
            options=options or [discord.SelectOption(label="Sin canales", value="none")],
            custom_id="mention_select_whitelist_channels"
        )

    # ============================
    # BOTONES PRINCIPALES
    # ============================

    def main_buttons(self, cfg, page):
        btn_enable = discord.ui.Button(
            label="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado",
            style=discord.ButtonStyle.green if cfg["enabled"] else discord.ButtonStyle.red,
            custom_id="mention_toggle_enabled"
        )

        btn_save = discord.ui.Button(
            label="💾 Guardar",
            style=discord.ButtonStyle.blurple,
            custom_id="mention_save"
        )

        btn_test = None
        if page == 6:
            btn_test = discord.ui.Button(
                label="🧪 Test Anti‑Mention",
                style=discord.ButtonStyle.gray,
                custom_id="mention_test"
            )

        return btn_enable, btn_save, btn_test

    # ============================
    # BOTONES DE NAVEGACIÓN
    # ============================

    def nav_buttons(self, page):
        buttons = []

        if page > 1:
            buttons.append(discord.ui.Button(
                label="⬅ Anterior",
                style=discord.ButtonStyle.secondary,
                custom_id="mention_prev_page"
            ))

        if page < 6:
            buttons.append(discord.ui.Button(
                label="Siguiente ➡",
                style=discord.ButtonStyle.secondary,
                custom_id="mention_next_page"
            ))

        return buttons

    # ============================
    # PANEL PRINCIPAL
    # ============================

    async def build_panel(self, interaction: discord.Interaction, page: int, initial: bool = False):
        guild = interaction.guild
        guild_id = str(guild.id)
        cfg = self.ensure_guild_config(guild_id)

        self.user_pages[interaction.user.id] = page

        embed = self.mention_embed_page(page)
        view = discord.ui.View(timeout=300)

        # Botón cerrar panel
        view.add_item(discord.ui.Button(
            label="🔒 Cerrar panel",
            style=discord.ButtonStyle.red,
            custom_id="mention_close_panel"
        ))

        # ============================
        # PÁGINAS
        # ============================

        if page == 1:
            embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)
            embed.add_field(name="Acción", value=cfg["action"], inline=False)
            embed.add_field(name="Tiempo de mute", value=f"{cfg['mute_time']}s", inline=False)
            embed.add_field(name="Modo progresivo", value="Sí" if cfg["progressive"] else "No", inline=False)

            btn_enable, btn_save, _ = self.main_buttons(cfg, page)
            view.add_item(btn_enable)
            view.add_item(discord.ui.Button(label="Cambiar acción", style=discord.ButtonStyle.blurple, custom_id="mention_change_action"))
            view.add_item(discord.ui.Button(label="Cambiar tiempo mute", style=discord.ButtonStyle.blurple, custom_id="mention_change_mute"))
            view.add_item(discord.ui.Button(label="Modo progresivo", style=discord.ButtonStyle.gray, custom_id="mention_toggle_progressive"))
            view.add_item(btn_save)

        elif page == 2:
            roles_everyone = [r.name for r in guild.roles if r.permissions.mention_everyone]

            embed.add_field(
                name="Roles con permiso @everyone",
                value="\n".join([f"• {r}" for r in roles_everyone]) or "Ninguno",
                inline=False
            )

            embed.add_field(
                name="Límite de menciones @everyone",
                value=f"{cfg['everyone']['max_mentions']} (módulo {'activado' if cfg['everyone']['enabled'] else 'desactivado'})",
                inline=False
            )

            view.add_item(discord.ui.Button(
                label="Quitar permiso @everyone a roles no‑admin",
                style=discord.ButtonStyle.red,
                custom_id="mention_remove_everyone_perm"
            ))

            view.add_item(discord.ui.Button(
                label="Cambiar límite @everyone",
                style=discord.ButtonStyle.blurple,
                custom_id="mention_change_everyone_limit"
            ))

            view.add_item(discord.ui.Button(
                label="Activar/Desactivar módulo @everyone",
                style=discord.ButtonStyle.gray,
                custom_id="mention_toggle_everyone"
            ))

        elif page == 3:
            embed.add_field(
                name="Menciones a usuarios",
                value=(
                    f"Máx. menciones: **{cfg['user_mentions']['max_mentions']}**\n"
                    f"Máx. repetición: **{cfg['user_mentions']['max_repeat']}**\n"
                    f"Módulo: **{'activado' if cfg['user_mentions']['enabled'] else 'desactivado'}**"
                ),
                inline=False
            )

            view.add_item(discord.ui.Button(
                label="Cambiar máx. menciones usuario",
                style=discord.ButtonStyle.blurple,
                custom_id="mention_change_user_max"
            ))
            view.add_item(discord.ui.Button(
                label="Cambiar máx. repetición usuario",
                style=discord.ButtonStyle.blurple,
                custom_id="mention_change_user_repeat"
            ))
            view.add_item(discord.ui.Button(
                label="Activar/Desactivar módulo usuarios",
                style=discord.ButtonStyle.gray,
                custom_id="mention_toggle_user_module"
            ))

        elif page == 4:
            embed.add_field(
                name="Menciones a roles",
                value=(
                    f"Máx. menciones: **{cfg['role_mentions']['max_mentions']}**\n"
                    f"Máx. repetición: **{cfg['role_mentions']['max_repeat']}**\n"
                    f"Módulo: **{'activado' if cfg['role_mentions']['enabled'] else 'desactivado'}**"
                ),
                inline=False
            )

            view.add_item(discord.ui.Button(
                label="Cambiar máx. menciones rol",
                style=discord.ButtonStyle.blurple,
                custom_id="mention_change_role_max"
            ))
            view.add_item(discord.ui.Button(
                label="Cambiar máx. repetición rol",
                style=discord.ButtonStyle.blurple,
                custom_id="mention_change_role_repeat"
            ))
            view.add_item(discord.ui.Button(
                label="Activar/Desactivar módulo roles",
                style=discord.ButtonStyle.gray,
                custom_id="mention_toggle_role_module"
            ))

        elif page == 5:
            embed.add_field(
                name="Whitelist",
                value="Configura usuarios, roles y canales que no serán afectados por el Anti‑Mention.",
                inline=False
            )

            view.add_item(self.select_whitelist_users(guild, cfg))
            view.add_item(self.select_whitelist_roles(guild, cfg))
            view.add_item(self.select_whitelist_channels(guild, cfg))

        elif page == 6:
            embed.add_field(
                name="Cooldown",
                value=f"{cfg['cooldown']} segundos entre acciones por usuario.",
                inline=False
            )
            embed.add_field(
                name="Logs",
                value=f"<#{cfg['logs_channel']}>" if cfg["logs_channel"] else "No configurado",
                inline=False
            )
            embed.add_field(
                name="Modo progresivo",
                value="Activado" if cfg["progressive"] else "Desactivado",
                inline=False
            )

            btn_enable, btn_save, btn_test = self.main_buttons(cfg, page)
            view.add_item(btn_enable)
            view.add_item(discord.ui.Button(
                label="Cambiar cooldown",
                style=discord.ButtonStyle.blurple,
                custom_id="mention_change_cooldown"
            ))
            view.add_item(self.select_logs_channel(guild, cfg))
            view.add_item(discord.ui.Button(
                label="Modo progresivo",
                style=discord.ButtonStyle.gray,
                custom_id="mention_toggle_progressive"
            ))
            view.add_item(btn_save)
            if btn_test:
                view.add_item(btn_test)

        # Navegación
        for btn in self.nav_buttons(page):
            view.add_item(btn)

        if initial:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.edit_original_response(embed=embed, view=view)

    # ============================
    # COMANDO PRINCIPAL
    # ============================

    @app_commands.command(name="antimention", description="Abre el panel de configuración del Anti‑Mention")
    async def antimention_cmd(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        self.ensure_guild_config(guild_id)
        self.user_pages[interaction.user.id] = 1
        await self.build_panel(interaction, page=1, initial=True)


# ============================
    # MODAL GENÉRICO
    # ============================

    class MentionModal(discord.ui.Modal):
        def __init__(self, title, label, callback_fn):
            super().__init__(title=title)
            self.callback_fn = callback_fn
            self.input = discord.ui.TextInput(label=label, required=True)
            self.add_item(self.input)

        async def on_submit(self, interaction: discord.Interaction):
            await self.callback_fn(interaction, self.input.value)

    # ============================
    # MANEJADOR DE INTERACCIONES
    # ============================

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        if not interaction.data:
            return

        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.startswith("mention_"):
            return

        guild = interaction.guild
        guild_id = str(guild.id)
        cfg = self.ensure_guild_config(guild_id)

        user_id = interaction.user.id
        page = self.user_pages.get(user_id, 1)

        # ============================
        # NAVEGACIÓN
        # ============================

        if custom_id == "mention_next_page":
            page = min(6, page + 1)
            self.user_pages[user_id] = page
            return await self.build_panel(interaction, page)

        if custom_id == "mention_prev_page":
            page = max(1, page - 1)
            self.user_pages[user_id] = page
            return await self.build_panel(interaction, page)

        # ============================
        # CERRAR PANEL
        # ============================

        if custom_id == "mention_close_panel":
            return await interaction.response.edit_message(
                content="🔒 Panel cerrado.",
                embed=None,
                view=None
            )

        # ============================
        # TOGGLES
        # ============================

        if custom_id == "mention_toggle_enabled":
            cfg["enabled"] = not cfg["enabled"]
            save_antimention(self.config)
            return await self.build_panel(interaction, page)

        if custom_id == "mention_toggle_progressive":
            cfg["progressive"] = not cfg["progressive"]
            save_antimention(self.config)
            return await self.build_panel(interaction, page)

        if custom_id == "mention_toggle_everyone":
            cfg["everyone"]["enabled"] = not cfg["everyone"]["enabled"]
            save_antimention(self.config)
            return await self.build_panel(interaction, page)

        if custom_id == "mention_toggle_user_module":
            cfg["user_mentions"]["enabled"] = not cfg["user_mentions"]["enabled"]
            save_antimention(self.config)
            return await self.build_panel(interaction, page)

        if custom_id == "mention_toggle_role_module":
            cfg["role_mentions"]["enabled"] = not cfg["role_mentions"]["enabled"]
            save_antimention(self.config)
            return await self.build_panel(interaction, page)

        # ============================
        # SELECTS
        # ============================

        if custom_id == "mention_select_logs_channel":
            channel_id = int(interaction.data["values"][0])
            cfg["logs_channel"] = channel_id
            save_antimention(self.config)
            return await interaction.response.send_message(
                f"📘 Canal de logs configurado en <#{channel_id}>",
                ephemeral=True
            )

        if custom_id == "mention_select_whitelist_users":
            cfg["whitelist_users"] = [int(v) for v in interaction.data["values"]]
            save_antimention(self.config)
            return await self.build_panel(interaction, page)

        if custom_id == "mention_select_whitelist_roles":
            cfg["whitelist_roles"] = [int(v) for v in interaction.data["values"]]
            save_antimention(self.config)
            return await self.build_panel(interaction, page)

        if custom_id == "mention_select_whitelist_channels":
            cfg["whitelist_channels"] = [int(v) for v in interaction.data["values"]]
            save_antimention(self.config)
            return await self.build_panel(interaction, page)

        # ============================
        # MODALES (CAMBIOS NUMÉRICOS)
        # ============================

        # Cambiar acción
        if custom_id == "mention_change_action":
            async def cb(i, value):
                cfg["action"] = value.lower()
                save_antimention(self.config)
                await i.response.send_message("💾 Acción actualizada.", ephemeral=True)
                await self.build_panel(i, page)

            return await interaction.response.send_modal(
                self.MentionModal("Cambiar acción", "warn / mute / kick / ban", cb)
            )

        # Cambiar tiempo mute
        if custom_id == "mention_change_mute":
            async def cb(i, value):
                cfg["mute_time"] = max(1, int(value))
                save_antimention(self.config)
                await i.response.send_message("💾 Tiempo mute actualizado.", ephemeral=True)
                await self.build_panel(i, page)

            return await interaction.response.send_modal(
                self.MentionModal("Cambiar tiempo mute", "Segundos:", cb)
            )

        # Cambiar límite @everyone
        if custom_id == "mention_change_everyone_limit":
            async def cb(i, value):
                cfg["everyone"]["max_mentions"] = max(1, int(value))
                save_antimention(self.config)
                await i.response.send_message("💾 Límite @everyone actualizado.", ephemeral=True)
                await self.build_panel(i, page)

            return await interaction.response.send_modal(
                self.MentionModal("Límite @everyone", "Máx. menciones:", cb)
            )

        # Cambiar límites usuario
        if custom_id == "mention_change_user_max":
            async def cb(i, value):
                cfg["user_mentions"]["max_mentions"] = max(1, int(value))
                save_antimention(self.config)
                await i.response.send_message("💾 Máx. menciones usuario actualizado.", ephemeral=True)
                await self.build_panel(i, page)

            return await interaction.response.send_modal(
                self.MentionModal("Máx. menciones usuario", "Cantidad:", cb)
            )

        if custom_id == "mention_change_user_repeat":
            async def cb(i, value):
                cfg["user_mentions"]["max_repeat"] = max(1, int(value))
                save_antimention(self.config)
                await i.response.send_message("💾 Repetición usuario actualizada.", ephemeral=True)
                await self.build_panel(i, page)

            return await interaction.response.send_modal(
                self.MentionModal("Máx. repetición usuario", "Cantidad:", cb)
            )

        # Cambiar límites rol
        if custom_id == "mention_change_role_max":
            async def cb(i, value):
                cfg["role_mentions"]["max_mentions"] = max(1, int(value))
                save_antimention(self.config)
                await i.response.send_message("💾 Máx. menciones rol actualizado.", ephemeral=True)
                await self.build_panel(i, page)

            return await interaction.response.send_modal(
                self.MentionModal("Máx. menciones rol", "Cantidad:", cb)
            )

        if custom_id == "mention_change_role_repeat":
            async def cb(i, value):
                cfg["role_mentions"]["max_repeat"] = max(1, int(value))
                save_antimention(self.config)
                await i.response.send_message("💾 Repetición rol actualizada.", ephemeral=True)
                await self.build_panel(i, page)

            return await interaction.response.send_modal(
                self.MentionModal("Máx. repetición rol", "Cantidad:", cb)
            )

        # Cambiar cooldown
        if custom_id == "mention_change_cooldown":
            async def cb(i, value):
                cfg["cooldown"] = max(0, int(value))
                save_antimention(self.config)
                await i.response.send_message("💾 Cooldown actualizado.", ephemeral=True)
                await self.build_panel(i, page)

            return await interaction.response.send_modal(
                self.MentionModal("Cambiar cooldown", "Segundos:", cb)
            )

        # ============================
        # QUITAR PERMISO @EVERYONE
        # ============================

        if custom_id == "mention_remove_everyone_perm":
            removed = []
            for role in guild.roles:
                if role.permissions.mention_everyone and not role.permissions.administrator:
                    perms = role.permissions
                    perms.update(mention_everyone=False)
                    await role.edit(permissions=perms)
                    removed.append(role.name)

            msg = "🔧 Permiso removido de:\n" + "\n".join(f"• {r}" for r in removed) if removed else "No había roles que modificar."

            return await interaction.response.send_message(msg, ephemeral=True)

        # ============================
        # GUARDAR
        # ============================

        if custom_id == "mention_save":
            save_antimention(self.config)
            return await interaction.response.send_message("💾 Configuración guardada.", ephemeral=True)

        # ============================
        # TEST
        # ============================

        if custom_id == "mention_test":
            return await interaction.response.send_message("🧪 Test Anti‑Mention ejecutado.", ephemeral=True)



# ============================
    # DETECCIÓN DE MENCIONES
    # ============================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild_id = str(message.guild.id)
        cfg = self.ensure_guild_config(guild_id)

        if not cfg["enabled"]:
            return

        user = message.author
        content = message.content

        # Whitelist
        if user.id in cfg["whitelist_users"]:
            return
        if any(r.id in cfg["whitelist_roles"] for r in user.roles):
            return
        if message.channel.id in cfg["whitelist_channels"]:
            return

        # Cooldown
        if not hasattr(self, "cooldowns"):
            self.cooldowns = {}

        now = discord.utils.utcnow().timestamp()
        if user.id in self.cooldowns and now - self.cooldowns[user.id] < cfg["cooldown"]:
            return
        self.cooldowns[user.id] = now

        # ============================
        # CONTROL @EVERYONE
        # ============================

        if cfg["everyone"]["enabled"]:
            if "@everyone" in content or "@here" in content:
                if not message.author.guild_permissions.mention_everyone:
                    return await self.apply_action(message, "everyone")

                count = content.count("@everyone") + content.count("@here")
                if count > cfg["everyone"]["max_mentions"]:
                    return await self.apply_action(message, "everyone_limit")

        # ============================
        # MENCIONES A USUARIOS
        # ============================

        if cfg["user_mentions"]["enabled"]:
            if len(message.mentions) > cfg["user_mentions"]["max_mentions"]:
                return await self.apply_action(message, "user_mentions")

            # Repetición
            ids = [m.id for m in message.mentions]
            if len(ids) >= cfg["user_mentions"]["max_repeat"]:
                if len(set(ids[-cfg["user_mentions"]["max_repeat"]:])) == 1:
                    return await self.apply_action(message, "user_repeat")

        # ============================
        # MENCIONES A ROLES
        # ============================

        if cfg["role_mentions"]["enabled"]:
            if len(message.role_mentions) > cfg["role_mentions"]["max_mentions"]:
                return await self.apply_action(message, "role_mentions")

            ids = [r.id for r in message.role_mentions]
            if len(ids) >= cfg["role_mentions"]["max_repeat"]:
                if len(set(ids[-cfg["role_mentions"]["max_repeat"]:])) == 1:
                    return await self.apply_action(message, "role_repeat")

    # ============================
    # APLICAR ACCIÓN
    # ============================

    async def apply_action(self, message: discord.Message, reason: str):
        guild_id = str(message.guild.id)
        cfg = self.ensure_guild_config(guild_id)
        action = cfg["action"]
        user = message.author

        # Borrar mensaje
        try:
            await message.delete()
        except:
            pass

        # Logs
        if cfg["logs_channel"]:
            ch = message.guild.get_channel(cfg["logs_channel"])
            if ch:
                await ch.send(
                    f"🔔 **Anti‑Mention**\n"
                    f"Usuario: {user.mention}\n"
                    f"Razón: `{reason}`\n"
                    f"Mensaje: `{message.content}`"
                )

        # Warn
        if action == "warn":
            return await message.channel.send(
                f"⚠️ {user.mention}, evita abusar de las menciones.",
                delete_after=5
            )

        # Kick
        if action == "kick":
            try:
                await user.kick(reason=f"Anti‑Mention ({reason})")
            except:
                pass
            return

        # Ban
        if action == "ban":
            try:
                await user.ban(reason=f"Anti‑Mention ({reason})")
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
                    discord.utils.utcnow() + discord.timedelta(seconds=duration),
                    reason=f"Anti‑Mention ({reason})"
                )
            except:
                pass

            return await message.channel.send(
                f"⛔ {user.mention} ha sido muteado por `{duration}` segundos.",
                delete_after=5
            )

# ============================
# SETUP DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(AntiMentionCog(bot))
