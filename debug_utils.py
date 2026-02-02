"""
Centralized debug utility for displaying debug messages in a GUI window.
Can be used by any module in the application.
"""
import threading
from queue import Queue
from typing import Optional, Callable

# Global debug state
_debug_enabled = False
_debug_callback: Optional[Callable[[str], None]] = None
_message_queue = Queue()


def set_debug_enabled(enabled: bool, callback: Optional[Callable[[str], None]] = None):
    """Enable or disable debug mode globally
    
    Args:
        enabled: Boolean to enable/disable debug mode
        callback: Optional callback function(message) to display debug messages
                  Should be thread-safe and handle messages from any thread
    """
    global _debug_enabled, _debug_callback
    _debug_enabled = enabled
    _debug_callback = callback
    return _debug_enabled


def get_debug_enabled() -> bool:
    """Get current debug state"""
    return _debug_enabled


def debug_print(message: str, module: str = "General"):
    """Print debug message to debug window (if enabled) or console
    
    Args:
        message: The debug message to display
        module: Optional module name to prefix the message (e.g., "InputHandler", "AutoAttack")
    
    This function is thread-safe and can be called from any thread.
    
    Performance: When debug is disabled, this function returns immediately with minimal overhead
    (just a boolean check). However, if you use f-strings with expensive operations like:
        debug_print(f"Value: {expensive_function()}", "Module")
    The expensive operation will still execute. For expensive operations, use debug_print_lazy() instead.
    """
    # Fast path: return immediately if debug is disabled (minimal overhead)
    if not _debug_enabled:
        return
    
    # Format message with module prefix
    formatted_message = f"[{module}] {message}"
    
    # Try to use callback (GUI window) first
    if _debug_callback:
        try:
            # Callback should handle thread-safety (e.g., using root.after())
            _debug_callback(formatted_message)
        except Exception:
            # Fallback to console if callback fails
            print(formatted_message)
    else:
        # Fallback to console if no callback
        print(formatted_message)


def debug_print_lazy(message_func: Callable[[], str], module: str = "General"):
    """Print debug message using lazy evaluation (for expensive operations)
    
    Args:
        message_func: A callable that returns the debug message string (only called if debug enabled)
        module: Optional module name to prefix the message
    
    Use this when creating the message string is expensive. The function is only called if debug is enabled.
    
    Example:
        # Instead of: debug_print(f"Value: {expensive_function()}", "Module")
        # Use: debug_print_lazy(lambda: f"Value: {expensive_function()}", "Module")
    """
    # Fast path: return immediately if debug is disabled (no function call overhead)
    if not _debug_enabled:
        return
    
    # Only evaluate the message function if debug is enabled
    message = message_func()
    debug_print(message, module)


def debug_print_error(message: str, module: str = "General", exception: Optional[Exception] = None):
    """Print error message with optional exception details
    
    Args:
        message: The error message
        module: Optional module name
        exception: Optional exception object to include traceback
    
    Performance: When debug is disabled, this returns immediately. Exception formatting only
    happens if debug is enabled.
    """
    # Fast path: return immediately if debug is disabled
    if not _debug_enabled:
        return
    
    error_msg = f"ERROR: {message}"
    if exception:
        import traceback
        error_msg += f"\n{type(exception).__name__}: {str(exception)}"
        error_msg += f"\n{traceback.format_exc()}"
    
    debug_print(error_msg, module)


def debug_print_warning(message: str, module: str = "General"):
    """Print warning message
    
    Args:
        message: The warning message
        module: Optional module name
    
    Performance: When debug is disabled, this returns immediately with minimal overhead.
    """
    # Fast path: return immediately if debug is disabled
    if not _debug_enabled:
        return
    
    debug_print(f"WARNING: {message}", module)


def debug_print_info(message: str, module: str = "General"):
    """Print info message
    
    Args:
        message: The info message
        module: Optional module name
    
    Performance: When debug is disabled, this returns immediately with minimal overhead.
    """
    # Fast path: return immediately if debug is disabled
    if not _debug_enabled:
        return
    
    debug_print(f"INFO: {message}", module)
