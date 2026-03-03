import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

# ============================
# CONFIG
# ============================

GLOBAL_OWNER_ID = 1394342273919225959

# ============================
# JSON HELPERS
# ============================

def load_json(path):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({}, f, indent=4)
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

blacklist_servers = load_json("blacklist_servers.json")
blacklist_global = load_json("blacklist_global.json")

# ============================
# SISTEMA DE ESPERA DE PRUEBAS
# ============================

pending_proofs = {}

# ============================
# MODAL PARA AÑADIR A GLOBAL
# ============================

class GlobalAddModal(discord.ui.Modal, title="➕ Añadir a Blacklist Global"):
    usuario = discord.ui.TextInput(
        label="Usuario o ID",
        placeholder="Ej: @Juan / 123456789012345678",
        required=True
    )
    reason = discord.ui.TextInput(
        label="Motivo",
        placeholder="Razón de la sanción",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message(
                "❌ No puedes usar este modal.",
                ephemeral=True
            )

        raw_user = self.usuario.value.strip()
        reason = self.reason.value.strip()

        # Convertir mención a ID
        if raw_user.startswith("<@") and raw_user.endswith(">"):
            raw_user = raw_user.replace("<@", "").replace(">", "").replace("!", "")

        try:
            target_id = int(raw_user)
        except:
            return await interaction.response.send_message(
                "❌ Debes introducir un usuario válido o un ID.",
                ephemeral=True
            )

        pending_proofs[interaction.user.id] = {
            "target_id": str(target_id),
            "reason": reason,
            "staff": interaction.user.id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        await interaction.response.send_message(
            "📎 **Ahora adjunta las pruebas (opcional).**\n"
            "Envía imágenes, vídeos o archivos **en tu siguiente mensaje**.\n\n"
            "Si no envías nada en 30 segundos, se guardará sin pruebas.",
            ephemeral=True
        )

# ============================
# COG PRINCIPAL
# ============================

class Blacklist(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================
    # COMANDO GLOBAL BLACKLIST
    # ============================

    @app_commands.command(
        name="global_blacklist",
        description="Añade un usuario a la blacklist GLOBAL (modal + pruebas opcionales)"
    )
    async def global_blacklist_cmd(self, interaction: discord.Interaction):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message(
                "❌ Solo el dueño del bot puede usar este comando.",
                ephemeral=True
            )
        await interaction.response.send_modal(GlobalAddModal())

    # ============================
    # CAPTURA DE PRUEBAS
    # ============================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        staff_id = message.author.id

        if staff_id not in pending_proofs:
            return

        entry = pending_proofs[staff_id]
        target_id = entry["target_id"]
        reason = entry["reason"]
        staff = entry["staff"]
        timestamp = entry["timestamp"]

        proofs = [a.url for a in message.attachments]

        blacklist_global[target_id] = {
            "razon": reason,
            "pruebas": proofs,
            "staff": staff,
            "fecha_ban": timestamp
        }
        save_json("blacklist_global.json", blacklist_global)

        del pending_proofs[staff_id]

        # DM estilo XN Protect
        try:
            user_obj = await self.bot.fetch_user(int(target_id))
            embed = discord.Embed(
                title="🚫 Has sido baneado globalmente (ModdyBot)",
                description=(
                    f"Has sido añadido a la **Blacklist Global de ModdyBot**.\n\n"
                    f"**Razón:** {reason}\n"
                    f"**Fecha del ban:** {timestamp}\n\n"
                    f"**Pruebas:**\n"
                    + ("\n".join(proofs) if proofs else "No se adjuntaron pruebas.") +
                    "\n\nSi quieres apelar tu sanción, escribe por DM a **lil_drakko**."
                ),
                color=discord.Color.red()
            )
            if proofs:
                embed.set_image(url=proofs[0])
            await user_obj.send(embed=embed)
        except:
            pass

        # Ban global inmediato
        for guild in self.bot.guilds:
            member = guild.get_member(int(target_id))
            if member:
                try:
                    await member.ban(reason="Blacklist global")
                except:
                    pass

        await message.channel.send(
            f"🌐 Usuario `{target_id}` añadido a la blacklist global.\n"
            f"Pruebas guardadas: **{len(proofs)}**",
            delete_after=10
        )


# ============================
    # AUTO-BAN GLOBAL (cuando entra un usuario baneado globalmente)
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        uid = str(member.id)

        if uid not in blacklist_global:
            return

        data = blacklist_global[uid]
        razon = data.get("razon", "No especificada")
        pruebas = data.get("pruebas", [])
        fecha_ban = data.get("fecha_ban", "Desconocida")

        # DM estilo XN Protect
        try:
            embed = discord.Embed(
                title="🚫 Acceso denegado (ModdyBot)",
                description=(
                    "Has intentado entrar a un servidor donde está ModdyBot, "
                    "pero estás **baneado globalmente**.\n\n"
                    f"**Razón:** {razon}\n"
                    f"**Fecha del ban:** {fecha_ban}\n\n"
                    f"**Pruebas:**\n"
                    + ("\n".join(pruebas) if pruebas else "No se adjuntaron pruebas.") +
                    "\n\nSi quieres apelar tu sanción, escribe por DM a **lil_drakko**."
                ),
                color=discord.Color.red()
            )
            if pruebas:
                embed.set_image(url=pruebas[0])

            await member.send(embed=embed)
        except:
            pass

        # Ban automático
        try:
            await member.ban(reason="Blacklist global")
        except:
            pass

    # ============================
    # GLOBAL UNBLACKLIST
    # ============================

    @app_commands.command(
        name="global_unblacklist",
        description="Quita un usuario de la blacklist GLOBAL"
    )
    async def global_unblacklist_cmd(self, interaction: discord.Interaction, usuario: str):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message(
                "❌ Solo el dueño del bot puede usar este comando.",
                ephemeral=True
            )

        # Convertir mención a ID
        if usuario.startswith("<@") and usuario.endswith(">"):
            usuario = usuario.replace("<@", "").replace(">", "").replace("!", "")

        try:
            uid = str(int(usuario))
        except:
            return await interaction.response.send_message(
                "❌ Debes introducir un usuario válido o un ID.",
                ephemeral=True
            )

        if uid not in blacklist_global:
            return await interaction.response.send_message(
                "ℹ️ Ese usuario no está en la blacklist global.",
                ephemeral=True
            )

        # Datos del ban
        data = blacklist_global[uid]
        razon = data.get("razon", "No especificada")
        pruebas = data.get("pruebas", [])
        fecha_ban = data.get("fecha_ban", "Desconocida")

        # Fecha del desban
        fecha_desban = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Eliminar del JSON
        del blacklist_global[uid]
        save_json("blacklist_global.json", blacklist_global)

        # Desban global
        unbanned_count = 0
        for guild in self.bot.guilds:
            try:
                await guild.unban(discord.Object(id=int(uid)))
                unbanned_count += 1
            except:
                pass

        # Embed para DM y para ti (idéntico)
        embed = discord.Embed(
            title="🔓 Usuario Desbaneado Globalmente (ModdyBot)",
            description=(
                f"**ID:** `{uid}`\n\n"
                f"**Razón original del ban:** {razon}\n"
                f"**Fecha del ban:** {fecha_ban}\n"
                f"**Fecha del desban:** {fecha_desban}\n\n"
                f"**Pruebas:**\n"
                + ("\n".join(pruebas) if pruebas else "No se adjuntaron pruebas.") +
                "\n\nSi quieres apelar tu sanción, escribe por DM a **lil_drakko**."
            ),
            color=discord.Color.green()
        )

        if pruebas:
            embed.set_image(url=pruebas[0])

        # DM al usuario
        try:
            user_obj = await self.bot.fetch_user(int(uid))
            await user_obj.send(embed=embed)
        except:
            pass

        # Mensaje ephemeral para ti
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # ============================
    # COMANDO DE PRUEBA — GLOBAL BLACKLIST
    # ============================

    @app_commands.command(
        name="global_blacklist_prueba",
        description="Simula un ban global SIN banear a nadie (solo para el dueño)"
    )
    async def global_blacklist_prueba(self, interaction: discord.Interaction):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message(
                "❌ Solo el dueño del bot puede usar este comando.",
                ephemeral=True
            )

        user = interaction.user
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

        # DM simulado
        try:
            embed_dm = discord.Embed(
                title="🚫 Has sido baneado globalmente (SIMULACIÓN)",
                description=(
                    f"Esto es una **prueba** del mensaje que recibiría un usuario.\n\n"
                    f"**Razón:** Prueba de sistema\n"
                    f"**Fecha del ban:** {fecha}\n\n"
                    f"**Pruebas:**\nNo se adjuntaron pruebas.\n\n"
                    "Si quieres apelar tu sanción, escribe por DM a **lil_drakko**."
                ),
                color=discord.Color.red()
            )
            await user.send(embed=embed_dm)
        except:
            pass

        # Logs simulados
        embed_logs = discord.Embed(
            title="🚨 Usuario Baneado Globalmente (SIMULACIÓN)",
            description=(
                f"**Usuario:** {user} (`{user.id}`)\n"
                f"**Razón:** Prueba de sistema\n"
                f"**Fecha:** {fecha}\n\n"
                "Este mensaje es solo una simulación."
            ),
            color=discord.Color.orange()
        )

        await interaction.response.send_message(
            "🧪 **Simulación enviada.**\nRevisa tu DM y el embed generado.",
            ephemeral=True
        )

        await interaction.channel.send(embed=embed_logs)

    # ============================
    # COMANDO DE PRUEBA — GLOBAL UNBLACKLIST
    # ============================

    @app_commands.command(
        name="global_unblacklist_prueba",
        description="Simula un unban global SIN modificar nada (solo para el dueño)"
    )
    async def global_unblacklist_prueba(self, interaction: discord.Interaction):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message(
                "❌ Solo el dueño del bot puede usar este comando.",
                ephemeral=True
            )

        user = interaction.user
        fecha_ban = "2026-01-01 12:00"
        fecha_desban = datetime.now().strftime("%Y-%m-%d %H:%M")

        embed = discord.Embed(
            title="🔓 Usuario Desbaneado Globalmente (SIMULACIÓN)",
            description=(
                f"**ID:** `{user.id}`\n\n"
                f"**Razón original del ban:** Prueba de sistema\n"
                f"**Fecha del ban:** {fecha_ban}\n"
                f"**Fecha del desban:** {fecha_desban}\n\n"
                "No se adjuntaron pruebas.\n\n"
                "Si quieres apelar tu sanción, escribe por DM a **lil_drakko**."
            ),
            color=discord.Color.green()
        )

        # DM simulado
        try:
            await user.send(embed=embed)
        except:
            pass

        # Ephemeral para ti
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
    )


    # ============================
    # GLOBAL BLACKLIST LIST
    # ============================

    @app_commands.command(
        name="global_blacklistlist",
        description="Muestra la lista completa de usuarios en la blacklist global"
    )
    async def global_blacklistlist_cmd(self, interaction: discord.Interaction):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message(
                "❌ Solo el dueño del bot puede usar este comando.",
                ephemeral=True
            )

        if not blacklist_global:
            return await interaction.response.send_message(
                "📭 La blacklist global está vacía.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🌐 Lista de Blacklist Global (ModdyBot)",
            description="Usuarios actualmente baneados globalmente:",
            color=discord.Color.blurple()
        )

        for uid, data in blacklist_global.items():
            razon = data.get("razon", "No especificada")
            fecha = data.get("fecha_ban", "Desconocida")
            staff = data.get("staff", "Desconocido")
            pruebas = data.get("pruebas", [])

            texto = (
                f"**Razón:** {razon}\n"
                f"**Fecha del ban:** {fecha}\n"
                f"**Staff:** <@{staff}>\n"
                f"**Pruebas:** "
                + (f"{len(pruebas)} archivo(s)" if pruebas else "No adjuntadas")
            )

            embed.add_field(
                name=f"ID: `{uid}`",
                value=texto,
                inline=False
            )

        embed.set_footer(text="Solo el dueño del bot puede ver esta información.")

        await interaction.response.send_message(embed=embed, ephemeral=True)




# ============================
    # GLOBAL INSPECT
    # ============================

    @app_commands.command(
        name="global_inspect",
        description="Inspecciona un usuario de la blacklist global"
    )
    async def global_inspect_cmd(self, interaction: discord.Interaction, usuario: str):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message(
                "❌ Solo el dueño del bot puede usar este comando.",
                ephemeral=True
            )

        # Convertir mención a ID
        if usuario.startswith("<@") and usuario.endswith(">"):
            usuario = usuario.replace("<@", "").replace(">", "").replace("!", "")

        try:
            uid = str(int(usuario))
        except:
            return await interaction.response.send_message(
                "❌ Debes introducir un usuario válido o un ID.",
                ephemeral=True
            )

        if uid not in blacklist_global:
            return await interaction.response.send_message(
                "ℹ️ Ese usuario no está en la blacklist global.",
                ephemeral=True
            )

        data = blacklist_global[uid]

        razon = data.get("razon", "No especificada")
        pruebas = data.get("pruebas", [])
        staff = data.get("staff", "Desconocido")
        fecha_ban = data.get("fecha_ban", "Desconocida")

        embed = discord.Embed(
            title=f"🔍 Inspección de usuario {uid}",
            color=discord.Color.orange()
        )

        embed.add_field(name="Motivo", value=razon, inline=False)
        embed.add_field(name="Staff", value=f"<@{staff}>", inline=False)
        embed.add_field(name="Fecha del ban", value=fecha_ban, inline=False)

        if pruebas:
            embed.add_field(
                name="Pruebas",
                value="\n".join(f"[Archivo]({url})" for url in pruebas),
                inline=False
            )
            embed.set_image(url=pruebas[0])
        else:
            embed.add_field(name="Pruebas", value="No se adjuntaron pruebas.", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ============================
    # BLACKLIST POR SERVIDOR (TU SISTEMA ORIGINAL)
    # ============================

    @app_commands.command(
        name="blacklist",
        description="Añade un usuario a la blacklist del servidor"
    )
    @app_commands.describe(
        usuario="Usuario a añadir",
        accion="kick / mute / ban / block",
        minutos="Solo para mute (0 = permanente)",
        razon="Razón"
    )
    async def blacklist_cmd(
        self,
        interaction: discord.Interaction,
        usuario: discord.User,
        accion: str,
        minutos: int = 10,
        razon: str = "No especificada"
    ):
        user = interaction.user

        if not (user.guild_permissions.administrator or user.guild_permissions.manage_guild):
            return await interaction.response.send_message(
                "❌ No tienes permisos.",
                ephemeral=True
            )

        accion = accion.lower()
        if accion not in ["kick", "mute", "ban", "block"]:
            return await interaction.response.send_message(
                "❌ Acciones válidas: kick / mute / ban / block",
                ephemeral=True
            )

        gid = str(interaction.guild.id)
        uid = str(usuario.id)

        if gid not in blacklist_servers:
            blacklist_servers[gid] = {"users": {}}

        blacklist_servers[gid]["users"][uid] = {
            "accion": accion,
            "minutos": minutos if accion == "mute" else 0,
            "razon": razon
        }

        save_json("blacklist_servers.json", blacklist_servers)

        await interaction.response.send_message(
            f"🚫 {usuario.mention} añadido a la blacklist del servidor.\n"
            f"**Acción:** {accion}\n"
            f"**Razón:** {razon}",
            ephemeral=True
        )

    @app_commands.command(
        name="unblacklist",
        description="Quita un usuario de la blacklist del servidor"
    )
    async def unblacklist_cmd(
        self,
        interaction: discord.Interaction,
        usuario: discord.User
    ):
        user = interaction.user

        if not (user.guild_permissions.administrator or user.guild_permissions.manage_guild):
            return await interaction.response.send_message(
                "❌ No tienes permisos.",
                ephemeral=True
            )

        gid = str(interaction.guild.id)
        uid = str(usuario.id)

        if gid not in blacklist_servers or uid not in blacklist_servers[gid]["users"]:
            return await interaction.response.send_message(
                "ℹ️ Ese usuario no está en la blacklist.",
                ephemeral=True
            )

        del blacklist_servers[gid]["users"][uid]
        save_json("blacklist_servers.json", blacklist_servers)

        await interaction.response.send_message(
            f"✅ {usuario.mention} eliminado de la blacklist del servidor.",
            ephemeral=True
        )

    @app_commands.command(
        name="blacklistlist",
        description="Lista la blacklist del servidor"
    )
    async def blacklistlist_cmd(self, interaction: discord.Interaction):
        gid = str(interaction.guild.id)

        if gid not in blacklist_servers or not blacklist_servers[gid]["users"]:
            return await interaction.response.send_message(
                "📭 La blacklist está vacía.",
                ephemeral=True
            )

        embed = discord.Embed(
            title=f"📜 Blacklist de {interaction.guild.name}",
            color=discord.Color.red()
        )

        for uid, data in blacklist_servers[gid]["users"].items():
            accion = data["accion"]
            minutos = data.get("minutos", 0)

            if accion == "mute" and minutos == 0:
                accion_texto = "mute permanente"
            elif accion == "mute":
                accion_texto = f"mute {minutos} min"
            else:
                accion_texto = accion

            embed.add_field(
                name=f"Usuario ID: {uid}",
                value=f"Acción: **{accion_texto}**\nRazón: {data['razon']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================
# PANEL GLOBAL
# ============================

def build_global_embed():
    if not blacklist_global:
        desc = "📭 La blacklist global está vacía."
    else:
        desc = "\n".join(
            f"• ID `{uid}` — Razón: {data['razon']}"
            for uid, data in blacklist_global.items()
        )

    embed = discord.Embed(
        title="🌐 Panel Blacklist Global",
        description=desc,
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Solo el dueño del bot puede usar este panel.")
    return embed

# ============================
# MODALS Y VIEW
# ============================

class GlobalRemoveModal(discord.ui.Modal, title="➖ Eliminar de Blacklist Global"):
    user_id = discord.ui.TextInput(label="ID de usuario", placeholder="123456789012345678")

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message("❌ No puedes usar este modal.", ephemeral=True)

        uid = str(self.user_id.value).strip()

        if uid not in blacklist_global:
            return await interaction.response.send_message(
                "ℹ️ Ese usuario no está en la blacklist global.",
                ephemeral=True
            )

        del blacklist_global[uid]
        save_json("blacklist_global.json", blacklist_global)

        await interaction.response.send_message(
            f"✅ Usuario ID `{uid}` eliminado de la blacklist global.",
            ephemeral=True
        )

class GlobalBlacklistView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=120)
        self.bot = bot

    @discord.ui.button(label="➕ Añadir", style=discord.ButtonStyle.success)
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message("❌ No puedes usar este panel.", ephemeral=True)
        await interaction.response.send_modal(GlobalAddModal())

    @discord.ui.button(label="➖ Eliminar", style=discord.ButtonStyle.danger)
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message("❌ No puedes usar este panel.", ephemeral=True)
        await interaction.response.send_modal(GlobalRemoveModal())

    @discord.ui.button(label="🔄 Actualizar", style=discord.ButtonStyle.primary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message("❌ No puedes usar este panel.", ephemeral=True)
        embed = build_global_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Cerrar", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message("❌ No puedes usar este panel.", ephemeral=True)
        await interaction.response.edit_message(content="Panel cerrado.", embed=None, view=None)

# ============================
# SETUP DEL COG
# ============================

async def setup(bot: commands.Bot):
    await bot.add_cog(Blacklist(bot))
