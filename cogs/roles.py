import discord
import asyncio
import json
import os
import sys
from discord.ext import commands
from discord import app_commands


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================
    # FUNCIONES DE PERMISOS
    # ============================

    def check_user_permissions(self, interaction):
        if not interaction.user.guild_permissions.manage_roles:
            return "❌ No tienes permisos para gestionar roles."
        return None

    def check_bot_permissions(self, interaction):
        if not interaction.guild.me.guild_permissions.manage_roles:
            return "❌ No tengo permisos para gestionar roles."
        return None

    def check_role_hierarchy(self, interaction, usuario, rol):
        # El usuario no puede modificar roles superiores a los suyos
        if rol.position >= interaction.user.top_role.position and interaction.user != interaction.guild.owner:
            return "❌ No puedes gestionar un rol igual o superior al tuyo."

        # El bot no puede modificar roles superiores a los suyos
        if rol.position >= interaction.guild.me.top_role.position:
            return "❌ Mi rol está por debajo del rol que intentas gestionar."

        # No permitir dar o quitar roles superiores al usuario objetivo
        if usuario.top_role.position > interaction.user.top_role.position and interaction.user != interaction.guild.owner:
            return "❌ No puedes modificar roles de alguien con un rol superior al tuyo."

        return None

    # ============================
    # ROLE ADD
    # ============================

    @app_commands.command(name="roleadd", description="Añade un rol a un usuario")
    @app_commands.describe(usuario="Usuario al que dar el rol", rol="Rol que quieres añadir")
    async def roleadd(self, interaction: discord.Interaction, usuario: discord.Member, rol: discord.Role):

        # Permisos del usuario
        error = self.check_user_permissions(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        # Permisos del bot
        error = self.check_bot_permissions(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        # Jerarquía
        error = self.check_role_hierarchy(interaction, usuario, rol)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        try:
            await usuario.add_roles(rol)
            await interaction.response.send_message(
                f"✅ Rol **{rol.name}** añadido a {usuario.mention}.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ No tengo permisos suficientes para añadir ese rol.",
                ephemeral=True
            )

    # ============================
    # ROLE REMOVE
    # ============================

    @app_commands.command(name="roleremove", description="Quita un rol a un usuario")
    @app_commands.describe(usuario="Usuario al que quitar el rol", rol="Rol que quieres remover")
    async def roleremove(self, interaction: discord.Interaction, usuario: discord.Member, rol: discord.Role):

        # Permisos del usuario
        error = self.check_user_permissions(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        # Permisos del bot
        error = self.check_bot_permissions(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        # Jerarquía
        error = self.check_role_hierarchy(interaction, usuario, rol)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        try:
            await usuario.remove_roles(rol)
            await interaction.response.send_message(
                f"🗑️ Rol **{rol.name}** removido de {usuario.mention}.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ No tengo permisos suficientes para quitar ese rol.",
                ephemeral=True
            )

    # ============================
    # TEMP ROLES PRO (PERSISTENTES)
    # ============================

    def load_temproles(self):
        try:
            with open("temproles.json", "r") as f:
                return json.load(f)
        except:
            return {}

    def save_temproles(self, data):
        with open("temproles.json", "w") as f:
            json.dump(data, f, indent=4)

    # ----------------------------
    # TEMP ROLE ADD
    # ----------------------------

    @app_commands.command(name="temproleadd", description="Añade un rol temporal a un usuario (persistente)")
    @app_commands.describe(usuario="Usuario", rol="Rol a añadir", minutos="Duración en minutos")
    async def temproleadd(self, interaction: discord.Interaction, usuario: discord.Member, rol: discord.Role, minutos: int):

        # Permisos del usuario
        error = self.check_user_permissions(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        # Permisos del bot
        error = self.check_bot_permissions(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        # Jerarquía
        error = self.check_role_hierarchy(interaction, usuario, rol)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        # Añadir rol
        try:
            await usuario.add_roles(rol)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ No tengo permisos para añadir ese rol.", ephemeral=True)

        # Guardar en JSON
        data = self.load_temproles()
        gid = str(interaction.guild.id)
        uid = str(usuario.id)

        if gid not in data:
            data[gid] = {}

        data[gid][uid] = {
            "rol": rol.id,
            "expira": (discord.utils.utcnow().timestamp() + minutos * 60)
        }

        self.save_temproles(data)

        await interaction.response.send_message(
            f"⏳ Rol **{rol.name}** añadido a {usuario.mention} por **{minutos} minutos**.",
            ephemeral=True
        )

    # ----------------------------
    # TEMP ROLE REMOVE MANUAL
    # ----------------------------

    @app_commands.command(name="temproleremove", description="Quita un rol temporal antes de que expire")
    @app_commands.describe(usuario="Usuario", rol="Rol a quitar")
    async def temproleremove(self, interaction: discord.Interaction, usuario: discord.Member, rol: discord.Role):

        # Permisos del usuario
        error = self.check_user_permissions(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        # Permisos del bot
        error = self.check_bot_permissions(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        # Jerarquía
        error = self.check_role_hierarchy(interaction, usuario, rol)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        try:
            await usuario.remove_roles(rol)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ No tengo permisos para quitar ese rol.", ephemeral=True)

        # Borrar del JSON
        data = self.load_temproles()
        gid = str(interaction.guild.id)
        uid = str(usuario.id)

        if gid in data and uid in data[gid]:
            del data[gid][uid]
            self.save_temproles(data)

        await interaction.response.send_message(
            f"🗑️ Rol **{rol.name}** removido manualmente de {usuario.mention}.",
            ephemeral=True
        )

    # ----------------------------
    # BACKGROUND TASK
    # ----------------------------

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.loop.create_task(self.temp_role_checker())

    async def temp_role_checker(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            data = self.load_temproles()
            cambios = False

            for gid in list(data.keys()):
                guild = self.bot.get_guild(int(gid))
                if not guild:
                    continue

                for uid in list(data[gid].keys()):
                    info = data[gid][uid]
                    expira = info["expira"]
                    rol_id = info["rol"]

                    if discord.utils.utcnow().timestamp() >= expira:
                        miembro = guild.get_member(int(uid))
                        rol = guild.get_role(rol_id)

                        if miembro and rol:
                            try:
                                await miembro.remove_roles(rol)
                            except:
                                pass

                        del data[gid][uid]
                        cambios = True

            if cambios:
                self.save_temproles(data)

            await asyncio.sleep(30)


async def setup(bot):
    await bot.add_cog(Roles(bot))
