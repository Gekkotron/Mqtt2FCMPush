#!/usr/bin/env python3
"""
FCM notification sender.
"""
import datetime
import logging
from typing import List, Dict, Any
from firebase_admin import messaging


class FCMSender:
    """Handles sending FCM notifications."""
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize FCM Sender.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    def send_notification(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Dict[str, Any] = None,
        priority: str = 'high',
        ttl: int = 43200
    ) -> List[str]:
        """
        Send FCM notification to devices.
        
        Args:
            tokens: List of FCM tokens
            title: Notification title
            body: Notification body
            data: Additional data payload
            priority: Message priority ('high' or 'normal')
            ttl: Time-to-live in seconds
            
        Returns:
            List of failed tokens
        """
        if not tokens:
            self.logger.warning(
                "No FCM tokens provided, cannot send notification"
            )
            return []
        
        try:
            # Prepare complete payload with all fields
            payload = {
                'title': title,
                'body': body,
            }
            
            # Add all additional data fields
            if data:
                payload.update(data)
            
            # Convert all values to strings (FCM requirement)
            payload = {k: str(v) for k, v in payload.items()}
            
            # Create FCM message
            message = messaging.MulticastMessage(
                data=payload,
                android=messaging.AndroidConfig(
                    ttl=datetime.timedelta(seconds=ttl),
                    priority=priority
                ),
                tokens=tokens
            )
            
            self.logger.info("Sending notification to %d devices", len(tokens))
            
            # Send the message
            response = messaging.send_each_for_multicast(message)
            
            self.logger.info(
                "Successfully sent: %d, Failed: %d",
                response.success_count,
                response.failure_count
            )
            
            # Handle failed tokens
            failed_tokens = []
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        failed_tokens.append(tokens[idx])
                        self.logger.warning(
                            "Failed to send to token %d: %s",
                            idx,
                            resp.exception
                        )
                
                self.logger.info("Failed tokens: %s", failed_tokens)
            
            return failed_tokens
            
        except Exception as e:
            self.logger.error("Error sending FCM notification: %s", e)
            return []
