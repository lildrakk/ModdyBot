import discord
from discord.ext import commands
from discord import app_commands
import json, os, time
from datetime import timedelta

CONFIG_FILE = "antimention.json"

# ============================================================
# CONFIG SEGURO (PERSISTENTE)
# ============================================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_config(data):
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, CONFIG_FILE)


# ============================================================
# COG ANTI‑MENTION
# ============================================================

class AntiMention(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.cooldowns = {}

    # --------------------------------------------------------
    # CONFIG POR SERVIDOR
    # --------------------------------------------------------

    def ensure_guild(self, guild_id: int):
        gid = str(guild_id)

        if gid not in self.config:
            self.config[gid] = {
                "enabled": False,
                "accion": "warn",
                "mute_time": 600,
                "cooldown": 3,
                "logs": None,

                "limit_users": 3,
                "limit_roles": 3,
                "limit_everyone": 1,

                "blocked_users": [],
                "blocked_roles": [],

                "whitelist_users": [],
                "whitelist_roles": [],
                "whitelist_channels": []
            }
            save_config(self.config)

        return self.config[gid]

    # ============================================================
    # COMANDO PRINCIPAL /antimention
    # ============================================================

    @app_commands.command(name="antimention", description="Configura el Anti‑Mention.")
    @app_commands.describe(
        activar="True/False para activar o desactivar",
        accion="1=warn, 2=mute, 3=kick, 4=ban",
        limite_usuarios="Límite de menciones a usuarios",
        limite_roles="Límite de menciones a roles",
        limite_everyone="0 o 1 para permitir @everyone",
        cooldown="Cooldown entre detecciones",
        logs="Canal de logs"
    )
    async def antimention_cmd(
        self,
        interaction: discord.Interaction,
        activar: bool = None,
        accion: int = None,
        limite_usuarios: int = None,
        limite_roles: int = None,
        limite_everyone: int = None,
        cooldown: int = None,
        logs: discord.TextChannel = None
    ):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        if activar is not None:
            cfg["enabled"] = activar

        if accion is not None:
            acciones = {1: "warn", 2: "mute", 3: "kick", 4: "ban"}
            if accion not in acciones:
                return await interaction.response.send_message("Valor inválido para acción.", ephemeral=True)
            cfg["accion"] = acciones[accion]

        if limite_usuarios is not None:
            cfg["limit_users"] = max(1, limite_usuarios)

        if limite_roles is not None:
            cfg["limit_roles"] = max(1, limite_roles)

        if limite_everyone is not None:
            cfg["limit_everyone"] = max(0, limite_everyone)

        if cooldown is not None:
            cfg["cooldown"] = max(0, cooldown)

        if logs is not None:
            cfg["logs"] = logs.id

        save_config(self.config)

        embed = discord.Embed(
            title="🛡 Configuración Anti‑Mention actualizada",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Estado", value="🟢 Activado" if cfg["enabled"] else "🔴 Desactivado", inline=False)
        embed.add_field(name="Acción", value=cfg["accion"], inline=False)
        embed.add_field(name="Límite usuarios", value=cfg["limit_users"], inline=True)
        embed.add_field(name="Límite roles", value=cfg["limit_roles"], inline=True)
        embed.add_field(name="Límite everyone", value=cfg["limit_everyone"], inline=True)
        embed.add_field(name="Cooldown", value=cfg["cooldown"], inline=True)
        embed.add_field(name="Logs", value=f"<#{cfg['logs']}>" if cfg["logs"] else "Ninguno", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ============================================================
    # COMANDO /antimention_config
    # ============================================================

    @app_commands.command(name="antimention_config", description="Configura whitelist y blacklist del Anti‑Mention.")
    async def antimention_config(self, interaction: discord.Interaction):

        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        class ConfigSelect(discord.ui.Select):
            def __init__(self):
                options = [
                    discord.SelectOption(label="Whitelist usuarios", value="w_users"),
                    discord.SelectOption(label="Whitelist roles", value="w_roles"),
                    discord.SelectOption(label="Whitelist canales", value="w_channels"),
                    discord.SelectOption(label="Blacklist usuarios", value="b_users"),
                    discord.SelectOption(label="Blacklist roles", value="b_roles"),
                ]
                super().__init__(placeholder="Selecciona qué quieres configurar", options=options)

            async def callback(self, i: discord.Interaction):
                tipo = self.values[0]

                if tipo == "w_users":
                    lista = cfg["whitelist_users"]
                    titulo = "Whitelist usuarios"
                elif tipo == "w_roles":
                    lista = cfg["whitelist_roles"]
                    titulo = "Whitelist roles"
                elif tipo == "w_channels":
                    lista = cfg["whitelist_channels"]
                    titulo = "Whitelist canales"
                elif tipo == "b_users":
                    lista = cfg["blocked_users"]
                    titulo = "Blacklist usuarios"
                else:
                    lista = cfg["blocked_roles"]
                    titulo = "Blacklist roles"

                class TargetSelect(discord.ui.Select):
                    def __init__(self):
                        opts = []

                        if "users" in tipo:
                            for m in guild.members[:25]:
                                opts.append(discord.SelectOption(label=m.name, value=str(m.id)))
                        elif "roles" in tipo:
                            for r in guild.roles[:25]:
                                opts.append(discord.SelectOption(label=r.name, value=str(r.id)))
                        else:
                            for c in guild.channels[:25]:
                                if isinstance(c, discord.TextChannel):
                                    opts.append(discord.SelectOption(label=c.name, value=str(c.id)))

                        super().__init__(placeholder="Selecciona elementos", options=opts, min_values=1, max_values=1)

                    async def callback(self, i2: discord.Interaction):
                        target_id = int(self.values[0])

                        if target_id in lista:
                            lista.remove(target_id)
                            accion = "eliminado"
                        else:
                            lista.append(target_id)
                            accion = "añadido"

                        save_config(self.config)

                        await i2.response.send_message(
                            f"✅ `{target_id}` {accion} en **{titulo}**.",
                            ephemeral=True
                        )

                view2 = discord.ui.View()
                view2.add_item(TargetSelect())

                await i.response.send_message(
                    f"Configurar **{titulo}**:",
                    view=view2,
                    ephemeral=True
                )

        view = discord.ui.View()
        view.add_item(ConfigSelect())

        await interaction.response.send_message(
            "Selecciona qué deseas configurar:",
            view=view,
            ephemeral=True
        )

    # ============================================================
    # DETECCIÓN DE MENCIONES
    # ============================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild = message.guild
        cfg = self.ensure_guild(guild.id)
        user = message.author
        content = message.content

        if not cfg["enabled"]:
            return

        if user.id in cfg["whitelist_users"]:
            return
        if any(r.id in cfg["whitelist_roles"] for r in user.roles):
            return
        if message.channel.id in cfg["whitelist_channels"]:
            return

        now = time.time()
        if user.id in self.cooldowns and now - self.cooldowns[user.id] < cfg["cooldown"]:
            return
        self.cooldowns[user.id] = now

        if any(u.id in cfg["blocked_users"] for u in message.mentions):
            return await self.apply_action(message, "Mención a usuario bloqueado")

        if any(r.id in cfg["blocked_roles"] for r in message.role_mentions):
            return await self.apply_action(message, "Mención a rol bloqueado")

        if len(message.mentions) > cfg["limit_users"]:
            return await self.apply_action(message, "Exceso de menciones a usuarios")

        if len(message.role_mentions) > cfg["limit_roles"]:
            return await self.apply_action(message, "Exceso de menciones a roles")

        if ("@everyone" in content or "@here" in content) and cfg["limit_everyone"] < 1:
            return await self.apply_action(message, "Uso de @everyone/@here")

    # ============================================================
    # APLICAR SANCIÓN
    # ============================================================

    async def apply_action(self, message: discord.Message, reason: str):
        guild = message.guild
        cfg = self.ensure_guild(guild.id)
        user = message.author
        action = cfg["accion"]

        try:
            await message.delete()
        except:
            pass

        aviso = discord.Embed(
            title="⚠️ Mención no permitida",
            description=f"{user.mention}, ese usuario/rol está **prohibido** ser mencionado.",
            color=discord.Color.orange()
        )
        try:
            await message.channel.send(user.mention, embed=aviso, delete_after=6)
        except:
            pass

        if cfg["logs"]:
            ch = guild.get_channel(cfg["logs"])
            if ch:
                embed = discord.Embed(
                    title="📘 Log Anti‑Mention",
                    description=f"Usuario: {user.mention}\nRazón: `{reason}`",
                    color=discord.Color.blue()
                )
                await ch.send(embed=embed)

        sancionado = False

        try:
            if action == "ban":
                await guild.ban(user, reason=f"Anti‑Mention: {reason}")
            elif action == "kick":
                await guild.kick(user, reason=f"Anti‑Mention: {reason}")
            elif action == "mute":
                await user.timeout(
                    discord.utils.utcnow() + timedelta(seconds=cfg["mute_time"]),
                    reason=f"Anti‑Mention: {reason}"
                )
            sancionado = True
        except:
            sancionado = False

        if not sancionado:
            embed = discord.Embed(
                title="⚠️ No se pudo aplicar sanción",
                description=f"Detecté abuso de menciones de {user.mention}, pero no tengo permisos.",
                color=discord.Color.yellow()
            )
        else:
            embed = discord.Embed(
                title="⛔ Sanción aplicada",
                description=f"Usuario: {user.mention}\nAcción: **{action}**\nRazón: {reason}",
                color=discord.Color.red()
            )

        await message.channel.send(embed=embed)

# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiMention(bot)) 
