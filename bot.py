import discord
from discord import app_commands
from datetime import datetime, timedelta
import pytz
import os
import asyncio
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

intents = discord.Intents.default()
intents.message_content = True

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'Bot conectado como {self.user}')
        try:
            synced = await self.tree.sync()
            print(f"Comandos sincronizados con éxito: {len(synced)}")
        except Exception as e:
            print(f"Error al sincronizar comandos: {e}")

client = MyClient()

# ==============================================================================
# TAREA EN SEGUNDO PLANO (RECORDATORIO Y FINALIZACIÓN)
# ==============================================================================
async def gestionar_evento(canal, mensaje, menciones, dt_inicio, dt_fin):
    ahora = datetime.now(pytz.utc)
    
    # 1. Esperar hasta 5 minutos antes de la scrim para el recordatorio
    segundos_para_aviso = (dt_inicio - ahora).total_seconds() - 300
    if segundos_para_aviso > 0:
        await asyncio.sleep(segundos_para_aviso)
        try:
            await canal.send(f"🔔 {menciones} **¡Prepárense!** La scrim está a punto de comenzar (5 minutos).", reference=mensaje)
        except Exception as e:
            print(f"Error enviando recordatorio: {e}")

    # 2. Esperar a que termine la scrim (según la duración indicada)
    ahora = datetime.now(pytz.utc)
    segundos_para_fin = (dt_fin - ahora).total_seconds()
    if segundos_para_fin > 0:
        await asyncio.sleep(segundos_para_fin)
        try:
            # Editamos el Embed para marcarlo como finalizado
            embed = mensaje.embeds[0]
            embed.title = f"🏁 [FINALIZADO] {embed.title.replace('🎮 ', '')}"
            embed.color = discord.Color.dark_grey() # Cambia a gris para no saturar visualmente
            await mensaje.edit(embed=embed)
            await mensaje.clear_reactions() # Limpia las reacciones de asistencia
        except Exception as e:
            print(f"Error finalizando la scrim: {e}")


# ==============================================================================
# 1. MÓDULO DE SCRIMS (FORMULARIO + COMANDO)
# ==============================================================================
class ScrimForm(discord.ui.Modal, title='Programar Nueva Scrim'):
    equipo1 = discord.ui.TextInput(label='Equipo 1', placeholder='Ej: Nuestro Equipo')
    equipo2 = discord.ui.TextInput(label='Equipo 2 (Rival)', placeholder='Ej: Los Rivales')
    fecha = discord.ui.TextInput(label='Fecha (Día/Mes)', placeholder='Ej: 21/05', max_length=5)
    hora = discord.ui.TextInput(label='Hora (Formato 24h)', placeholder='Ej: 22:00', max_length=5)
    detalles = discord.ui.TextInput(label='Detalles Adicionales', placeholder='Reglas, mapas, etc.', required=False)

    def __init__(self, rol1: discord.Role, rol2: discord.Role, timezone_str: str, duracion_minutos: int):
        super().__init__()
        self.rol1 = rol1
        self.rol2 = rol2
        self.tz = pytz.timezone(timezone_str)
        self.duracion_minutos = duracion_minutos

    async def on_submit(self, interaction: discord.Interaction):
        try:
            año_actual = datetime.now().year
            fecha_str = f"{self.fecha.value.strip()}/{año_actual} {self.hora.value.strip()}"
            
            local_dt = datetime.strptime(fecha_str, '%d/%m/%Y %H:%M')
            local_dt = self.tz.localize(local_dt)
            
            ahora_en_tz = datetime.now(self.tz)
            if local_dt <= ahora_en_tz:
                await interaction.response.send_message("❌ **Fecha inválida.** La hora introducida ya pasó. Coloca una hora futura.", ephemeral=True)
                return

            timestamp_inicio = int(local_dt.timestamp())
            
            dt_fin = local_dt + timedelta(minutes=self.duracion_minutos)
            timestamp_fin = int(dt_fin.timestamp())

            menciones = self.rol1.mention
            if self.rol2:
                menciones += f" {self.rol2.mention}"

            embed = discord.Embed(
                title=f"🎮 {self.equipo1.value} vs {self.equipo2.value}",
                color=discord.Color.from_rgb(0, 150, 255)
            )
            
            desc_detalles = f"**Detalles:** {self.detalles.value}\n\n" if self.detalles.value else ""
            
            embed.description = f"{desc_detalles}" \
                                f"📅 **Fecha:** <t:{timestamp_inicio}:D>\n" \
                                f"⏰ **Horario Local:** <t:{timestamp_inicio}:t> hs — Fin aprox: <t:{timestamp_fin}:t> hs\n" \
                                f"⏳ **Comienza:** <t:{timestamp_inicio}:R>\n\n" \
                                f"📢 *Reaccionen para confirmar asistencia.*"
            
            await interaction.response.send_message(content=menciones, embed=embed)
            mensaje = await interaction.original_response()
            
            await mensaje.add_reaction('✅')
            await mensaje.add_reaction('❌')
            await mensaje.add_reaction('❓')

            dt_inicio_utc = local_dt.astimezone(pytz.utc)
            dt_fin_utc = dt_fin.astimezone(pytz.utc)
            
            client.loop.create_task(gestionar_evento(interaction.channel, mensaje, menciones, dt_inicio_utc, dt_fin_utc))

        except ValueError:
            await interaction.response.send_message("❌ Formato incorrecto. Asegúrate de usar `DD/MM` para la fecha y `HH:MM` para la hora.", ephemeral=True)


@client.tree.command(name="scrim", description="Programa una nueva scrim entre dos equipos")
@app_commands.describe(
    rol1="Rol del primer equipo",
    duracion="Duración estimada de la scrim en MINUTOS (Ej: 40 para BO1, 120 para BO3)",
    rol2="Rol del segundo equipo (Opcional)",
    zona="Zona horaria (Por defecto: Venezuela)"
)
@app_commands.choices(zona=[
    app_commands.Choice(name="🇻🇪 Venezuela (Por defecto)", value="America/Caracas"),
    app_commands.Choice(name="🇨🇴 Colombia", value="America/Bogota"),
    app_commands.Choice(name="🇸🇻 El Salvador", value="America/El_Salvador"),
    app_commands.Choice(name="🇲🇽 México (CDMX)", value="America/Mexico_City"),
    app_commands.Choice(name="🇺🇸 Miami (USA)", value="America/New_York")
])
async def scrim(interaction: discord.Interaction, rol1: discord.Role, duracion: int, rol2: discord.Role = None, zona: app_commands.Choice[str] = None):
    if duracion <= 0:
        await interaction.response.send_message("❌ La duración debe ser mayor a 0 minutos.", ephemeral=True)
        return
        
    tz_seleccionada = zona.value if zona else "America/Caracas"
    await interaction.response.send_modal(ScrimForm(rol1, rol2, tz_seleccionada, duracion))


# ==============================================================================
# 2. MÓDULO ESTILO DYNO (CREADOR DE EMBEDS PERSONALIZADOS)
# ==============================================================================
class EmbedCreadorForm(discord.ui.Modal, title='Crear Mensaje Personalizado'):
    titulo = discord.ui.TextInput(label='Título del Embed', placeholder='Ej: ¡Anuncio Importante!')
    descripcion = discord.ui.TextInput(
        label='Contenido (Soporta Markdown)', 
        placeholder='Escribe el cuerpo del mensaje aquí... Usa **negrita** o saltos de línea.', 
        style=discord.TextStyle.paragraph, 
        max_length=2000
    )
    color_hex = discord.ui.TextInput(label='Color Lateral HEX (Opcional)', placeholder='Ej: #FFC107', required=False, max_length=7)
    imagen_url = discord.ui.TextInput(label='URL de Imagen o Banner (Opcional)', placeholder='https://i.imgur.com/...jpg', required=False)

    def __init__(self, canal: discord.TextChannel):
        super().__init__()
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        color_input = self.color_hex.value.strip()
        color_rgb = discord.Color.from_rgb(0, 150, 255)
        if color_input:
            if not color_input.startswith('#'):
                color_input = f"#{color_input}"
            try:
                color_rgb = discord.Color.from_str(color_input)
            except ValueError:
                pass

        embed = discord.Embed(
            title=self.titulo.value,
            description=self.descripcion.value,
            color=color_rgb
        )
        
        if self.imagen_url.value.strip().startswith('http'):
            embed.set_image(url=self.imagen_url.value.strip())
            
        embed.set_footer(text="Anuncio Oficial del Servidor", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

        try:
            await self.canal.send(embed=embed)
            await interaction.response.send_message(f"✅ Embed enviado correctamente al canal {self.canal.mention}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ No tengo permisos necesarios para escribir en {self.canal.mention}", ephemeral=True)


@client.tree.command(name="embed", description="Envía un embed personalizado al canal de texto que elijas")
@app_commands.describe(canal="El canal de texto a donde se enviará el anuncio")
async def embed_creador(interaction: discord.Interaction, canal: discord.TextChannel):
    if interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_modal(EmbedCreadorForm(canal))
    else:
        await interaction.response.send_message("❌ No tienes el permiso `Gestionar Mensajes` para usar este comando.", ephemeral=True)

                
# ==============================================================================
# ARRANQUE DEL BOT
# ==============================================================================
if __name__ == "__main__":
    token = os.environ.get('DISCORD_TOKEN')
    client.run(token)
