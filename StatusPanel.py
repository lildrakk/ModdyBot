import discord
from discord.ext import commands, tasks
import datetime, psutil, time, shutil, os, json

STATUS_CHANNEL_ID = 1488931533472399660
MESSAGE_ID_FILE = "status_message.txt"

# ============================
# LÍMITES REALES DEL PLAN
# ============================

MAX_RAM_MB = 512
MAX_DISK_MB = 512
MAX_CPU_PERCENT = 75

# ============================
# FUNCIÓN PARA BARRAS
# ============================

def barra(porcentaje):
    bloques = int((porcentaje / 100) * 10)
    return "█" * bloques + "░" * (10 - bloques)

# ============================
# TAMAÑO REAL DE LA CARPETA
# ============================

def folder_size(path="."):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    return round(total / (1024**2), 2)  # MB

# ============================
# CARGAR MANTENIMIENTO
# ============================

def load_maintenance():
    try:
        with open("maintenance.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"active": False}

# ============================
# PANEL
# ============================

class StatusPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.estado_anterior = None
        self.update_panel.start()

    def cog_unload(self):
        self.update_panel.cancel()

    def save_message_id(self, msg_id):
        with open(MESSAGE_ID_FILE, "w") as f:
            f.write(str(msg_id))

    def load_message_id(self):
        try:
            with open(MESSAGE_ID_FILE, "r") as f:
                return int(f.read().strip())
        except:
            return None

    @tasks.loop(seconds=60)
    async def update_panel(self):
        await self.bot.wait_until_ready()

        channel = self.bot.get_channel(STATUS_CHANNEL_ID)
        if not channel:
            return

        # ============================
        # DETECTAR MANTENIMIENTO
        # ============================

        data = load_maintenance()
        en_mantenimiento = data.get("active", False)
        razon = data.get("reason")
        expires_at = data.get("expires_at")

        # Detectar cambios de estado → enviar @everyone
        estado_actual = en_mantenimiento
        estado_anterior = self.estado_anterior

        if estado_anterior is None:
            self.estado_anterior = estado_actual
        else:
            if estado_actual != estado_anterior:
                if estado_actual:
                    await channel.send("@everyone 🔧 El bot ha entrado en mantenimiento.")
                else:
                    await channel.send("@everyone 🟢 El bot ha salido del mantenimiento.")
                self.estado_anterior = estado_actual

        # ============================
        # DATOS DEL BOT
        # ============================

        ping = round(self.bot.latency * 1000)
        servers = len(self.bot.guilds)

        uptime_seconds = int(time.time() - self.start_time)
        uptime = str(datetime.timedelta(seconds=uptime_seconds))

        # ============================
        # USO REAL DEL BOT
        # ============================

        process = psutil.Process()

        ram_used_mb = round(process.memory_info().rss / (1024**2), 2)
        ram_used_mb = min(ram_used_mb, MAX_RAM_MB)
        ram_percent = (ram_used_mb / MAX_RAM_MB) * 100

        cpu_real = process.cpu_percent(interval=1)
        cpu_percent = min(cpu_real, MAX_CPU_PERCENT)
        cpu_bar_percent = (cpu_percent / MAX_CPU_PERCENT) * 100

        disk_used_mb = folder_size()
        disk_used_mb = min(disk_used_mb, MAX_DISK_MB)
        disk_percent = (disk_used_mb / MAX_DISK_MB) * 100

        # ============================
        # EMBED
        # ============================

        embed = discord.Embed(
            title="<a:alarmazul:1491858094043693177> Panel de Estado del Bot",
            color=discord.Color(0x0A3D62)
        )

        # Estado principal
        if en_mantenimiento:
            estado_texto = "🛠️ En mantenimiento"
        else:
            estado_texto = "Online"

        embed.add_field(
            name="<a:flechazul:1492182951532826684> Estado",
            value=estado_texto,
            inline=False
        )

        # Mostrar razón si existe
        if en_mantenimiento and razon:
            embed.add_field(
                name="Razón",
                value=razon,
                inline=False
            )

        # Mostrar tiempo restante si existe
        if en_mantenimiento and expires_at:
            try:
                exp = datetime.datetime.fromisoformat(expires_at)
                restante = exp - datetime.datetime.now()
                minutos = int(restante.total_seconds() // 60)
                embed.add_field(
                    name="Tiempo restante",
                    value=f"{minutos} minutos",
                    inline=False
                )
            except:
                pass

        # Datos normales del panel
        embed.add_field(name="<:wifi:1493976408865898568> Ping", value=f"{ping} ms", inline=True)
        embed.add_field(name="<:discord:1483506738954244258> Servidores", value=str(servers), inline=True)
        embed.add_field(name="<:cronometro:1493972193598509056> Uptime", value=uptime, inline=False)

        embed.add_field(
            name="RAM",
            value=f"{barra(ram_percent)} {ram_used_mb} MB / {MAX_RAM_MB} MB",
            inline=False
        )

        embed.add_field(
            name="Disco",
            value=f"{barra(disk_percent)} {disk_used_mb} MB / {MAX_DISK_MB} MB",
            inline=False
        )

        embed.add_field(
            name="CPU",
            value=f"{barra(cpu_bar_percent)} {cpu_percent}% / {MAX_CPU_PERCENT}%",
            inline=False
        )

        embed.set_footer(text="ModdyBot • Panel de estado")

        # ============================
        # EDITAR O CREAR MENSAJE
        # ============================

        msg_id = self.load_message_id()
        message = None

        if msg_id:
            try:
                message = await channel.fetch_message(msg_id)
            except:
                message = None

        if message:
            try:
                await message.edit(embed=embed)
                return
            except:
                pass

        new_msg = await channel.send(embed=embed)
        self.save_message_id(new_msg.id)

    @update_panel.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(StatusPanel(bot))
