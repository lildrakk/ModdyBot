import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
from datetime import datetime


# ============================
# JSON LOADERS
# ============================

def load_backups(user_id):
    folder = f"backups/{user_id}"
    path = f"{folder}/backups.json"

    if not os.path.exists(folder):
        os.makedirs(folder)

    if not os.path.exists(path):
        data = {"backups": []}
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        return data

    with open(path, "r") as f:
        return json.load(f)


def save_backups(user_id, data):
    folder = f"backups/{user_id}"
    path = f"{folder}/backups.json"

    if not os.path.exists(folder):
        os.makedirs(folder)

    with open(path, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# COG DE BACKUPS
# ============================

class BackupsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    # ============================
    # BACKUP CREAR
    # ============================

    @app_commands.command(
        name="backup_crear",
        description="Crea un backup del servidor (Premium)"
    )
    async def backup_crear(self, interaction: discord.Interaction):

        guild = interaction.guild
        user_id = interaction.user.id

        await interaction.response.send_message(
            "📦 Creando backup ordenado...",
            ephemeral=True
        )

        try:
            data = load_backups(user_id)

            backup_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            backup = {"id": backup_id, "roles": [], "channels": []}

            # -----------------------------
            # GUARDAR ROLES
            # -----------------------------
            for role in sorted(guild.roles, key=lambda r: r.position):
                if role.is_default():
                    continue

                backup["roles"].append({
                    "name": role.name,
                    "color": role.color.value,
                    "permissions": role.permissions.value,
                    "position": role.position
                })

            # -----------------------------
            # GUARDAR CATEGORÍAS Y CANALES
            # -----------------------------
            for category in sorted(guild.categories, key=lambda c: c.position):

                backup["channels"].append({
                    "name": category.name,
                    "type": "category",
                    "category": None,
                    "position": category.position
                })

                for channel in sorted(category.channels, key=lambda c: c.position):

                    tipo = "text"
                    if isinstance(channel, discord.VoiceChannel):
                        tipo = "voice"
                    elif isinstance(channel, discord.StageChannel):
                        tipo = "stage"
                    elif isinstance(channel, discord.ForumChannel):
                        tipo = "forum"

                    backup["channels"].append({
                        "name": channel.name,
                        "type": tipo,
                        "category": category.name,
                        "position": channel.position
                    })

            # -----------------------------
            # CANALES SIN CATEGORÍA
            # -----------------------------
            for channel in sorted(guild.channels, key=lambda c: c.position):
                if channel.category is None and not isinstance(channel, discord.CategoryChannel):

                    tipo = "text"
                    if isinstance(channel, discord.VoiceChannel):
                        tipo = "voice"
                    elif isinstance(channel, discord.StageChannel):
                        tipo = "stage"
                    elif isinstance(channel, discord.ForumChannel):
                        tipo = "forum"

                    backup["channels"].append({
                        "name": channel.name,
                        "type": tipo,
                        "category": None,
                        "position": channel.position
                    })

            # Guardar backup
            data["backups"].append(backup)
            save_backups(user_id, data)

            await interaction.followup.send(
                f"✅ **Backup creado correctamente**\n🆔 ID: `{backup_id}`",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                "❌ **Hubo un error al crear el backup.**\n"
                "🔁 Inténtalo de nuevo.\n"
                "🆘 Si el error persiste, únete al servidor de soporte:\n"
                "https://discord.gg/qrMnzGztm3",
                ephemeral=True
            )
            print(f"Error en backup_crear: {e}")


# ============================
    # BACKUP RESTAURAR
    # ============================

    @app_commands.command(
        name="backup_restaurar",
        description="Restaura un backup del servidor (TOTAL A1)"
    )
    @app_commands.describe(
        backup_id="ID del backup a restaurar"
    )
    async def backup_restaurar(self, interaction: discord.Interaction, backup_id: str):

        guild = interaction.guild
        user_id = interaction.user.id

        await interaction.response.send_message(
            "⏳ Restaurando backup... Esto puede tardar unos segundos.",
            ephemeral=True
        )

        try:
            data = load_backups(user_id)

            backup = None
            for b in data["backups"]:
                if b["id"] == backup_id:
                    backup = b
                    break

            if not backup:
                return await interaction.followup.send(
                    "❌ No se encontró un backup con ese ID.",
                    ephemeral=True
                )

            # -----------------------------
            # 1. BORRAR CANALES
            # -----------------------------
            for channel in guild.channels:
                try:
                    await channel.delete()
                except:
                    pass

            # -----------------------------
            # 2. BORRAR ROLES (menos @everyone)
            # -----------------------------
            for role in guild.roles:
                if role.is_default():
                    continue
                try:
                    await role.delete()
                except:
                    pass

            # -----------------------------
            # 3. CREAR ROLES DEL BACKUP
            # -----------------------------
            new_roles = {}

            for role_data in sorted(backup["roles"], key=lambda r: r["position"]):
                new_role = await guild.create_role(
                    name=role_data["name"],
                    color=discord.Color(role_data["color"]),
                    permissions=discord.Permissions(role_data["permissions"])
                )
                new_roles[role_data["name"]] = new_role

            # -----------------------------
            # 4. CREAR CATEGORÍAS
            # -----------------------------
            categories = {}

            for ch in backup["channels"]:
                if ch["type"] == "category":
                    try:
                        cat = await guild.create_category(
                            name=ch["name"],
                            position=ch["position"]
                        )
                        categories[ch["name"]] = cat
                        await asyncio.sleep(1)
                    except:
                        pass

            # -----------------------------
            # 5. CREAR CANALES
            # -----------------------------
            for ch in backup["channels"]:
                if ch["type"] == "category":
                    continue

                parent = categories.get(ch["category"])

                try:
                    if ch["type"] == "text":
                        await guild.create_text_channel(
                            name=ch["name"],
                            category=parent,
                            position=ch["position"]
                        )

                    elif ch["type"] == "voice":
                        await guild.create_voice_channel(
                            name=ch["name"],
                            category=parent,
                            position=ch["position"]
                        )

                    elif ch["type"] == "stage":
                        await guild.create_stage_channel(
                            name=ch["name"],
                            category=parent,
                            position=ch["position"]
                        )

                    elif ch["type"] == "forum":
                        await guild.create_forum_channel(
                            name=ch["name"],
                            category=parent,
                            position=ch["position"]
                        )

                    await asyncio.sleep(1.5)

                except Exception as e:
                    print(f"Error creando canal {ch['name']}: {e}")
                    await asyncio.sleep(5)

            await interaction.followup.send(
                "✅ **Backup restaurado correctamente.**",
                ephemeral=True
            )

        except Exception as e:
            print(f"Error en backup_restaurar: {e}")
            await interaction.followup.send(
                "❌ **Hubo un error al restaurar el backup.**\n"
                "🔁 Inténtalo de nuevo.\n"
                "🆘 Si el error persiste, únete al servidor de soporte:\n"
                "https://discord.gg/qrMnzGztm3",
                ephemeral=True
            )


    # ============================
    # BACKUP LISTAR
    # ============================

    @app_commands.command(
        name="backup_listar",
        description="Muestra todos los backups del usuario"
    )
    async def backup_listar(self, interaction: discord.Interaction):

        user_id = interaction.user.id
        data = load_backups(user_id)

        if not data["backups"]:
            return await interaction.response.send_message(
                "📭 No tienes backups creados.",
                ephemeral=True
            )

        mensaje = "📦 **Lista de backups disponibles:**\n\n"

        for b in sorted(data["backups"], key=lambda x: x["id"], reverse=True):
            mensaje += (
                f"🆔 **{b['id']}**\n"
                f"• Roles: **{len(b['roles'])}**\n"
                f"• Canales: **{len(b['channels'])}**\n\n"
            )

        await interaction.response.send_message(mensaje, ephemeral=True)


    # ============================
    # BACKUP BORRAR
    # ============================

    @app_commands.command(
        name="backup_borrar",
        description="Borra un backup del usuario"
    )
    @app_commands.describe(
        backup_id="ID del backup a borrar"
    )
    async def backup_borrar(self, interaction: discord.Interaction, backup_id: str):

        user_id = interaction.user.id
        data = load_backups(user_id)

        backup = None
        for b in data["backups"]:
            if b["id"] == backup_id:
                backup = b
                break

        if not backup:
            return await interaction.response.send_message(
                "❌ No existe un backup con ese ID.",
                ephemeral=True
            )

        data["backups"].remove(backup)
        save_backups(user_id, data)

        await interaction.response.send_message(
            f"🗑️ Backup `{backup_id}` borrado correctamente.",
            ephemeral=True
        )


# ============================
# SETUP DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(BackupsCog(bot))