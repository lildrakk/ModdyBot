import discord
from discord.ext import commands
from discord import app_commands
import json, os

CONFIG_FILE = "antibots.json"

# ============================================================
# CONFIG
# ============================================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}

    with open(CONFIG_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================================================
# COG ANTI‑BOTS PRO
# ============================================================

class AntiBots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()

    # --------------------------------------------------------
    # CONFIG POR SERVIDOR
    # --------------------------------------------------------

    def ensure_guild(self, guild_id: int):
        gid = str(guild_id)

        if gid not in self.config:
            self.config[gid] = {
                "enabled": False,
                "log_channel": None
            }
            save_config(self.config)

        return self.config[gid]

    # --------------------------------------------------------
    # COMANDO /antibots
    # --------------------------------------------------------

    @app_commands.command(
        name="antibots",
        description="Activa o desactiva el sistema Anti‑Bots."
    )
    @app_commands.describe(
        estado="Activar o desactivar el Anti‑Bots",
        log_channel="Canal donde se enviarán los logs"
    )
    @app_commands.choices(
        estado=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ]
    )
    async def antibots_cmd(
        self,
        interaction: discord.Interaction,
        estado: str = None,
        log_channel: discord.TextChannel = None
    ):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        if estado:
            cfg["enabled"] = (estado == "activar")

        if log_channel:
            cfg["log_channel"] = log_channel.id

        save_config(self.config)

        embed = discord.Embed(
            title="🤖 Configuración Anti‑Bots actualizada",
            color=discord.Color.yellow()
        )

        embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)
        embed.add_field(name="Log channel", value=f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "No configurado", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --------------------------------------------------------
    # COMANDO /antibots_config
    # --------------------------------------------------------

    @app_commands.command(
        name="antibots_config",
        description="Muestra la configuración actual del Anti‑Bots."
    )
    async def antibots_config(self, interaction: discord.Interaction):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        embed = discord.Embed(
            title="🤖 Configuración actual del Anti‑Bots",
            color=discord.Color.blue()
        )

        embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)
        embed.add_field(name="Log channel", value=f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "No configurado", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --------------------------------------------------------
    # DETECCIÓN DE BOTS NUEVOS
    # --------------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        cfg = self.ensure_guild(guild.id)

        if not cfg["enabled"]:
            return

        # Solo actuar si es un bot
        if not member.bot:
            return

        # Detectar si NO está verificado
        if not member.public_flags.verified_bot:
            await self.handle_unverified_bot(member, cfg)

    # --------------------------------------------------------
    # MANEJO DE BOT NO VERIFICADO
    # --------------------------------------------------------

    async def handle_unverified_bot(self, bot_member: discord.Member, cfg):
        guild = bot_member.guild

        # Buscar quién invitó al bot
        inviter = None
        try:
            logs = await guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add).flatten()
            for entry in logs:
                if entry.target.id == bot_member.id:
                    inviter = entry.user
                    break
        except:
            inviter = None

        # Intentar expulsar al bot
        bot_kicked = False
        try:
            await bot_member.kick(reason="Bot no verificado (Anti‑Bots)")
            bot_kicked = True
        except:
            bot_kicked = False

        # Intentar expulsar al usuario que lo metió
        inviter_kicked = False
        if inviter:
            try:
                await guild.kick(inviter, reason="Meter bots no verificados (Anti‑Bots)")
                inviter_kicked = True
            except:
                inviter_kicked = False

        # Enviar logs
        log_channel_id = cfg["log_channel"]
        if log_channel_id:
            channel = guild.get_channel(log_channel_id)
            if channel:
                if bot_kicked:
                    desc = f"🤖 Bot no verificado expulsado: {bot_member.mention}"
                else:
                    desc = f"⚠️ No pude expulsar al bot no verificado: {bot_member.mention}"

                if inviter:
                    if inviter_kicked:
                        desc += f"\n👤 Usuario expulsado: {inviter.mention}"
                    else:
                        desc += f"\n⚠️ No pude expulsar al usuario que lo metió: {inviter.mention}"

                embed = discord.Embed(
                    title="🚨 Anti‑Bots",
                    description=desc,
                    color=discord.Color.red() if bot_kicked else discord.Color.yellow()
                )
                await channel.send(embed=embed)


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiBots(bot))
