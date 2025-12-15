"""
Configuration file for MQTT to FCM Push service.
Update these values according to your environment.
Environment variables take precedence over default values.
"""
import os

# MQTT Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "notification/#")
MQTT_USERNAME = os.getenv("MQTT_USERNAME") or None
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD") or None

# Firebase Configuration
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "credential.json")

# Firestore Configuration
# Set to False to only use tokens from MQTT payload
USE_FIRESTORE = os.getenv("USE_FIRESTORE", "True").lower() in (
    "true", "1", "yes"
)
FIRESTORE_COLLECTION = os.getenv("FIRESTORE_COLLECTION", "notification")
# Set to True to send notifications only to admin users
ADMIN_ONLY = os.getenv("ADMIN_ONLY", "True").lower() in (
    "true", "1", "yes"
)

# Notification Configuration
DEFAULT_PRIORITY = os.getenv("DEFAULT_PRIORITY", "high")
DEFAULT_TTL = int(os.getenv("DEFAULT_TTL", "43200"))

# Retry Configuration
RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL", "60"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "10"))

# Heartbeat Configuration
HEARTBEAT_ENABLED = os.getenv("HEARTBEAT_ENABLED", "True").lower() in (
    "true", "1", "yes"
)
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "60"))
HEARTBEAT_TOPIC = os.getenv("HEARTBEAT_TOPIC", "notification/heartbeat")
