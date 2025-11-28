"""Keystroke event listener (privacy-preserving: only timing, not content)"""
import time
from typing import Optional, Callable
from pynput import keyboard
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    """Keystroke event types"""
    KEY_DOWN = "down"
    KEY_UP = "up"


@dataclass
class KeystrokeEvent:
    """Keystroke event data structure"""
    timestamp: float
    key_code: int
    event_type: EventType
    session_id: str


class KeystrokeListener:
    """Listens to keystroke events and logs timing metadata only"""
    
    def __init__(self, session_id: str, callback: Optional[Callable[[KeystrokeEvent], None]] = None):
        """
        Initialize keystroke listener
        
        Args:
            session_id: Current session identifier
            callback: Optional callback function to handle events
        """
        self.session_id = session_id
        self.callback = callback
        self.listener: Optional[keyboard.Listener] = None
        self.is_listening = False
        
    def _on_press(self, key):
        """Handle key press event"""
        try:
            key_code = key.vk if hasattr(key, 'vk') else hash(key)
            event = KeystrokeEvent(
                timestamp=time.time(),
                key_code=key_code,
                event_type=EventType.KEY_DOWN,
                session_id=self.session_id
            )
            if self.callback:
                self.callback(event)
        except Exception as e:
            print(f"Error handling key press: {e}")
    
    def _on_release(self, key):
        """Handle key release event"""
        try:
            key_code = key.vk if hasattr(key, 'vk') else hash(key)
            event = KeystrokeEvent(
                timestamp=time.time(),
                key_code=key_code,
                event_type=EventType.KEY_UP,
                session_id=self.session_id
            )
            if self.callback:
                self.callback(event)
        except Exception as e:
            print(f"Error handling key release: {e}")
    
    def start(self):
        """Start listening to keystrokes"""
        if self.is_listening:
            return
        
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
        self.is_listening = True
    
    def stop(self):
        """Stop listening to keystrokes"""
        if self.listener:
            self.listener.stop()
            self.listener = None
        self.is_listening = False
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()

