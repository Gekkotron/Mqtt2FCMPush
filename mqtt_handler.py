#!/usr/bin/env python3
"""
MQTT client handler.
"""
import json
import logging
from typing import Dict, Any, Callable
import paho.mqtt.client as mqtt


class MQTTHandler:
    """Handles MQTT client operations."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        logger: logging.Logger,
        message_callback: Callable[[Dict[str, Any]], None]
    ):
        """
        Initialize MQTT Handler.
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
            message_callback: Callback function for processing messages
        """
        self.config = config
        self.logger = logger
        self.message_callback = message_callback
        self.client = None
        
        self._init_mqtt()
    
    def _init_mqtt(self):
        """Initialize MQTT client and set up callbacks."""
        try:
            self.client = mqtt.Client()
            
            # Set username and password if provided
            username = self.config.get('mqtt_username')
            password = self.config.get('mqtt_password')
            if username and password:
                self.client.username_pw_set(username, password)
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            
            self.logger.info("MQTT client initialized")
        except Exception as e:
            self.logger.error("Failed to initialize MQTT client: %s", e)
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker."""
        if rc == 0:
            self.logger.info("Connected to MQTT broker successfully")
            topic = self.config.get('mqtt_topic', 'notifications/#')
            client.subscribe(topic)
            self.logger.info("Subscribed to topic: %s", topic)
        else:
            self.logger.error(
                "Failed to connect to MQTT broker. Return code: %s", rc
            )
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker."""
        if rc != 0:
            self.logger.warning(
                "Unexpected disconnection from MQTT broker. "
                "Return code: %s",
                rc
            )
        else:
            self.logger.info("Disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        """Callback for when a message is received from the broker."""
        try:
            self.logger.info("Received message on topic %s", msg.topic)
            payload = json.loads(msg.payload.decode('utf-8'))
            self.logger.debug("Payload: %s", payload)
            
            # Call the message callback
            self.message_callback(payload)
            
        except json.JSONDecodeError as e:
            self.logger.error(
                "Failed to parse message payload as JSON: %s", e
            )
        except Exception as e:
            self.logger.error("Error processing message: %s", e)
    
    def connect(self):
        """Connect to MQTT broker."""
        try:
            broker = self.config.get('mqtt_broker')
            port = self.config.get('mqtt_port', 1883)
            
            if not broker:
                raise ValueError("mqtt_broker is required in config")
            
            self.logger.info(
                "Connecting to MQTT broker at %s:%d", broker, port
            )
            self.client.connect(broker, port, 60)
            
        except Exception as e:
            self.logger.error("Failed to connect to MQTT broker: %s", e)
            raise
    
    def start_loop(self):
        """Start the MQTT client loop (blocking)."""
        self.client.loop_forever()
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.disconnect()
            self.logger.info("MQTT client disconnected")
