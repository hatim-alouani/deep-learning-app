#!/bin/bash

echo "[+] Starting insert loop..."
while true
do
    echo "[*] Running insert.py..."
    python3 /flask/insertData/insert.py
    echo "[✔] Waiting 30 seconds..."
    sleep 30
done
