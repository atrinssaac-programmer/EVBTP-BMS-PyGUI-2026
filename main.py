import sys
import os
import ctypes
from pathlib import Path
from collections import deque

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from PySide6.QtCharts import (
    QChart, QChartView, QBarSeries,
    QBarSet, QValueAxis
)


from config import BMSConfig
from data_provider import BMSDataProvider
from logger import BMSLogger

# =========================
# Windows Taskbar Icon
# =========================
myappid = 'atri.evbtp.bmsui.v4'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# =========================
# FONT MANAGER
# =========================
class FontManager:
    def __init__(self, base_title=24, base_value=16, base_temp=14, min_size=8):
        self.base_title = base_title
        self.base_value = base_value
        self.base_temp = base_temp
        self.min_size = min_size

    def apply(self, widget, role="value", scale=1.0):
        f = widget.font()
        base_size = getattr(self, f"base_{role}", self.base_value)
        f.setPointSize(max(self.min_size, int(base_size * scale)))
        widget.setFont(f)

# =========================
class BMSWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        # Set application icon
        icon_path = Path(__file__).parent / "assets" / "ATRI_Logo.ico"
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            app.setWindowIcon(icon)
            self.setWindowIcon(icon)

        self.setWindowTitle("BMS Dashboard - Created by ATRI, Pyin Oo Lwin")
        self.resize(1280, 680)
        self.base_width = 1280

        # ---------------- THEME ENGINE ----------------
        self.available_qss = [
            ("ATRI Dark", "atri_dark.qss"),
            ("ATRI Light", "atri_light.qss"),
            ("EV Blue", "ev_blue.qss"),
        ]
        self.load_qss(Path(__file__).parent / "themes" / "atri_dark.qss")

        # ---------------- DATA ----------------
        self.provider = BMSDataProvider()
        self.logger = BMSLogger()
        self.provider.data_ready.connect(self.update_ui)

        self.timer = QTimer()
        self.timer.timeout.connect(self.provider.poll)
        self.timer.start(BMSConfig.UPDATE_MS)

        # ---------------- DIAGNOSTIC STATE ----------------
        self.prev_current = None
        self.prev_packV = None
        self.ir_history = deque(maxlen=50)
        
        # Font Manager
        self.font_mgr = FontManager()
        
        # ---------------- UI ----------------
        self.build_ui()

    # =========================
    # THEME
    # =========================
    def load_qss(self, filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print("QSS load error:", e)

    def theme_changed(self, idx):
        filename = self.themeCombo.itemData(idx)
        if filename:
            self.load_qss(Path(__file__).parent / "themes" / filename)

    # =========================
    def make_frame(self):
        f = QFrame()
        f.setFrameShape(QFrame.StyledPanel)
        f.setLineWidth(2)
        f.setMinimumHeight(40) 
        return f

    # -------------------------
    # Responsive scale factor (width + DPI aware)
    # -------------------------
    def get_scale_factor(self):
        screen = self.screen() or QApplication.primaryScreen()
        dpi_scale = screen.devicePixelRatio()  
        width_scale = self.width() / self.base_width
        return width_scale * dpi_scale
    
    # -------------------------
    # Dynamic font scaling on resize
    # -------------------------
    def resizeEvent(self, event):
        scale = self.get_scale_factor()
        self.font_mgr.apply(self.titleLabel, "title", scale)

        for lbl in [self.packV, self.packI, self.soc, self.soh, self.vdelta]:
            self.font_mgr.apply(lbl, "value", scale)

        for lbl in self.tempLabels:
            self.font_mgr.apply(lbl, "temp", scale)

        super().resizeEvent(event)
    
    # =========================
    def build_ui(self):
        # ---- Scroll Area ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        scroll.setWidget(container)

        self.setCentralWidget(scroll)

        main = QVBoxLayout(container)

        # main.addWidget(self.build_title())
        main.addWidget(self.build_title_with_logo())
        main.addWidget(self.build_pack())
        main.addWidget(self.build_cells())
        main.addWidget(self.build_temps())
        main.addWidget(self.build_diagnostics())
        main.addLayout(self.build_bottom())
        main.addWidget(self.build_deptitle())

    # ---------------- TITLE ----------------
    def build_title(self):
        self.titleLabel = QLabel("EV Battery Technology Platform - BMS Monitoring System")
        self.titleLabel.setAlignment(Qt.AlignCenter)
        self.titleLabel.setObjectName("title")
        return self.titleLabel

    # ---------------- TITLE WITH LOGO ----------------
    def build_title_with_logo(self):
        """Create a horizontal layout with logo and title text."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        # Logo
        logo_path = Path(__file__).parent / "assets" / "ATRI_Logo.png"
        logo_label = QLabel()
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            # Scale logo to reasonable height (e.g. 32px) while keeping aspect ratio
            scaled_pixmap = pixmap.scaledToHeight(64, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            # Fallback: show nothing or a placeholder
            logo_label.setVisible(False)

        # Title label
        self.titleLabel = QLabel("EV Battery Technology Platform - BMS Monitoring System")
        self.titleLabel.setAlignment(Qt.AlignCenter)
        self.titleLabel.setObjectName("title")
        # Fix the height so it doesn't take too much space
        self.titleLabel.setMaximumHeight(90)
        self.titleLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout.addWidget(logo_label)
        layout.addWidget(self.titleLabel)

        return container

    # ---------- Department TITLE ----------
    def build_deptitle(self):
        deptitle = QLabel("Design & Develop by Automotive Technology Research Institute")
        deptitle.setObjectName("deptitle")
        deptitle.setAlignment(Qt.AlignRight)
        # Fix the height so it doesn't take too much space
        deptitle.setMaximumHeight(30)
        deptitle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return deptitle
    
    # ---------------- PACK ----------------
    def build_pack(self):
        box = QGroupBox("Pack Overview")
        grid = QGridLayout(box)

        self.packV = QLabel("--")
        self.packI = QLabel("--")
        self.soc   = QLabel("--")
        self.soh   = QLabel("--")
        self.vdelta= QLabel("--")

        items = [
            ("Pack V", self.packV),
            ("Pack I", self.packI),
            ("SOC",    self.soc),
            ("SOH",    self.soh),
            ("ΔV",     self.vdelta),
        ]

        for i, (text, value_lbl) in enumerate(items):

            # ---- Tile Frame ----
            frame = QFrame()
            frame.setFrameShape(QFrame.StyledPanel)
            frame.setLineWidth(2)
            frame.setMinimumHeight(40)

            h = QHBoxLayout(frame)
            h.setContentsMargins(8,4,8,4)

            name_lbl = QLabel(text)
            name_lbl.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            name_lbl.setProperty("static", True)

            value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_lbl.setProperty("static", True)

            h.addWidget(name_lbl)
            h.addWidget(value_lbl)

            grid.addWidget(frame, 0, i)

        return box


    # ---------------- CELLS ----------------
    def build_cells(self):
        box = QGroupBox("Cell Voltages")
        grid = QGridLayout(box)

        self.cellValueLabels = []

        for i in range(BMSConfig.NUM_CELLS):

            # ---- container layout (no frame) ----
            h = QHBoxLayout()

            # ---------- Name Frame ----------
            name_frame = QFrame()
            name_frame.setFrameShape(QFrame.StyledPanel)
            # name_frame.setLineWidth(2)
            name_frame.setLineWidth(6)

            name_layout = QHBoxLayout(name_frame)
            name_layout.setContentsMargins(6,2,6,2)

            name = QLabel(f"C{i+1}")
            name.setAlignment(Qt.AlignCenter)
            name.setProperty("static", True)
            name_layout.addWidget(name)

            # ---------- Value Frame ----------
            val_frame = QFrame()
            val_frame.setFrameShape(QFrame.StyledPanel)
            val_frame.setLineWidth(2)

            val_layout = QHBoxLayout(val_frame)
            val_layout.setContentsMargins(6,2,6,2)

            val = QLabel("-- V")
            val.setAlignment(Qt.AlignCenter)
            val_layout.addWidget(val)

            # ---- Add both frames ----
            h.addWidget(name_frame)
            h.addWidget(val_frame)

            r,c = divmod(i, BMSConfig.CELLS_PER_ROW)
            grid.addLayout(h, r, c)

            self.cellValueLabels.append(val)

        return box


    # ---------------- TEMPS ----------------
    def build_temps(self):
        box = QGroupBox("Temperatures")
        grid = QGridLayout(box)

        self.tempLabels=[]

        for i in range(BMSConfig.NUM_TEMPS):
            f=self.make_frame()
            v=QHBoxLayout(f)

            n=QLabel(f"T{i+1}")
            n.setAlignment(Qt.AlignCenter)
            n.setProperty("static", True)

            val=QLabel("-- °C")
            val.setAlignment(Qt.AlignCenter)

            v.addWidget(n)
            v.addWidget(val)

            grid.addWidget(f,0,i)
            self.tempLabels.append(val)

        return box

    # ---------------- DIAGNOSTICS ----------------
    def build_diagnostics(self):
        box = QGroupBox("Advanced Diagnostics")
        main_layout = QVBoxLayout(box)

        # -------- Metrics Frame  --------
        metrics_frame = QFrame()
        metrics_frame.setFrameShape(QFrame.StyledPanel)
        metrics_frame.setLineWidth(2)
        metrics_frame.setMinimumHeight(45)

        h = QHBoxLayout(metrics_frame)
        h.setContentsMargins(12,6,12,6)

        self.lblPower = QLabel("Power: -- kW")
        self.lblPower.setProperty("static", False)
        self.lblEff   = QLabel("Efficiency: -- %")
        self.lblEff.setProperty("static", False)
        self.lblIR    = QLabel("Pack IR: -- mΩ")
        self.lblIR.setProperty("static", False)

        for lbl in [self.lblPower, self.lblEff, self.lblIR]:
            lbl.setAlignment(Qt.AlignCenter)
            h.addWidget(lbl)

        main_layout.addWidget(metrics_frame)
        
        # -------- Histogram  --------
        self.barset = QBarSet("ΔV mV")
        self.series = QBarSeries()
        self.series.append(self.barset)

        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.setTitle("Cell Deviation Histogram")

        axisX = QValueAxis()
        axisX.setRange(0, BMSConfig.NUM_CELLS)
        self.chart.addAxis(axisX, Qt.AlignBottom)
        self.series.attachAxis(axisX)

        axisY = QValueAxis()
        axisY.setRange(-50, 50)
        self.chart.addAxis(axisY, Qt.AlignLeft)
        self.series.attachAxis(axisY)

        self.chartView = QChartView(self.chart)
        self.chartView.setMinimumHeight(220)

        main_layout.addWidget(self.chartView)

        return box

    # ---------------- BOTTOM ----------------
    def build_bottom(self):
        lay = QHBoxLayout()

        # Buttons
        self.btnConnect = QPushButton("Connect")
        self.btnDisconnect = QPushButton("Disconnect")
        self.btnStart=QPushButton("Start Log")
        self.btnStop=QPushButton("Stop Log")
        self.btnExit=QPushButton("Exit")

        self.btnConnect.clicked.connect(self.connect_com_port)
        self.btnDisconnect.clicked.connect(self.disconnect_com_port)
        self.btnStart.clicked.connect(self.logger.start)
        self.btnStop.clicked.connect(self.logger.stop)
        self.btnExit.clicked.connect(self.close)

        # Theme dropdown
        self.themeCombo = QComboBox()
        for name, filename in self.available_qss:
            self.themeCombo.addItem(name, filename)

        self.themeCombo.currentIndexChanged.connect(self.theme_changed)

        # Add buttons to layout
        lay.addWidget(self.btnConnect)
        lay.addWidget(self.btnDisconnect)
        lay.addStretch()
        lay.addWidget(self.btnStart)
        lay.addWidget(self.btnStop)
        lay.addWidget(QLabel("Theme"))
        lay.addWidget(self.themeCombo)
        lay.addStretch()
        lay.addWidget(self.btnExit)
        
        # Set initial button states
        self.update_com_buttons(connected=False)
        
        return lay

        # ---------- COM PORT HANDLERS ----------
    def connect_com_port(self):
        """
        Prompt user to select a COM port, then connect via BMSDataProvider.
        """
        ports = self.provider.list_serial_ports()
        if not ports:
            QMessageBox.warning(self, "COM Connection", "No COM ports detected!")
            return

        port, ok = QInputDialog.getItem(self, "Select COM Port", "Available COM Ports:", ports, 0, False)
        if ok and port:
            try:
                self.provider.connect(port)
                QMessageBox.information(self, "COM Connection", f"Connected to {port} successfully!")
                self.update_com_buttons(connected=True)
            except Exception as e:
                QMessageBox.critical(self, "COM Connection Error", f"Failed to connect:\n{str(e)}")
                self.update_com_buttons(connected=False)

    def disconnect_com_port(self):
        """
        Disconnect from the BMS COM port.
        """
        try:
            self.provider.disconnect()
            QMessageBox.information(self, "COM Connection", "Disconnected successfully!")
            self.update_com_buttons(connected=False)
        except Exception as e:
            QMessageBox.critical(self, "COM Disconnect Error", f"Failed to disconnect:\n{str(e)}")

    # ---------- BUTTON STATE UPDATE ----------
    def update_com_buttons(self, connected: bool):
        """
        Enable/disable Connect and Disconnect buttons based on connection status.
        """
        self.btnConnect.setEnabled(not connected)
        self.btnDisconnect.setEnabled(connected)
    
    # =========================
    # UPDATE UI
    # =========================
    def update_ui(self,data):
        packV=data["packV"]
        packI=data["packI"]
        cells=data["cells"]

        self.packV.setText(f"{packV:.1f} V")
        self.packI.setText(f"{packI:.1f} A")
        self.soc.setText(f"{data['soc']} %")
        self.soh.setText(f"{data['soh']} %")
        self.vdelta.setText(f"{data['delta']*1000:.0f} mV")

        # -------- POWER --------
        power = packV*packI/1000
        self.lblPower.setText(f"Power: {power:.2f} kW")

        eff = 95.0 if packI>0 else 0.0
        self.lblEff.setText(f"Efficiency: {eff:.1f} %")

        # -------- IR --------
        if self.prev_current is not None:
            dI=packI-self.prev_current
            dV=packV-self.prev_packV
            if abs(dI)>1:
                R=abs(dV/dI)
                self.ir_history.append(R)
                avg=sum(self.ir_history)/len(self.ir_history)
                self.lblIR.setText(f"Pack IR: {avg*1000:.2f} mΩ")

        self.prev_current=packI
        self.prev_packV=packV

        # -------- MIN/MAX --------
        vmin=min(cells)
        vmax=max(cells)

        for lbl,v in zip(self.cellValueLabels,cells):
            lbl.setText(f"{v:.3f} V")

            if v<3.2: lbl.setStyleSheet("color:red;")
            elif v<3.4: lbl.setStyleSheet("color:orange;")
            else: lbl.setStyleSheet("color:lightgreen;")

#             f.setStyleSheet("")
#             if v==vmax:
#                 f.setStyleSheet("border:2px solid cyan;")
#             elif v==vmin:
#                 f.setStyleSheet("border:2px solid magenta;")

        # -------- TEMPS --------
        for lbl,t in zip(self.tempLabels,data["temps"]):
            lbl.setText(f"{t} °C")

        # -------- HISTOGRAM --------
        vavg=sum(cells)/len(cells)
        devs=[(v-vavg)*1000 for v in cells]

        self.barset.remove(0,self.barset.count())
        for d in devs:
            self.barset<<d

        self.logger.log(data)

# =========================
if __name__=="__main__":
    app=QApplication(sys.argv)
    w=BMSWindow(app)
    w.show()
    sys.exit(app.exec())
