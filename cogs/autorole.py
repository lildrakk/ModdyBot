import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio


AUTOROLE_FILE = "autorole.json"


# ============================
# JSON LOADER
# ============================

def load_autorole():
    if not os.path.exists(AUTOROLE_FILE):
        with open(AUTOROLE_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}

    with open(AUTOROLE_FILE, "r") as f:
        return json.load(f)


def save_autorole(data):
    with open(AUTOROLE_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# COG AUTOROLE
# ============================

class AutoroleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.autorole = load_autorole()


    # ============================
    # /autorole on
    # ============================

    @app_commands.command(
        name="autorole_on",
        description="Activa el sistema de autorole en este servidor"
    )
    async def autorole_on(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "❌ No tienes permisos para usar este comando.",
                ephemeral=True
            )

        guild_id = str(interaction.guild.id)

        if guild_id not in self.autorole:
            self.autorole[guild_id] = {"enabled": True, "roles": []}
        else:
            self.autorole[guild_id]["enabled"] = True

        save_autorole(self.autorole)

        await interaction.response.send_message(
            "✅ Autorole **activado** en este servidor.",
            ephemeral=True
        )


    # ============================
    # /autorole off
    # ============================

    @app_commands.command(
        name="autorole_off",
        description="Desactiva el sistema de autorole en este servidor"
    )
    async def autorole_off(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "❌ No tienes permisos.",
                ephemeral=True
            )

        guild_id = str(interaction.guild.id)

        if guild_id not in self.autorole:
            self.autorole[guild_id] = {"enabled": False, "roles": []}
        else:
            self.autorole[guild_id]["enabled"] = False

        save_autorole(self.autorole)

        await interaction.response.send_message(
            "🛑 Autorole **desactivado**.",
            ephemeral=True
        )


    # ============================
    # /autorole add
    # ============================

    @app_commands.command(
        name="autorole_add",
        description="Añade un rol al sistema de autorole"
    )
    @app_commands.describe(rol="Selecciona el rol que se asignará automáticamente")
    async def autorole_add(self, interaction: discord.Interaction, rol: discord.Role):

        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "❌ No tienes permisos.",
                ephemeral=True
            )

        guild_id = str(interaction.guild.id)

        if guild_id not in self.autorole:
            self.autorole[guild_id] = {"enabled": True, "roles": []}

        if str(rol.id) in self.autorole[guild_id]["roles"]:
            return await interaction.response.send_message(
                "⚠️ Ese rol ya está en la lista.",
                ephemeral=True
            )

        # Verificar jerarquía
        if rol >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                "❌ No puedo asignar ese rol porque está por encima de mi rol.",
                ephemeral=True
            )

        self.autorole[guild_id]["roles"].append(str(rol.id))
        save_autorole(self.autorole)

        await interaction.response.send_message(
            f"✅ Rol **{rol.name}** añadido al autorole.",
            ephemeral=True
        )


    # ============================
    # /autorole remove
    # ============================

    @app_commands.command(
        name="autorole_remove",
        description="Elimina un rol del autorole"
    )
    @app_commands.describe(rol="Rol que quieres eliminar del autorole")
    async def autorole_remove(self, interaction: discord.Interaction, rol: discord.Role):

        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "❌ No tienes permisos.",
                ephemeral=True
            )

        guild_id = str(interaction.guild.id)

        if guild_id not in self.autorole or str(rol.id) not in self.autorole[guild_id]["roles"]:
            return await interaction.response.send_message(
                "⚠️ Ese rol no está en el autorole.",
                ephemeral=True
            )

        self.autorole[guild_id]["roles"].remove(str(rol.id))
        save_autorole(self.autorole)

        await interaction.response.send_message(
            f"🗑️ Rol **{rol.name}** eliminado del autorole.",
            ephemeral=True
        )


    # ============================
    # /autorole list
    # ============================

    @app_commands.command(
        name="autorole_list",
        description="Muestra los roles configurados en el autorole"
    )
    async def autorole_list(self, interaction: discord.Interaction):

        guild_id = str(interaction.guild.id)

        if guild_id not in self.autorole or not self.autorole[guild_id]["roles"]:
            return await interaction.response.send_message(
                "📭 No hay roles configurados.",
                ephemeral=True
            )

        roles = [
            interaction.guild.get_role(int(r)).mention
            for r in self.autorole[guild_id]["roles"]
            if interaction.guild.get_role(int(r))
        ]

        lista = "\n".join(roles)

        await interaction.response.send_message(
            f"📌 **Roles configurados:**\n{lista}",
            ephemeral=True
        )


    # ============================
    # EVENTO: on_member_join
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        guild_id = str(member.guild.id)

        if guild_id not in self.autorole:
            return

        config = self.autorole[guild_id]

        if not config.get("enabled", False):
            return

        roles_ids = config.get("roles", [])
        if not roles_ids:
            return

        await asyncio.sleep(3)  # Delay estilo Carl-bot

        roles_to_add = [
            member.guild.get_role(int(r))
            for r in roles_ids
            if member.guild.get_role(int(r))
        ]

        try:
            await member.add_roles(*roles_to_add, reason="Autorole automático")
        except:
            pass


# ============================
# SETUP DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(AutoroleCog(bot))
