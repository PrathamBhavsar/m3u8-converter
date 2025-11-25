"""Stop flag for graceful shutdown of video conversion."""

import signal
import sys
from typing import Optional


class StopFlag:
    """Thread-safe stop flag for graceful conversion shutdown."""
    
    _instance: Optional['StopFlag'] = None
    
    def __init__(self):
        """Initialize the stop flag."""
        self._stop_requested = False
        self._signal_handlers_registered = False
    
    @classmethod
    def get_instance(cls) -> 'StopFlag':
        """Get singleton instance of StopFlag."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def request_stop(self):
        """Request a graceful stop after current folder completes."""
        self._stop_requested = True
        print("\n[STOP] Stop requested - will finish current video and exit...")
    
    def is_stop_requested(self) -> bool:
        """Check if stop has been requested."""
        return self._stop_requested
    
    def reset(self):
        """Reset the stop flag."""
        self._stop_requested = False
    
    def register_signal_handlers(self):
        """Register signal handlers for Ctrl+C and termination signals."""
        if self._signal_handlers_registered:
            return
        
        def signal_handler(signum, frame):
            """Handle interrupt signals gracefully."""
            self.request_stop()
        
        # Register handlers for common interrupt signals
        try:
            signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
            signal.signal(signal.SIGTERM, signal_handler)  # Termination
            self._signal_handlers_registered = True
        except Exception:
            # Some signals may not be available on all platforms
            pass
