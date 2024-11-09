import machine
import uasyncio as asyncio
import network
import socket
import time
import dht

# Configuración Wi-Fi
SSID = "******" #nombre de la red
PASSWORD = "*******" #Contraseña de la red

# Conexión Wi-Fi
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        pass
    print('Conectado a Wi-Fi:', wlan.ifconfig())

# Configuración del Sensor MQ-2
sensor = machine.ADC(machine.Pin(26))  # GP26 (ADC0)

# Configuración del Sensor DHT11
dht_sensor = dht.DHT11(machine.Pin(15))  # Pin GPIO15 para DHT11

#Configuracion de LED's
led_rojo = machine.Pin(17, machine.Pin.OUT)  # LED rojo en GP16
led_verde = machine.Pin(16, machine.Pin.OUT)  # LED verde en GP17

# Función para leer el valor del sensor MQ-2
def leer_gas():
    lectura = sensor.read_u16()  # Leer el valor ADC
    # Escalar el valor de 0-65535 a un rango de 0-1023
    return int((lectura/65535)*100)   # Valor de 0 a 1023

# Función para leer los valores de temperatura y humedad del DHT11
def leer_dht():
    try:
        dht_sensor.measure()
        temperatura = dht_sensor.temperature()  # Temperatura en °C
        humedad = dht_sensor.humidity()  # Humedad en %
        return temperatura, humedad
    except OSError as e:
        print("Error al leer el sensor DHT11:", e)
        return None, None

# Función para controlar los LEDs
def controlar_leds(gas):
    if gas >= 70:
        led_rojo.on()  # Enciende el LED rojo
        led_verde.off()  # Apaga el LED verde
    else:
        led_rojo.off()  # Apaga el LED rojo
        led_verde.on()  # Enciende el LED verde


# Listas para almacenar los datos históricos
historico_gas = []
historico_temperatura = []
historico_humedad = []

# Servidor Web
async def servidor_web():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print('Escuchando en', addr)

    while True:
        cl, addr = s.accept()
        print('Cliente conectado desde', addr)
        request = cl.recv(1024)
        request = str(request)
        print("Request:", request)

        # Leer datos del sensor MQ-2 y DHT11
        gas = leer_gas()
        controlar_leds(gas)
        temperatura, humedad = leer_dht()

        # Agregar los datos al histórico
        historico_gas.append(gas)
        historico_temperatura.append(temperatura)
        historico_humedad.append(humedad)

        # Limitar los datos a los últimos 50
        if len(historico_gas) > 50:
            historico_gas.pop(0)
            historico_temperatura.pop(0)
            historico_humedad.pop(0)

        # Crear respuesta HTML
        html = """
        <html>
            <head>
                <title>Monitor de calidad ambiental</title>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <meta http-equiv="refresh" content="2">
            </head>
            <body>
                <h1>Lectura de Gases Peligrosos</h1>
                <p>Ultimas lecturas</p>
                <p>Gases """ + str(gas) + """ %</p>
                <p>Temperatura: """ + str(temperatura) + """C</p>
                <p>Humedad: """ + str(humedad) + """ %</p>
                <canvas id="graficaG" width="200" height="100"></canvas>
                <canvas id="graficaT" width="200" height="100"></canvas>
                <canvas id="graficaH" width="200" height="100"></canvas>
                <script>
                    var ctx = document.getElementById('graficaG').getContext('2d');
                    var chart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: """ + str(list(range(len(historico_gas)))) + """,
                            datasets: [{
                                label: 'Concentracion de Gas',
                                data: """ + str(historico_gas) + """,
                                borderColor: 'rgb(75, 192, 192)',
                                tension: 0.1
                            }]
                        }
                    });
                </script>
                
                <script>
                    var ctx = document.getElementById('graficaT').getContext('2d');
                    var chart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: """ + str(list(range(len(historico_gas)))) + """,
                            datasets: [{
                                label: 'Temperatura (C)',
                                data: """ + str(historico_temperatura) + """,
                                borderColor: 'rgb(255, 99, 132)',
                                tension: 0.1
                            }]
                        }
                    });
                </script>
                <script>
                    var ctx = document.getElementById('graficaH').getContext('2d');
                    var chart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: """ + str(list(range(len(historico_gas)))) + """,
                            datasets: [{
                                label: 'Humedad (%)',
                                data: """ + str(historico_humedad) + """,
                                borderColor: 'rgb(153, 102, 255)',
                                tension: 0.1
                            }]
                        }
                    });
                </script>
            </body>
        </html>
        """

        # Enviar respuesta al cliente
        cl.send('HTTP/1.1 200 OK\r\n')
        cl.send('Content-Type: text/html\r\n')
        cl.send('Connection: close\r\n\r\n')
        cl.send(html)
        cl.close()

# Función principal para ejecutar el servidor y la conexión Wi-Fi
async def main():
    conectar_wifi()
    await asyncio.gather(servidor_web())

# Ejecutar la función principal
asyncio.run(main())
