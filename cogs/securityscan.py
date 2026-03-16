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
            conclusion = "➡️ Este rol puede destruir el servidor si cae en malas manos."
        elif score >= 60:
            risk = "🟧 Peligroso"
            conclusion = "➡️ Este rol tiene permisos muy sensibles, úsalo con cuidado."
        elif score >= 25:
            risk = "🟨 Moderado"
            conclusion = "➡️ Este rol puede causar molestias, pero no es crítico."
        else:
            risk = "🟩 Seguro"
            conclusion = "➡️ Este rol no representa un riesgo importante."

        return {
            "critical": critical,
            "dangerous": dangerous,
            "moderate": moderate,
            "score": score,
            "risk": risk,
            "conclusion": conclusion,
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
    # EMBED COMPLETO
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

        # ============================
        # RIESGO GLOBAL
        # ============================

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
            title="🛡️ SecurityScan — Análisis completo del servidor",
            description="Análisis avanzado de roles, permisos, bots, usuarios y canales.",
            color=discord.Color.red() if "🟥" in server_risk else discord.Color.orange()
        )

        embed.add_field(
            name="📊 Resumen del servidor",
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

        # ============================
        # ROLES PELIGROSOS
        # ============================

        if critical_roles:
            embed.add_field(
                name="🟥 Roles MUY peligrosos",
                value="\n".join(f"• {r.mention} (`{r.name}`)" for r in critical_roles)[:1024],
                inline=False
            )
        else:
            embed.add_field(
                name="🟥 Roles MUY peligrosos",
                value="✅ No se han detectado roles extremadamente peligrosos.",
                inline=False
            )

        if dangerous_roles:
            embed.add_field(
                name="🟧 Roles peligrosos",
                value="\n".join(f"• {r.mention} (`{r.name}`)" for r in dangerous_roles)[:1024],
                inline=False
            )
        else:
            embed.add_field(
                name="🟧 Roles peligrosos",
                value="✅ No se han detectado roles peligrosos significativos.",
                inline=False
            )

        # ============================
        # BOTS PELIGROSOS
        # ============================

        if bots_dangerous:
            text = ""
            for m, s in sorted(bots_dangerous, key=lambda x: x[1], reverse=True)[:10]:
                text += f"• {m.mention} — riesgo `{s}`\n"
            embed.add_field(
                name="🤖 Bots con permisos peligrosos",
                value=text[:1024],
                inline=False
            )
        else:
            embed.add_field(
                name="🤖 Bots con permisos peligrosos",
                value="✅ No se han detectado bots con riesgo alto.",
                inline=False
            )

        # ============================
        # USUARIOS PELIGROSOS
        # ============================

        if users_dangerous:
            text = ""
            for m, s in sorted(users_dangerous, key=lambda x: x[1], reverse=True)[:10]:
                text += f"• {m.mention} — riesgo `{s}`\n"
            embed.add_field(
                name="👤 Usuarios con roles peligrosos",
                value=text[:1024],
                inline=False
            )
        else:
            embed.add_field(
                name="👤 Usuarios con roles peligrosos",
                value="✅ No se han detectado usuarios con riesgo alto.",
                inline=False
            )

        # ============================
        # CANALES PELIGROSOS
        # ============================

        if risky_channels:
            embed.add_field(
                name="📢 Canales con configuración peligrosa",
                value="\n".join(f"• {t}" for t in risky_channels)[:1024],
                inline=False
            )
        else:
            embed.add_field(
                name="📢 Canales con configuración peligrosa",
                value="✅ No se han detectado canales con permisos críticos mal configurados.",
                inline=False
            )

        # ============================
        # WEBHOOKS
        # ============================

        webhooks_info = []
        try:
            for ch in guild.text_channels:
                hooks = await ch.webhooks()
                for wh in hooks:
                    webhooks_info.append(f"{wh.name} en {ch.mention}")
        except:
            pass

        if webhooks_info:
            embed.add_field(
                name="🪝 Webhooks detectados",
                value="\n".join(f"• {w}" for w in webhooks_info)[:1024],
                inline=False
            )
        else:
            embed.add_field(
                name="🪝 Webhooks detectados",
                value="ℹ️ No se han encontrado webhooks o no se pudieron listar.",
                inline=False
            )

        # ============================
        # INVITACIONES
        # ============================

        invites_info = []
        try:
            invites = await guild.invites()
            for inv in invites:
                if inv.max_age == 0 and inv.max_uses == 0:
                    invites_info.append(f"Invitación permanente: {inv.code} (creada por {inv.inviter})")
        except:
            pass

        if invites_info:
            embed.add_field(
                name="🔗 Invitaciones permanentes",
                value="\n".join(f"• {i}" for i in invites_info)[:1024],
                inline=False
            )
        else:
            embed.add_field(
                name="🔗 Invitaciones permanentes",
                value="✅ No se han detectado invitaciones permanentes sin límite.",
                inline=False
            )

        # ============================
        # RECOMENDACIONES
        # ============================

        recomendaciones = []

        if critical_roles:
            recomendaciones.append("• Revisa los roles **muy peligrosos** y limita quién los tiene.")
        if dangerous_roles:
            recomendaciones.append("• Baja de posición o quita permisos a los **roles peligrosos**.")
        if bots_dangerous:
            recomendaciones.append("• Revisa los bots con permisos elevados.")
        if risky_channels:
            recomendaciones.append("• Ajusta permisos en los canales marcados como peligrosos.")
        if invites_info:
            recomendaciones.append("• Elimina invitaciones permanentes que no sean necesarias.")

        if not recomendaciones:
            recomendaciones.append("• La configuración actual parece razonablemente segura.")

        embed.add_field(
            name="🛠️ Recomendaciones",
            value="\n".join(recomendaciones)[:1024],
            inline=False
        )

        embed.set_footer(text=f"Análisis completado en {guild.name}.")

        return embed, role_analysis

    # ============================
    # COMANDO PRINCIPAL
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
