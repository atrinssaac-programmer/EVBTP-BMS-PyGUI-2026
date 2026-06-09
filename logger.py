"""
BMS Logger Module

Provides CSV logging functionality for BMS data.
Handles file creation, data writing, and proper resource cleanup.
"""
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from config import BMSConfig

logger = logging.getLogger(__name__)


class BMSLogger:
    """
    Logger class for recording BMS data to CSV files.
    
    Attributes:
        file: Open file handle for the CSV log file.
        writer: CSV writer object for writing data rows.
        is_logging: Flag indicating if logging is currently active.
    """
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize the BMS logger.
        
        Args:
            log_dir: Directory to store log files. Defaults to current directory.
        """
        self._file: Optional[Any] = None
        self._writer: Optional[csv.writer] = None
        self._is_logging: bool = False
        self._log_dir = log_dir or Path.cwd()
        
    def start(self) -> bool:
        """
        Start logging to a new CSV file.
        
        Returns:
            True if logging started successfully, False otherwise.
        """
        if self._is_logging:
            logger.warning("Logging already in progress")
            return False
        
        try:
            # Ensure log directory exists
            self._log_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bms_{timestamp}.csv"
            filepath = self._log_dir / filename
            
            # Open file and create writer
            self._file = open(filepath, "w", newline="", encoding="utf-8")
            self._writer = csv.writer(self._file)
            
            # Write header row
            header = ["Time", "PackV", "PackI", "SOC", "SOH"]
            header.extend([f"C{i+1}" for i in range(BMSConfig.NUM_CELLS)])
            header.extend([f"T{i+1}" for i in range(BMSConfig.NUM_TEMPS)])
            self._writer.writerow(header)
            
            self._is_logging = True
            logger.info(f"Logging started: {filepath}")
            return True
            
        except (IOError, OSError) as e:
            logger.error(f"Failed to start logging: {e}")
            self._cleanup()
            return False
    
    def log(self, data: Dict[str, Any]) -> bool:
        """
        Log a single data record.
        
        Args:
            data: Dictionary containing BMS data values.
            
        Returns:
            True if data was logged successfully, False otherwise.
        """
        if not self._is_logging or self._writer is None:
            return False
        
        try:
            row = [
                datetime.now().isoformat(),
                data.get("packV", 0.0),
                data.get("packI", 0.0),
                data.get("soc", 0),
                data.get("soh", 0),
                *data.get("cells", []),
                *data.get("temps", [])
            ]
            self._writer.writerow(row)
            self._file.flush()  # Ensure data is written to disk
            return True
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to log data: {e}")
            return False
    
    def stop(self) -> None:
        """Stop logging and close the file."""
        self._cleanup()
        logger.info("Logging stopped")
    
    def _cleanup(self) -> None:
        """Internal method to clean up resources."""
        if self._file:
            try:
                self._file.close()
            except Exception as e:
                logger.error(f"Error closing log file: {e}")
        self._file = None
        self._writer = None
        self._is_logging = False
    
    @property
    def is_logging(self) -> bool:
        """Check if logging is currently active."""
        return self._is_logging
