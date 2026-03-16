import discord
from discord.ext import commands
from discord import app_commands

class SecurityScanView(discord.ui.View):
    def __init__(self, cog, interaction, analysis_data):
        super().__init__(timeout=120)
        self.cog = cog
        self.interaction = interaction
        self.analysis_data = analysis_data

    @discord.ui.button(label="🔄 Actualizar análisis", style=discord.ButtonStyle.blurple)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message(
                "❌ Solo quien ejecutó el comando puede usar estos botones.",
                ephemeral=True
            )

        embed, analysis_data = await self.cog.build_security_embed(interaction.guild)
        self.analysis_data = analysis_data

        await interaction.response.edit_message(embed=embed, view=self)


class SecurityScan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.CRITICAL = {
            "administrator": "Administrador total",
            "manage_guild": "Administrar servidor",
            "manage_roles": "Administrar roles",
            "manage_channels": "Administrar canales",
            "manage_webhooks": "Administrar webhooks",
            "ban_members": "Banear miembros",
            "kick_members": "Expulsar miembros",
            "manage_permissions": "Administrar permisos"
        }

        self.DANGEROUS = {
            "mention_everyone": "Mencionar @everyone",
            "manage_messages": "Administrar mensajes",
            "mute_members": "Mutear miembros",
            "deafen_members": "Ensordecer miembros",
            "move_members": "Mover miembros"
        }

        self.MODERATE = {
            "create_instant_invite": "Crear invitaciones",
            "attach_files": "Enviar archivos",
            "embed_links": "Insertar enlaces"
        }

    # ============================
    # ANALIZADORES
    # ============================

    def analyze_role(self, role: discord.Role, bot_top_role: discord.Role, member_count: int):
        perms = role.permissions

        critical = []
        dangerous = []
        moderate = []

        for perm, desc in self.CRITICAL.items():
            if getattr(perms, perm, False):
                critical.append(desc)

        for perm, desc in self.DANGEROUS.items():
            if getattr(perms, perm, False):
                dangerous.append(desc)

        for perm, desc in self.MODERATE.items():
            if getattr(perms, perm, False):
                moderate.append(desc)

        score = len(critical) * 30 + len(dangerous) * 15 + len(moderate) * 5

        if role.position > bot_top_role.position:
            score += 40

        if member_count > 50 and (critical or dangerous):
            score += 20
        elif member_count > 10 and (critical or dangerous):
            score += 10

        if score >= 90:
            risk = "🟥 Muy peligroso"
        elif score >= 60:
            risk = "🟧 Peligroso"
        elif score >= 25:
            risk = "🟨 Moderado"
        else:
            risk = "🟩 Seguro"

        return {
            "critical": critical,
            "dangerous": dangerous,
            "moderate": moderate,
            "score": score,
            "risk": risk,
            "members": member_count
        }

    def analyze_member_risk(self, member: discord.Member, role_analysis):
        score = 0
        for role, data in role_analysis:
            if role in member.roles:
                score += data["score"]
        return score

    def analyze_channel(self, channel: discord.TextChannel):
        risky = []
        overwrites = channel.overwrites

        for target, ow in overwrites.items():
            if isinstance(target, discord.Role):
                if ow.mention_everyone is True:
                    risky.append(f"{channel.mention}: {target.name} puede mencionar @everyone")
                if ow.send_messages is True and ow.attach_files is True:
                    risky.append(f"{channel.mention}: {target.name} puede enviar archivos libremente")

        return risky

    # ============================
    # EMBED PRINCIPAL
    # ============================

    async def build_security_embed(self, guild: discord.Guild):
        bot_member = guild.get_member(self.bot.user.id)
        bot_top_role = bot_member.top_role if bot_member else guild.roles[-1]

        roles = [r for r in guild.roles if not r.is_default()][::-1]

        role_analysis = []
        total_score = 0
        critical_roles = []
        dangerous_roles = []

        for role in roles:
            member_count = sum(1 for m in guild.members if role in m.roles)
            data = self.analyze_role(role, bot_top_role, member_count)
            role_analysis.append((role, data))
            total_score += data["score"]

            if data["score"] >= 90:
                critical_roles.append(role)
            elif data["score"] >= 60:
                dangerous_roles.append(role)

        bots_dangerous = []
        users_dangerous = []

        for member in guild.members:
            m_score = self.analyze_member_risk(member, role_analysis)
            if member.bot and m_score >= 60:
                bots_dangerous.append((member, m_score))
            elif not member.bot and m_score >= 80:
                users_dangerous.append((member, m_score))

        risky_channels = []
        for ch in guild.text_channels:
            risky_channels.extend(self.analyze_channel(ch))

        avg_score = total_score / max(len(role_analysis), 1)
        if avg_score >= 80:
            server_risk = "🟥 Riesgo global: Muy alto"
        elif avg_score >= 50:
            server_risk = "🟧 Riesgo global: Alto"
        elif avg_score >= 25:
            server_risk = "🟨 Riesgo global: Medio"
        else:
            server_risk = "🟩 Riesgo global: Bajo"

        embed = discord.Embed(
            title="🛡️ SecurityScan — Análisis del servidor",
            description="Análisis completo de roles, permisos, bots, usuarios y canales.",
            color=discord.Color.red() if "🟥" in server_risk else discord.Color.orange()
        )

        embed.add_field(
            name="📊 Resumen",
            value=(
                f"{server_risk}\n"
                f"• Roles analizados: `{len(role_analysis)}`\n"
                f"• Roles muy peligrosos: `{len(critical_roles)}`\n"
                f"• Roles peligrosos: `{len(dangerous_roles)}`\n"
                f"• Bots peligrosos: `{len(bots_dangerous)}`\n"
                f"• Usuarios con riesgo alto: `{len(users_dangerous)}`"
            ),
            inline=False
        )

        return embed, role_analysis

    # ============================
    # COMANDO PRINCIPAL (ARREGLADO)
    # ============================

    @app_commands.command(
        name="securityscan",
        description="Analiza la seguridad del servidor actual."
    )
    async def securityscan(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Solo administradores pueden usar este comando.",
                ephemeral=True
            )

        # Respuesta inmediata para evitar interacción fallida
        await interaction.response.send_message(
            "🔍 Analizando la seguridad del servidor...",
            ephemeral=True
        )

        embed, analysis_data = await self.build_security_embed(interaction.guild)

        view = SecurityScanView(self, interaction, analysis_data)

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=view
        )


async def setup(bot):
    await bot.add_cog(SecurityScan(bot)) 
