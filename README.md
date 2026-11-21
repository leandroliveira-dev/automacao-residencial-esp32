# 🏠 Sistema de Automação Residencial IoT com ESP32

Projeto acadêmico de automação residencial desenvolvido com **ESP32 e MicroPython**, utilizando o simulador **Wokwi**.

O sistema monitora o ambiente por meio de sensores, controla dispositivos eletrônicos e permite o acompanhamento e gerenciamento remoto através de uma página web e de um dashboard Node-RED, utilizando comunicação MQTT.

## 🧰 Tecnologias utilizadas

- ESP32 e MicroPython
- Wokwi e Visual Studio Code
- MQTT (HiveMQ)
- Node-RED
- HTML
- Google Sheets e Google Apps Script

## 🔌 Componentes e pinagem

| Tipo | Componente | GPIO | Função |
|---|---|---:|---|
| Sensor | DHT22 | 15 | Temperatura e umidade |
| Sensor | LDR | 34 | Luminosidade |
| Sensor | MQ-2 | 35 | Detecção de gás e fumaça |
| Sensor | PIR | 32 | Detecção de movimento |
| Atuador | LED amarelo | 26 | Iluminação |
| Atuador | Relé | 25 | Acionamento de dispositivo |
| Atuador | Servo motor | 14 | Controle do portão |
| Atuador | Buzzer | 12 | Alertas sonoros |
| Display | OLED SSD1306 | SDA 21 / SCL 22 | Exibição de informações |

## ⚙️ Funcionalidades

- Monitoramento de temperatura, umidade, luminosidade, gás e movimento.
- Controle individual de LED, relé, servo motor e buzzer.
- Modo automático baseado nas leituras dos sensores.
- Página web hospedada no ESP32.
- Comunicação MQTT bidirecional.
- Dashboard de monitoramento e controle no Node-RED.
- Exibição de informações em display OLED.
- Registro periódico de dados no Google Sheets.
- Alertas por e-mail via Google Apps Script.

## 📡 Comunicação e automação

O ESP32 atua como unidade central, recebendo dados dos sensores e controlando os atuadores.

A comunicação MQTT utiliza o broker HiveMQ para publicar informações de status, enviar alertas e receber comandos do Node-RED.

O sistema também permite controle pela página web, enquanto a integração com Google Sheets possibilita armazenar o histórico das leituras.

## 📁 Estrutura do projeto

```text
automacao-residencial-esp32/
├── main.py
├── index.html
├── ssd1306.py
├── secrets_exemplo.py
├── upload.sh
├── firmware.bin
├── diagram.json
├── wokwi.toml
├── README.md
└── .gitignore
```

O arquivo `secrets.py` contém as credenciais locais e não é enviado ao repositório.

## 🚀 Como executar

**1.** Clone o repositório:

```bash
git clone URL_DO_REPOSITORIO
cd automacao-residencial-esp32
```

**2.** Crie e ative o ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3.** Instale o mpremote:

```bash
pip install mpremote
```

**4.** Configure as credenciais:

```bash
cp secrets_exemplo.py secrets.py
```

Edite `secrets.py` com as configurações necessárias.

**5.** Abra o projeto no VS Code e inicie a simulação pelo Wokwi.

**6.** Com a simulação em execução, envie os arquivos ao ESP32:

```bash
./upload.sh
```

**7.** Acesse a página web:

```text
http://localhost:8180
```

Configure o Node-RED, o broker MQTT e a integração com Google Sheets conforme os parâmetros definidos no projeto.

**Observação:** após reiniciar a simulação do Wokwi, pode ser necessário enviar novamente os arquivos ao ESP32.

--------------------
Projeto acadêmico desenvolvido para aplicação prática de conceitos de **Internet das Coisas (IoT)**.

**Desenvolvido com ESP32 e MicroPython.**