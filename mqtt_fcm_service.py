#!/usr/bin/env python3
"""
MQTT to FCM Push Notification Service
Connects to an MQTT broker and sends FCM push notifications to Android devices.
Tokens can be provided in MQTT payload or retrieved from Firestore.
"""
import logging
from typing import Dict, Any
from firebase_manager import FirebaseManager
from fcm_sender import FCMSender
from mqtt_handler import MQTTHandler


class Mqtt2FCMPush:
    """Main service class coordinating MQTT and FCM operations."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the MQTT to FCM Push service.
        
        Args:
            config: Configuration dictionary containing:
                - mqtt_broker: MQTT broker address
                - mqtt_port: MQTT broker port (default: 1883)
                - mqtt_topic: MQTT topic to subscribe to
                - mqtt_username: Optional MQTT username
                - mqtt_password: Optional MQTT password
                - firebase_credentials: Path to Firebase credentials JSON
                - firestore_collection: Firestore collection name for tokens
                - admin_only: Send notifications only to admin users
        """
        self.config = config
        self.logger = self._setup_logger()
        
        # Initialize components
        self.firebase_manager = FirebaseManager(self.config, self.logger)
        self.fcm_sender = FCMSender(self.logger)
        self.mqtt_handler = MQTTHandler(
            self.config,
            self.logger,
            self._handle_mqtt_message
        )
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('Mqtt2FCMPush')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    def _handle_mqtt_message(self, payload: Dict[str, Any]):
        """
        Handle incoming MQTT message and send FCM notification.
        
        Args:
            payload: MQTT message payload
        """
        # Get tokens from payload or Firestore
        tokens = payload.get('tokens', [])
        
        if not tokens:
            # Automatically use Firestore when no tokens provided
            tokens = self.firebase_manager.get_tokens_from_firestore()
        
        if not tokens:
            self.logger.warning(
                "No FCM tokens available, cannot send notification"
            )
            return
        
        # Extract notification parameters
        title = payload.get('title', 'Notification')
        body = payload.get('body', '')
        data = payload.get('data', {})
        priority = payload.get('priority', 'high')
        ttl = payload.get('ttl', 43200)
        
        # Send notification
        failed_tokens = self.fcm_sender.send_notification(
            tokens=tokens,
            title=title,
            body=body,
            data=data,
            priority=priority,
            ttl=ttl
        )
        
        # Remove failed tokens from Firestore
        if failed_tokens:
            self.firebase_manager.remove_failed_tokens(failed_tokens)
    
    def send_fcm_notification(self, payload: Dict[str, Any]):
        """
        Manually send FCM notification (for programmatic use).
        
        Args:
            payload: Notification payload containing:
                - title: Notification title
                - body: Notification body
                - tokens: Optional list of FCM tokens
                - data: Optional additional data
                - priority: Optional priority (default: 'high')
                - ttl: Optional time-to-live in seconds (default: 43200)
        """
        self._handle_mqtt_message(payload)
    
    def start(self):
        """Start the MQTT to FCM Push service."""
        try:
            self.logger.info("Starting MQTT to FCM Push service...")
            self.mqtt_handler.connect()
            self.mqtt_handler.start_loop()
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
            self.stop()
        except Exception as e:
            self.logger.error("Error in main loop: %s", e)
            raise
    
    def stop(self):
        """Stop the service and disconnect."""
        self.mqtt_handler.disconnect()

