"""
Configuration file for MQTT to FCM Push service.
Update these values according to your environment.
"""

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "notification/#"
MQTT_USERNAME = None  # Set to your MQTT username if required
MQTT_PASSWORD = None  # Set to your MQTT password if required

# Firebase Configuration
FIREBASE_CREDENTIALS = "credential.json"

# Firestore Configuration
USE_FIRESTORE = True  # Set to False to only use tokens from MQTT payload
FIRESTORE_COLLECTION = "notification"
ADMIN_ONLY = True  # Set to True to send notifications only to admin users

# Notification Configuration
DEFAULT_PRIORITY = "high"  # "high" or "normal"
DEFAULT_TTL = 43200  # Time-to-live in seconds (12 hours)
