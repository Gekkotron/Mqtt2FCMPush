#!/bin/sh

echo "Waiting for MQTT broker to be ready..."
sleep 5

echo "Starting MQTT to FCM Push service with auto-restart..."

# Run with auto-restart on crash
while true; do
    echo "[$(date)] Starting service..."
    python main.py
    EXIT_CODE=$?
    
    # Exit gracefully on SIGINT/SIGTERM (exit codes 0, 130, 143)
    if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 130 ] || [ $EXIT_CODE -eq 143 ]; then
        echo "[$(date)] Service stopped gracefully"
        exit 0
    fi
    
    # Otherwise restart after delay
    echo "[$(date)] Service crashed with exit code $EXIT_CODE. Restarting in 5 seconds..."
    sleep 5
done
