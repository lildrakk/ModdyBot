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
# COG ANTI-MENTION
# ============================

class AntiMentionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_antimention()


    # ============================
    # /antimention
    # ============================

    @app_commands.command(
        name="antimention",
        description="Activa o desactiva el sistema anti-mentions"
    )
    @app_commands.describe(estado="on/off")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def antimention_cmd(self, interaction: discord.Interaction, estado: str):

        guild_id = str(interaction.guild.id)

        if guild_id not in self.config:
            self.config[guild_id] = {"enabled": False}

        if estado.lower() == "on":
            self.config[guild_id]["enabled"] = True
            save_antimention(self.config)
            return await interaction.response.send_message(
                "📣 Anti‑mention **activado** en este servidor.",
                ephemeral=True
            )

        elif estado.lower() == "off":
            self.config[guild_id]["enabled"] = False
            save_antimention(self.config)
            return await interaction.response.send_message(
                "📣 Anti‑mention **desactivado**.",
                ephemeral=True
            )

        else:
            return await interaction.response.send_message(
                "❌ Usa: `on` o `off`.",
                ephemeral=True
            )


    # ============================
    # EVENTO: DETECCIÓN DE MENCIONES
    # ============================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if not message.guild:
            return
        if message.author.bot:
            return

        guild_id = str(message.guild.id)

        # Anti-mention desactivado
        if guild_id not in self.config or not self.config[guild_id]["enabled"]:
            return

        # No hay menciones
        if not message.mentions and not message.role_mentions:
            return

        # ============================
        # DETECTAR SPAM DE MENCIONES
        # ============================

        # Contar menciones a cada usuario
        user_counts = {}
        for user in message.mentions:
            user_counts[user.id] = user_counts.get(user.id, 0) + 1

        # Contar menciones a cada rol
        role_counts = {}
        for role in message.role_mentions:
            role_counts[role.id] = role_counts.get(role.id, 0) + 1

        # Si un usuario o rol fue mencionado 3+ veces → borrar
        for uid, count in user_counts.items():
            if count >= 3:
                await message.delete()
                return await message.channel.send(
                    f"{message.author.mention} 🚫 No puedes mencionar **3 veces** a la misma persona.",
                    delete_after=5
                )

        for rid, count in role_counts.items():
            if count >= 3:
                await message.delete()
                return await message.channel.send(
                    f"{message.author.mention} 🚫 No puedes mencionar **3 veces** al mismo rol.",
                    delete_after=5
                )


# ============================
# SETUP DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(AntiMentionCog(bot))
