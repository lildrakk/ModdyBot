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
    # ROLE ADD
    # ============================

    @app_commands.command(name="roleadd", description="Añade un rol a un usuario")
    @app_commands.describe(usuario="Usuario al que dar el rol", rol="Rol que quieres añadir")
    async def roleadd(self, interaction: discord.Interaction, usuario: discord.Member, rol: discord.Role):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

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
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

        try:
            await usuario.remove_roles(rol)
            await interaction.response.send_message(
                f"❌ Rol **{rol.name}** removido de {usuario.mention}.",
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
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

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
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

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