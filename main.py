# main.py - Casa inteligente (ESP32 + MicroPython, simulado no Wokwi)
#
# Sensores : DHT22 (temperatura/umidade), LDR (luz), MQ-2 (gas), PIR (movimento)
# Atuadores: LED (iluminacao), rele (exaustor), servo (portao), buzzer (sirene)
# Saidas   : OLED, MQTT (HiveMQ), pagina web embarcada, Google Sheets + e-mail
#
# Topicos MQTT (PREFIXO vem do secrets.py):
#   PREFIXO/status        -> ESP32 publica o estado completo (JSON) a cada 2 s
#   PREFIXO/alerta        -> ESP32 publica quando um alerta dispara (JSON)
#   PREFIXO/cmd/led       -> comando para o LED     ("1" liga, "0" desliga)
#   PREFIXO/cmd/rele      -> comando para o rele    ("1" / "0")
#   PREFIXO/cmd/buzzer    -> comando para o buzzer  ("1" / "0")
#   PREFIXO/cmd/servo     -> angulo do servo        ("0" a "180")
#   PREFIXO/cmd/auto      -> modo automatico        ("1" / "0")

import gc
import network
import socket
import time
import ujson
import dht
import ssd1306
import secrets
from machine import Pin, ADC, PWM, I2C

try:
    import urequests as requests
except ImportError:
    requests = None

try:
    from umqtt.simple import MQTTClient
except ImportError:
    MQTTClient = None

# configuracao
WIFI_SSID = getattr(secrets, "WIFI_SSID", "Wokwi-GUEST")
WIFI_PASS = getattr(secrets, "WIFI_PASS", "")
GOOGLE_SHEETS_URL = getattr(secrets, "GOOGLE_SHEETS_URL", "")
INTERVALO_SHEETS_MS = getattr(secrets, "INTERVALO_SHEETS_MIN", 120) * 60 * 1000

MQTT_BROKER = getattr(secrets, "MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = getattr(secrets, "MQTT_PORT", 1883)
MQTT_CLIENT_ID = getattr(secrets, "MQTT_CLIENT_ID", "esp32-leandro-casa-01")
PREFIXO = getattr(secrets, "MQTT_PREFIXO", "leandro-oliveira/casa")

TOPIC_STATUS = (PREFIXO + "/status").encode()
TOPIC_ALERTA = (PREFIXO + "/alerta").encode()
TOPIC_CMD = (PREFIXO + "/cmd/#").encode()

GAS_ALERTA = 60          # % de gas acima do qual dispara alerta
TEMP_ALERTA = 35         # graus C acima dos quais dispara alerta
TEMP_VENTILACAO = 30     # graus C para ligar o exaustor no modo automatico
LUZ_ESCURO = 30          # % de luz abaixo do qual o LED acende no automatico

INTERVALO_CICLO_MS = 2000
REENVIO_ALERTA_MS = 300000   # enquanto o alerta durar, avisa de novo a cada 5 min

# hardware
sensor_dht = dht.DHT22(Pin(15))

adc_ldr = ADC(Pin(34))
adc_ldr.atten(ADC.ATTN_11DB)

adc_gas = ADC(Pin(35))
adc_gas.atten(ADC.ATTN_11DB)

sensor_pir = Pin(32, Pin.IN)

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)

led = Pin(26, Pin.OUT, value=0)
rele = Pin(25, Pin.OUT, value=0)
servo = PWM(Pin(14), freq=50)
buzzer = PWM(Pin(12), freq=2000, duty=0)

# estado
estado = {
    "temp": 0.0,
    "umid": 0.0,
    "luz": 0,
    "gas": 0,
    "pir": 0,
    "auto": 1,
    "led": 0,
    "rele": 0,
    "servo": 0,       # angulo de 0 a 180
    "buzzer": 0,
    "alerta": "",     # "", "GAS", "TEMP" ou "GAS+TEMP"
}

ip_atual = "Sem WiFi"
mqtt_client = None
ultima_tentativa_mqtt = 0
precisa_publicar = False
servidor = None
alerta_anterior = ""
ultimo_alerta_ms = 0


# atuadores
def aplicar_atuadores():
    led.value(estado["led"])
    rele.value(estado["rele"])
    servo.duty(26 + estado["servo"] * 102 // 180)   # 0.5 ms a 2.5 ms
    buzzer.duty(128 if estado["buzzer"] else 0)


def para_int(texto):
    t = texto.strip().lower()
    if t in ("on", "true"):
        return 1
    if t in ("off", "false"):
        return 0
    return int(float(t))


def aplicar_comando(dev, val):
    """Usado pelo MQTT e pela pagina web. Retorna False se o dispositivo for invalido."""
    global precisa_publicar
    if dev == "auto":
        estado["auto"] = 1 if val else 0
        executar_automacao()
    elif dev in ("led", "rele", "buzzer"):
        estado["auto"] = 0                 # comando manual desliga o automatico
        estado[dev] = 1 if val else 0
    elif dev == "servo":
        estado["servo"] = max(0, min(180, val))
    else:
        return False
    aplicar_atuadores()
    atualizar_oled()
    precisa_publicar = True
    return True


# WiFi
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        oled.fill(0)
        oled.text("Conectando WiFi", 0, 10)
        oled.text(WIFI_SSID[:16], 0, 26)
        oled.show()
        wlan.connect(WIFI_SSID, WIFI_PASS)
        tentativas = 0
        while not wlan.isconnected() and tentativas < 20:
            time.sleep(0.5)
            tentativas += 1
    ip = wlan.ifconfig()[0] if wlan.isconnected() else "Sem WiFi"
    print("WiFi:", ip)
    return ip


# MQTT
def ao_receber_mqtt(topic, msg):
    try:
        dev = topic.decode().split("/")[-1]
        if aplicar_comando(dev, para_int(msg.decode())):
            print("MQTT cmd:", dev, msg)
        else:
            print("MQTT ignorado:", topic)
    except Exception as e:
        print("Erro ao processar MQTT:", e)


def conectar_mqtt():
    global mqtt_client
    if MQTTClient is None:
        print("umqtt.simple nao disponivel neste firmware")
        return
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
        client.set_callback(ao_receber_mqtt)
        client.connect()
        client.subscribe(TOPIC_CMD)
        mqtt_client = client
        print("MQTT conectado em", MQTT_BROKER, "| ouvindo", TOPIC_CMD)
    except Exception as e:
        print("Falha ao conectar MQTT:", e)
        mqtt_client = None


def garantir_mqtt():
    """Tenta reconectar no maximo a cada 10 s para nao travar o laco principal."""
    global ultima_tentativa_mqtt
    if mqtt_client is not None:
        return
    agora = time.ticks_ms()
    if time.ticks_diff(agora, ultima_tentativa_mqtt) < 10000:
        return
    ultima_tentativa_mqtt = agora
    conectar_mqtt()


def checar_mqtt():
    global mqtt_client
    if mqtt_client is None:
        return
    try:
        mqtt_client.check_msg()
    except Exception as e:
        print("MQTT caiu:", e)
        mqtt_client = None


def publicar_status():
    global mqtt_client
    if mqtt_client is None:
        return
    try:
        mqtt_client.publish(TOPIC_STATUS, ujson.dumps(estado).encode())
    except Exception as e:
        print("Erro publicando status:", e)
        mqtt_client = None


# sensores
def ler_sensores():
    try:
        sensor_dht.measure()
        estado["temp"] = sensor_dht.temperature()
        estado["umid"] = sensor_dht.humidity()
    except OSError:
        pass

    raw_ldr = adc_ldr.read()
    estado["luz"] = max(0, min(100, int((4095 - raw_ldr) * 100 / 4095)))

    raw_gas = adc_gas.read()
    estado["gas"] = max(0, min(100, int(raw_gas * 100 / 4095)))

    estado["pir"] = sensor_pir.value()


# alertas e automacao
def calcular_alerta():
    """O alerta e calculado sempre, independente do modo automatico/manual."""
    tipos = []
    if estado["gas"] > GAS_ALERTA:
        tipos.append("GAS")
    if estado["temp"] > TEMP_ALERTA:
        tipos.append("TEMP")
    estado["alerta"] = "+".join(tipos)


def executar_automacao():
    if not estado["auto"]:
        return
    estado["led"] = 1 if (estado["luz"] < LUZ_ESCURO or estado["pir"] == 1) else 0
    estado["rele"] = 1 if (estado["temp"] > TEMP_VENTILACAO or estado["gas"] > GAS_ALERTA) else 0
    estado["buzzer"] = 1 if estado["alerta"] else 0


def enviar_sheets(tipo):
    """tipo = 'leitura' (a cada INTERVALO_SHEETS_MS) ou 'alerta' (no momento do alerta).
    O Apps Script grava a linha na aba certa e, se for alerta, envia o e-mail."""
    if not GOOGLE_SHEETS_URL or requests is None:
        return
    gc.collect()
    try:
        dados = dict(estado)
        dados["tipo"] = tipo
        res = requests.post(
            GOOGLE_SHEETS_URL,
            data=ujson.dumps(dados).encode(),
            headers={"Content-Type": "application/json"},
        )
        print("Sheets (" + tipo + ") HTTP:", res.status_code)   # 200 ou 302 = ok
        res.close()
    except Exception as e:
        print("Erro Sheets:", e)
    finally:
        gc.collect()


def notificar_alerta(alerta):
    global mqtt_client
    print("ALERTA:", alerta)
    if mqtt_client is not None:
        try:
            dados = {"alerta": alerta, "gas": estado["gas"], "temp": estado["temp"]}
            mqtt_client.publish(TOPIC_ALERTA, ujson.dumps(dados).encode())
        except Exception as e:
            print("Erro publicando alerta:", e)
            mqtt_client = None
    enviar_sheets("alerta")


def processar_notificacao():
    """Dispara quando um alerta novo aparece e repete a cada REENVIO_ALERTA_MS."""
    global alerta_anterior, ultimo_alerta_ms
    alerta = estado["alerta"]
    agora = time.ticks_ms()
    if alerta:
        novo = alerta != alerta_anterior
        if novo or time.ticks_diff(agora, ultimo_alerta_ms) >= REENVIO_ALERTA_MS:
            ultimo_alerta_ms = agora
            notificar_alerta(alerta)
    alerta_anterior = alerta


# OLED
def atualizar_oled():
    e = estado
    oled.fill(0)
    oled.text("IP:" + ip_atual, 0, 0)
    oled.text("Sala Luz{}% L{}".format(e["luz"], e["led"]), 0, 8)
    oled.text("Coz. Gas{}% R{}".format(e["gas"], e["rele"]), 0, 16)
    oled.text("Quarto {:.0f}C {:.0f}%".format(e["temp"], e["umid"]), 0, 24)
    oled.text("Gar. PIR{} Pt{}".format(e["pir"], e["servo"]), 0, 32)
    oled.text("Bz:{} Modo:{}".format(e["buzzer"], "AUTO" if e["auto"] else "MANUAL"), 0, 40)
    oled.text("ALERTAS:", 0, 48)
    oled.text("!! " + e["alerta"] if e["alerta"] else "Nenhum", 0, 56)
    oled.show()


# pagina web
def iniciar_servidor():
    global servidor
    try:
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", 80))
        s.listen(2)
        s.setblocking(False)
        servidor = s
        print("Pagina web: http://localhost:8180 (Wokwi) ou http://" + ip_atual)
    except Exception as e:
        print("Falha ao iniciar servidor web:", e)
        servidor = None


def parse_query(query):
    params = {}
    for par in query.split("&"):
        if "=" in par:
            chave, valor = par.split("=", 1)
            params[chave] = valor
    return params


def enviar_json(cl, obj):
    cl.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
             b"Cache-Control: no-store\r\nConnection: close\r\n\r\n")
    cl.write(ujson.dumps(obj).encode())


def enviar_pagina(cl):
    try:
        f = open("index.html", "rb")
    except OSError:
        cl.write(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\nindex.html nao encontrado")
        return
    cl.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n")
    while True:
        bloco = f.read(512)
        if not bloco:
            break
        cl.write(bloco)
    f.close()


def atender_http():
    """Atende no maximo uma conexao por chamada, sem bloquear o laco principal."""
    if servidor is None:
        return
    try:
        cl, _ = servidor.accept()
    except OSError:
        return
    try:
        cl.settimeout(2)
        req = cl.recv(1024)
        if not req:
            return
        partes = req.split(b"\r\n", 1)[0].decode().split(" ")
        caminho = partes[1] if len(partes) > 1 else "/"
        rota, _, query = caminho.partition("?")

        if rota == "/":
            enviar_pagina(cl)
        elif rota == "/api/estado":
            enviar_json(cl, estado)
        elif rota == "/api/cmd":
            p = parse_query(query)
            try:
                ok = aplicar_comando(p.get("dev", ""), para_int(p.get("val", "0")))
            except Exception as e:
                print("Erro cmd web:", e)
                ok = False
            if ok:
                enviar_json(cl, estado)
            else:
                cl.write(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\ncomando invalido")
        else:
            cl.write(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
    except Exception as e:
        print("Erro HTTP:", e)
    finally:
        cl.close()


# inicializacao
aplicar_atuadores()
ip_atual = conectar_wifi()
iniciar_servidor()
conectar_mqtt()
ultima_tentativa_mqtt = time.ticks_ms()

ultimo_ciclo = time.ticks_add(time.ticks_ms(), -INTERVALO_CICLO_MS)   # roda um ciclo ja na partida
ultimo_sheets = time.ticks_ms()

while True:
    agora = time.ticks_ms()

    checar_mqtt()
    atender_http()

    if precisa_publicar:
        precisa_publicar = False
        publicar_status()

    if time.ticks_diff(agora, ultimo_ciclo) >= INTERVALO_CICLO_MS:
        ultimo_ciclo = agora
        ler_sensores()
        calcular_alerta()
        executar_automacao()
        aplicar_atuadores()
        atualizar_oled()
        garantir_mqtt()
        publicar_status()
        processar_notificacao()   # por ultimo: a chamada HTTPS pode demorar alguns segundos
        gc.collect()

    if GOOGLE_SHEETS_URL and time.ticks_diff(agora, ultimo_sheets) >= INTERVALO_SHEETS_MS:
        ultimo_sheets = agora
        enviar_sheets("leitura")

    time.sleep_ms(50)