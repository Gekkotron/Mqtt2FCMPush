#!/usr/bin/env python3
"""
Firebase and Firestore management for FCM notifications.
"""
import logging
from typing import List, Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore


class FirebaseManager:
    """Manages Firebase Admin SDK and Firestore operations."""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        """
        Initialize Firebase Manager.
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.db = None
        
        self._init_firebase()
        self._init_firestore()
    
    def _init_firebase(self):
        """Initialize Firebase Admin SDK."""
        try:
            cred_path = self.config.get('firebase_credentials')
            if not cred_path:
                raise ValueError(
                    "firebase_credentials path is required in config"
                )
            
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            self.logger.info("Firebase initialized successfully")
        except Exception as e:
            self.logger.error("Failed to initialize Firebase: %s", e)
            raise
    
    def _init_firestore(self):
        """Initialize Firestore client."""
        try:
            self.db = firestore.client()
            self.logger.info("Firestore initialized successfully")
        except Exception as e:
            self.logger.error("Failed to initialize Firestore: %s", e)
            raise
    
    def get_tokens_from_firestore(self) -> List[str]:
        """
        Retrieve FCM tokens from Firestore.
        
        Returns:
            List of FCM tokens
        """
        tokens = []
        
        if not self.db:
            self.logger.warning(
                "Firestore not initialized, cannot retrieve tokens"
            )
            return tokens
        
        try:
            collection_name = self.config.get(
                'firestore_collection', 'notification'
            )
            admin_only = self.config.get('admin_only', False)
            
            col_snapshot = self.db.collection(collection_name).stream()
            
            for doc in col_snapshot:
                doc_dict = doc.to_dict()
                display_name = doc_dict.get('displayName', 'Unknown')
                is_admin = doc_dict.get('admin', False)
                user_tokens = doc_dict.get('tokens', [])
                
                # Check admin status if admin_only is enabled
                if admin_only:
                    self.logger.info(
                        "User '%s' - admin field: %s (is_admin: %s)",
                        display_name,
                        doc_dict.get('admin', 'NOT_SET'),
                        is_admin
                    )
                    if is_admin:
                        tokens.extend(user_tokens)
                        self.logger.info(
                            "Added %d tokens for ADMIN user: %s",
                            len(user_tokens),
                            display_name
                        )
                    else:
                        self.logger.info(
                            "Skipped NON-ADMIN user: %s", display_name
                        )
                else:
                    tokens.extend(user_tokens)
                    self.logger.debug(
                        "Added tokens for user: %s", display_name
                    )
            
            self.logger.info(
                "Retrieved %d tokens from Firestore", len(tokens)
            )
            
        except Exception as e:
            self.logger.error(
                "Error retrieving tokens from Firestore: %s", e
            )
        
        return tokens
    
    def remove_failed_tokens(self, failed_tokens: List[str]):
        """
        Remove failed tokens from Firestore.
        
        Args:
            failed_tokens: List of FCM tokens that failed
        """
        if not self.db or not failed_tokens:
            return
        
        try:
            collection_name = self.config.get(
                'firestore_collection', 'notification'
            )
            admin_only = self.config.get('admin_only', False)
            
            col_snapshot = self.db.collection(collection_name).stream()
            
            for doc in col_snapshot:
                doc_dict = doc.to_dict()
                
                # Skip non-admin users if admin_only is enabled
                if admin_only and not doc_dict.get('admin', False):
                    continue
                
                user_tokens = doc_dict.get('tokens', [])
                removable_tokens = [
                    token for token in user_tokens
                    if token in failed_tokens
                ]
                
                if removable_tokens:
                    device = doc_dict.get('device', 'Unknown')
                    self.logger.info(
                        "Removing %d invalid tokens for device: %s",
                        len(removable_tokens),
                        device
                    )
                    
                    # Uncomment to actually remove tokens
                    doc.reference.update({
                        'tokens': firestore.ArrayRemove(removable_tokens)
                 })
                    
        except Exception as e:
            self.logger.error(
                "Error removing failed tokens from Firestore: %s", e
            )
