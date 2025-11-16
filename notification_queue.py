#!/usr/bin/env python3
"""
Notification queue manager with retry logic and TTL management.
Persists failed notifications and retries them periodically.
"""
import json
import logging
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class NotificationQueue:
    """Manages queued notifications with retry logic and TTL."""
    
    def __init__(
        self,
        queue_file: str = 'notification_queue.json',
        retry_interval: int = 60,
        max_retries: int = 10,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize notification queue.
        
        Args:
            queue_file: Path to queue persistence file
            retry_interval: Seconds between retry attempts
            max_retries: Maximum retry attempts before discarding
            logger: Logger instance
        """
        self.queue_file = Path(queue_file)
        self.retry_interval = retry_interval
        self.max_retries = max_retries
        self.logger = logger or logging.getLogger(__name__)
        self.queue: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        self.retry_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Load existing queue
        self._load_queue()
    
    def _load_queue(self):
        """Load queue from disk."""
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        self.queue = json.loads(content)
                    else:
                        self.queue = []
                self.logger.info(
                    "Loaded %d notifications from queue", len(self.queue)
                )
            except json.JSONDecodeError as e:
                self.logger.error("Failed to parse queue file: %s", e)
                self.queue = []
                # Backup corrupted file
                backup_file = self.queue_file.with_suffix('.json.backup')
                try:
                    self.queue_file.rename(backup_file)
                    self.logger.info(
                        "Corrupted queue backed up to %s", backup_file
                    )
                except Exception as backup_error:
                    self.logger.error(
                        "Failed to backup corrupted queue: %s", backup_error
                    )
            except Exception as e:
                self.logger.error("Failed to load queue: %s", e)
                self.queue = []
    
    def _save_queue(self):
        """Save queue to disk."""
        try:
            with open(self.queue_file, 'w') as f:
                json.dump(self.queue, f, indent=2)
        except Exception as e:
            self.logger.error("Failed to save queue: %s", e)
    
    def add_notification(self, notification: Dict[str, Any]):
        """
        Add notification to queue.
        
        Args:
            notification: Notification payload with required fields:
                - title: Notification title
                - body: Notification body
                - tokens: List of FCM tokens
                - data: Optional additional data
                - priority: Optional priority
                - ttl: Time-to-live in seconds
        """
        with self.lock:
            # Add queue metadata
            queued_notification = {
                'notification': notification,
                'queued_at': datetime.now().isoformat(),
                'expires_at': (
                    datetime.now() + 
                    timedelta(seconds=notification.get('ttl', 43200))
                ).isoformat(),
                'retry_count': 0,
                'next_retry': datetime.now().isoformat()
            }
            
            self.queue.append(queued_notification)
            self._save_queue()
            
            self.logger.info(
                "Added notification to queue: '%s' (total: %d)",
                notification.get('title', 'Untitled'),
                len(self.queue)
            )
    
    def _is_expired(self, queued_notification: Dict[str, Any]) -> bool:
        """Check if notification has exceeded its TTL."""
        expires_at = datetime.fromisoformat(
            queued_notification['expires_at']
        )
        return datetime.now() > expires_at
    
    def _should_retry(self, queued_notification: Dict[str, Any]) -> bool:
        """Check if notification should be retried now."""
        next_retry = datetime.fromisoformat(
            queued_notification['next_retry']
        )
        return datetime.now() >= next_retry
    
    def get_notifications_to_retry(self) -> List[Dict[str, Any]]:
        """
        Get notifications that should be retried.
        
        Returns:
            List of notifications ready for retry
        """
        with self.lock:
            to_retry = []
            expired = []
            max_retries_reached = []
            
            for item in self.queue:
                # Check if expired
                if self._is_expired(item):
                    expired.append(item)
                    continue
                
                # Check if max retries reached
                if item['retry_count'] >= self.max_retries:
                    max_retries_reached.append(item)
                    continue
                
                # Check if ready for retry
                if self._should_retry(item):
                    to_retry.append(item)
            
            # Remove expired and max-retried notifications
            for item in expired:
                self.queue.remove(item)
                self.logger.warning(
                    "Notification expired (TTL): '%s'",
                    item['notification'].get('title', 'Untitled')
                )
            
            for item in max_retries_reached:
                self.queue.remove(item)
                self.logger.error(
                    "Max retries reached for notification: '%s'",
                    item['notification'].get('title', 'Untitled')
                )
            
            if expired or max_retries_reached:
                self._save_queue()
            
            return to_retry
    
    def mark_success(self, queued_notification: Dict[str, Any]):
        """
        Remove successfully sent notification from queue.
        
        Args:
            queued_notification: Queued notification item
        """
        with self.lock:
            if queued_notification in self.queue:
                self.queue.remove(queued_notification)
                self._save_queue()
                self.logger.info(
                    "Notification sent successfully: '%s'",
                    queued_notification['notification'].get(
                        'title', 'Untitled'
                    )
                )
    
    def mark_failure(self, queued_notification: Dict[str, Any]):
        """
        Update retry metadata for failed notification.
        
        Args:
            queued_notification: Queued notification item
        """
        with self.lock:
            if queued_notification in self.queue:
                queued_notification['retry_count'] += 1
                queued_notification['next_retry'] = (
                    datetime.now() + 
                    timedelta(seconds=self.retry_interval)
                ).isoformat()
                self._save_queue()
                self.logger.warning(
                    "Notification failed (retry %d/%d): '%s'",
                    queued_notification['retry_count'],
                    self.max_retries,
                    queued_notification['notification'].get(
                        'title', 'Untitled'
                    )
                )
    
    def start_retry_worker(self, send_callback):
        """
        Start background worker to retry failed notifications.
        
        Args:
            send_callback: Function to call for sending notifications
                          Should accept notification dict and return bool
        """
        if self.running:
            self.logger.warning("Retry worker already running")
            return
        
        self.running = True
        self.retry_thread = threading.Thread(
            target=self._retry_worker,
            args=(send_callback,),
            daemon=True
        )
        self.retry_thread.start()
        self.logger.info("Retry worker started")
    
    def _retry_worker(self, send_callback):
        """Background worker that retries failed notifications."""
        while self.running:
            try:
                notifications = self.get_notifications_to_retry()
                
                for queued_notification in notifications:
                    notification = queued_notification['notification']
                    
                    self.logger.info(
                        "Retrying notification: '%s' (attempt %d/%d)",
                        notification.get('title', 'Untitled'),
                        queued_notification['retry_count'] + 1,
                        self.max_retries
                    )
                    
                    # Attempt to send
                    success = send_callback(notification)
                    
                    if success:
                        self.mark_success(queued_notification)
                    else:
                        self.mark_failure(queued_notification)
                
            except Exception as e:
                self.logger.error("Error in retry worker: %s", e)
            
            # Sleep before next check
            time.sleep(10)
    
    def stop_retry_worker(self):
        """Stop the retry worker."""
        self.running = False
        if self.retry_thread:
            self.retry_thread.join(timeout=5)
        self.logger.info("Retry worker stopped")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status.
        
        Returns:
            Dictionary with queue statistics
        """
        with self.lock:
            total = len(self.queue)
            expired_count = sum(
                1 for item in self.queue if self._is_expired(item)
            )
            ready_count = sum(
                1 for item in self.queue 
                if self._should_retry(item) and not self._is_expired(item)
            )
            
            return {
                'total': total,
                'ready_to_retry': ready_count,
                'expired': expired_count,
                'waiting': total - ready_count - expired_count
            }
