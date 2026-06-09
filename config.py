"""
BMS Configuration Module

This module contains all configuration constants for the BMS monitoring system.
Centralized configuration allows for easy customization and maintenance.
"""
from typing import Final


class BMSConfig:
    """Configuration class for Battery Management System parameters."""
    
    # Cell configuration
    NUM_CELLS: Final[int] = 12
    CELLS_PER_ROW: Final[int] = 4
    
    # Temperature sensors
    NUM_TEMPS: Final[int] = 4
    
    # Update interval in milliseconds
    UPDATE_MS: Final[int] = 1000
    
    # Voltage thresholds (in volts)
    CELL_VOLTAGE_CRITICAL_LOW: Final[float] = 3.0
    CELL_VOLTAGE_WARNING_LOW: Final[float] = 3.4
    CELL_VOLTAGE_NORMAL: Final[float] = 3.7
    CELL_VOLTAGE_MAX: Final[float] = 4.2
    
    # Current threshold for IR calculation (in amps)
    CURRENT_DELTA_THRESHOLD: Final[float] = 1.0
    
    # Internal resistance history size
    IR_HISTORY_SIZE: Final[int] = 50
    
    # Serial communication
    DEFAULT_BAUDRATE: Final[int] = 115200
