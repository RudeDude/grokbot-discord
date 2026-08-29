#!/bin/sh
DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
cd "$DIR"
PYTHON="${DIR}/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi
while true; do
  "$PYTHON" -m grokbot_discord >> "$DIR/bridge.log" 2>&1
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) grokbot_discord exited $?, restart in 3s" >> "$DIR/bridge.log"
  sleep 3
done
