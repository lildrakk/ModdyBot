import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time
from datetime import datetime, timezone

ANTIRAID_FILE = "antiraid.json"


# ============================
# JSON LOADER
# ============================

def load_antiraid():
    if not os.path.exists(ANTIRAID_FILE):
        data = {
            "enabled": False,
            "raid_limit": 5,
            "time_window": 10,
            "min_account_days": 7,   # AHORA EN DÍAS
            "action": "ban"
        }
        with open(ANTIRAID_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return data

    with open(ANTIRAID_FILE, "r") as f:
        return json.load(f)


def save_antiraid(data):
    with open(ANTIRAID_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ============================
# COG ANTI-RAID
# ============================

class AntiRaidCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.antiraid = load_antiraid()
        self.join_times = []


    # ============================
    # COMANDO /antiraid
    # ============================

    @app_commands.command(
        name="antiraid",
        description="Configura el sistema Anti-Raid"
    )
    @app_commands.describe(
        enabled="Activa o desactiva el Anti-Raid (on/off)",
        action="Acción cuando se detecta un raid: kick / ban / lockdown",
        raid_limit="Usuarios necesarios para detectar raid",
        time_window="Segundos para medir el raid",
        min_account_days="Días mínimos de antigüedad de cuenta"
    )
    async def antiraid_config(
        self,
        interaction: discord.Interaction,
        enabled: str = None,
        action: str = None,
        raid_limit: int = None,
        time_window: int = None,
        min_account_days: int = None
    ):

        cambios = []

        # Activar / desactivar
        if enabled:
            enabled = enabled.lower()
            if enabled in ["on", "off"]:
                self.antiraid["enabled"] = (enabled == "on")
                cambios.append(f"🟢 Anti-Raid: **{enabled.upper()}**")
            else:
                return await interaction.response.send_message(
                    "❌ Usa: on / off",
                    ephemeral=True
                )

        # Acción
        if action:
            action = action.lower()
            if action in ["kick", "ban", "lockdown"]:
                self.antiraid["action"] = action
                cambios.append(f"⚙️ Acción: **{action.upper()}**")
            else:
                return await interaction.response.send_message(
                    "❌ Acciones válidas: kick / ban / lockdown",
                    ephemeral=True
                )

        # Límite de raid
        if raid_limit:
            self.antiraid["raid_limit"] = raid_limit
            cambios.append(f"👥 Límite de raid: **{raid_limit} usuarios**")

        # Ventana de tiempo
        if time_window:
            self.antiraid["time_window"] = time_window
            cambios.append(f"⏳ Ventana de tiempo: **{time_window} segundos**")

        # Antigüedad mínima (DÍAS)
        if min_account_days:
            self.antiraid["min_account_days"] = min_account_days
            cambios.append(
                f"📅 Antigüedad mínima: **{min_account_days} días**"
            )

        save_antiraid(self.antiraid)

        if not cambios:
            return await interaction.response.send_message(
                "ℹ️ No se ha cambiado nada. Usa las opciones del comando.",
                ephemeral=True
            )

        mensaje = "🛡️ **Anti-Raid actualizado:**\n" + "\n".join(cambios)

        await interaction.response.send_message(mensaje, ephemeral=True)


    # ============================
    # EVENTO: on_member_join
    # ============================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        now = time.time()

        if not self.antiraid.get("enabled", False):
            return

        # Obtener canal de logs (opcional)
        try:
            from main import logs
            log_channel_id = logs.get("log_channel")
            log_channel = member.guild.get_channel(log_channel_id) if log_channel_id else None
        except:
            log_channel = None

        # ============================
        # 1. PROTECCIÓN CUENTAS NUEVAS (EN DÍAS)
        # ============================

        account_age_days = (datetime.now(timezone.utc) - member.created_at).days
        min_days = self.antiraid["min_account_days"]

        if account_age_days < min_days:
            try:
                await member.kick(reason="Cuenta demasiado nueva (Anti-Raid)")
            except:
                pass

            if log_channel:
                await log_channel.send(
                    f"⚠️ **Cuenta nueva expulsada automáticamente**\n"
                    f"👤 Usuario: {member.mention}\n"
                    f"📅 Antigüedad: **{account_age_days} días** (mínimo {min_days})"
                )
            return

        # ============================
        # 2. REGISTRAR ENTRADA PARA DETECTAR RAID
        # ============================

        self.join_times.append(now)

        # Limpiar entradas antiguas
        self.join_times[:] = [
            t for t in self.join_times if now - t <= self.antiraid["time_window"]
        ]

        # ============================
        # 3. DETECTAR RAID
        # ============================

        if len(self.join_times) >= self.antiraid["raid_limit"]:

            accion = self.antiraid["action"]

            # Acción configurada
            if accion == "ban":
                try:
                    await member.ban(reason="Raid detectado (Anti-Raid)")
                except:
                    pass

            elif accion == "kick":
                try:
                    await member.kick(reason="Raid detectado (Anti-Raid)")
                except:
                    pass

            elif accion == "lockdown":
                for channel in member.guild.channels:
                    try:
                        await channel.set_permissions(
                            member.guild.default_role,
                            send_messages=False
                        )
                    except:
                        pass

            # Logs
            if log_channel:
                await log_channel.send(
                    f"🚨 **RAID DETECTADO**\n"
                    f"👥 Entradas en pocos segundos: **{len(self.join_times)}**\n"
                    f"🔧 Acción ejecutada: **{accion.upper()}**"
                )

            return


# ============================
# SETUP DEL COG
# ============================

async def setup(bot):
    await bot.add_cog(AntiRaidCog(bot))
