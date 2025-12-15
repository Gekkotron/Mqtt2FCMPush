#!/usr/bin/env python3
"""
Main entry point for MQTT to FCM Push service.
"""
import sys
import config
from mqtt_fcm_service import Mqtt2FCMPush


def main():
    """Main function to start the service."""
    # Load configuration
    service_config = {
        'mqtt_broker': config.MQTT_BROKER,
        'mqtt_port': config.MQTT_PORT,
        'mqtt_topic': config.MQTT_TOPIC,
        'mqtt_username': config.MQTT_USERNAME,
        'mqtt_password': config.MQTT_PASSWORD,
        'firebase_credentials': config.FIREBASE_CREDENTIALS,
        'firestore_collection': config.FIRESTORE_COLLECTION,
        'admin_only': config.ADMIN_ONLY,
        'retry_interval': config.RETRY_INTERVAL,
        'max_retries': config.MAX_RETRIES,
        'heartbeat_enabled': config.HEARTBEAT_ENABLED,
        'heartbeat_interval': config.HEARTBEAT_INTERVAL,
        'heartbeat_topic': config.HEARTBEAT_TOPIC
    }
    
    try:
        # Create and start the service
        service = Mqtt2FCMPush(service_config)
        service.start()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
