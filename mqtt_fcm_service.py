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
from notification_queue import NotificationQueue


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
        self.notification_queue = NotificationQueue(
            logger=self.logger,
            retry_interval=config.get('retry_interval', 60),
            max_retries=config.get('max_retries', 10)
        )
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
        
        # Create complete notification payload
        notification = {
            'tokens': tokens,
            'title': payload.get('title', 'Notification'),
            'body': payload.get('body', ''),
            'data': payload.get('data', {}),
            'priority': payload.get('priority', 'high'),
            'ttl': payload.get('ttl', 43200)
        }
        
        # Try to send notification
        success = self._send_notification(notification)
        
        # Queue for retry if failed
        if not success:
            self.notification_queue.add_notification(notification)
    
    def _send_notification(self, notification: Dict[str, Any]) -> bool:
        """
        Send FCM notification.
        
        Args:
            notification: Complete notification payload
            
        Returns:
            True if successful, False otherwise
        """
        try:
            failed_tokens = self.fcm_sender.send_notification(
                tokens=notification['tokens'],
                title=notification['title'],
                body=notification['body'],
                data=notification['data'],
                priority=notification['priority'],
                ttl=notification['ttl']
            )
            
            # Remove failed tokens from Firestore
            if failed_tokens:
                self.firebase_manager.remove_failed_tokens(failed_tokens)
            
            # Consider it success if at least some tokens succeeded
            return len(failed_tokens) < len(notification['tokens'])
            
        except Exception as e:
            self.logger.error("Error sending notification: %s", e)
            return False
    
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
            
            # Start retry worker
            self.notification_queue.start_retry_worker(
                self._send_notification
            )
            
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
        self.notification_queue.stop_retry_worker()
        self.mqtt_handler.disconnect()
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get notification queue status.
        
        Returns:
            Dictionary with queue statistics
        """
        return self.notification_queue.get_queue_status()

