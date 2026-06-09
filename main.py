"""
BMS Dashboard - Main Application Module

A comprehensive Battery Management System monitoring interface built with PySide6.
Provides real-time visualization of cell voltages, temperatures, and diagnostics.

Created by ATRI (Automotive Technology Research Institute), Pyin Oo Lwin
"""
import sys
import os
import ctypes
import logging
from pathlib import Path
from collections import deque
from typing import Optional, List, Dict, Any, Final

from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QFrame, QLabel, QPushButton,
    QComboBox, QScrollArea, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap, QFont
from PySide6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QValueAxis

from config import BMSConfig
from data_provider import BMSDataProvider
from logger import BMSLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Windows Taskbar Icon (Windows only)
try:
    APP_ID: Final[str] = 'atri.evbtp.bmsui.v4'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except AttributeError:
    # Not on Windows, skip taskbar icon setup
    pass


class FontManager:
    """
    Manages dynamic font scaling based on window size and DPI.
    
    Attributes:
        base_title: Base font size for title text.
        base_value: Base font size for value displays.
        base_temp: Base font size for temperature displays.
        min_size: Minimum allowed font size.
    """
    
    def __init__(
        self,
        base_title: int = 24,
        base_value: int = 16,
        base_temp: int = 14,
        min_size: int = 8
    ):
        """Initialize font manager with base sizes."""
        self.base_title: int = base_title
        self.base_value: int = base_value
        self.base_temp: int = base_temp
        self.min_size: int = min_size
    
    def apply(self, widget: QLabel, role: str = "value", scale: float = 1.0) -> None:
        """
        Apply scaled font to a widget.
        
        Args:
            widget: Target widget to apply font to.
            role: Font role ('title', 'value', or 'temp').
            scale: Scaling factor based on window size/DPI.
        """
        font: QFont = widget.font()
        base_size: int = getattr(self, f"base_{role}", self.base_value)
        new_size: int = max(self.min_size, int(base_size * scale))
        font.setPointSize(new_size)
        widget.setFont(font)


class BMSWindow(QMainWindow):
    """
    Main BMS monitoring window.
    
    Provides comprehensive battery monitoring with real-time updates,
    theme switching, data logging, and serial communication.
    """
    
    def __init__(self, app: QApplication):
        """
        Initialize the BMS window.
        
        Args:
            app: Qt application instance.
        """
        super().__init__()
        self._app: QApplication = app
        
        # Setup application icon
        self._setup_icon()
        
        # Window properties
        self.setWindowTitle("BMS Dashboard - Created by ATRI, Pyin Oo Lwin")
        self._base_width: Final[int] = 1280
        self.resize(self._base_width, 680)
        
        # Theme configuration
        self._available_qss: List[tuple] = [
            ("ATRI Dark", "atri_dark.qss"),
            ("ATRI Light", "atri_light.qss"),
        ]
        self._load_qss(Path(__file__).parent / "themes" / "atri_dark.qss")
        
        # Data provider and logger
        self._provider: BMSDataProvider = BMSDataProvider()
        self._logger: BMSLogger = BMSLogger()
        self._provider.data_ready.connect(self._update_ui)
        
        # Polling timer
        self._timer: QTimer = QTimer()
        self._timer.timeout.connect(self._provider.poll)
        self._timer.start(BMSConfig.UPDATE_MS)
        
        # Diagnostic state
        self._prev_current: Optional[float] = None
        self._prev_pack_v: Optional[float] = None
        self._ir_history: deque = deque(maxlen=BMSConfig.IR_HISTORY_SIZE)
        
        # Font manager for responsive UI
        self._font_mgr: FontManager = FontManager()
        
        # Build UI components
        self._build_ui()
        
        logger.info("BMS Window initialized")
    
    def _setup_icon(self) -> None:
        """Set up application and window icon."""
        icon_path: Path = Path(__file__).parent / "assets" / "ATRI_Logo.ico"
        if icon_path.exists():
            icon: QIcon = QIcon(str(icon_path))
            self._app.setWindowIcon(icon)
            self.setWindowIcon(icon)
            logger.debug(f"Icon loaded from {icon_path}")
    
    def _load_qss(self, filepath: Path) -> bool:
        """
        Load and apply a QSS stylesheet.
        
        Args:
            filepath: Path to the QSS file.
            
        Returns:
            True if loaded successfully, False otherwise.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
            logger.debug(f"Stylesheet loaded: {filepath}")
            return True
        except (IOError, OSError) as e:
            logger.error(f"QSS load error: {e}")
            return False
    
    def _on_theme_changed(self, index: int) -> None:
        """Handle theme selection change."""
        filename: Optional[str] = self.theme_combo.itemData(index)
        if filename:
            filepath: Path = Path(__file__).parent / "themes" / filename
            self._load_qss(filepath)
    
    def _create_frame(self) -> QFrame:
        """Create a styled frame widget."""
        frame: QFrame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setLineWidth(2)
        frame.setMinimumHeight(40)
        return frame
    
    def _get_scale_factor(self) -> float:
        """Calculate responsive scale factor based on width and DPI."""
        screen = self.screen() or QApplication.primaryScreen()
        dpi_scale: float = screen.devicePixelRatio()
        width_scale: float = self.width() / self._base_width
        return width_scale * dpi_scale
    
    def resizeEvent(self, event) -> None:
        """Handle window resize events for responsive font scaling."""
        scale: float = self._get_scale_factor()
        
        # Scale title
        if hasattr(self, 'title_label'):
            self._font_mgr.apply(self.title_label, "title", scale)
        
        # Scale value labels
        value_labels = [
            getattr(self, 'pack_v', None),
            getattr(self, 'pack_i', None),
            getattr(self, 'soc', None),
            getattr(self, 'soh', None),
            getattr(self, 'v_delta', None),
        ]
        for lbl in value_labels:
            if lbl:
                self._font_mgr.apply(lbl, "value", scale)
        
        # Scale temperature labels
        for lbl in getattr(self, 'temp_labels', []):
            self._font_mgr.apply(lbl, "temp", scale)
        
        super().resizeEvent(event)
    
    def _build_ui(self) -> None:
        """Build the complete user interface."""
        # Scroll area for content
        scroll: QScrollArea = QScrollArea()
        scroll.setWidgetResizable(True)
        
        container: QWidget = QWidget()
        scroll.setWidget(container)
        self.setCentralWidget(scroll)
        
        # Main vertical layout
        main_layout: QVBoxLayout = QVBoxLayout(container)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Add UI sections
        main_layout.addWidget(self._build_title_with_logo())
        main_layout.addWidget(self._build_pack_overview())
        main_layout.addWidget(self._build_cells_section())
        main_layout.addWidget(self._build_temps_section())
        main_layout.addWidget(self._build_diagnostics())
        main_layout.addLayout(self._build_bottom_controls())
        main_layout.addWidget(self._build_deptitle())
    
    def _build_title_with_logo(self) -> QWidget:
        """Create title section with logo."""
        container: QWidget = QWidget()
        layout: QHBoxLayout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        
        # Logo
        logo_path: Path = Path(__file__).parent / "assets" / "ATRI_Logo.png"
        logo_label: QLabel = QLabel()
        if logo_path.exists():
            pixmap: QPixmap = QPixmap(str(logo_path))
            scaled_pixmap: QPixmap = pixmap.scaledToHeight(64, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setVisible(False)
        
        # Title label
        self.title_label: QLabel = QLabel(
            "EV Battery Technology Platform - BMS Monitoring System"
        )
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setObjectName("title")
        self.title_label.setMaximumHeight(90)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        layout.addWidget(logo_label)
        layout.addWidget(self.title_label)
        
        return container
    
    def _build_deptitle(self) -> QLabel:
        """Create department credit label."""
        deptitle: QLabel = QLabel(
            "Design & Develop by Automotive Technology Research Institute"
        )
        deptitle.setObjectName("deptitle")
        deptitle.setAlignment(Qt.AlignRight)
        deptitle.setMaximumHeight(30)
        deptitle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return deptitle
    
    def _build_pack_overview(self) -> QGroupBox:
        """Create pack overview section with key metrics."""
        box: QGroupBox = QGroupBox("Pack Overview")
        grid: QGridLayout = QGridLayout(box)
        
        # Create value labels
        self.pack_v: QLabel = QLabel("--")
        self.pack_i: QLabel = QLabel("--")
        self.soc: QLabel = QLabel("--")
        self.soh: QLabel = QLabel("--")
        self.v_delta: QLabel = QLabel("--")
        
        items: List[tuple] = [
            ("Pack V", self.pack_v),
            ("Pack I", self.pack_i),
            ("SOC", self.soc),
            ("SOH", self.soh),
            ("ΔV", self.v_delta),
        ]
        
        for i, (text, value_lbl) in enumerate(items):
            # Create tile frame
            frame: QFrame = QFrame()
            frame.setFrameShape(QFrame.StyledPanel)
            frame.setLineWidth(2)
            frame.setMinimumHeight(40)
            
            h_layout: QHBoxLayout = QHBoxLayout(frame)
            h_layout.setContentsMargins(8, 4, 8, 4)
            
            # Name label
            name_lbl: QLabel = QLabel(text)
            name_lbl.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            name_lbl.setProperty("static", True)
            
            # Value label
            value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_lbl.setProperty("static", True)
            
            h_layout.addWidget(name_lbl)
            h_layout.addWidget(value_lbl)
            
            grid.addWidget(frame, 0, i)
        
        return box
    
    def _build_cells_section(self) -> QGroupBox:
        """Create cell voltages display section."""
        box: QGroupBox = QGroupBox("Cell Voltages")
        grid: QGridLayout = QGridLayout(box)
        
        self.cell_value_labels: List[QLabel] = []
        
        for i in range(BMSConfig.NUM_CELLS):
            # Horizontal layout for name + value
            h_layout: QHBoxLayout = QHBoxLayout()
            
            # Name frame
            name_frame: QFrame = QFrame()
            name_frame.setFrameShape(QFrame.StyledPanel)
            name_frame.setLineWidth(2)
            
            name_layout: QHBoxLayout = QHBoxLayout(name_frame)
            name_layout.setContentsMargins(6, 2, 6, 2)
            
            name: QLabel = QLabel(f"C{i+1}")
            name.setAlignment(Qt.AlignCenter)
            name.setProperty("static", True)
            name_layout.addWidget(name)
            
            # Value frame
            val_frame: QFrame = QFrame()
            val_frame.setFrameShape(QFrame.StyledPanel)
            val_frame.setLineWidth(2)
            
            val_layout: QHBoxLayout = QHBoxLayout(val_frame)
            val_layout.setContentsMargins(6, 2, 6, 2)
            
            val: QLabel = QLabel("-- V")
            val.setAlignment(Qt.AlignCenter)
            val_layout.addWidget(val)
            
            # Add frames to layout
            h_layout.addWidget(name_frame)
            h_layout.addWidget(val_frame)
            
            # Position in grid
            row, col = divmod(i, BMSConfig.CELLS_PER_ROW)
            grid.addLayout(h_layout, row, col)
            
            self.cell_value_labels.append(val)
        
        return box
    
    def _build_temps_section(self) -> QGroupBox:
        """Create temperature display section."""
        box: QGroupBox = QGroupBox("Temperatures")
        grid: QGridLayout = QGridLayout(box)
        
        self.temp_labels: List[QLabel] = []
        
        for i in range(BMSConfig.NUM_TEMPS):
            frame: QFrame = self._create_frame()
            h_layout: QHBoxLayout = QHBoxLayout(frame)
            
            name: QLabel = QLabel(f"T{i+1}")
            name.setAlignment(Qt.AlignCenter)
            name.setProperty("static", True)
            
            val: QLabel = QLabel("-- °C")
            val.setAlignment(Qt.AlignCenter)
            
            h_layout.addWidget(name)
            h_layout.addWidget(val)
            
            grid.addWidget(frame, 0, i)
            self.temp_labels.append(val)
        
        return box
    
    def _build_diagnostics(self) -> QGroupBox:
        """Create advanced diagnostics section with chart."""
        box: QGroupBox = QGroupBox("Advanced Diagnostics")
        main_layout: QVBoxLayout = QVBoxLayout(box)
        
        # Metrics frame
        metrics_frame: QFrame = QFrame()
        metrics_frame.setFrameShape(QFrame.StyledPanel)
        metrics_frame.setLineWidth(2)
        metrics_frame.setMinimumHeight(45)
        
        h_layout: QHBoxLayout = QHBoxLayout(metrics_frame)
        h_layout.setContentsMargins(12, 6, 12, 6)
        
        self.lbl_power: QLabel = QLabel("Power: -- kW")
        self.lbl_eff: QLabel = QLabel("Efficiency: -- %")
        self.lbl_ir: QLabel = QLabel("Pack IR: -- mΩ")
        
        for lbl in [self.lbl_power, self.lbl_eff, self.lbl_ir]:
            lbl.setAlignment(Qt.AlignCenter)
            h_layout.addWidget(lbl)
        
        main_layout.addWidget(metrics_frame)
        
        # Histogram chart
        self.barset: QBarSet = QBarSet("ΔV mV")
        self.series: QBarSeries = QBarSeries()
        self.series.append(self.barset)
        
        self.chart: QChart = QChart()
        self.chart.addSeries(self.series)
        self.chart.setTitle("Cell Deviation Histogram")
        
        axis_x: QValueAxis = QValueAxis()
        axis_x.setRange(0, BMSConfig.NUM_CELLS)
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.series.attachAxis(axis_x)
        
        axis_y: QValueAxis = QValueAxis()
        axis_y.setRange(-50, 50)
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        self.series.attachAxis(axis_y)
        
        self.chart_view: QChartView = QChartView(self.chart)
        self.chart_view.setMinimumHeight(220)
        
        main_layout.addWidget(self.chart_view)
        
        return box
    
    def _build_bottom_controls(self) -> QHBoxLayout:
        """Create bottom control panel with buttons and theme selector."""
        layout: QHBoxLayout = QHBoxLayout()
        
        # Connection buttons
        self.btn_connect: QPushButton = QPushButton("Connect")
        self.btn_disconnect: QPushButton = QPushButton("Disconnect")
        self.btn_start: QPushButton = QPushButton("Start Log")
        self.btn_stop: QPushButton = QPushButton("Stop Log")
        self.btn_exit: QPushButton = QPushButton("Exit")
        
        # Connect button signals
        self.btn_connect.clicked.connect(self._connect_com_port)
        self.btn_disconnect.clicked.connect(self._disconnect_com_port)
        self.btn_start.clicked.connect(self._start_logging)
        self.btn_stop.clicked.connect(self._stop_logging)
        self.btn_exit.clicked.connect(self.close)
        
        # Theme selector
        self.theme_combo: QComboBox = QComboBox()
        for name, filename in self._available_qss:
            self.theme_combo.addItem(name, filename)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        
        # Assemble layout
        layout.addWidget(self.btn_connect)
        layout.addWidget(self.btn_disconnect)
        layout.addStretch()
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        layout.addWidget(QLabel("Theme"))
        layout.addWidget(self.theme_combo)
        layout.addStretch()
        layout.addWidget(self.btn_exit)
        
        # Set initial button states
        self._update_com_buttons(connected=False)
        
        return layout
    
    def _connect_com_port(self) -> None:
        """Prompt user to select and connect to a COM port."""
        ports: List[str] = self._provider.list_serial_ports()
        
        if not ports:
            QMessageBox.warning(self, "COM Connection", "No COM ports detected!")
            return
        
        port: str
        ok: bool
        port, ok = QInputDialog.getItem(
            self, "Select COM Port", "Available COM Ports:", ports, 0, False
        )
        
        if ok and port:
            if self._provider.connect(port):
                QMessageBox.information(
                    self, "COM Connection", f"Connected to {port} successfully!"
                )
                self._update_com_buttons(connected=True)
            else:
                QMessageBox.critical(
                    self, "COM Connection Error", 
                    f"Failed to connect to {port}"
                )
                self._update_com_buttons(connected=False)
    
    def _disconnect_com_port(self) -> None:
        """Disconnect from the current COM port."""
        if self._provider.disconnect():
            QMessageBox.information(
                self, "COM Connection", "Disconnected successfully!"
            )
            self._update_com_buttons(connected=False)
        else:
            QMessageBox.critical(
                self, "COM Disconnect Error", "Failed to disconnect"
            )
    
    def _update_com_buttons(self, connected: bool) -> None:
        """Update button states based on connection status."""
        self.btn_connect.setEnabled(not connected)
        self.btn_disconnect.setEnabled(connected)
    
    def _start_logging(self) -> None:
        """Start data logging."""
        if self._logger.start():
            QMessageBox.information(
                self, "Logging", "Data logging started successfully!"
            )
        else:
            QMessageBox.warning(
                self, "Logging", "Failed to start logging. Check permissions."
            )
    
    def _stop_logging(self) -> None:
        """Stop data logging."""
        self._logger.stop()
        QMessageBox.information(self, "Logging", "Data logging stopped.")
    
    def closeEvent(self, event) -> None:
        """Handle application close event with proper cleanup."""
        # Stop polling
        self._timer.stop()
        
        # Disconnect from serial port
        if self._provider.is_connected:
            self._provider.disconnect()
        
        # Stop logging
        if self._logger.is_logging:
            self._logger.stop()
        
        logger.info("Application closing")
        event.accept()
    
    def _update_ui(self, data: Dict[str, Any]) -> None:
        """
        Update UI with new BMS data.
        
        Args:
            data: Dictionary containing BMS measurements.
        """
        pack_v: float = data["packV"]
        pack_i: float = data["packI"]
        cells: List[float] = data["cells"]
        
        # Update pack overview
        self.pack_v.setText(f"{pack_v:.1f} V")
        self.pack_i.setText(f"{pack_i:.1f} A")
        self.soc.setText(f"{data['soc']} %")
        self.soh.setText(f"{data['soh']} %")
        self.v_delta.setText(f"{data['delta']*1000:.0f} mV")
        
        # Calculate and display power
        power: float = pack_v * pack_i / 1000
        self.lbl_power.setText(f"Power: {power:.2f} kW")
        
        # Calculate efficiency (simplified model)
        eff: float = 95.0 if pack_i > 0 else 0.0
        self.lbl_eff.setText(f"Efficiency: {eff:.1f} %")
        
        # Calculate internal resistance
        if self._prev_current is not None:
            delta_i: float = pack_i - self._prev_current
            delta_v: float = pack_v - self._prev_pack_v
            
            if abs(delta_i) > BMSConfig.CURRENT_DELTA_THRESHOLD:
                resistance: float = abs(delta_v / delta_i)
                self._ir_history.append(resistance)
                
                if self._ir_history:
                    avg_ir: float = sum(self._ir_history) / len(self._ir_history)
                    self.lbl_ir.setText(f"Pack IR: {avg_ir*1000:.2f} mΩ")
        
        self._prev_current = pack_i
        self._prev_pack_v = pack_v
        
        # Update cell voltages with color coding
        v_min: float = min(cells)
        v_max: float = max(cells)
        
        for lbl, voltage in zip(self.cell_value_labels, cells):
            lbl.setText(f"{voltage:.3f} V")
            
            # Color code based on voltage level
            if voltage < BMSConfig.CELL_VOLTAGE_CRITICAL_LOW:
                lbl.setStyleSheet("color: red;")
            elif voltage < BMSConfig.CELL_VOLTAGE_WARNING_LOW:
                lbl.setStyleSheet("color: orange;")
            else:
                lbl.setStyleSheet("color: lightgreen;")
        
        # Update temperature displays
        for lbl, temp in zip(self.temp_labels, data["temps"]):
            lbl.setText(f"{temp} °C")
        
        # Update histogram
        v_avg: float = sum(cells) / len(cells)
        deviations: List[float] = [(v - v_avg) * 1000 for v in cells]
        
        self.barset.remove(0, self.barset.count())
        for dev in deviations:
            self.barset << dev
        
        # Log data if logging is active
        self._logger.log(data)


def main() -> int:
    """
    Main entry point for the BMS Dashboard application.
    
    Returns:
        Application exit code.
    """
    app: QApplication = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("BMS Dashboard")
    app.setOrganizationName("ATRI")
    
    # Create and show main window
    window: BMSWindow = BMSWindow(app)
    window.show()
    
    logger.info("BMS Dashboard started")
    
    return sys.exit(app.exec())


if __name__ == "__main__":
    sys.exit(main())
