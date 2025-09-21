"""
Computer handler factory and interface definitions.

This module provides a factory function to create computer handlers from different
computer interface types, supporting both the ComputerHandler protocol and the
Computer library interface.
"""

from .base import AsyncComputerHandler
from .cua import cuaComputerHandler
from .custom import CustomComputerHandler
from computer import Computer as cuaComputer

def is_agent_computer(computer):
    """Check if the given computer is a ComputerHandler or CUA Computer."""
    return isinstance(computer, AsyncComputerHandler) or \
        isinstance(computer, cuaComputer) or \
        (isinstance(computer, dict)) or \
        hasattr(computer, 'is_gui_proxy') or \
        hasattr(computer, 'interface')

async def make_computer_handler(computer):
    """
    Create a computer handler from a computer interface.

    Args:
        computer: Either a ComputerHandler instance, Computer instance, dict of functions, or proxy object

    Returns:
        ComputerHandler: A computer handler instance

    Raises:
        ValueError: If the computer type is not supported
    """
    if isinstance(computer, AsyncComputerHandler):
        return computer
    if isinstance(computer, cuaComputer):
        computer_handler = cuaComputerHandler(computer)
        await computer_handler._initialize()
        return computer_handler
    if isinstance(computer, dict):
        return CustomComputerHandler(computer)
    # Handle proxy objects that have an interface attribute
    if hasattr(computer, 'interface'):
        # Create a custom handler that delegates to the proxy's interface
        async def get_dimensions_async():
            screen_size = await computer.interface.get_screen_size()
            if isinstance(screen_size, dict):
                return (screen_size.get('width', 0), screen_size.get('height', 0))
            elif isinstance(screen_size, tuple):
                return screen_size
            else:
                return (0, 0)

        return CustomComputerHandler({
            'screenshot': computer.interface.screenshot,
            'get_environment': lambda: 'linux',
            'get_dimensions': get_dimensions_async,
            'click': computer.interface.left_click,
            'double_click': computer.interface.double_click,
            'move': computer.interface.move_cursor,
            'type': computer.interface.type_text,
            'keypress': computer.interface.press_key,
            'press_key': computer.interface.press_key,
            'hotkey': computer.interface.hotkey,
            'scroll': computer.interface.scroll,
            'wait': lambda ms=1000: None,  # Proxy doesn't have wait, stub it
        })
    raise ValueError(f"Unsupported computer type: {type(computer)}")