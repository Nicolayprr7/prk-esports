import discord
from discord import app_commands
from datetime import datetime
import pytz
import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- TRUCO PARA HOSTING GRATUITO (Servidor Web para Render Free) ---
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Team Spirit Bot Is Running")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()
# ------------------------------------------------------------------

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
# 1. MÓDULO DE SCRIMS (FORMULARIO + COMANDO)
# ==============================================================================
class ScrimForm(discord.ui.Modal, title='Programar Nueva Scrim'):
    rival = discord.ui.TextInput(label='Rival', placeholder='Ej: Levi Team')
    detalles = discord.ui.TextInput(label='Detalles', placeholder='Ej: Scrim nocturna', default='Scrim nocturna')
    fecha_hora = discord.ui.TextInput(label='Fecha y Hora (Día-Mes HORA:MIN en 24h)', placeholder='Ej: 21-05 22:00 (No uses AM/PM)')
    pais = discord.ui.TextInput(label='Tu País (SV, VE o COL)', placeholder='SV / VE / COL', max_length=3)

    def __init__(self, rol: discord.Role):
        super().__init__()
        self.rol = rol

    async def on_submit(self, interaction: discord.Interaction):
        pais_input = self.pais.value.upper().strip()
        if pais_input == 'SV':
            tz = pytz.timezone('America/El_Salvador')
        elif pais_input == 'VE':
            tz = pytz.timezone('America/Caracas')
        elif pais_input == 'COL':
            tz = pytz.timezone('America/Bogota')
        else:
            await interaction.response.send_message("❌ **País no válido.** Usa exactamente: `SV`, `VE` o `COL`.", ephemeral=True)
            return

        try:
            año_actual = datetime.now().year
            fecha_completa = f"{self.fecha_hora.value.strip()}-{año_actual}"
            
            local_dt = datetime.strptime(fecha_completa, '%d-%m %H:%M-%Y')
            local_dt = tz.localize(local_dt)
            
            ahora_en_tz = datetime.now(tz)
            if local_dt <= ahora_en_tz:
                await interaction.response.send_message("❌ **Fecha inválida.** No puedes programar una scrim para el pasado. Pon una hora futura.", ephemeral=True)
                return

            timestamp = int(local_dt.timestamp())
            timestamp_fin = timestamp + 7200

            embed = discord.Embed(
                title=f"🎮 {self.rol.name} vs {self.rival.value}",
                color=discord.Color.from_rgb(255, 193, 7) # Dorado Team Spirit
            )
            embed.description = f"**Detalles:** {self.detalles.value}\n\n" \
                                f"📅 **Fecha:** <t:{timestamp}:D>\n" \
                                f"⏰ **Horario Local:** <t:{timestamp}:t> hs — Fin: <t:{timestamp_fin}:t> hs\n" \
                                f"⏳ **Comienza:** <t:{timestamp}:R>\n\n" \
                                f"📢 *Reaccionen para confirmar asistencia.*"
            
            await interaction.response.send_message(content=self.rol.mention, embed=embed)
            mensaje = await interaction.original_response()
            
            await mensaje.add_reaction('✅')
            await mensaje.add_reaction('❌')
            await mensaje.add_reaction('❓')

        except ValueError:
            await interaction.response.send_message("❌ Formato incorrecto. Usa: Día-Mes Hora:Min en formato 24h (Ej: 21-05 22:00)", ephemeral=True)


@client.tree.command(name="scrim", description="Programa una scrim seleccionando el rol del equipo")
@app_commands.describe(rol="El rol del equipo al que vas a hacer ping (Ej: @Div1)")
async def scrim(interaction: discord.Interaction, rol: discord.Role):
    await interaction.response.send_modal(ScrimForm(rol))


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
        # Configurar color (Dorado por defecto si no ponen nada o ponen algo mal)
        color_input = self.color_hex.value.strip()
        color_rgb = discord.Color.from_rgb(255, 193, 7)
        if color_input:
            if not color_input.startswith('#'):
                color_input = f"#{color_input}"
            try:
                color_rgb = discord.Color.from_str(color_input)
            except ValueError:
                pass

        # Construir el Embed personalizado
        embed = discord.Embed(
            title=self.titulo.value,
            description=self.descripcion.value,
            color=color_rgb
        )
        
        # Añadir imagen si es un enlace válido
        if self.imagen_url.value.strip().startswith('http'):
            embed.set_image(url=self.imagen_url.value.strip())
            
        embed.set_footer(text="Anuncio oficial de Team Spirit", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

        # Intentar enviar al canal especificado anteriormente
        try:
            await self.canal.send(embed=embed)
            await interaction.response.send_message(f"✅ Embed enviado correctamente al canal {self.canal.mention}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ No tengo permisos necesarios para escribir en {self.canal.mention}", ephemeral=True)


@client.tree.command(name="embed", description="Envía un embed personalizado al canal de texto que elijas")
@app_commands.describe(canal="El canal de texto a donde se enviará el anuncio")
async def embed_creador(interaction: discord.Interaction, canal: discord.TextChannel):
    # Permiso de seguridad para que solo los moderadores/admin usen el comando
    if interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_modal(EmbedCreadorForm(canal))
    else:
        await interaction.response.send_message("❌ No tienes el permiso `Gestionar Mensajes` para usar este comando.", ephemeral=True)


# ==============================================================================
# ARRANQUE DEL BOT
# ==============================================================================
if __name__ == "__main__":
    Thread(target=run_web_server, daemon=True).start()
    
    # Recuerda configurar tu Token real en la variable o dejarlo aquí abajo pegado
    token = os.environ.get('DISCORD_TOKEN', 'MTUwNzIwMjM0MjAyMDMyMTMwMA.G4LAKL.PdYR4NnXJOIi2cXyT24WvmVhlLY5YxX6-9jCXM')
    client.run(token)
