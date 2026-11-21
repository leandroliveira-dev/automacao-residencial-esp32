#!/usr/bin/env bash
set -e

PORT="rfc2217://localhost:4000"

echo "Enviando arquivos para o ESP32..."

python -m mpremote connect "port:$PORT" fs cp ssd1306.py :ssd1306.py
python -m mpremote connect "port:$PORT" fs cp secrets.py :secrets.py
python -m mpremote connect "port:$PORT" fs cp index.html :index.html
python -m mpremote connect "port:$PORT" fs cp main.py :main.py

echo "Reiniciando ESP32..."
python -m mpremote connect "port:$PORT" reset

echo "Envio concluído!"
