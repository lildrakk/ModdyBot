import discord
from discord.ext import commands
from discord import app_commands
import json
import os

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
# COG PRINCIPAL
# ============================

class Blacklist(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================
    # PANEL GLOBAL
    # ============================

    @app_commands.command(name="global_panel", description="Abre el panel PRO de blacklist global")
    async def global_panel_cmd(self, interaction: discord.Interaction):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message(
                "❌ Solo el dueño del bot puede usar este panel.",
                ephemeral=True
            )

        embed = build_global_embed()
        view = GlobalBlacklistView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ============================
    # BLACKLIST POR SERVIDOR
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
async def unblacklist_cmd(self, interaction: discord.Interaction, usuario: discord.User):

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

@app_commands.command(name="blacklistlist", description="Lista la blacklist del servidor")
async def blacklistlist_cmd(self, interaction: discord.Interaction):
    gid = str(interaction.guild.id)

    if gid not in blacklist_servers or not blacklist_servers[gid]["users"]:
        return await interaction.response.send_message("📭 La blacklist está vacía.", ephemeral=True)

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
    # BLACKLIST GLOBAL
    # ============================

    @app_commands.command(name="global_blacklist", description="Añade un usuario a la blacklist GLOBAL")
    async def global_blacklist_cmd(
        self,
        interaction: discord.Interaction,
        usuario: discord.User,
        razon: str = "No especificada"
    ):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message(
                "❌ Solo el dueño del bot puede usar este comando.",
                ephemeral=True
            )

        uid = str(usuario.id)
        blacklist_global[uid] = {"razon": razon}
        save_json("blacklist_global.json", blacklist_global)

        # DM al usuario
        try:
            embed = discord.Embed(
                title="🚫 Aviso de Sanción Global",
                description=(
                    f"{usuario.mention}, has sido añadido a la **blacklist global**.\n"
                    f"**Motivo:** {razon}\n"
                    f"Serás expulsado automáticamente de todos los servidores que usen este sistema."
                ),
                color=discord.Color.red()
            )

            file = discord.File("assets/md_alert.jpeg", filename="alerta.jpeg")
            embed.set_thumbnail(url="attachment://alerta.jpeg")

            await usuario.send(embed=embed, file=file)
        except:
            pass

        await interaction.response.send_message(
            f"🌐 {usuario.mention} añadido a la blacklist global.",
            ephemeral=True
        )

    @app_commands.command(name="global_unblacklist", description="Quita un usuario de la blacklist GLOBAL")
    async def global_unblacklist_cmd(self, interaction: discord.Interaction, usuario: discord.User):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message(
                "❌ Solo el dueño del bot puede usar este comando.",
                ephemeral=True
            )

        uid = str(usuario.id)

        if uid not in blacklist_global:
            return await interaction.response.send_message(
                "ℹ️ Ese usuario no está en la blacklist global.",
                ephemeral=True
            )

        del blacklist_global[uid]
        save_json("blacklist_global.json", blacklist_global)

        await interaction.response.send_message(
            f"✅ {usuario.mention} eliminado de la blacklist global.",
            ephemeral=True
        )

    @app_commands.command(name="global_blacklistlist", description="Lista la blacklist GLOBAL")
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
            title="🌐 Blacklist Global",
            color=discord.Color.dark_red()
        )

        for uid, data in blacklist_global.items():
            embed.add_field(
                name=f"Usuario ID: {uid}",
                value=f"Razón: {data['razon']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ============================
    # AUTO-BAN GLOBAL
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        uid = str(member.id)

        # Global
        if uid in blacklist_global:
            try:
                await member.ban(reason="Blacklist global")
            except:
                pass
            return

        # Por servidor
        gid = str(member.guild.id)
        if gid in blacklist_servers and uid in blacklist_servers[gid]["users"]:
            data = blacklist_servers[gid]["users"][uid]
            accion = data["accion"]

            try:
                if accion == "kick":
                    await member.kick(reason="Blacklist del servidor")
                elif accion == "ban":
                    await member.ban(reason="Blacklist del servidor")
                elif accion == "mute":
                    pass  # Aquí puedes integrar tu sistema de mute
            except:
                pass


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

class GlobalAddModal(discord.ui.Modal, title="➕ Añadir a Blacklist Global"):
    user_id = discord.ui.TextInput(label="ID de usuario", placeholder="123456789012345678")
    reason = discord.ui.TextInput(label="Razón", default="No especificada", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != GLOBAL_OWNER_ID:
            return await interaction.response.send_message("❌ No puedes usar este modal.", ephemeral=True)

        uid = str(self.user_id.value).strip()
        razon = str(self.reason.value) if self.reason.value else "No especificada"

        blacklist_global[uid] = {"razon": razon}
        save_json("blacklist_global.json", blacklist_global)

        await interaction.response.send_message(
            f"🌐 Usuario ID `{uid}` añadido a la blacklist global.\nRazón: {razon}",
            ephemeral=True
        )


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
