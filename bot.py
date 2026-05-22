import discord
from discord import app_commands
from datetime import datetime
import pytz

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

# Formulario Emergente (Ahora ya no pide la división, porque se seleccionó antes)
class ScrimForm(discord.ui.Modal, title='Programar Nueva Scrim'):
    rival = discord.ui.TextInput(label='Rival', placeholder='Ej: Levi Team')
    detalles = discord.ui.TextInput(label='Detalles', placeholder='Ej: Scrim nocturna', default='Scrim nocturna')
    fecha_hora = discord.ui.TextInput(label='Fecha y Hora (Día-Mes Hora:Min)', placeholder='Ej: 21-05 22:00')
    pais = discord.ui.TextInput(label='Tu País (SV, VE o COL)', placeholder='SV / VE / COL', max_length=3)

    # Le pasamos el rol seleccionado al formulario al crearlo
    def __init__(self, rol: discord.Role):
        super().__init__()
        self.rol = rol

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Validar estrictamente la zona horaria
        pais_input = self.pais.value.upper().strip()
        if pais_input == 'SV':
            tz = pytz.timezone('America/El_Salvador')
        elif pais_input == 'VE':
            tz = pytz.timezone('America/Caracas')
        elif pais_input == 'COL':
            tz = pytz.timezone('America/Bogota')
        else:
            await interaction.response.send_message(
                "❌ **País no válido.** Usa: `SV`, `VE` o `COL`.", 
                ephemeral=True
            )
            return

        try:
            # 2. Procesar la fecha con el año actual automático
            año_actual = datetime.now().year
            fecha_completa = f"{self.fecha_hora.value.strip()}-{año_actual}"
            
            local_dt = datetime.strptime(fecha_completa, '%d-%m %H:%M-%Y')
            local_dt = tz.localize(local_dt)
            
            timestamp = int(local_dt.timestamp())
            timestamp_fin = timestamp + 7200

            # 3. Diseñar el Embed (El título ahora usa el nombre real del rol seleccionado)
            embed = discord.Embed(
                title=f"🎮 {self.rol.name} vs {self.rival.value}",
                color=discord.Color.from_rgb(255, 193, 7)
            )
            embed.description = f"**Detalles:** {self.detalles.value}\n\n" \
                                f"📅 **Horario Local:** <t:{timestamp}:F> — <t:{timestamp_fin}:t>\n" \
                                f"⏰ **Comienza:** <t:{timestamp}:R>\n\n" \
                                f"📢 *Reaccionen para confirmar asistencia.*"
            
            # 4. Enviar la mención del rol seleccionado y el embed
            await interaction.response.send_message(content=self.rol.mention, embed=embed)
            mensaje = await interaction.original_response()
            
            await mensaje.add_reaction('✅')
            await mensaje.add_reaction('❌')
            await mensaje.add_reaction('❓')

        except ValueError:
            await interaction.response.send_message("❌ Formato de fecha incorrecto. Usa: Día-Mes Hora:Min (Ej: 21-05 22:00)", ephemeral=True)

# El comando ahora OBLIGA a elegir un rol del servidor al escribir /scrim
@client.tree.command(name="scrim", description="Programa una scrim seleccionando el rol del equipo")
@app_commands.describe(rol="El rol del equipo al que vas a pingear (Ej: @Div1)")
async def scrim(interaction: discord.Interaction, rol: discord.Role):
    # Le mandamos el rol al formulario
    await interaction.response.send_modal(ScrimForm(rol))

client.run('MTUwNzIwMjM0MjAyMDMyMTMwMA.G4LAKL.PdYR4NnXJOIi2cXyT24WvmVhlLY5YxX6-9jCXM')