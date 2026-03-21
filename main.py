import discord
import os
from discord.ext import commands

# 🔧 Forzar que el directorio de trabajo sea la raíz del proyecto
os.chdir(os.path.dirname(os.path.abspath(__file__)))
print("📌 Directorio fijado a:", os.getcwd())

# DEBUG 1 — Mostrar directorio actual
print("📁 Directorio actual:", os.getcwd())

# DEBUG 2 — Listar TODO lo que hay en el proyecto
print("📂 Archivos en la raíz:", os.listdir("."))

# DEBUG 3 — Comprobar si existe la carpeta cogs
if not os.path.exists("./cogs"):
    print("❌ ERROR: La carpeta 'cogs' NO existe en la raíz del proyecto.")
else:
    print("✔ Carpeta 'cogs' encontrada.")
    print("📂 Contenido de /cogs:", os.listdir("./cogs"))

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=";",
            intents=discord.Intents.all()
        )

    async def setup_hook(self):
        print("🔍 Iniciando carga de cogs...")

        if not os.path.exists("./cogs"):
            print("❌ ERROR: No se encontró la carpeta /cogs durante setup_hook.")
            return

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✔ Cargado: {filename}")
                except Exception as e:
                    print(f"❌ Error cargando {filename}: {e}")

bot = Bot()

@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"🔗 Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")

    from keep_alive import keep_alive
    keep_alive()
    print("🌐 Flask iniciado después de sincronizar comandos.")

TOKEN = os.getenv("TOKEN")
if TOKEN is None:
    print("❌ ERROR: No se encontró la variable de entorno TOKEN.")
else:
    print("✔ TOKEN encontrado, iniciando bot...")

bot.run(TOKEN) 
