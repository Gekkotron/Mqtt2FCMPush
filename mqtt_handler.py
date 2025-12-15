#!/usr/bin/env python3
"""
MQTT client handler.
"""
import json
import logging
import threading
import time
from datetime import datetime
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
        self.heartbeat_thread = None
        self.heartbeat_stop_event = threading.Event()
        self.reconnect_delay = config.get('reconnect_delay_min', 1)
        self.reconnect_delay_max = config.get('reconnect_delay_max', 60)
        self.is_connected = False
        
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
            self.is_connected = True
            self.reconnect_delay = self.config.get('reconnect_delay_min', 1)
            
            topic = self.config.get('mqtt_topic', 'notifications/#')
            client.subscribe(topic)
            self.logger.info("Subscribed to topic: %s", topic)
            
            # Start heartbeat if enabled
            if self.config.get('heartbeat_enabled', True):
                self._start_heartbeat()
        else:
            self.logger.error(
                "Failed to connect to MQTT broker. Return code: %s", rc
            )
            self.is_connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker."""
        self.is_connected = False
        
        # Stop heartbeat on disconnect
        self._stop_heartbeat()
        
        if rc != 0:
            self.logger.warning(
                "Unexpected disconnection from MQTT broker. "
                "Return code: %s. Will auto-reconnect.",
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
        """Connect to MQTT broker with retry logic."""
        broker = self.config.get('mqtt_broker')
        port = self.config.get('mqtt_port', 1883)
        auto_reconnect = self.config.get('auto_reconnect', True)
        
        if not broker:
            raise ValueError("mqtt_broker is required in config")
        
        while True:
            try:
                self.logger.info(
                    "Connecting to MQTT broker at %s:%d", broker, port
                )
                self.client.connect(broker, port, 60)
                break
                
            except Exception as e:
                if not auto_reconnect:
                    self.logger.error("Failed to connect to MQTT broker: %s", e)
                    raise
                
                self.logger.error(
                    "Failed to connect to MQTT broker: %s. "
                    "Retrying in %d seconds...",
                    e, self.reconnect_delay
                )
                time.sleep(self.reconnect_delay)
                
                # Exponential backoff
                self.reconnect_delay = min(
                    self.reconnect_delay * 2,
                    self.reconnect_delay_max
                )
    
    def start_loop(self):
        """Start the MQTT client loop (blocking) with auto-reconnect."""
        self.client.loop_forever(retry_first_connection=True)
    
    def _heartbeat_worker(self):
        """Background worker that publishes periodic heartbeats."""
        heartbeat_topic = self.config.get('heartbeat_topic', 'notification/heartbeat')
        interval = self.config.get('heartbeat_interval', 60)
        
        self.logger.info(
            "Heartbeat started: topic=%s, interval=%ds",
            heartbeat_topic,
            interval
        )
        
        while not self.heartbeat_stop_event.wait(timeout=interval):
            try:
                # Only publish if connected
                if not self.is_connected or not self.client:
                    self.logger.debug("Skipping heartbeat - not connected")
                    continue
                
                heartbeat_payload = {
                    'timestamp': datetime.now(),
                }
                
                result = self.client.publish(
                    heartbeat_topic,
                    json.dumps(heartbeat_payload),
                    qos=1,
                    retain=True
                )
                
                # Wait for publish to complete
                result.wait_for_publish(timeout=5)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.info("Heartbeat sent to %s", heartbeat_topic)
                else:
                    self.logger.warning("Heartbeat publish failed with rc=%s", result.rc)
                
            except Exception as e:
                self.logger.error("Error sending heartbeat: %s", e)
    
    def _start_heartbeat(self):
        """Start the heartbeat thread."""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return
        
        self.heartbeat_stop_event.clear()
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker,
            daemon=True
        )
        self.heartbeat_thread.start()
    
    def _stop_heartbeat(self):
        """Stop the heartbeat thread."""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.logger.info("Stopping heartbeat...")
            self.heartbeat_stop_event.set()
            self.heartbeat_thread.join(timeout=5)
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self._stop_heartbeat()
        if self.client:
            self.client.disconnect()
            self.logger.info("MQTT client disconnected")
