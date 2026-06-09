# =========================================================
# DATA PROVIDER (Simulated → replace later)
# =========================================================
import random
import serial.tools.list_ports

from PySide6.QtCore import QObject, Signal
from config import BMSConfig

class BMSDataProvider(QObject):

    data_ready = Signal(dict)

    def poll(self):
        volts = [round(random.uniform(3.0,4.2),3)
                 for _ in range(BMSConfig.NUM_CELLS)]

        temps = [random.randint(20,65)
                 for _ in range(BMSConfig.NUM_TEMPS)]

        data = {
            "cells": volts,
            "temps": temps,
            "packV": sum(volts),
            "packI": random.uniform(-40,120),
            "soc": random.randint(40,100),
            "soh": random.randint(85,100),
            "vmin": min(volts),
            "vmax": max(volts),
            "delta": max(volts)-min(volts)
        }

        self.data_ready.emit(data)

    def __init__(self):
        super().__init__()
        self.serial_port = None

    def list_serial_ports(self):
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect(self, port, baudrate=115200):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.serial_port = serial.Serial(port, baudrate)

    def disconnect(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
