import discord
from discord import app_commands
from datetime import datetime
import pytz
import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- TRUCO PARA HOSTING GRATUITO (Mantiene el bot vivo en Render Free) ---
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot Online")

def run_web_server():
    # Render asigna un puerto automático en la variable PORT, si no usa el 8080
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()
# ------------------------------------------------------------------------

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
            print(f"Comandos sincronizados: {len(synced)}")
        except Exception as e:
            print(e)

client = MyClient()

# Formulario Emergente
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
            await interaction.response.send_message("❌ **País no válido.** Usa: `SV`, `VE` o `COL`.", ephemeral=True)
            return

        try:
            año_actual = datetime.now().year
            fecha_completa = f"{self.fecha_hora.value.strip()}-{año_actual}"
            
            local_dt = datetime.strptime(fecha_completa, '%d-%m %H:%M-%Y')
            local_dt = tz.localize(local_dt)
            
            ahora_en_tz = datetime.now(tz)
            if local_dt <= ahora_en_tz:
                await interaction.response.send_message("❌ **Fecha inválida.** No puedes programar una scrim para el pasado.", ephemeral=True)
                return

            timestamp = int(local_dt.timestamp())
            timestamp_fin = timestamp + 7200
            
# 4. Diseñar el Embed (Corregido para formato 24h nativo de Discord)
            embed = discord.Embed(
                title=f"🎮 {self.rol.name} vs {self.rival.value}",
                color=discord.Color.from_rgb(255, 193, 7)
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
@app_commands.describe(rol="El rol del equipo al que vas a pingear (Ej: @Div1)")
async def scrim(interaction: discord.Interaction, rol: discord.Role):
    await interaction.response.send_modal(ScrimForm(rol))

# Al arrancar, encendemos el servidor web falso en paralelo y luego el bot
if __name__ == "__main__":
    Thread(target=run_web_server, daemon=True).start()
    
    # Intenta leer desde las variables ocultas de Render, si no usa un texto vacío por seguridad
    token = os.environ.get('DISCORD_TOKEN', 'MTUwNzIwMjM0MjAyMDMyMTMwMA.G4LAKL.PdYR4NnXJOIi2cXyT24WvmVhlLY5YxX6-9jCXM')
    client.run(token)