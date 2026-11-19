# Sistema de Automação Residencial IoT com ESP32

Projeto de automação residencial desenvolvido em **MicroPython** utilizando o microcontrolador **ESP32** no simulador **Wokwi (VS Code)**, com comunicação bidirecional via **MQTT (HiveMQ)**, dashboard em **Node-RED**, página web embarcada no ESP32, registro histórico no **Google Sheets** e alertas por e-mail via **SMTP Gmail**.

## Componentes e Pinagem Planejada

| Tipo | Componente | Pino ESP32 | Função |
| :--- | :--- | :---: | :--- |
| Sensor | DHT22 | GPIO 15 | Temperatura e umidade |
| Sensor | LDR | GPIO 34 | Luminosidade externa |
| Sensor | MQ-2 | GPIO 35 | Detecção de gás / fumaça |
| Sensor | PIR | GPIO 32 | Detecção de presença / movimento |
| Atuador | LED Amarelo (PWM) | GPIO 26 | Iluminação da sala (0% a 100%) |
| Atuador | Módulo Relé | GPIO 25 | Acionamento do ar-condicionado |
| Atuador | Servo Motor | GPIO 14 | Abertura/fechamento do portão (0° a 180°) |
| Atuador | Buzzer | GPIO 12 | Sirene de alerta |
| Display | OLED SSD1306 (I2C) | SDA 21 / SCL 22 | Painel local de status e alertas |

## Como Configurar
1. Copie o arquivo `secrets_exemplo.py` para `secrets.py` e preencha suas credenciais.
2. Abra o projeto no VS Code com as extensões **Wokwi Simulator** e **PyMakr**.