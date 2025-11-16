#!/bin/sh
set -e

echo "Waiting for MQTT broker to be ready..."
sleep 5

echo "Starting MQTT to FCM Push service..."
exec python main.py
