import sys
import os
import json
import time
import math
import random
from datetime import datetime
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QProgressBar, QTextEdit, QFileDialog, QMessageBox,
                             QTabWidget, QTableView, QComboBox, QScrollArea, QTableWidget, QTableWidgetItem,
                             QListWidget, QGroupBox, QListWidgetItem, QFrame, QSplitter, QGraphicsView,
                             QGraphicsScene, QGraphicsPixmapItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMimeData, QPoint, QPointF
from PyQt5.QtGui import (QDrag, QPixmap, QPainter, QPen, QFont, QPainterPath, QColor, 
                         QLinearGradient, QBrush, QPolygonF)

# Import your script functions
from scripts.step_01_data_cleaning import run_cleaning
from scripts.step_02_fd_discovery import run_fd_discovery
from scripts.step_03_key_nf_analysis import run_key_analysis
from scripts.step_04_3nf_decomposition import run_3nf_decomposition
from scripts.step_05_ER_Chen_Export import run_er_export

# --- Path Setup ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(APP_DIR)

class DraggableButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.original_text = text

    def mouseMoveEvent(self, e):
        if e.buttons() != Qt.LeftButton:
            return

        mime_data = QMimeData()
        mime_data.setData("application/x-etl-step", self.original_text.encode())
        mime_data.setText(self.original_text)

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.MoveAction)

class DraggableLabel(QLabel):
    moved = pyqtSignal()

    def __init__(self, text, parent):
        super().__init__(text, parent)
        self.offset = QPoint()
        self.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #5dade2;
                border-radius: 8px;
                padding: 12px;
                color: #2c3e50;
                font-weight: bold;
            }
        """)
        self.adjustSize()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.offset = e.pos()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton:
            self.move(self.mapToParent(e.pos() - self.offset))
            self.moved.emit()

    def mouseReleaseEvent(self, e):
        self.offset = QPoint()

class Canvas(QFrame):
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.setFrameShape(QFrame.StyledPanel)
        self.setAcceptDrops(True)
        self.items = []
        self.connections = []
        self.setStyleSheet("background-color: #fdfefe;")

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat("application/x-etl-step"):
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        if e.mimeData().hasFormat("application/x-etl-step"):
            item_text = e.mimeData().text()
            
            # Enforce step order
            expected_index = self.app.last_completed_canvas_step + 1
            try:
                current_index = self.app.step_order.index(item_text)
            except ValueError:
                return # Should not happen if button text is in map

            if current_index != expected_index:
                error_msg = f"Invalid step order. Please add '<b>{self.app.step_order[expected_index]}</b>' next."
                QMessageBox.critical(self, "Workflow Error", error_msg)
                e.ignore()
                return

            pos = e.pos()
            self.add_item(item_text, pos)
            e.accept()

            if item_text in self.app.task_map:
                self.app.task_map[item_text]()
        else:
            e.ignore()

    def add_item(self, text, pos):
        label = DraggableLabel(text, self)
        label.move(pos - label.rect().center())
        label.show()
        label.moved.connect(self.update)
        
        if self.items:
            last_item = self.items[-1]
            self.connections.append((last_item, label))

        self.items.append(label)
        self.update()

    def clear(self):
        for item in self.items:
            item.deleteLater()
        self.items.clear()
        self.connections.clear()
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw Grid Background
        grid_size = 20
        width = self.width()
        height = self.height()
        grid_pen = QPen(QColor("#e9f7ef"), 1, Qt.SolidLine)
        painter.setPen(grid_pen)
        for x in range(0, width, grid_size):
            painter.drawLine(x, 0, x, height)
        for y in range(0, height, grid_size):
            painter.drawLine(0, y, width, y)

        # Draw Connections
        for start_item, end_item in self.connections:
            start_pos = start_item.geometry().center()
            end_pos = end_item.geometry().center()
            
            path = QPainterPath()
            path.moveTo(start_pos)

            control_offset = 80
            ctrl1 = QPointF(start_pos.x() + control_offset, start_pos.y())
            ctrl2 = QPointF(end_pos.x() - control_offset, end_pos.y())
            path.cubicTo(ctrl1, ctrl2, end_pos)

            gradient = QLinearGradient(start_pos, end_pos)
            gradient.setColorAt(0.0, QColor("#85c1e9"))
            gradient.setColorAt(1.0, QColor("#3498db"))
            line_pen = QPen(gradient, 3)
            painter.setPen(line_pen)
            painter.drawPath(path)

            # Draw Arrow Head
            angle = path.angleAtPercent(1.0)
            arrow_size = 15

            painter.save()
            arrow_pen = QPen(QColor("#3498db"), 2)
            painter.setPen(arrow_pen)
            painter.setBrush(Qt.NoBrush)

            painter.translate(end_pos)
            painter.rotate(-angle)

            arrow_head = QPolygonF([
                QPointF(-arrow_size, -arrow_size / 2),
                QPointF(0, 0),
                QPointF(-arrow_size, arrow_size / 2)
            ])
            
            painter.drawPolyline(arrow_head)
            painter.restore()

class ZoomableView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

    def wheelEvent(self, event):
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)

class WorkerThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    log = pyqtSignal(str)
    info = pyqtSignal(str)
    enable_button = pyqtSignal(str)
    start_progress = pyqtSignal()
    stop_progress = pyqtSignal()

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.start_progress.emit()
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.stop_progress.emit()

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETL Pipeline")
        self.setGeometry(100, 100, 1400, 900)
        self.input_csv_path = None
        self.input_csv_basename = None
        self.performance_data = []
        self.current_step_name = None
        self.start_time = None

        self.step_order = [
            "Load CSV",
            "1. Clean Data (1NF)",
            "2. Find FDs",
            "3. Find Candidate Keys",
            "4. Decompose to 3NF",
            "5. Generate ERD"
        ]
        self.last_completed_canvas_step = -1

        self.base_dir = APP_DIR
        self.cleaned_dir = os.path.join(self.base_dir, "data", "cleaned")
        self.decomposed_dir = os.path.join(self.base_dir, "data", "decomposed")
        os.makedirs(self.cleaned_dir, exist_ok=True)
        os.makedirs(self.decomposed_dir, exist_ok=True)

        self.init_ui()
        self.apply_stylesheet()
        self.log("Application started.")

        self.task_map = {
            "Load CSV": self.load_csv,
            "1. Clean Data (1NF)": self.run_step_cleaning,
            "2. Find FDs": self.run_step_fd_discovery,
            "3. Find Candidate Keys": self.run_step_key_analysis,
            "4. Decompose to 3NF": self.run_step_3nf,
            "5. Generate ERD": self.run_step_er_export
        }

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # Control Frame (Left Side)
        self.control_frame = QWidget()
        self.control_frame.setFixedWidth(320)
        self.control_layout = QVBoxLayout(self.control_frame)
        self.control_layout.setAlignment(Qt.AlignTop)

        self.title_label = QLabel("ETL Control Panel")
        self.title_label.setObjectName("titleLabel")
        self.control_layout.addWidget(self.title_label, alignment=Qt.AlignCenter)

        self.buttons = {}
        self.add_button("Load CSV", self.load_csv, draggable=True)
        self.add_button("1. Clean Data (1NF)", self.run_step_cleaning)
        self.add_button("2. Find FDs", self.run_step_fd_discovery)
        self.add_button("Download FDs (.json)", self.download_fds, enabled=False, draggable=False)
        self.add_button("3. Find Candidate Keys", self.run_step_key_analysis)
        self.add_button("Download CKs (.json)", self.download_cks, enabled=False, draggable=False)
        self.add_button("4. Decompose to 3NF", self.run_step_3nf)
        self.add_button("Download Tables (.zip)", self.download_tables, enabled=False, draggable=False)
        self.add_button("5. Generate ERD", self.run_step_er_export)
        self.add_button("Download ERD (.png)", self.download_erd, enabled=False, draggable=False)

        self.progress_bar = QProgressBar()
        self.control_layout.addWidget(self.progress_bar)

        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setObjectName("logWidget")
        self.control_layout.addWidget(self.log_widget)

        self.main_layout.addWidget(self.control_frame, 1)

        # Display Frame (Right Side) with Tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("tabs")
        self.main_layout.addWidget(self.tabs, 3)

        # Canvas Tab
        self.canvas_tab = QWidget()
        self.tabs.addTab(self.canvas_tab, "Canvas")
        self.canvas_layout = QVBoxLayout(self.canvas_tab)
        canvas_top_layout = QHBoxLayout()
        canvas_top_layout.addStretch()
        clear_canvas_button = QPushButton("Clear Canvas")
        clear_canvas_button.clicked.connect(self.clear_canvas)
        canvas_top_layout.addWidget(clear_canvas_button)
        self.canvas_layout.addLayout(canvas_top_layout)
        self.canvas = Canvas(self)
        self.canvas_layout.addWidget(self.canvas)

        # Performance Report Tab
        self.performance_tab = QWidget()
        self.tabs.addTab(self.performance_tab, "Performance Report")
        self.performance_layout = QVBoxLayout(self.performance_tab)
        self.performance_table = QTableWidget()
        self.performance_table.setColumnCount(4)
        self.performance_table.setHorizontalHeaderLabels(["ETL Step", "Execution Time (s)", "Status", "Timestamp"])
        self.performance_table.horizontalHeader().setStretchLastSection(True)
        self.performance_layout.addWidget(self.performance_table)
        
        perf_summary_layout = QHBoxLayout()
        clear_perf_button = QPushButton("Clear Report")
        clear_perf_button.clicked.connect(self.clear_performance_report)
        self.total_time_label = QLabel("Total Time: 0.00s")
        perf_summary_layout.addWidget(self.total_time_label)
        perf_summary_layout.addStretch()
        perf_summary_layout.addWidget(clear_perf_button)
        self.performance_layout.addLayout(perf_summary_layout)

        # Functional Dependencies Tab
        self.fds_tab = QWidget()
        self.tabs.addTab(self.fds_tab, "Functional Dependencies")
        self.fds_layout = QVBoxLayout(self.fds_tab)
        self.fds_table = QTableWidget()
        self.fds_table.setColumnCount(2)
        self.fds_table.setHorizontalHeaderLabels(["LHS", "RHS"])
        self.fds_table.horizontalHeader().setStretchLastSection(True)
        self.fds_table.setAlternatingRowColors(True)
        self.fds_layout.addWidget(self.fds_table)

        # Candidate Keys Tab
        self.cks_tab = QWidget()
        self.tabs.addTab(self.cks_tab, "Candidate Keys")
        self.cks_layout = QVBoxLayout(self.cks_tab)
        self.cks_table = QTableWidget()
        self.cks_table.setColumnCount(1)
        self.cks_table.setHorizontalHeaderLabels(["Candidate Key"])
        self.cks_table.horizontalHeader().setStretchLastSection(True)
        self.cks_table.setAlternatingRowColors(True)
        self.cks_layout.addWidget(self.cks_table)

        # Decomposed Tables Tab
        self.tables_tab = QWidget()
        self.tabs.addTab(self.tables_tab, "Decomposed Tables")
        self.tables_layout = QVBoxLayout(self.tables_tab)
        self.tables_scroll_area = QScrollArea()
        self.tables_scroll_area.setWidgetResizable(True)
        self.tables_scroll_content = QWidget()
        self.tables_scroll_layout = QVBoxLayout(self.tables_scroll_content)
        self.tables_scroll_layout.setAlignment(Qt.AlignTop)
        self.tables_scroll_area.setWidget(self.tables_scroll_content)
        self.tables_layout.addWidget(self.tables_scroll_area)

        # ER Diagram Tab
        self.er_diagram_tab = QWidget()
        self.tabs.addTab(self.er_diagram_tab, "ER Diagram")
        self.er_diagram_layout = QVBoxLayout(self.er_diagram_tab)
        self.er_scene = QGraphicsScene()
        self.er_view = ZoomableView(self.er_scene)
        zoom_layout = QHBoxLayout()
        zoom_in_button = QPushButton("Zoom In")
        zoom_in_button.clicked.connect(lambda: self.er_view.scale(1.2, 1.2))
        zoom_out_button = QPushButton("Zoom Out")
        zoom_out_button.clicked.connect(lambda: self.er_view.scale(1 / 1.2, 1 / 1.2))
        fit_view_button = QPushButton("Fit to View")
        fit_view_button.clicked.connect(self.fit_er_view)
        zoom_layout.addStretch()
        zoom_layout.addWidget(zoom_in_button)
        zoom_layout.addWidget(zoom_out_button)
        zoom_layout.addWidget(fit_view_button)
        zoom_layout.addStretch()
        self.er_diagram_layout.addLayout(zoom_layout)
        self.er_diagram_layout.addWidget(self.er_view)

    def add_button(self, text, callback, enabled=True, draggable=True):
        display_text = text
        if draggable:
            button = DraggableButton(text)
            display_text = f'⠿ {text}'
            if text == "Load CSV":
                 button.clicked.connect(callback)
        else:
            button = QPushButton(text)
            button.clicked.connect(callback)
        
        button.setText(display_text)
        button.setEnabled(enabled)
        self.control_layout.addWidget(button)
        self.buttons[text] = button

    def apply_stylesheet(self):
        stylesheet = """
            QMainWindow { background-color: #f7f8fa; }
            QWidget { font-family: 'Segoe UI', Arial, sans-serif; }
            #control_frame { background-color: #ffffff; border-right: 1px solid #dcdcdc; }
            #titleLabel { font-size: 22px; font-weight: 600; color: #2c3e50; padding-bottom: 15px; padding-top: 5px; }
            QPushButton { background-color: #3498db; color: white; font-weight: bold; padding: 10px; border-radius: 4px; border: none; text-align: left; padding-left: 10px; }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:disabled { background-color: #d5dbe1; color: #888888; }
            #logWidget { background-color: #2c3e50; color: #ecf0f1; font-family: 'Consolas', 'Menlo', monospace; font-size: 11px; border: 1px solid #34495e; border-radius: 4px; }
            QTabWidget::pane { border: 1px solid #dcdcdc; border-radius: 4px; background-color: #ffffff; padding: 10px; }
            QTabBar::tab { background: #e4e7eb; color: #555; padding: 12px 20px; border: 1px solid #dcdcdc; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #ffffff; color: #3498db; font-weight: bold; border-bottom: 1px solid #ffffff; }
            QTableWidget { gridline-color: #e0e0e0; font-size: 12px; border: 1px solid #dcdcdc; border-radius: 4px; alternate-background-color: #fbfcfd; }
            QHeaderView::section { background-color: #f2f4f7; padding: 8px; border: none; border-bottom: 1px solid #dcdcdc; font-size: 12px; font-weight: bold; color: #333; }
            QListWidget { font-size: 13px; border: 1px solid #dcdcdc; border-radius: 4px; background-color: #ffffff; }
            QListWidget::item:hover { background-color: #f2f9ff; }
            QGroupBox { font-weight: bold; font-size: 16px; color: #2c3e50; border: 1px solid #d7dfe9; border-radius: 8px; margin-top: 15px; background-color: #f8f9fa; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 5px 10px; background-color: #e4e7eb; border-top-left-radius: 8px; border-top-right-radius: 8px; border-bottom: 1px solid #d7dfe9; }
            QScrollArea { border: none; }
            QGraphicsView { border-radius: 4px; border: 1px solid #dcdcdc; }
        """
        self.setStyleSheet(stylesheet)
        self.control_frame.setObjectName("control_frame")

    def clear_canvas(self):
        self.canvas.clear()
        self.last_completed_canvas_step = -1
        self.log("Canvas cleared.")

    def fit_er_view(self):
        if not self.er_scene.items():
            return
        self.er_view.fitInView(self.er_scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def run_in_thread(self, func, step_name, *args, **kwargs):
        self.current_step_name = step_name
        self.start_time = time.time()
        self.worker = WorkerThread(func, *args, **kwargs)
        self.worker.finished.connect(self.on_thread_finished)
        self.worker.error.connect(self.on_thread_error)
        self.worker.log.connect(self.log)
        self.worker.info.connect(self.show_info_message)
        self.worker.enable_button.connect(self.enable_button)
        self.worker.start_progress.connect(lambda: self.progress_bar.setRange(0, 0))
        self.worker.stop_progress.connect(lambda: self.progress_bar.setRange(0, 100))
        self.worker.start()

    def on_thread_finished(self, result):
        if self.current_step_name and self.start_time:
            duration = time.time() - self.start_time
            entry = {
                "step": self.current_step_name,
                "duration": duration,
                "status": "Success",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.performance_data.append(entry)
            self.update_performance_table()
            
            # Update canvas step tracking on success
            if self.current_step_name in self.step_order:
                step_index = self.step_order.index(self.current_step_name)
                self.last_completed_canvas_step = step_index

    def on_thread_error(self, message):
        if self.current_step_name and self.start_time:
            duration = time.time() - self.start_time
            entry = {
                "step": self.current_step_name,
                "duration": duration,
                "status": "Error",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.performance_data.append(entry)
            self.update_performance_table()
        QMessageBox.critical(self, "Error", message)

    def update_performance_table(self):
        self.performance_table.setRowCount(0)
        total_duration = 0
        for entry in self.performance_data:
            row_position = self.performance_table.rowCount()
            self.performance_table.insertRow(row_position)
            self.performance_table.setItem(row_position, 0, QTableWidgetItem(entry["step"]))
            self.performance_table.setItem(row_position, 1, QTableWidgetItem(f"{entry['duration']:.4f}"))
            status_item = QTableWidgetItem(entry["status"])
            if entry["status"] == "Error":
                status_item.setForeground(QColor("red"))
            else:
                total_duration += entry["duration"]
            self.performance_table.setItem(row_position, 2, status_item)
            self.performance_table.setItem(row_position, 3, QTableWidgetItem(entry["timestamp"]))
        self.total_time_label.setText(f"Total Successful Time: {total_duration:.4f}s")

    def clear_performance_report(self):
        self.performance_data = []
        self.update_performance_table()

    def log(self, message):
        self.log_widget.append(message)
        QApplication.processEvents()

    def show_info_message(self, message):
        QMessageBox.information(self, "Success", message)

    def enable_button(self, button_text):
        if button_text in self.buttons:
            self.buttons[button_text].setEnabled(True)

    def load_csv(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select a CSV file", "", "CSV files (*.csv);;All files (*.*)")
        if filepath:
            self.input_csv_path = filepath
            self.input_csv_basename = os.path.splitext(os.path.basename(filepath))[0]
            self.log(f"Selected: {os.path.basename(filepath)}")
            self.last_completed_canvas_step = 0 # Mark Load CSV as complete for canvas
            self.enable_button("1. Clean Data (1NF)")

    def run_step_cleaning(self):
        self.log("Cleaning data...")
        output_file = os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_cleaned.csv")
        self.run_in_thread(run_cleaning, "1. Clean Data (1NF)", self.input_csv_path, output_file)
        self.worker.finished.connect(lambda: self.show_info_message("Data cleaning complete."))
        self.worker.finished.connect(lambda: self.enable_button("2. Find FDs"))

    def run_step_fd_discovery(self):
        self.log("Finding FDs...")
        input_file = os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_cleaned.csv")
        output_file = os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_fds.json")
        self.run_in_thread(run_fd_discovery, "2. Find FDs", input_file, output_file, max_lhs_size=2)
        self.worker.finished.connect(lambda: self.show_info_message("FD discovery complete."))
        self.worker.finished.connect(lambda: self.enable_button("3. Find Candidate Keys"))
        self.worker.finished.connect(lambda: self.enable_button("Download FDs (.json)"))
        self.worker.finished.connect(self.display_fds)

    def run_step_key_analysis(self):
        self.log("Analyzing keys...")
        input_file = os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_cleaned.csv")
        fd_file = os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_fds.json")
        output_file = os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_key_analysis.json")
        self.run_in_thread(run_key_analysis, "3. Find Candidate Keys", input_file, fd_file, output_file, max_key_size=2)
        self.worker.finished.connect(lambda: self.show_info_message("Key analysis complete."))
        self.worker.finished.connect(lambda: self.enable_button("4. Decompose to 3NF"))
        self.worker.finished.connect(lambda: self.enable_button("Download CKs (.json)"))
        self.worker.finished.connect(self.display_cks)

    def run_step_3nf(self):
        self.log("Decomposing to 3NF...")
        input_file = os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_cleaned.csv")
        fd_file = os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_fds.json")
        keys_file = os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_key_analysis.json")
        decomposed_output_dir = os.path.join(self.decomposed_dir, self.input_csv_basename)
        os.makedirs(decomposed_output_dir, exist_ok=True)
        self.run_in_thread(run_3nf_decomposition, "4. Decompose to 3NF", input_file, fd_file, keys_file, decomposed_output_dir)
        self.worker.finished.connect(lambda: self.show_info_message("3NF decomposition complete."))
        self.worker.finished.connect(lambda: self.enable_button("5. Generate ERD"))
        self.worker.finished.connect(lambda: self.enable_button("Download Tables (.zip)"))
        self.worker.finished.connect(self.display_decomposed_tables)

    def run_step_er_export(self):
        self.log("Generating ER diagram...")
        summary_file = os.path.join(self.decomposed_dir, self.input_csv_basename, "3nf_decomposition_summary.json")
        output_dot = os.path.join(self.decomposed_dir, self.input_csv_basename, f"{self.input_csv_basename}_er_diagram.dot")
        self.run_in_thread(run_er_export, "5. Generate ERD", summary_file, output_dot)
        self.worker.finished.connect(lambda: self.show_info_message("ERD generated."))
        self.worker.finished.connect(lambda: self.enable_button("Download ERD (.png)"))
        self.worker.finished.connect(self.display_er_diagram)

    def download_file(self, source_path, title, file_filter, default_name):
        save_path, _ = QFileDialog.getSaveFileName(self, title, default_name, file_filter)
        if save_path:
            try:
                import shutil
                shutil.copy(source_path, save_path)
                self.show_info_message(f"Saved to {save_path}")
            except Exception as e:
                self.on_thread_error(str(e))

    def download_fds(self):
        self.download_file(os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_fds.json"), "Save FDs as...", "JSON files (*.json)", f"{self.input_csv_basename}_fds.json")

    def download_cks(self):
        self.download_file(os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_key_analysis.json"), "Save CKs as...", "JSON files (*.json)", f"{self.input_csv_basename}_key_analysis.json")

    def download_erd(self):
        self.download_file(os.path.join(self.decomposed_dir, self.input_csv_basename, f"{self.input_csv_basename}_er_diagram.png"), "Save ERD as...", "PNG files (*.png)", f"{self.input_csv_basename}_er_diagram.png")

    def download_tables(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Decomposed Tables as...", "tables.zip", "ZIP files (*.zip)")
        if not save_path:
            return
        try:
            import zipfile
            decomposed_output_dir = os.path.join(self.decomposed_dir, self.input_csv_basename)
            with zipfile.ZipFile(save_path, 'w') as zf:
                for filename in os.listdir(decomposed_output_dir):
                    if filename.endswith(".csv"):
                        zf.write(os.path.join(decomposed_output_dir, filename), arcname=filename)
            self.show_info_message(f"Tables saved to {save_path}")
        except Exception as e:
            self.on_thread_error(str(e))

    def display_fds(self):
        fd_path = os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_fds.json")
        try:
            with open(fd_path, 'r') as f:
                fds = json.load(f)
            self.fds_table.setRowCount(0)
            for lhs_str, rhs_list in fds.items():
                row_position = self.fds_table.rowCount()
                self.fds_table.insertRow(row_position)
                self.fds_table.setItem(row_position, 0, QTableWidgetItem(lhs_str))
                self.fds_table.setItem(row_position, 1, QTableWidgetItem(", ".join(rhs_list)))
            self.tabs.setCurrentWidget(self.fds_tab)
        except Exception as e:
            self.on_thread_error(f"Could not read FDs file: {e}")

    def display_cks(self):
        ck_path = os.path.join(self.cleaned_dir, f"{self.input_csv_basename}_key_analysis.json")
        try:
            with open(ck_path, 'r') as f:
                data = json.load(f)
            
            candidate_keys = data.get('candidate_keys', [])
            self.cks_table.setRowCount(len(candidate_keys))
            
            for i, ck in enumerate(candidate_keys):
                item = QTableWidgetItem(", ".join(ck))
                self.cks_table.setItem(i, 0, item)
                
            self.tabs.setCurrentWidget(self.cks_tab)
        except Exception as e:
            self.on_thread_error(f"Could not read candidate keys file: {e}")

    def display_decomposed_tables(self):
        decomposed_output_dir = os.path.join(self.decomposed_dir, self.input_csv_basename)
        for i in reversed(range(self.tables_scroll_layout.count())):
            self.tables_scroll_layout.itemAt(i).widget().setParent(None)

        try:
            summary_path = os.path.join(decomposed_output_dir, "3nf_decomposition_summary.json")
            with open(summary_path, 'r') as f:
                summary = json.load(f)

            for table_details in summary.get('relations', []):
                table_name = table_details.get('table', 'Unnamed Table')
                group_box = QGroupBox(table_name)
                layout = QVBoxLayout()
                attributes_list = QListWidget()
                for attr in table_details.get('attributes', []):
                    item = QListWidgetItem(attr)
                    if attr in table_details.get('primary_key', []):
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                        item.setText(f"🔑 {attr}")
                    attributes_list.addItem(item)
                layout.addWidget(attributes_list)
                group_box.setLayout(layout)
                self.tables_scroll_layout.addWidget(group_box)

            self.tabs.setCurrentWidget(self.tables_tab)
        except Exception as e:
            self.on_thread_error(f"Could not display decomposed tables: {e}")

    def display_er_diagram(self):
        er_diagram_path = os.path.join(self.decomposed_dir, self.input_csv_basename, f"{self.input_csv_basename}_er_diagram.png")
        self.er_scene.clear()
        try:
            if os.path.exists(er_diagram_path):
                pixmap = QPixmap(er_diagram_path)
                self.er_scene.addPixmap(pixmap)
                self.fit_er_view()
                self.tabs.setCurrentWidget(self.er_diagram_tab)
            else:
                self.er_scene.addText("ER Diagram not found.")
                self.log(f"ER Diagram not found at {er_diagram_path}")
        except Exception as e:
            self.on_thread_error(f"Could not display ER Diagram: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_app = App()
    main_app.show()
    sys.exit(app.exec_())