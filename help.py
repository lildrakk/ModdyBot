import discord
from discord.ext import commands
from discord import app_commands

COLOR = discord.Color(0x0A3D62)

# ============================================================
# SELECT MENU
# ============================================================

class HelpSelect(discord.ui.Select):
    def __init__(self):

        options = [
            discord.SelectOption(label="Moderación", emoji="🟥"),
            discord.SelectOption(label="Seguridad", emoji="🛡️"),
            discord.SelectOption(label="Información", emoji="ℹ️"),
            discord.SelectOption(label="Utilidad", emoji="🛠️"),
            discord.SelectOption(label="Verificación", emoji="🧩"),
            discord.SelectOption(label="Blacklist", emoji="🚫"),
            discord.SelectOption(label="Giveaways", emoji="🎉"),
            discord.SelectOption(label="Backups", emoji="📦"),
        ]

        super().__init__(
            placeholder="Selecciona una categoría…",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        categoria = self.values[0]

        # ============================
        # EMBEDS POR CATEGORÍA
        # ============================

        if categoria == "Moderación":
            embed = discord.Embed(
                title="🟥 Moderación",
                description=(
                    "**/ban** — Sistema de expulsión permanente.\n"
                    "**/unban** — Sistema para revertir expulsiones.\n"
                    "**/mute** — Sistema de silencio temporal.\n"
                    "**/unmute** — Sistema para retirar silencios.\n"
                    "**/warn** — Sistema de advertencias.\n"
                    "**/ver_warns** — Consulta de advertencias.\n"
                    "**/eliminar_warn** — Eliminación de advertencias.\n"
                    "**/eliminar_warns** — Limpieza total de advertencias.\n"
                    "**/purge** — Eliminación de mensajes.\n"
                    "**/purgeuser** — Eliminación de mensajes de un usuario.\n"
                    "**/purgebot** — Eliminación de mensajes de bots.\n"
                    "**/nick** — Gestión de nombres de usuario."
                ),
                color=COLOR
            )

        elif categoria == "Seguridad":
            embed = discord.Embed(
                title="🛡️ Seguridad",
                description=(
                    "**/antibots** — Sistema de bloqueo de bots desconocidos.\n"
                    "**/antibots_config** — Configuración del sistema antibots.\n"
                    "**/antiflood** — Sistema de control de spam masivo.\n"
                    "**/antilinks** — Sistema de bloqueo de enlaces no permitidos.\n"
                    "**/antilinks_whitelist** — Gestión de enlaces permitidos.\n"
                    "**/antiraid** — Sistema de protección contra raids.\n"
                    "**/antiraid_config** — Configuración del sistema antiraid.\n"
                    "**/antialts** — Sistema contra cuentas alternativas.\n"
                    "**/antiping** — Sistema de control de menciones masivas.\n"
                    "**/antiping_objetivo** — Configuración del objetivo protegido.\n"
                    "**/antiping_whitelist** — Gestión de usuarios permitidos.\n"
                    "**/securityscan** — Análisis de seguridad del servidor."
                ),
                color=COLOR
            )

        elif categoria == "Información":
            embed = discord.Embed(
                title="ℹ️ Información",
                description=(
                    "**/botinfo** — Información del bot.\n"
                    "**/serverinfo** — Información del servidor.\n"
                    "**/userinfo** — Información de un usuario."
                ),
                color=COLOR
            )

        elif categoria == "Utilidad":
            embed = discord.Embed(
                title="🛠️ Utilidad",
                description=(
                    "**/say** — Enviar un mensaje mediante el bot.\n"
                    "**/spoiler** — Enviar un spoiler formateado.\n"
                    "**/dmwelcome** — Sistema de bienvenida por mensaje directo."
                ),
                color=COLOR
            )

        elif categoria == "Verificación":
            embed = discord.Embed(
                title="🧩 Verificación",
                description=(
                    "**/verificacion** — Sistema de verificación del servidor.\n"
                    "**/verificacion_enviar** — Enviar el panel de verificación."
                ),
                color=COLOR
            )

        elif categoria == "Blacklist":
            embed = discord.Embed(
                title="🚫 Blacklist",
                description=(
                    "**/global_blacklist** — Gestión de la blacklist global.\n"
                    "**/blacklist** — Añadir usuarios a la blacklist.\n"
                    "**/unblacklist** — Eliminar usuarios de la blacklist.\n"
                    "**/blacklistlist** — Lista de usuarios bloqueados."
                ),
                color=COLOR
            )

        elif categoria == "Giveaways":
            embed = discord.Embed(
                title="🎉 Giveaways",
                description=(
                    "**/giveaway** — Crear un sorteo.\n"
                    "**/reroll** — Repetir ganador."
                ),
                color=COLOR
            )

        elif categoria == "Backups":
            embed = discord.Embed(
                title="📦 Backups",
                description=(
                    "**/backup_crear** — Crear una copia del servidor.\n"
                    "**/backup_restaurar** — Restaurar un backup.\n"
                    "**/backup_borrar** — Eliminar un backup.\n"
                    "**/backup_listar** — Listar backups disponibles.\n"
                    "**/backup_info** — Información detallada de un backup."
                ),
                color=COLOR
            )

        await interaction.response.edit_message(embed=embed)


# ============================================================
# VIEW DEL SELECT
# ============================================================

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpSelect())


# ============================================================
# COG PRINCIPAL
# ============================================================

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Panel de ayuda del bot.")
    async def help(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="📘 Panel de Ayuda — ModdyBot",
            description=(
                "Selecciona una categoría en el menú inferior para ver los comandos disponibles.\n\n"
                "ModdyBot ofrece sistemas avanzados de moderación, seguridad, verificación, backups y más."
            ),
            color=COLOR
        )

        await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
