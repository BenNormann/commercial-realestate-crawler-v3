"""
Desktop GUI application for the Commercial Real Estate Crawler.
Now using Windows Task Scheduler instead of Windows Service.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import threading

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# Import debug logger
from debug.logger import setup_logger
# Set up logger
logger = setup_logger("gui", logging.DEBUG)

# Import PyQt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QCheckBox, QComboBox, QPushButton, QTabWidget,
    QListWidget, QListWidgetItem, QProgressBar, QSpinBox, QTimeEdit,
    QGroupBox, QFormLayout, QFileDialog, QMessageBox, QTextEdit,
    QScrollArea, QSplitter, QFrame
)
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QIcon, QFont, QPalette

# Import project modules
from task_scheduler.task_manager import TaskSchedulerManager
from scraper.scraper_manager import ScraperManager
from utils.email_sender import EmailSender
import userinfo

# Configuration constants
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# Default configuration
DEFAULT_CONFIG = {
    'property_types': ['Office', 'Retail', 'Industrial', 'Multifamily'],
    'min_price': '',
    'max_price': '',
    'location': 'Seattle, WA',
    'websites': ['commercialmls.com', 'loopnet.com'],
    'days_back': 1,
    'save_credentials': False,
    'send_email': False,
    'dark_mode': True,
    'enable_background': False,
    'hide_terminal': True
}

class WorkerThread(QThread):
    """Worker thread for background tasks"""
    progress_updated = pyqtSignal(dict)
    
    def __init__(self, task_manager, parent=None):
        super().__init__(parent)
        self.running = True
        self.task_manager = task_manager
        self.parent = parent
    
    def run(self):
        """Run the worker thread"""
        while self.running:
            # Get task status
            try:
                status = self.task_manager.get_task_status()
                
                # Add latest results info if available
                try:
                    latest_results_file = os.path.join(CONFIG_DIR, "latest_results.json")
                    if os.path.exists(latest_results_file):
                        with open(latest_results_file, 'r') as f:
                            latest_data = json.load(f)
                            status['latest_results'] = latest_data
                except Exception as e:
                    logger.debug(f"Could not load latest results: {e}")
                
                self.progress_updated.emit(status)
            except Exception as e:
                logger.error(f"Error in worker thread: {str(e)}")
                status = {"installed": False, "enabled": False, "error": str(e)}
                self.progress_updated.emit(status)
            
            # Sleep for a bit
            time.sleep(3)
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        self.wait()

class MainWindow(QMainWindow):
    """Main window for the application"""
    
    def __init__(self, debug_mode=False):
        """Initialize the main window"""
        super().__init__()
        
        # Store debug mode
        self.debug_mode = debug_mode
        self.scraping_running = False  # Track if scraping is currently running
        
        # Initialize task manager
        self.task_manager = TaskSchedulerManager()
        
        # Setup window
        self.setWindowTitle("Commercial Real Estate Crawler - Task Scheduler")
        self.setGeometry(100, 100, 1200, 800)
        
        # Setup styles (dark theme)
        self.setup_dark_theme()
        
        # Load configuration
        self.load_config()
        
        # Create and set up the UI
        self.setup_ui()
        
        # Load values into UI elements
        self.load_values()
        
        # Setup auto-save connections after loading values
        self.setup_auto_save()
        
        # Setup background status checker
        self.setup_status_checker()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    self.user_config = json.load(f)
            else:
                # Create config directory if it doesn't exist
                os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
                self.user_config = DEFAULT_CONFIG.copy()
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(self.user_config, f, indent=2)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            self.user_config = DEFAULT_CONFIG.copy()
    
    def setup_dark_theme(self):
        """Set up modern dark theme for the application"""
        # Apply a modern dark stylesheet with proper contrast
        self.setStyleSheet("""
            /* Main Window */
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            
            /* Input Fields - Dark background with white text */
            QLineEdit, QSpinBox, QTimeEdit {
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 11px;
                selection-background-color: #0078d4;
            }
            
            QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus {
                border-color: #0078d4;
                background-color: #404040;
            }
            
            QLineEdit::placeholder {
                color: #888888;
            }
            
            /* Buttons */
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                color: white;
                font-weight: 500;
                font-size: 11px;
                min-height: 20px;
            }
            
            QPushButton:hover {
                background-color: #106ebe;
            }
            
            QPushButton:pressed {
                background-color: #005a9e;
            }
            
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            
            /* Checkboxes */
            QCheckBox {
                color: #ffffff;
                font-size: 11px;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid #555555;
                background-color: #3c3c3c;
            }
            
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #ffffff;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }
            
            QCheckBox::indicator:hover {
                border-color: #0078d4;
            }
            
            /* Group Boxes */
            QGroupBox {
                font-weight: 600;
                font-size: 12px;
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #323232;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: #ffffff;
                background-color: #323232;
            }
            
            /* Tabs */
            QTabWidget::pane {
                border: 2px solid #555555;
                border-radius: 6px;
                background-color: #2b2b2b;
                margin-top: -1px;
            }
            
            QTabBar::tab {
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 10px 16px;
                margin-right: 2px;
                color: #ffffff;
                font-weight: 500;
                min-width: 80px;
            }
            
            QTabBar::tab:selected {
                background-color: #2b2b2b;
                border-color: #555555;
                border-bottom: 2px solid #2b2b2b;
            }
            
            QTabBar::tab:hover:!selected {
                background-color: #484848;
            }
            
            /* Labels */
            QLabel {
                color: #ffffff;
                font-size: 11px;
            }
            
            /* Text Areas */
            QTextEdit {
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-radius: 6px;
                color: #ffffff;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                selection-background-color: #0078d4;
            }
            
            /* Scrollbars */
            QScrollBar:vertical {
                background-color: #3c3c3c;
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            
            /* ComboBox */
            QComboBox {
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 11px;
            }
            
            QComboBox:focus {
                border-color: #0078d4;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTMgNC41TDYgNy41TDkgNC41IiBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }
            
            /* SpinBox specific */
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
                border: none;
                background-color: #555555;
            }
            
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #666666;
            }
            
            QSpinBox::up-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTIuNSA3LjVMNSA1TDcuNSA3LjUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }
            
            QSpinBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTcuNSAyLjVMNSA1TDIuNSAyLjUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }
        """)
    
    def setup_ui(self):
        """Set up the user interface"""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_config_tab()
        self.create_status_tab()
        self.create_results_tab()
        self.create_logs_tab()
    
    def create_config_tab(self):
        """Create the configuration tab"""
        config_widget = QWidget()
        layout = QVBoxLayout(config_widget)
        
        # Main control buttons (4 simplified buttons)
        button_group = QGroupBox("Main Controls")
        button_layout = QHBoxLayout(button_group)
        
        # Run Now button (green) - Auto-installs if needed
        self.run_now_btn = QPushButton("⚡ Run Now")
        self.run_now_btn.setMinimumHeight(50)
        self.run_now_btn.setStyleSheet("QPushButton { background-color: #3d7d3d; } QPushButton:hover { background-color: #2d5d2d; }")
        self.run_now_btn.clicked.connect(self.run_now)
        button_layout.addWidget(self.run_now_btn)
        
        # Schedule button - Auto-installs if needed
        self.save_schedule_btn = QPushButton("💾 Save Search Parameters")
        self.save_schedule_btn.setMinimumHeight(50)
        self.save_schedule_btn.clicked.connect(self.save_and_schedule)
        button_layout.addWidget(self.save_schedule_btn)
        

        
        layout.addWidget(button_group)
        
        # Search Configuration
        search_group = QGroupBox("Search Configuration")
        search_layout = QFormLayout(search_group)
        
        # Property Types
        self.property_types = QWidget()
        types_layout = QHBoxLayout(self.property_types)
        types_layout.setContentsMargins(0, 0, 0, 0)
        
        self.office_cb = QCheckBox("Office")
        self.retail_cb = QCheckBox("Retail")
        self.industrial_cb = QCheckBox("Industrial")
        self.multifamily_cb = QCheckBox("Multifamily")
        
        types_layout.addWidget(self.office_cb)
        types_layout.addWidget(self.retail_cb)
        types_layout.addWidget(self.industrial_cb)
        types_layout.addWidget(self.multifamily_cb)
        types_layout.addStretch()
        
        search_layout.addRow("Property Types:", self.property_types)
        
        # Location
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("e.g., Melbourne, VIC")
        search_layout.addRow("Location:", self.location_edit)
        
        # Price Range
        price_widget = QWidget()
        price_layout = QHBoxLayout(price_widget)
        price_layout.setContentsMargins(0, 0, 0, 0)
        
        self.min_price_edit = QLineEdit()
        self.min_price_edit.setPlaceholderText("Min price")
        self.max_price_edit = QLineEdit()
        self.max_price_edit.setPlaceholderText("Max price")
        
        price_layout.addWidget(QLabel("Min:"))
        price_layout.addWidget(self.min_price_edit)
        price_layout.addWidget(QLabel("Max:"))
        price_layout.addWidget(self.max_price_edit)
        price_layout.addStretch()
        
        search_layout.addRow("Price Range:", price_widget)
        
        # Websites
        websites_widget = QWidget()
        websites_layout = QHBoxLayout(websites_widget)
        websites_layout.setContentsMargins(0, 0, 0, 0)
        
        self.realcommercial_cb = QCheckBox("LoopNet.com")
        self.commercialrealestate_cb = QCheckBox("CommercialMLS.com")
        
        websites_layout.addWidget(self.realcommercial_cb)
        websites_layout.addWidget(self.commercialrealestate_cb)
        websites_layout.addStretch()
        
        search_layout.addRow("Websites:", websites_widget)
        
        # Days Back
        self.days_back_spin = QSpinBox()
        self.days_back_spin.setMinimum(1)
        self.days_back_spin.setMaximum(30)
        self.days_back_spin.setValue(1)
        search_layout.addRow("Days Back:", self.days_back_spin)
        
        layout.addWidget(search_group)
        
        # Scheduling Configuration
        schedule_group = QGroupBox("Scheduling Configuration")
        schedule_layout = QFormLayout(schedule_group)
        
        # Background enabled
        self.background_enabled_cb = QCheckBox("Enable Background Scheduling")
        schedule_layout.addRow("", self.background_enabled_cb)
        
        # Scheduled times (support multiple times)
        self.scheduled_times_widget = QWidget()
        self.scheduled_times_layout = QVBoxLayout(self.scheduled_times_widget)
        self.scheduled_times_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with add button
        times_header = QHBoxLayout()
        times_header.addWidget(QLabel("Scheduled Times:"))
        self.add_time_btn = QPushButton("Add Time")
        self.add_time_btn.setMaximumWidth(100)
        self.add_time_btn.clicked.connect(self.add_scheduled_time)
        times_header.addWidget(self.add_time_btn)
        times_header.addStretch()
        
        header_widget = QWidget()
        header_widget.setLayout(times_header)
        self.scheduled_times_layout.addWidget(header_widget)
        
        # Container for time entries
        self.times_container = QWidget()
        self.times_container_layout = QVBoxLayout(self.times_container)
        self.times_container_layout.setContentsMargins(0, 0, 0, 0)
        self.scheduled_times_layout.addWidget(self.times_container)
        
        schedule_layout.addRow("", self.scheduled_times_widget)
        
        layout.addWidget(schedule_group)
        
        # Email Configuration
        email_group = QGroupBox("Email Notifications")
        email_layout = QFormLayout(email_group)
        
        # Email address
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("your.email@gmail.com")
        email_layout.addRow("Email Address:", self.email_edit)
        
        # App password with help button
        password_widget = QWidget()
        password_layout = QHBoxLayout(password_widget)
        password_layout.setContentsMargins(0, 0, 0, 0)
        
        self.email_password_edit = QLineEdit()
        self.email_password_edit.setEchoMode(QLineEdit.Password)
        self.email_password_edit.setPlaceholderText("App Password (not regular password)")
        
        # Help button for app password explanation
        self.help_btn = QPushButton("?")
        self.help_btn.setFixedWidth(32)
        self.help_btn.setStyleSheet("QPushButton { background-color: #0078d4; border: 1px solid #ffffff; border-radius: 6px; font-weight: bold; font-size: 14px; padding: 6px; }")
        self.help_btn.clicked.connect(self.show_app_password_help)
        
        password_layout.addWidget(self.email_password_edit)
        password_layout.addWidget(self.help_btn)
        
        email_layout.addRow("App Password:", password_widget)
        
        # Send email checkbox
        self.send_email_cb = QCheckBox("Send email notifications when scraping completes")
        email_layout.addRow("", self.send_email_cb)
        
        # Save credentials checkbox
        self.save_credentials_cb = QCheckBox("Save email credentials (required for scheduled emails)")
        self.save_credentials_cb.toggled.connect(self.toggle_email_credentials)
        email_layout.addRow("", self.save_credentials_cb)
        
        layout.addWidget(email_group)
        layout.addStretch()
        
        self.tab_widget.addTab(config_widget, "Configuration")

    def create_status_tab(self):
        """Create the status tab"""
        status_widget = QWidget()
        layout = QVBoxLayout(status_widget)
        
        # Status information
        status_group = QGroupBox("Task Status")
        status_layout = QFormLayout(status_group)
        
        self.status_installed_label = QLabel("Not checked")
        self.status_enabled_label = QLabel("Not checked")
        self.status_state_label = QLabel("Not checked")
        self.status_last_run_label = QLabel("Never")
        self.status_next_run_label = QLabel("Not scheduled")
        self.status_results_count_label = QLabel("No results")
        
        status_layout.addRow("Task Installed:", self.status_installed_label)
        status_layout.addRow("Task Enabled:", self.status_enabled_label)
        status_layout.addRow("Task State:", self.status_state_label)
        status_layout.addRow("Last Run:", self.status_last_run_label)
        status_layout.addRow("Next Run:", self.status_next_run_label)
        status_layout.addRow("Last Results:", self.status_results_count_label)
        
        layout.addWidget(status_group)
        layout.addStretch()
        
        self.tab_widget.addTab(status_widget, "Status")
    
    def create_results_tab(self):
        """Create the results tab"""
        results_widget = QWidget()
        layout = QVBoxLayout(results_widget)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Results")
        refresh_btn.clicked.connect(self.refresh_results)
        layout.addWidget(refresh_btn)
        
        # Results display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        
        self.tab_widget.addTab(results_widget, "Results")

    def create_logs_tab(self):
        """Create the logs tab"""
        logs_widget = QWidget()
        layout = QVBoxLayout(logs_widget)
        
        # Refresh button
        refresh_log_btn = QPushButton("Refresh Logs")
        refresh_log_btn.clicked.connect(self.refresh_logs)
        layout.addWidget(refresh_log_btn)
        
        # Logs display
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        layout.addWidget(self.logs_text)
        
        self.tab_widget.addTab(logs_widget, "Logs")

    def load_values(self):
        """Load configuration values into UI elements"""
        try:
            # Property types (handle both old "Investment" and new "Multifamily" for config compatibility)
            property_types = self.user_config.get('property_types', [])
            self.office_cb.setChecked('Office' in property_types)
            self.retail_cb.setChecked('Retail' in property_types)
            self.industrial_cb.setChecked('Industrial' in property_types)
            # Handle both old "Investment" configs and new "Multifamily"
            self.multifamily_cb.setChecked('Multifamily' in property_types or 'Investment' in property_types)
            
            # Location
            self.location_edit.setText(self.user_config.get('location', ''))
            
            # Price range
            self.min_price_edit.setText(str(self.user_config.get('min_price', '')))
            self.max_price_edit.setText(str(self.user_config.get('max_price', '')))
            
            # Websites
            websites = self.user_config.get('websites', [])
            self.realcommercial_cb.setChecked('loopnet.com' in websites)
            self.commercialrealestate_cb.setChecked('commercialmls.com' in websites)
            
            # Days back
            self.days_back_spin.setValue(self.user_config.get('days_back', 1))
            
            # Background enabled
            self.background_enabled_cb.setChecked(self.user_config.get('enable_background', False))
            
            # Scheduled times
            scheduled_times = self.user_config.get('scheduled_times', ['11:00'])
            for time_str in scheduled_times:
                self.add_scheduled_time(time_str)
            
            # Email settings
            email, password = userinfo.get_email_credentials()
            self.email_edit.setText(email)
            self.email_password_edit.setText(password)
            self.send_email_cb.setChecked(self.user_config.get('send_email', False))
            
            # Update credentials checkbox state without triggering the toggle event
            has_credentials = bool(email and password)
            self.save_credentials_cb.blockSignals(True)  # Temporarily block signals
            self.save_credentials_cb.setChecked(has_credentials)
            self.save_credentials_cb.blockSignals(False)  # Re-enable signals
                
        except Exception as e:
            logger.error(f"Error loading values: {str(e)}")

    def add_scheduled_time(self, time_str=None):
        """Add a new scheduled time entry"""
        time_widget = QWidget()
        time_layout = QHBoxLayout(time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        
        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("hh:mm AP")  # 12-hour format with AM/PM
        if time_str:
            try:
                hour, minute = time_str.split(':')
                time_edit.setTime(QTime(int(hour), int(minute)))
            except:
                time_edit.setTime(QTime(11, 0))  # Default time (11:00 AM)
        else:
            time_edit.setTime(QTime(11, 0))  # Default time (11:00 AM)
        
        # Connect auto-save to new time field
        time_edit.timeChanged.connect(self.auto_save_config)
        
        remove_btn = QPushButton("Remove")
        remove_btn.setMaximumWidth(90)
        remove_btn.setStyleSheet("QPushButton { background-color: #5d2d2d; } QPushButton:hover { background-color: #7d3d3d; }")
        remove_btn.clicked.connect(lambda: self.remove_scheduled_time(time_widget))
        
        time_layout.addWidget(time_edit)
        time_layout.addWidget(remove_btn)
        time_layout.addStretch()
        
        self.times_container_layout.addWidget(time_widget)

    def remove_scheduled_time(self, time_widget):
        """Remove a scheduled time entry"""
        self.times_container_layout.removeWidget(time_widget)
        time_widget.deleteLater()
        # Auto-save after removing a time
        self.auto_save_config()

    def get_scheduled_times(self):
        """Get all scheduled times as string list"""
        times = []
        for i in range(self.times_container_layout.count()):
            widget = self.times_container_layout.itemAt(i).widget()
            if widget:
                time_edit = widget.findChild(QTimeEdit)
                if time_edit:
                    time = time_edit.time()
                    time_str = f"{time.hour():02d}:{time.minute():02d}"
                    logger.info(f"Time widget shows: {time.toString('hh:mm AP')}, hour()={time.hour()}, minute()={time.minute()}, 24h format: {time_str}")
                    times.append(time_str)
        return times

    def setup_auto_save(self):
        """Setup auto-save connections for all form fields"""
        # Prevent duplicate setup
        if hasattr(self, '_auto_save_setup'):
            return
        self._auto_save_setup = True
        
        # Property type checkboxes
        self.office_cb.toggled.connect(self.auto_save_config)
        self.retail_cb.toggled.connect(self.auto_save_config)
        self.industrial_cb.toggled.connect(self.auto_save_config)
        self.multifamily_cb.toggled.connect(self.auto_save_config)
        
        # Text fields
        self.location_edit.textChanged.connect(self.auto_save_config)
        self.min_price_edit.textChanged.connect(self.auto_save_config)
        self.max_price_edit.textChanged.connect(self.auto_save_config)
        
        # Website checkboxes
        self.realcommercial_cb.toggled.connect(self.auto_save_config)
        self.commercialrealestate_cb.toggled.connect(self.auto_save_config)
        
        # Spinbox and background settings
        self.days_back_spin.valueChanged.connect(self.auto_save_config)
        self.background_enabled_cb.toggled.connect(self.auto_save_config)
        
        # Email settings (only checkbox auto-saves, credentials saved manually)
        self.send_email_cb.toggled.connect(self.auto_save_config)
        
        logger.info("Auto-save enabled for all configuration fields")

    def auto_save_config(self):
        """Auto-save configuration whenever any field changes"""
        try:
            self.save_configuration()
            logger.debug("Configuration auto-saved")
        except Exception as e:
            logger.error(f"Auto-save failed: {str(e)}")
    
    def setup_status_checker(self):
        """Set up background status checking"""
        self.worker_thread = WorkerThread(self.task_manager, self)
        self.worker_thread.progress_updated.connect(self.update_status_display)
        self.worker_thread.start()
    
    def update_status_display(self, status):
        """Update the status display with current information"""
        try:
            # Update status labels
            self.status_installed_label.setText("Yes" if status.get('installed', False) else "No")
            self.status_enabled_label.setText("Yes" if status.get('enabled', False) else "No")
            
            # Override status if manual scraping is running
            if self.scraping_running:
                self.status_state_label.setText("Running (Manual)")
            else:
                self.status_state_label.setText(status.get('state', 'Unknown'))
                
            self.status_last_run_label.setText(status.get('last_run', 'Never'))
            self.status_next_run_label.setText(status.get('next_run', 'Not scheduled'))
            
            # Update results count if available
            if 'latest_results' in status:
                latest = status['latest_results']
                total_results = latest.get('total_results', 0)
                run_time = latest.get('datetime', 'Unknown')
                self.status_results_count_label.setText(f"{total_results} results at {run_time}")
            
            # Update button states (with auto-install, most buttons are always available)
            installed = status.get('installed', False)
            
            # Run Now and Schedule are always enabled (they auto-install)
            self.run_now_btn.setEnabled(True)
            self.save_schedule_btn.setEnabled(True)
            
        except Exception as e:
            logger.error(f"Error updating status display: {str(e)}")

    def run_now(self):
        """Run the task immediately"""
        try:
            # Configuration is auto-saved, but ensure it's current
            self.save_configuration()
            
            # Auto-install task if not installed
            if not self.task_manager.is_task_installed():
                logger.info("Task not installed for run now, auto-installing...")
                if not self.task_manager.install_task():
                    QMessageBox.warning(self, "Error", "Failed to install task. Please try the Install Task button.")
                return
            
            # Run using ScraperManager directly for immediate execution
            self.run_scraper_directly()
        
        except Exception as e:
            logger.error(f"Error running task now: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error running task: {str(e)}")

    def run_scraper_directly(self):
        """Run the scraper directly for immediate execution"""
        try:
            # Get search parameters
            property_types = []
            if self.office_cb.isChecked():
                property_types.append('office')
            if self.retail_cb.isChecked():
                property_types.append('retail')
            if self.industrial_cb.isChecked():
                property_types.append('industrial')
            if self.multifamily_cb.isChecked():
                property_types.append('multifamily')
            
            location = self.location_edit.text().strip()
            min_price = self.min_price_edit.text().strip() or None
            max_price = self.max_price_edit.text().strip() or None
            
            websites = []
            if self.realcommercial_cb.isChecked():
                websites.append('loopnet.com')
            if self.commercialrealestate_cb.isChecked():
                websites.append('commercialmls.com')
            
            days_back = self.days_back_spin.value()
            
            # Validate parameters
            if not location or not property_types or not websites:
                QMessageBox.warning(self, "Error", "Please fill in all required fields: location, property types, and websites.")
                return
            
            # Calculate start date
            start_date = datetime.now() - timedelta(days=days_back)
            
            # Show progress dialog
            QMessageBox.information(self, "Running", "Scraping started! Check the Results tab for progress.")
            
            # Run in separate thread to avoid blocking UI
            def run_scraper():
                try:
                    # Set running state
                    self.scraping_running = True
                    
                    logger.info(f"Running manual scraping with config: location={location}, types={property_types}, websites={websites}")
                    
                    # Execute search using ScraperManager  
                    manager = ScraperManager(debug_mode=self.debug_mode)
                    results = manager.search(
                        property_types=property_types,
                        location=location,
                        min_price=min_price,
                        max_price=max_price,
                        start_date=start_date,
                        websites=websites
                    )
                    
                    # Save latest results (overwrite previous)
                    total_results = 0
                    if isinstance(results, dict):
                        for website, website_results in results.items():
                            count = len(website_results) if website_results else 0
                            total_results += count
                            logger.info(f"Found {count} results on {website}")
                    else:
                        total_results = len(results) if results else 0
                        logger.info(f"Found {total_results} total results")
                    
                    # Save to single latest results file (overwrite each time)
                    os.makedirs(CONFIG_DIR, exist_ok=True)
                    latest_results_file = os.path.join(CONFIG_DIR, "latest_results.json")
                    results_data = {
                        "results": results,
                        "total_results": total_results,
                        "datetime": datetime.now().isoformat(),
                        "trigger": "manual_run"
                    }
                    with open(latest_results_file, 'w') as f:
                        json.dump(results_data, f, indent=2, default=str)
                    
                    logger.info(f"=== Manual scraping completed successfully! Total results: {total_results} ===")
                    
                    # Send email if enabled and configured
                    self.send_scraping_email(results, results_data)
                
                except Exception as e:
                    logger.error(f"Error during manual scraping: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                finally:
                    # Always clear running state
                    self.scraping_running = False
            
            # Run in background thread
            thread = threading.Thread(target=run_scraper)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.error(f"Error running scraper directly: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error running scraper: {str(e)}")

    def save_and_schedule(self):
        """Save configuration and schedule the task"""
        try:
            # Save configuration first (auto-save already handled this, but ensure it's saved)
            self.save_configuration()
            
            # Auto-install task if not installed
            if not self.task_manager.is_task_installed():
                logger.info("Task not installed, auto-installing...")
                if not self.task_manager.install_task():
                    QMessageBox.warning(self, "Error", "Failed to install task. Please try the Install Task button.")
                    return
            
            # Check if background scheduling is enabled
            if not self.background_enabled_cb.isChecked():
                QMessageBox.information(self, "Info", "Configuration saved. Background scheduling is disabled.")
                return
            
            # Get scheduled times
            times = self.get_scheduled_times()
            if not times:
                QMessageBox.warning(self, "Error", "Please add at least one scheduled time.")
                return
            
            # Schedule the task
            if self.task_manager.schedule_times(times):
                QMessageBox.information(self, "Success", f"Task scheduled for times: {', '.join(times)}")
            else:
                QMessageBox.warning(self, "Error", "Failed to schedule task. Check logs for details.")
        
        except Exception as e:
            logger.error(f"Error saving and scheduling: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error saving and scheduling: {str(e)}")

    def kill_task(self):
        """Remove the scheduled task completely"""
        try:
            reply = QMessageBox.question(self, "Confirm", "Are you sure you want to completely remove the scheduled task?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                if self.task_manager.delete_task():
                    QMessageBox.information(self, "Success", "Task removed successfully!")
                else:
                    QMessageBox.warning(self, "Error", "Failed to remove task. Check logs for details.")
        
        except Exception as e:
            logger.error(f"Error removing task: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error removing task: {str(e)}")
    
    def save_configuration(self):
        """Save the current configuration"""
        try:
            # Collect property types
            property_types = []
            if self.office_cb.isChecked():
                property_types.append('Office')
            if self.retail_cb.isChecked():
                property_types.append('Retail')
            if self.industrial_cb.isChecked():
                property_types.append('Industrial')
            if self.multifamily_cb.isChecked():
                property_types.append('Multifamily')
            
            # Collect websites
            websites = []
            if self.realcommercial_cb.isChecked():
                websites.append('loopnet.com')
            if self.commercialrealestate_cb.isChecked():
                websites.append('commercialmls.com')
            
            # Update configuration (email credentials saved separately via button)
            self.user_config.update({
                'property_types': property_types,
                'location': self.location_edit.text().strip(),
                'min_price': self.min_price_edit.text().strip(),
                'max_price': self.max_price_edit.text().strip(),
                'websites': websites,
                'days_back': self.days_back_spin.value(),
                'enable_background': self.background_enabled_cb.isChecked(),
                'scheduled_times': self.get_scheduled_times(),
                'send_email': self.send_email_cb.isChecked()
            })
            
            # Save to file
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.user_config, f, indent=2)
            
            logger.info(f"Configuration saved successfully to {CONFIG_FILE}")
            logger.info(f"Saved config: {self.user_config}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            raise

    def toggle_email_credentials(self):
        """Toggle email credentials save state"""
        try:
            if self.save_credentials_cb.isChecked():
                # Save credentials
                email = self.email_edit.text().strip()
                password = self.email_password_edit.text()
                
                if not email or not password:
                    QMessageBox.warning(self, "Error", "Please enter both email address and app password before saving.")
                    self.save_credentials_cb.setChecked(False)  # Uncheck if validation fails
                    return
                
                # Validate email format
                if '@' not in email or '.' not in email:
                    QMessageBox.warning(self, "Error", "Please enter a valid email address.")
                    self.save_credentials_cb.setChecked(False)  # Uncheck if validation fails
                    return
                
                # Save credentials to userinfo.py
                userinfo.set_email_credentials(email, password)
                QMessageBox.information(self, "Success", "Email credentials saved successfully!\n\nScheduled emails will now work when scraping completes.")
                
            else:
                # Clear credentials
                reply = QMessageBox.question(self, "Confirm", "Are you sure you want to clear saved email credentials?",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    userinfo.set_email_credentials("", "")
                    QMessageBox.information(self, "Cleared", "Email credentials cleared.\n\nScheduled emails will not work until credentials are saved again.")
                else:
                    self.save_credentials_cb.setChecked(True)  # Recheck if user cancels
                    return
            
        except Exception as e:
            logger.error(f"Error toggling email credentials: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error with email credentials: {str(e)}")
            self.save_credentials_cb.setChecked(False)  # Reset on error

    def show_app_password_help(self):
        """Show help dialog for app password setup"""
        help_text = """
        <h3>Gmail App Password Setup</h3>
        <p>An <b>App Password</b> is a special password for third-party applications to access your Gmail account securely.</p>
        
        <h4>To create an App Password:</h4>
        <ol>
        <li>Go to your <a href="https://myaccount.google.com/">Google Account</a></li>
        <li>Click on <b>Security</b> in the left menu</li>
        <li>Under "Signing in to Google", click <b>2-Step Verification</b></li>
        <li>Enable 2-Step Verification if not already enabled</li>
        <li>Go back to Security, scroll down to <b>App passwords</b></li>
        <li>Click <b>App passwords</b></li>
        <li>Select <b>Mail</b> and <b>Windows Computer</b></li>
        <li>Click <b>Generate</b></li>
        <li>Copy the 16-character password (example: "abcd efgh ijkl mnop")</li>
        <li>Paste it in the App Password field above</li>
        </ol>
        
        <p><b>Note:</b> Use your App Password, NOT your regular Gmail password!</p>
        """
        
        msg = QMessageBox()
        msg.setWindowTitle("App Password Help")
        msg.setTextFormat(Qt.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()

    def refresh_results(self):
        """Refresh the results display with detailed listing information"""
        try:
            results_text = ""
            
            # Look for latest results file
            latest_results_file = os.path.join(CONFIG_DIR, "latest_results.json")
            if os.path.exists(latest_results_file):
                try:
                    with open(latest_results_file, 'r') as f:
                        data = json.load(f)
                    
                    results = data.get('results', {})
                    total_results = data.get('total_results', 0)
                    run_time = data.get('datetime', 'Unknown')
                    trigger = data.get('trigger', 'Unknown')
                    
                    # DEBUG: Log what we're actually getting
                    logger.info(f"DEBUG: results type = {type(results)}")
                    logger.info(f"DEBUG: results = {results}")
                    if isinstance(results, dict):
                        for website, website_results in results.items():
                            logger.info(f"DEBUG: {website} has {len(website_results) if website_results else 0} results")
                            if website_results and len(website_results) > 0:
                                logger.info(f"DEBUG: First listing for {website}: {website_results[0]}")
                    
                    results_text = self.format_results_text(results, total_results, run_time, trigger)
                    
                except Exception as e:
                    results_text = f"Error reading latest results: {str(e)}"
            else:
                results_text = "No results yet. Run scraping to see results here."
            
            self.results_text.setPlainText(results_text)
        
        except Exception as e:
            logger.error(f"Error refreshing results: {str(e)}")
            self.results_text.setPlainText(f"Error loading results: {str(e)}")

    def format_listing_details(self, listing):
        """Format a single listing's details for display"""
        details = []
        
        # Title/Address
        if 'title' in listing and listing['title']:
            details.append(listing['title'])
        elif 'address' in listing and listing['address']:
            details.append(listing['address'])
        else:
            details.append("Property Details")
        
        # Price
        if 'price' in listing and listing['price']:
            details.append(f"💰 Price: {listing['price']}")
        
        # Property Type
        if 'property_type' in listing and listing['property_type']:
            details.append(f"🏢 Type: {listing['property_type']}")
        
        # Size/Area
        if 'size' in listing and listing['size']:
            details.append(f"📐 Size: {listing['size']}")
        elif 'area' in listing and listing['area']:
            details.append(f"📐 Area: {listing['area']}")
        
        # Location
        if 'location' in listing and listing['location']:
            details.append(f"📍 Location: {listing['location']}")
        elif 'address' in listing and listing['address'] and 'title' in listing:
            details.append(f"📍 Address: {listing['address']}")
        
        # Description
        if 'description' in listing and listing['description']:
            desc = listing['description'][:200] + "..." if len(listing['description']) > 200 else listing['description']
            details.append(f"📝 Description: {desc}")
        
        # URL
        if 'url' in listing and listing['url']:
            details.append(f"🔗 URL: {listing['url']}")
        
        # Date
        if 'date' in listing and listing['date']:
            details.append(f"📅 Listed: {listing['date']}")
        
        return details

    def format_results_text(self, results, total_results, run_time, trigger):
        """Format results data into display text"""
        results_text = f"=== Latest Results ({trigger} run at {run_time}) ===\n"
        results_text += f"Total Properties Found: {total_results}\n\n"
        
        if total_results > 0:
            # Handle both dict format {website: [listings]} and list format [listings]
            if isinstance(results, dict):
                # Multiple websites format
                for website, website_results in results.items():
                    if website_results and len(website_results) > 0:
                        results_text += f"{'='*50}\n"
                        results_text += f"{website.upper()} - {len(website_results)} Properties\n"
                        results_text += f"{'='*50}\n\n"
                        
                        for i, listing in enumerate(website_results, 1):
                            results_text += f"[{i}] "
                            listing_details = self.format_listing_details(listing)
                            results_text += "\n".join(listing_details)
                            results_text += "\n\n" + "-"*40 + "\n\n"
            elif isinstance(results, list):
                # Single website or combined results format
                results_text += f"{'='*50}\n"
                results_text += f"SEARCH RESULTS - {len(results)} Properties\n"
                results_text += f"{'='*50}\n\n"
                
                for i, listing in enumerate(results, 1):
                    results_text += f"[{i}] "
                    listing_details = self.format_listing_details(listing)
                    results_text += "\n".join(listing_details)
                    results_text += "\n\n" + "-"*40 + "\n\n"
            else:
                results_text += f"Found {total_results} results but data format not recognized.\n"
        else:
            results_text += "No new properties found matching your criteria.\n"
        
        return results_text

    def send_scraping_email(self, results, results_data):
        """Send email with scraping results if email is enabled and configured"""
        try:
            # Check if email notifications are enabled
            if not self.send_email_cb.isChecked():
                logger.debug("Email notifications disabled, skipping email send")
                return
            
            # Check if credentials are saved
            email, password = userinfo.get_email_credentials()
            if not email or not password:
                logger.warning("Email credentials not configured, skipping email send")
                return
            
            # Prepare email content
            total_results = results_data.get('total_results', 0)
            run_time = results_data.get('datetime', 'Unknown')
            
            subject = f"Commercial Real Estate Search Results - {total_results} Properties Found"
            
            # Create detailed email body (without emojis for better email compatibility)
            email_body = f"""Commercial Real Estate Search Results
=====================================

Search completed: {run_time}
Total properties found: {total_results}

"""
            
            if total_results > 0:
                # Handle both dict format {website: [listings]} and list format [listings]
                if isinstance(results, dict):
                    # Multiple websites format
                    for website, website_results in results.items():
                        if website_results and len(website_results) > 0:
                            email_body += f"{'='*50}\n"
                            email_body += f"{website.upper()} - {len(website_results)} Properties\n"
                            email_body += f"{'='*50}\n\n"
                            
                            for i, listing in enumerate(website_results, 1):
                                email_body += f"[{i}] "
                                listing_details = self.format_listing_details(listing)
                                # Remove emojis for email
                                email_details = [detail.replace('💰 ', '').replace('🏢 ', '').replace('📐 ', '').replace('📍 ', '').replace('📝 ', '').replace('🔗 ', '').replace('📅 ', '') for detail in listing_details]
                                email_body += "\n".join(email_details)
                                email_body += "\n\n" + "-"*40 + "\n\n"
                elif isinstance(results, list):
                    # Single website or combined results format
                    email_body += f"{'='*50}\n"
                    email_body += f"SEARCH RESULTS - {len(results)} Properties\n"
                    email_body += f"{'='*50}\n\n"
                    
                    for i, listing in enumerate(results, 1):
                        email_body += f"[{i}] "
                        listing_details = self.format_listing_details(listing)
                        # Remove emojis for email
                        email_details = [detail.replace('💰 ', '').replace('🏢 ', '').replace('📐 ', '').replace('📍 ', '').replace('📝 ', '').replace('🔗 ', '').replace('📅 ', '') for detail in listing_details]
                        email_body += "\n".join(email_details)
                        email_body += "\n\n" + "-"*40 + "\n\n"
                else:
                    email_body += f"Found {total_results} results but data format not recognized.\n"
            else:
                email_body += "No new properties found matching your criteria.\n"
            
            email_body += """
---
This email was automatically sent by the Commercial Real Estate Crawler.
To stop receiving these emails, uncheck 'Send email notifications' in the application.
            """
            
            # Send email
            email_sender = EmailSender()
            success = email_sender.send_email(email, subject, email_body, email, password)
            
            if success:
                logger.info(f"Scraping results email sent successfully to {email}")
            else:
                logger.error("Failed to send scraping results email")
                
        except Exception as e:
            logger.error(f"Error sending scraping results email: {str(e)}")

    def refresh_logs(self):
        """Refresh the logs display"""
        try:
            log_text = ""
            
            # Look for log files
            log_files = []
            
            # Check debug directory
            debug_dir = os.path.join(os.path.dirname(__file__), '..', 'debug')
            if os.path.exists(debug_dir):
                for filename in os.listdir(debug_dir):
                    if filename.endswith('.log'):
                        log_files.append(os.path.join(debug_dir, filename))
            
            # Check config directory for task runner logs
            if os.path.exists(CONFIG_DIR):
                for filename in os.listdir(CONFIG_DIR):
                    if filename.endswith('.log'):
                        log_files.append(os.path.join(CONFIG_DIR, filename))
            
            if log_files:
                # Sort by modification time, most recent first
                log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                
                # Read the most recent log file (last 100 lines)
                try:
                    with open(log_files[0], 'r') as f:
                        lines = f.readlines()
                        
                        # Get last 100 lines
                        recent_lines = lines[-100:] if len(lines) > 100 else lines
                        log_text = ''.join(recent_lines)
                        
                        log_text = f"=== Last 100 lines from {os.path.basename(log_files[0])} ===\n\n" + log_text
                        
                except Exception as e:
                    log_text = f"Error reading log file: {str(e)}"
            else:
                log_text = "No log files found."
            
            self.logs_text.setPlainText(log_text)
        
        except Exception as e:
            logger.error(f"Error refreshing logs: {str(e)}")
            self.logs_text.setPlainText(f"Error loading logs: {str(e)}")
    
    def closeEvent(self, event):
        """Handle application close event"""
        try:
            # Stop the worker thread
            if hasattr(self, 'worker_thread'):
                self.worker_thread.stop()
            
            event.accept()
        except Exception as e:
            logger.error(f"Error during close: {str(e)}")
        event.accept()

def main():
    """Main function to run the application"""
    import os
    import sys
    
    # More aggressive Qt MIME database fix - set before any Qt operations
    os.environ['QT_LOGGING_RULES'] = 'qt.qpa.mime=false'
    os.environ['QT_PLUGIN_PATH'] = r'C:\Users\benos\anaconda3\Library\plugins'
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = r'C:\Users\benos\anaconda3\Library\plugins\platforms'
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for better dark theme support
    
    # Set application properties
    app.setApplicationName("Commercial Real Estate Crawler")
    app.setApplicationVersion("3.0")
    app.setOrganizationName("Commercial Real Estate Tools")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    main()