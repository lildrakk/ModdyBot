import discord
from discord.ext import commands
from discord import app_commands
import platform
import datetime


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================
    # BOTINFO
    # ============================

    @app_commands.command(name="botinfo", description="Muestra información detallada del bot.")
    async def botinfo(self, interaction: discord.Interaction):

        uptime = datetime.datetime.utcnow() - self.bot.launch_time

        embed = discord.Embed(
            title="🤖 Información del Bot",
            color=discord.Color.blue()
        )

        embed.add_field(name="🆔 Nombre", value=self.bot.user.name, inline=True)
        embed.add_field(name="🏷️ ID", value=self.bot.user.id, inline=True)
        embed.add_field(name="📅 Creado el", value=self.bot.user.created_at.strftime("%d/%m/%Y"), inline=True)

        embed.add_field(name="📡 Servidores", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="👥 Usuarios totales", value=sum(g.member_count for g in self.bot.guilds), inline=True)
        embed.add_field(name="📚 Comandos", value=len(self.bot.tree.get_commands()), inline=True)

        embed.add_field(name="⚙️ Python", value=platform.python_version(), inline=True)
        embed.add_field(name="🧩 discord.py", value=discord.__version__, inline=True)

        embed.add_field(name="🕒 Uptime", value=str(uptime).split('.')[0], inline=True)
        embed.add_field(name="🌐 Latencia", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="👤 Desarrollador", value="lil_drakko", inline=True)

        embed.set_thumbnail(url=self.bot.user.avatar)
        embed.set_footer(text="Información del bot")

        await interaction.response.send_message(embed=embed)

    # ============================
    # SERVERINFO
    # ============================

    @app_commands.command(name="serverinfo", description="Muestra información detallada del servidor.")
    async def serverinfo(self, interaction: discord.Interaction):

        guild = interaction.guild

        embed = discord.Embed(
            title=f"📊 Información del Servidor: {guild.name}",
            color=discord.Color.green()
        )

        embed.add_field(name="🆔 ID", value=guild.id, inline=True)
        embed.add_field(name="👑 Dueño", value=guild.owner.mention, inline=True)
        embed.add_field(name="📅 Creado el", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)

        embed.add_field(name="👥 Miembros", value=guild.member_count, inline=True)
        embed.add_field(name="🤖 Bots", value=sum(1 for m in guild.members if m.bot), inline=True)
        embed.add_field(name="🧑‍🤝‍🧑 Humanos", value=sum(1 for m in guild.members if not m.bot), inline=True)

        embed.add_field(name="📁 Canales totales", value=len(guild.channels), inline=True)
        embed.add_field(name="💬 Texto", value=len(guild.text_channels), inline=True)
        embed.add_field(name="🔊 Voz", value=len(guild.voice_channels), inline=True)

        embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="🖼️ Emojis", value=len(guild.emojis), inline=True)
        
        embed.add_field(name="📌 Boosts", value=guild.premium_subscription_count, inline=True)
        embed.add_field(name="💎 Nivel Boost", value=guild.premium_tier, inline=True)

        embed.set_thumbnail(url=guild.icon)
        embed.set_footer(text="Información del servidor")

        await interaction.response.send_message(embed=embed)

    # ============================
    # USERINFO
    # ============================

    @app_commands.command(name="userinfo", description="Muestra información detallada de un usuario.")
    async def userinfo(self, interaction: discord.Interaction, usuario: discord.Member = None):

        usuario = usuario or interaction.user

        roles = [r.mention for r in usuario.roles if r != interaction.guild.default_role]
        roles = ", ".join(roles) if roles else "Sin roles"

        embed = discord.Embed(
            title=f"👤 Información de {usuario}",
            color=usuario.color
        )

        embed.add_field(name="🆔 ID", value=usuario.id, inline=True)
        embed.add_field(name="📅 Cuenta creada", value=usuario.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="📥 Entró al servidor", value=usuario.joined_at.strftime("%d/%m/%Y"), inline=True)

        embed.add_field(name="🎭 Roles", value=roles, inline=False)
        embed.add_field(name="💼 Es bot?", value="Sí" if usuario.bot else "No", inline=True)
        embed.add_field(name="📌 Nick", value=usuario.nick or "Ninguno", inline=True)

        embed.add_field(name="📊 Color", value=str(usuario.color), inline=True)
        embed.add_field(name="📈 Rol más alto", value=usuario.top_role.mention, inline=True)
        embed.add_field(name="📶 Estado", value=str(usuario.status).title(), inline=True)

        embed.set_thumbnail(url=usuario.avatar)
        embed.set_footer(text="Información del usuario")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    bot.launch_time = datetime.datetime.utcnow()
    await bot.add_cog(Info(bot))