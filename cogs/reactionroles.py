import discord
from discord.ext import commands
from discord import app_commands
import json
import os

RR_FILE = "reaction_roles.json"


def load_rr():
    if not os.path.exists(RR_FILE):
        with open(RR_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}
    with open(RR_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}


def save_rr(data: dict):
    with open(RR_FILE, "w") as f:
        json.dump(data, f, indent=4)


class RRPanelView(discord.ui.View):
    def __init__(self, cog: "ReactionRoles", guild: discord.Guild):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild = guild
        self.guild_id = str(guild.id)

        self.cog.ensure_guild(self.guild_id)
        messages = self.cog.rr[self.guild_id]["messages"]

        options: list[discord.SelectOption] = []
        if messages:
            for mid, info in messages.items():
                ch_id = info.get("channel_id")
                roles_map = info.get("roles", {})
                label = f"ID {mid} | #{self.cog.channel_name(guild, ch_id)} | {len(roles_map)} emojis"
                options.append(discord.SelectOption(label=label[:100], value=mid))
        else:
            options.append(discord.SelectOption(label="Sin mensajes configurados", value="none", default=True))

        self.select = RRMessageSelect(self.cog, self.guild_id, options)
        self.add_item(self.select)

        self.add_item(RRRefreshButton(self.cog))
        self.add_item(RRCloseButton())


class RRMessageSelect(discord.ui.Select):
    def __init__(self, cog: "ReactionRoles", guild_id: str, options: list[discord.SelectOption]):
        super().__init__(
            placeholder="Selecciona un mensaje para ver sus roles",
            min_values=1,
            max_values=1,
            options=options
        )
        self.cog = cog
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        if value == "none":
            return await interaction.response.send_message("❌ No hay mensajes configurados.", ephemeral=True)

        data = self.cog.rr[self.guild_id]["messages"].get(value)
        if not data:
            return await interaction.response.send_message("❌ Ese mensaje ya no está configurado.", ephemeral=True)

        channel_id = data.get("channel_id")
        mode = data.get("mode", "toggle")
        roles_map = data.get("roles", {})

        lines = []
        guild = interaction.guild
        for emoji, rid in roles_map.items():
            role = guild.get_role(rid) if guild else None
            rname = role.name if role else f"Rol ID {rid}"
            lines.append(f"{emoji} → {rname}")

        embed = discord.Embed(
            title="📄 Detalles del mensaje de Reaction Roles",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Mensaje ID", value=f"`{value}`", inline=True)
        embed.add_field(name="Canal", value=f"<#{channel_id}>", inline=True)
        embed.add_field(name="Modo", value=f"`{mode}`", inline=True)
        embed.add_field(
            name="Roles configurados",
            value="\n".join(lines) if lines else "No hay roles configurados.",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class RRRefreshButton(discord.ui.Button):
    def __init__(self, cog: "ReactionRoles"):
        super().__init__(label="🔄 Actualizar", style=discord.ButtonStyle.primary)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return
        view = RRPanelView(self.cog, guild)
        embed = self.cog.build_main_embed(str(guild.id))
        await interaction.response.edit_message(embed=embed, view=view)


class RRCloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="❌ Cerrar panel", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="Panel cerrado.", embed=None, view=None)


class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rr: dict = load_rr()

    def ensure_guild(self, guild_id: str):
        if guild_id not in self.rr:
            self.rr[guild_id] = {"messages": {}, "enabled": True}
            save_rr(self.rr)

    def channel_name(self, guild: discord.Guild, channel_id: int | None) -> str:
        if not channel_id:
            return "desconocido"
        ch = guild.get_channel(channel_id)
        return ch.name if isinstance(ch, discord.TextChannel) else "desconocido"

    def build_main_embed(self, guild_id: str) -> discord.Embed:
        self.ensure_guild(guild_id)
        gdata = self.rr[guild_id]
        enabled = gdata.get("enabled", True)
        messages = gdata["messages"]

        embed = discord.Embed(
            title="🎛️ Reaction Roles — Panel Principal",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="Estado del sistema",
            value="🟢 Activado" if enabled else "🔴 Desactivado",
            inline=False
        )

        if not messages:
            embed.add_field(
                name="Mensajes configurados",
                value="No hay mensajes de reaction roles aún.",
                inline=False
            )
        else:
            lines = []
            for mid, info in messages.items():
                ch_id = info.get("channel_id")
                mode = info.get("mode", "toggle")
                roles_map = info.get("roles", {})
                lines.append(
                    f"• ID `{mid}` — Canal: <#{ch_id}> — Modo: `{mode}` — {len(roles_map)} emojis"
                )
            embed.add_field(
                name="Mensajes configurados",
                value="\n".join(lines),
                inline=False
            )

        embed.set_footer(text="Usa los comandos /rr_add, /rr_remove y /rr_list para gestionar los roles.")
        return embed

    # ---------- Comandos de configuración ----------

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="reactionroles", description="Abre el panel de Reaction Roles")
    async def reactionroles_cmd(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)

        guild_id = str(interaction.guild.id)
        self.ensure_guild(guild_id)

        embed = self.build_main_embed(guild_id)
        view = RRPanelView(self, interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="rr_toggle", description="Activa o desactiva el sistema de Reaction Roles")
    async def rr_toggle(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)

        guild_id = str(interaction.guild.id)
        self.ensure_guild(guild_id)
        current = self.rr[guild_id].get("enabled", True)
        self.rr[guild_id]["enabled"] = not current
        save_rr(self.rr)

        await interaction.response.send_message(
            f"✅ Sistema de Reaction Roles ahora está: **{'Activado' if not current else 'Desactivado'}**",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="rr_add", description="Añade un reaction role a un mensaje")
    @app_commands.describe(
        mensaje_id="ID del mensaje (copia el ID con modo desarrollador)",
        emoji="Emoji normal o personalizado",
        rol="Rol que se dará al reaccionar"
    )
    async def rr_add(self, interaction: discord.Interaction, mensaje_id: str, emoji: str, rol: discord.Role):
        if not interaction.guild or not interaction.channel:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)

        guild_id = str(interaction.guild.id)
        self.ensure_guild(guild_id)

        try:
            mid_int = int(mensaje_id)
        except ValueError:
            return await interaction.response.send_message("❌ ID de mensaje inválido.", ephemeral=True)

        try:
            msg = await interaction.channel.fetch_message(mid_int)
        except discord.NotFound:
            return await interaction.response.send_message("❌ No encontré ese mensaje en este canal.", ephemeral=True)

        try:
            await msg.add_reaction(emoji)
        except Exception:
            return await interaction.response.send_message("❌ No puedo usar ese emoji en ese mensaje.", ephemeral=True)

        gdata = self.rr[guild_id]
        messages = gdata["messages"]
        if mensaje_id not in messages:
            messages[mensaje_id] = {
                "channel_id": interaction.channel.id,
                "mode": "toggle",
                "roles": {}
            }

        messages[mensaje_id]["roles"][emoji] = rol.id
        save_rr(self.rr)

        await interaction.response.send_message(
            f"✅ Añadido reaction role:\n"
            f"• Mensaje: `{mensaje_id}`\n"
            f"• Emoji: {emoji}\n"
            f"• Rol: {rol.mention}",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="rr_remove", description="Elimina un reaction role de un mensaje")
    @app_commands.describe(
        mensaje_id="ID del mensaje",
        emoji="Emoji configurado a eliminar"
    )
    async def rr_remove(self, interaction: discord.Interaction, mensaje_id: str, emoji: str):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)

        guild_id = str(interaction.guild.id)
        self.ensure_guild(guild_id)

        gdata = self.rr[guild_id]
        messages = gdata["messages"]

        if mensaje_id not in messages:
            return await interaction.response.send_message("❌ Ese mensaje no tiene reaction roles.", ephemeral=True)

        roles_map = messages[mensaje_id].get("roles", {})
        if emoji not in roles_map:
            return await interaction.response.send_message("❌ Ese emoji no está configurado en ese mensaje.", ephemeral=True)

        del roles_map[emoji]
        if not roles_map:
            del messages[mensaje_id]

        save_rr(self.rr)

        await interaction.response.send_message(
            f"🗑️ Eliminado reaction role del mensaje `{mensaje_id}` con emoji {emoji}.",
            ephemeral=True
        )

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="rr_list", description="Lista los reaction roles configurados en el servidor")
    async def rr_list(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)

        guild_id = str(interaction.guild.id)
        self.ensure_guild(guild_id)

        messages = self.rr[guild_id]["messages"]
        if not messages:
            return await interaction.response.send_message("📭 No hay reaction roles configurados.", ephemeral=True)

        embed = discord.Embed(
            title="📋 Reaction Roles configurados",
            color=discord.Color.blurple()
        )

        for mid, info in messages.items():
            ch_id = info.get("channel_id")
            mode = info.get("mode", "toggle")
            roles_map = info.get("roles", {})
            lines = []
            for emoji, rid in roles_map.items():
                role = interaction.guild.get_role(rid)
                rname = role.mention if role else f"Rol ID {rid}"
                lines.append(f"{emoji} → {rname}")
            embed.add_field(
                name=f"Mensaje `{mid}` — Canal: <#{ch_id}> — Modo: {mode}",
                value="\n".join(lines) if lines else "Sin roles.",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    # ---------- Eventos de reacción ----------

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        guild_id = str(payload.guild_id)
        self.ensure_guild(guild_id)

        if not self.rr[guild_id].get("enabled", True):
            return

        msg_id = str(payload.message_id)
        gdata = self.rr[guild_id]
        messages = gdata["messages"]

        if msg_id not in messages:
            return

        msg_data = messages[msg_id]
        roles_map = msg_data.get("roles", {})
        emoji_str = str(payload.emoji)

        if emoji_str not in roles_map:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        role_id = roles_map[emoji_str]
        role = guild.get_role(role_id)
        if not role:
            return

        mode = msg_data.get("mode", "toggle")

        # Modo single: quitar otros roles del mismo mensaje
        if mode == "single":
            for em, rid in roles_map.items():
                if rid != role_id:
                    if rid in [r.id for r in member.roles]:
                        try:
                            r_obj = guild.get_role(rid)
                            if r_obj: await member.remove_roles(r_obj)
                        except: pass

        if role in member.roles:
            await member.remove_roles(role, reason="Reaction Role (Toggle)")
        else:
            await member.add_roles(role, reason="Reaction Role (Toggle/Single)")


    @app_commands.command(name="rr_remove", description="Elimina un reaction role de un mensaje")
    @app_commands.describe(
        mensaje_id="ID del mensaje",
        emoji="Emoji configurado a eliminar"
    )
    async def rr_remove(self, interaction: discord.Interaction, mensaje_id: str, emoji: str):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)

        guild_id = str(interaction.guild.id)
        self.ensure_guild(guild_id)

        gdata = self.rr[guild_id]
        messages = gdata["messages"]

        if mensaje_id not in messages:
            return await interaction.response.send_message("❌ Ese mensaje no tiene reaction roles.", ephemeral=True)

        roles_map = messages[mensaje_id].get("roles", {})
        if emoji not in roles_map:
            return await interaction.response.send_message("❌ Ese emoji no está configurado en ese mensaje.", ephemeral=True)

        del roles_map[emoji]
        if not roles_map:
            del messages[mensaje_id]

        save_rr(self.rr)

        await interaction.response.send_message(
            f"🗑️ Eliminado reaction role del mensaje `{mensaje_id}` con emoji {emoji}.",
            ephemeral=True
        )

    @app_commands.command(name="rr_list", description="Lista los reaction roles configurados en el servidor")
    async def rr_list(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)

        guild_id = str(interaction.guild.id)
        self.ensure_guild(guild_id)

        messages = self.rr[guild_id]["messages"]
        if not messages:
            return await interaction.response.send_message("📭 No hay reaction roles configurados.", ephemeral=True)

        embed = discord.Embed(
            title="📋 Reaction Roles configurados",
            color=discord.Color.blurple()
        )

        for mid, info in messages.items():
            ch_id = info.get("channel_id")
            mode = info.get("mode", "toggle")
            roles_map = info.get("roles", {})
            lines = []
            for emoji, rid in roles_map.items():
                role = interaction.guild.get_role(rid)
                rname = role.mention if role else f"Rol ID {rid}"
                lines.append(f"{emoji} → {rname}")
            embed.add_field(
                name=f"Mensaje `{mid}` — Canal: <#{ch_id}> — Modo: {mode}",
                value="\n".join(lines) if lines else "Sin roles.",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---------- Eventos de reacción ----------

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        guild_id = str(payload.guild_id)
        self.ensure_guild(guild_id)

        if not self.rr[guild_id].get("enabled", True):
            return

        msg_id = str(payload.message_id)
        gdata = self.rr[guild_id]
        messages = gdata["messages"]

        if msg_id not in messages:
            return

        msg_data = messages[msg_id]
        roles_map = msg_data.get("roles", {})
        emoji_str = str(payload.emoji)

        if emoji_str not in roles_map:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        role_id = roles_map[emoji_str]
        role = guild.get_role(role_id)
        if not role:
            return

        mode = msg_data.get("mode", "toggle")

        # Modo single: quitar otros roles del mismo mensaje
        if mode == "single":
            for em, rid in roles_map.items():
                if rid != role_id:
                    r = guild.get_role(rid)
                    if r and r in member.roles:
                        try:
                            await member.remove_roles(r, reason="Reaction Roles (single mode)")
                        except Exception:
                            pass

        if role not in member.roles:
            try:
                await member.add_roles(role, reason="Reaction Roles")
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        guild_id = str(payload.guild_id)
        self.ensure_guild(guild_id)

        if not self.rr[guild_id].get("enabled", True):
            return

        msg_id = str(payload.message_id)
        gdata = self.rr[guild_id]
        messages = gdata["messages"]

        if msg_id not in messages:
            return

        msg_data = messages[msg_id]
        roles_map = msg_data.get("roles", {})
        emoji_str = str(payload.emoji)

        if emoji_str not in roles_map:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        role_id = roles_map[emoji_str]
        role = guild.get_role(role_id)
        if not role:
            return

        mode = msg_data.get("mode", "toggle")

        # En modo single no quitamos el rol al quitar la reacción
        if mode == "single":
            return

        if role in member.roles:
            try:
                await member.remove_roles(role, reason="Reaction Roles (remove reaction)")
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
