"""
BMS Data Provider Module

Handles data acquisition from BMS hardware (or simulated data).
Emits data via Qt signals for UI updates.
"""
import random
import logging
from typing import List, Dict, Any, Optional

import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, Signal

from config import BMSConfig

logger = logging.getLogger(__name__)


class BMSDataProvider(QObject):
    """
    Data provider for Battery Management System.
    
    Handles both simulated data generation and real hardware communication.
    Emits data_ready signal when new data is available.
    
    Attributes:
        data_ready: Signal emitted with dictionary of BMS data.
    """
    
    data_ready = Signal(dict)
    
    def __init__(self):
        """Initialize the data provider."""
        super().__init__()
        self._serial_port: Optional[serial.Serial] = None
        self._is_connected: bool = False
    
    def list_serial_ports(self) -> List[str]:
        """
        List available serial ports on the system.
        
        Returns:
            List of port device names.
        """
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]
            logger.debug(f"Found {len(ports)} serial ports: {ports}")
            return ports
        except Exception as e:
            logger.error(f"Error listing serial ports: {e}")
            return []
    
    def connect(self, port: str, baudrate: int = BMSConfig.DEFAULT_BAUDRATE) -> bool:
        """
        Connect to a serial port.
        
        Args:
            port: Serial port name (e.g., 'COM3', '/dev/ttyUSB0').
            baudrate: Baud rate for serial communication.
            
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            # Close existing connection if any
            if self._serial_port and self._serial_port.is_open:
                self.disconnect()
            
            self._serial_port = serial.Serial(port, baudrate, timeout=1)
            self._is_connected = True
            logger.info(f"Connected to {port} at {baudrate} baud")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Serial connection error: {e}")
            self._is_connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
            self._is_connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from the serial port.
        
        Returns:
            True if disconnection successful or not connected, False on error.
        """
        try:
            if self._serial_port and self._serial_port.is_open:
                self._serial_port.close()
                logger.info("Disconnected from serial port")
            self._is_connected = False
            return True
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if currently connected to a serial port."""
        return self._is_connected and self._serial_port and self._serial_port.is_open
    
    def poll(self) -> None:
        """
        Poll for new BMS data and emit via signal.
        
        Currently generates simulated data. Replace with actual hardware
        communication when ready.
        """
        try:
            if self.is_connected:
                # TODO: Implement actual hardware data reading
                # For now, use simulated data even when connected
                pass
            
            data = self._generate_simulated_data()
            self.data_ready.emit(data)
            
        except Exception as e:
            logger.error(f"Error polling data: {e}")
            # Emit default data on error to prevent UI crashes
            error_data = self._generate_simulated_data()
            self.data_ready.emit(error_data)
    
    def _generate_simulated_data(self) -> Dict[str, Any]:
        """
        Generate simulated BMS data for testing.
        
        Returns:
            Dictionary containing simulated BMS measurements.
        """
        # Generate cell voltages with realistic variation
        base_voltage = 3.7
        cells = [
            round(base_voltage + random.uniform(-0.15, 0.15), 3)
            for _ in range(BMSConfig.NUM_CELLS)
        ]
        
        # Generate temperature readings
        temps = [random.randint(25, 45) for _ in range(BMSConfig.NUM_TEMPS)]
        
        # Calculate pack values
        pack_voltage = sum(cells)
        pack_current = random.uniform(-10, 80)  # Discharge/charge current
        
        # Calculate SOC/SOH (simulated)
        soc = random.randint(50, 100)
        soh = random.randint(90, 100)
        
        # Calculate min/max/delta
        vmin = min(cells)
        vmax = max(cells)
        delta = vmax - vmin
        
        data = {
            "cells": cells,
            "temps": temps,
            "packV": pack_voltage,
            "packI": pack_current,
            "soc": soc,
            "soh": soh,
            "vmin": vmin,
            "vmax": vmax,
            "delta": delta
        }
        
        return data
