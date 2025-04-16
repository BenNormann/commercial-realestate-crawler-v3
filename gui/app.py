"""
Desktop GUI application for the Commercial Real Estate Crawler.
"""

import os
import sys
import json
import time
import logging
import ctypes
from datetime import datetime
from pathlib import Path
import subprocess
import win32serviceutil
import win32service
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
import config
# Import service directly
from service import ScraperService, install
# Create service runner script dynamically
import userinfo

class WorkerThread(QThread):
    """Worker thread for background tasks"""
    progress_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.parent = parent
    
    def run(self):
        """Run the worker thread"""
        while self.running:
            # Get service status directly
            status = {}
            try:
                # Use the parent's method to get status
                if self.parent and hasattr(self.parent, '_get_service_status'):
                    status = self.parent._get_service_status()
                else:
                    # Fallback if parent not set or method missing
                    status = {"installed": False, "running": False, "executing": False, "error": "Parent reference error"}
            except Exception as e:
                logger.error(f"Error in worker thread: {str(e)}")
                status = {"installed": False, "running": False, "executing": False, "error": str(e)}
                
            self.progress_updated.emit(status)
            
            # Sleep for a bit
            time.sleep(2)
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        self.wait()

class MainWindow(QMainWindow):
    """Main window for the application"""
    
    def __init__(self):
        """Initialize the main window"""
        super().__init__()
        
        # Setup window
        self.setWindowTitle("Commercial Real Estate Crawler")
        self.setGeometry(100, 100, 1200, 800)
        
        # Installation flag to prevent multiple installation attempts
        self.installation_pending = False
        
        # Setup styles (dark theme)
        self.setup_dark_theme()
        
        # Load configuration
        self.load_config()
        
        # Create and set up the UI
        self.setup_ui()
        
        # Load values into UI elements
        self.load_values()
        
        # Initial service check - but do NOT auto-install
        # (launcher.py now handles installation)
        
        # Setup background status checker
        self.setup_status_checker()
    
    def _get_service_status(self):
        """Get the status of the service using sc query"""
        try:
            # Check if service is installed
            result = subprocess.run(
                ["sc", "query", "CommercialRealEstateScraper"], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Parse result
            status_info = {
                "installed": False,
                "running": False,
                "executing": False,
                "error": ""
            }
            
            # If service exists
            if "RUNNING" in result.stdout:
                status_info["installed"] = True
                status_info["running"] = True
            elif "STOPPED" in result.stdout:
                status_info["installed"] = True
            elif "specified service does not exist" not in result.stdout:
                # If the query succeeded but service is in another state
                status_info["installed"] = True
                
            # Check for error
            if result.stderr:
                status_info["error"] = result.stderr.strip()
                
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting service status: {str(e)}")
            return {"installed": False, "running": False, "executing": False, "error": str(e)}
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(config.CONFIG_FILE):
                with open(config.CONFIG_FILE, 'r') as f:
                    self.user_config = json.load(f)
            else:
                # Create config directory if it doesn't exist
                os.makedirs(os.path.dirname(config.CONFIG_FILE), exist_ok=True)
                self.user_config = config.DEFAULT_CONFIG
                with open(config.CONFIG_FILE, 'w') as f:
                    json.dump(self.user_config, f, indent=2)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            self.user_config = config.DEFAULT_CONFIG
    
    def setup_dark_theme(self):
        """Set up dark theme for the application"""
        dark_palette = QPalette()
        
        # Set dark color scheme
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        
        # Apply the palette
        QApplication.setPalette(dark_palette)
        
        # Set stylesheet for additional customization
        QApplication.setStyle("Fusion")
        stylesheet = """
            QMainWindow {
                background-color: #353535;
            }
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
            QPushButton:pressed {
                background-color: #1a72ca;
            }
            QProgressBar {
                text-align: center;
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #333;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                border-radius: 4px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #444;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #2a82da;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 4px;
                margin-top: 20px;
                color: white;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
            }
            QLineEdit, QComboBox, QCheckBox, QSpinBox, QTimeEdit {
                background-color: #444;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget {
                background-color: #333;
                border: 1px solid #555;
                color: white;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                margin: 1px 0;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #2a82da;
            }
            QScrollBar:vertical {
                border: none;
                background: #444;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #666;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QTextEdit {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """
        self.setStyleSheet(stylesheet)
    
    def setup_ui(self):
        """Set up the UI components"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Create tabs
        config_tab = self.create_config_tab()
        results_tab = self.create_results_tab()
        status_tab = self.create_status_tab()
        
        # Add tabs to widget
        tab_widget.addTab(config_tab, "Configuration")
        tab_widget.addTab(results_tab, "Results")
        tab_widget.addTab(status_tab, "Status")
    
    def create_config_tab(self):
        """Create the configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create a scroll area for the configuration
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Create a widget for the scroll area
        scroll_widget = QWidget()
        scroll.setWidget(scroll_widget)
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Search parameters group
        search_group = QGroupBox("Search Parameters")
        search_layout = QFormLayout(search_group)
        
        # Location
        self.location_field = QLineEdit()
        search_layout.addRow("Location:", self.location_field)
        
        # Property types
        property_types_layout = QVBoxLayout()
        self.office_checkbox = QCheckBox("Office")
        self.retail_checkbox = QCheckBox("Retail")
        self.industrial_checkbox = QCheckBox("Industrial")
        self.multifamily_checkbox = QCheckBox("Multifamily")
        property_types_layout.addWidget(self.office_checkbox)
        property_types_layout.addWidget(self.retail_checkbox)
        property_types_layout.addWidget(self.industrial_checkbox)
        property_types_layout.addWidget(self.multifamily_checkbox)
        search_layout.addRow("Property Types:", property_types_layout)
        
        # Price range
        price_layout = QHBoxLayout()
        self.min_price_field = QLineEdit()
        self.max_price_field = QLineEdit()
        price_layout.addWidget(QLabel("Min:"))
        price_layout.addWidget(self.min_price_field)
        price_layout.addWidget(QLabel("Max:"))
        price_layout.addWidget(self.max_price_field)
        search_layout.addRow("Price Range:", price_layout)
        
        # Days back
        self.days_back_spin = QSpinBox()
        self.days_back_spin.setRange(1, 365)
        search_layout.addRow("Days Back:", self.days_back_spin)
        
        # Websites
        websites_layout = QVBoxLayout()
        self.commercialmls_checkbox = QCheckBox("commercialmls.com")
        self.loopnet_checkbox = QCheckBox("loopnet.com")
        websites_layout.addWidget(self.commercialmls_checkbox)
        websites_layout.addWidget(self.loopnet_checkbox)
        search_layout.addRow("Websites:", websites_layout)
        
        # Add search group to the layout
        scroll_layout.addWidget(search_group)
        
        # Email settings group
        email_group = QGroupBox("Email Settings")
        email_layout = QFormLayout(email_group)
        
        # Email checkbox
        self.send_email_checkbox = QCheckBox("Send email notifications")
        email_layout.addRow("", self.send_email_checkbox)
        
        # Email credentials
        self.email_field = QLineEdit()
        email_layout.addRow("Email Address:", self.email_field)
        
        self.password_field = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.Password)
        email_layout.addRow("App Password:", self.password_field)
        
        # Save credentials checkbox
        self.save_credentials_checkbox = QCheckBox("Save credentials")
        email_layout.addRow("", self.save_credentials_checkbox)
        
        # Add email group to the layout
        scroll_layout.addWidget(email_group)
        
        # Background service group
        background_group = QGroupBox("Background Service")
        background_layout = QFormLayout(background_group)
        
        # Enable background checkbox
        self.enable_background_checkbox = QCheckBox("Enable background service")
        background_layout.addRow("", self.enable_background_checkbox)
        
        # Background time
        self.background_time_edit = QTimeEdit()
        self.background_time_edit.setDisplayFormat("HH:mm")
        background_layout.addRow("Run Time:", self.background_time_edit)
        
        # Hide terminal checkbox
        self.hide_terminal_checkbox = QCheckBox("Hide terminal window")
        background_layout.addRow("", self.hide_terminal_checkbox)
        
        # Add background group to the layout
        scroll_layout.addWidget(background_group)
        
        # Appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)
        
        # Dark mode checkbox
        self.dark_mode_checkbox = QCheckBox("Dark Mode")
        appearance_layout.addRow("", self.dark_mode_checkbox)
        
        # Add appearance group to the layout
        scroll_layout.addWidget(appearance_group)
        
        # Service control group
        service_group = QGroupBox("Service Control")
        service_layout = QHBoxLayout(service_group)
        
        # Start button
        self.start_button = QPushButton("Start Service")
        self.start_button.clicked.connect(self.start_service)
        service_layout.addWidget(self.start_button)
        
        # Stop button
        self.stop_button = QPushButton("Stop Service")
        self.stop_button.clicked.connect(self.stop_service)
        service_layout.addWidget(self.stop_button)
        
        # Schedule button
        self.schedule_button = QPushButton("Schedule Service")
        self.schedule_button.clicked.connect(self.schedule_service)
        service_layout.addWidget(self.schedule_button)
        
        # Remove button
        self.remove_button = QPushButton("Remove Service")
        self.remove_button.clicked.connect(self.remove_service)
        service_layout.addWidget(self.remove_button)
        
        # Add service group to the layout
        scroll_layout.addWidget(service_group)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        # Save button
        self.save_button = QPushButton("Save Configuration")
        self.save_button.clicked.connect(self.save_configuration)
        self.save_button.setMinimumHeight(40)
        actions_layout.addWidget(self.save_button)
        
        # Search now button
        self.search_button = QPushButton("Search Now")
        self.search_button.clicked.connect(self.run_search_now)
        self.search_button.setMinimumHeight(40)
        actions_layout.addWidget(self.search_button)
        
        # Add actions layout to the main layout
        scroll_layout.addLayout(actions_layout)
        
        # Add some spacing
        scroll_layout.addStretch()
        
        return tab
    
    def create_results_tab(self):
        """Create the results tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Results display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh Results")
        self.refresh_button.clicked.connect(self.refresh_results)
        layout.addWidget(self.refresh_button)
        
        return tab
    
    def create_status_tab(self):
        """Create the status tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Status information
        status_group = QGroupBox("Service Status")
        status_layout = QFormLayout(status_group)
        
        # Status label
        self.status_label = QLabel("Unknown")
        status_layout.addRow("Status:", self.status_label)
        
        # Last run label
        self.last_run_label = QLabel("Never")
        status_layout.addRow("Last Run:", self.last_run_label)
        
        # Next run label
        self.next_run_label = QLabel("Not scheduled")
        status_layout.addRow("Next Run:", self.next_run_label)
        
        # Results count label
        self.results_count_label = QLabel("0")
        status_layout.addRow("Results Count:", self.results_count_label)
        
        # Progress label
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_label = QLabel("0%")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        status_layout.addRow("Progress:", progress_layout)
        
        # Error label
        self.error_label = QLabel("None")
        status_layout.addRow("Error:", self.error_label)
        
        layout.addWidget(status_group)
        
        # Log viewer
        log_group = QGroupBox("Service Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # Refresh log button
        self.refresh_log_button = QPushButton("Refresh Log")
        self.refresh_log_button.clicked.connect(self.refresh_log)
        log_layout.addWidget(self.refresh_log_button)
        
        layout.addWidget(log_group)
        
        return tab
    
    def load_values(self):
        """Load values from configuration into UI elements"""
        # Load search parameters
        self.location_field.setText(self.user_config.get('location', ''))
        
        property_types = self.user_config.get('property_types', [])
        self.office_checkbox.setChecked('Office' in property_types)
        self.retail_checkbox.setChecked('Retail' in property_types)
        self.industrial_checkbox.setChecked('Industrial' in property_types)
        self.multifamily_checkbox.setChecked('Multifamily' in property_types)
        
        self.min_price_field.setText(str(self.user_config.get('min_price', '')))
        self.max_price_field.setText(str(self.user_config.get('max_price', '')))
        
        self.days_back_spin.setValue(int(self.user_config.get('days_back', 1)))
        
        websites = self.user_config.get('websites', [])
        self.commercialmls_checkbox.setChecked('commercialmls.com' in websites)
        self.loopnet_checkbox.setChecked('loopnet.com' in websites)
        
        # Load email settings
        self.send_email_checkbox.setChecked(self.user_config.get('send_email', False))
        
        # Load email credentials using the global functions
        email, password = userinfo.get_email_credentials()
        self.email_field.setText(email)
        self.password_field.setText(password)
        
        self.save_credentials_checkbox.setChecked(self.user_config.get('save_credentials', False))
        
        # Load background service settings
        self.enable_background_checkbox.setChecked(self.user_config.get('enable_background', False))
        
        time_str = self.user_config.get('background_time', '03:00')
        time_parts = time_str.split(':')
        qtime = QTime(int(time_parts[0]), int(time_parts[1]))
        self.background_time_edit.setTime(qtime)
        
        self.hide_terminal_checkbox.setChecked(self.user_config.get('hide_terminal', True))
        
        # Load appearance settings
        self.dark_mode_checkbox.setChecked(self.user_config.get('dark_mode', True))
    
    def setup_status_checker(self):
        """Set up the status checker thread"""
        self.worker_thread = WorkerThread(self)
        self.worker_thread.progress_updated.connect(self.update_status)
        self.worker_thread.start()
    
    def update_status(self):
        """Update the status of the service and the UI elements."""
        try:
            # Get service status
            service_status_info = self._get_service_status()
            logger.debug(f"Status response: {service_status_info}")
            
            # Clear connection error if we got a valid response
            self.connection_error = False
            
            # Reset error display if we got a valid response
            self.error_label.setText("")
            
            if service_status_info is None:
                logger.error("Received None status")
                self.status_label.setText("Unknown")
                return
            
            # Extract status information
            installed = service_status_info.get("installed", False)
            running = service_status_info.get("running", False)
            executing = service_status_info.get("executing", False)
            error_msg = service_status_info.get("error", "")
            
            # Determine service status from fields
            service_status = "unknown"
            if not installed:
                service_status = "not installed"
                # Don't auto-install here anymore
            elif not running:
                service_status = "stopped"
            elif executing:
                service_status = "executing"
            elif running:
                service_status = "running"
            
            logger.debug(f"Service status: {service_status}, Error: {error_msg}")
            
            # Update status label
            self.status_label.setText(service_status.capitalize())
            
            # Update last_run and next_run
            self.last_run_label.setText("N/A")
            self.next_run_label.setText("N/A")
            
            # Update results count
            self.results_count_label.setText("N/A")
            
            # Update progress
            self.progress_bar.setValue(0)
            if executing:
                self.progress_bar.setMaximum(0)  # Show indeterminate progress
            else:
                self.progress_bar.setMaximum(100)
                self.progress_bar.setValue(0)
            self.progress_label.setText("")
            
            # Display error if present
            if error_msg:
                self.error_label.setText(str(error_msg))
            
            # Update buttons based on status
            if service_status == "not installed":
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(False)
                self.schedule_button.setEnabled(False)
                self.remove_button.setEnabled(False)
            elif service_status == "stopped":
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                self.schedule_button.setEnabled(False)
                self.remove_button.setEnabled(True)
            elif service_status == "running":
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.schedule_button.setEnabled(True)
                self.remove_button.setEnabled(False)
            elif service_status == "executing":
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.schedule_button.setEnabled(False)
                self.remove_button.setEnabled(False)
            else:
                # Default case for unknown statuses
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(False)
                self.schedule_button.setEnabled(False)
                self.remove_button.setEnabled(True)
                
            # Reset installation pending flag if service is now installed
            if installed:
                self.installation_pending = False
        
        except Exception as e:
            # Handle connection errors
            logger.error(f"Error updating status: {str(e)}")
            self.connection_error = True
            self.status_label.setText("Disconnected")
            self.progress_bar.setValue(0)
            self.progress_label.setText("")
            
            # Update buttons for disconnected state
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.schedule_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            
            # Show error
            self.error_label.setText(f"Connection error: {str(e)}")
    
    def save_configuration(self):
        """Save the configuration"""
        try:
            # Get property types
            property_types = []
            if self.office_checkbox.isChecked():
                property_types.append('Office')
            if self.retail_checkbox.isChecked():
                property_types.append('Retail')
            if self.industrial_checkbox.isChecked():
                property_types.append('Industrial')
            if self.multifamily_checkbox.isChecked():
                property_types.append('Multifamily')
            
            # Get websites
            websites = []
            if self.commercialmls_checkbox.isChecked():
                websites.append('commercialmls.com')
            if self.loopnet_checkbox.isChecked():
                websites.append('loopnet.com')
            
            # Update configuration
            self.user_config.update({
                'property_types': property_types,
                'min_price': self.min_price_field.text(),
                'max_price': self.max_price_field.text(),
                'location': self.location_field.text(),
                'websites': websites,
                'days_back': self.days_back_spin.value(),
                'save_credentials': self.save_credentials_checkbox.isChecked(),
                'send_email': self.send_email_checkbox.isChecked(),
                'dark_mode': self.dark_mode_checkbox.isChecked(),
                'enable_background': self.enable_background_checkbox.isChecked(),
                'background_time': self.background_time_edit.time().toString('HH:mm'),
                'hide_terminal': self.hide_terminal_checkbox.isChecked()
            })
            
            # Save configuration to file
            os.makedirs(os.path.dirname(config.CONFIG_FILE), exist_ok=True)
            with open(config.CONFIG_FILE, 'w') as f:
                json.dump(self.user_config, f, indent=2)
            
            # Save email credentials if requested
            if self.save_credentials_checkbox.isChecked():
                # Create a UserInfo instance
                user_info = userinfo.UserInfo()
                user_info.email = self.email_field.text()
                user_info.password = self.password_field.text()
                user_info.save()
            
            QMessageBox.information(self, "Success", "Configuration saved successfully.")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to save configuration: {str(e)}")
    
    def check_and_install_service(self):
        """Check if service is installed and install if needed - REMOVED FUNCTIONALITY"""
        # This functionality has been moved to launch_gui.py
        # We no longer auto-install on app start
        logger.info("Service installation is now handled by the launcher")
        # No actual implementation needed
    
    def start_service(self):
        """Start the Windows service"""
        try:
            # Show confirmation dialog
            result = QMessageBox.question(
                self, 
                "Administrator Privileges Required",
                "Starting the service requires administrator privileges.\n\n"
                "Click 'Yes' to continue.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                # Create a temporary vbs script to elevate privileges
                vbs_path = os.path.join(os.environ['TEMP'], 'elevate_service_start.vbs')
                with open(vbs_path, 'w') as f:
                    f.write('Set UAC = CreateObject("Shell.Application")\n')
                    f.write('UAC.ShellExecute "net", "start CommercialRealEstateScraper", "", "runas", 1\n')
                
                # Execute the VBS script
                subprocess.Popen(['cscript.exe', vbs_path])
                
                QMessageBox.information(
                    self,
                    "Service Starting",
                    "The service start command has been executed.\n\n"
                    "Please wait a few moments for the service to start."
                )
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during service start: {str(e)}")
            
    def stop_service(self):
        """Stop the Windows service"""
        try:
            # Show confirmation dialog
            result = QMessageBox.question(
                self, 
                "Administrator Privileges Required",
                "Stopping the service requires administrator privileges.\n\n"
                "Click 'Yes' to continue.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                # Create a temporary vbs script to elevate privileges
                vbs_path = os.path.join(os.environ['TEMP'], 'elevate_service_stop.vbs')
                with open(vbs_path, 'w') as f:
                    f.write('Set UAC = CreateObject("Shell.Application")\n')
                    f.write('UAC.ShellExecute "net", "stop CommercialRealEstateScraper", "", "runas", 1\n')
                
                # Execute the VBS script
                subprocess.Popen(['cscript.exe', vbs_path])
                
                QMessageBox.information(
                    self,
                    "Service Stopping",
                    "The service stop command has been executed.\n\n"
                    "Please wait a few moments for the service to stop."
                )
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during service stop: {str(e)}")
            
    def remove_service(self):
        """Remove the Windows service"""
        try:
            # Show confirmation dialog
            result = QMessageBox.question(
                self, 
                "Administrator Privileges Required",
                "Removing the service requires administrator privileges.\n\n"
                "Click 'Yes' to continue.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                # Create a small Python script that will handle the removal
                remove_script = os.path.join(os.environ['TEMP'], 'remove_service.py')
                
                # Write the removal script
                with open(remove_script, 'w') as f:
                    f.write('import sys\n')
                    f.write('import os\n')
                    f.write(f'sys.path.append(r"{parent_dir}")\n')  # Add parent directory to path
                    f.write('import win32serviceutil\n')
                    f.write('from service.service import ScraperService\n')
                    f.write('win32serviceutil.HandleCommandLine(ScraperService, argv=["", "remove"])\n')
                
                # Create a VBS script to run the Python script with admin privileges
                vbs_path = os.path.join(os.environ['TEMP'], 'elevate_service_remove.vbs')
                with open(vbs_path, 'w') as f:
                    f.write('Set UAC = CreateObject("Shell.Application")\n')
                    py_path = sys.executable.replace('\\', '\\\\')
                    script_path = remove_script.replace('\\', '\\\\')
                    f.write(f'UAC.ShellExecute "{py_path}", "{script_path}", "", "runas", 1\n')
                
                # Execute the VBS script to run with admin privileges
                subprocess.Popen(['cscript.exe', vbs_path])
                
                QMessageBox.information(
                    self,
                    "Service Removal",
                    "The service removal command has been executed.\n\n"
                    "Please wait a few moments for the service to be removed."
                )
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during service removal: {str(e)}")
    
    def schedule_service(self):
        """Schedule the service to run at configured time"""
        try:
            # Get the configured time
            scheduled_time = self.background_time_edit.time().toString('HH:mm')
            
            # Update configuration with the scheduled time
            self.user_config['background_time'] = scheduled_time
            self.user_config['enable_background'] = True
            
            # Save to file
            with open(config.CONFIG_FILE, 'w') as f:
                json.dump(self.user_config, f, indent=2)
            
            QMessageBox.information(
                self, 
                "Service Scheduled", 
                f"Service has been scheduled to run at {scheduled_time}."
            )
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during service scheduling: {str(e)}")
    
    def run_search_now(self):
        """Run the search immediately"""
        try:
            # Show confirmation dialog
            result = QMessageBox.question(
                self, 
                "Run Immediate Search",
                "This will trigger an immediate search with the current configuration settings.\n\n"
                "Click 'Yes' to continue.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                # Create a small Python script that will run the scraper
                run_script = os.path.join(os.environ['TEMP'], 'run_service_now.py')
                
                # Write the run script
                with open(run_script, 'w') as f:
                    f.write('import sys\n')
                    f.write('import os\n')
                    f.write(f'sys.path.append(r"{parent_dir}")\n')  # Add parent directory to path
                    f.write('import servicemanager\n')
                    f.write('from service.service import ScraperService\n')
                    f.write('servicemanager.Initialize()\n')
                    f.write('servicemanager.PrepareToHostSingle(ScraperService)\n')
                    f.write('service = ScraperService([])\n')
                    f.write('service.run_scraper()\n')
                
                # Create a VBS script to run the Python script with admin privileges
                vbs_path = os.path.join(os.environ['TEMP'], 'elevate_service_run_now.vbs')
                with open(vbs_path, 'w') as f:
                    f.write('Set UAC = CreateObject("Shell.Application")\n')
                    py_path = sys.executable.replace('\\', '\\\\')
                    script_path = run_script.replace('\\', '\\\\')
                    f.write(f'UAC.ShellExecute "{py_path}", "{script_path}", "", "runas", 1\n')
                
                # Execute the VBS script to run with admin privileges
                subprocess.Popen(['cscript.exe', vbs_path])
                
                # Show confirmation to user
                QMessageBox.information(
                    self,
                    "Search Started",
                    "The immediate search has been triggered.\n\n"
                    "Check the results tab or log files for search results."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error triggering immediate search: {str(e)}")
    
    def refresh_results(self):
        """Refresh the results display"""
        self.results_text.clear()
        self.results_text.append("Refreshing status...")
        
        # Get the status directly from service
        status = self._get_service_status()
        
        # Display the service status
        self.results_text.append("\nService Status:")
        if status.get("installed", False):
            self.results_text.append("  - Service is installed")
        else:
            self.results_text.append("  - Service is NOT installed")
            
        if status.get("running", False):
            self.results_text.append("  - Service is running")
        else:
            self.results_text.append("  - Service is NOT running")
            
        if status.get("executing", False):
            self.results_text.append("  - Service is currently executing a task")
        else:
            self.results_text.append("  - Service is idle")
            
        # Add service configuration from self.user_config
        self.results_text.append("\nService Configuration:")
        self.results_text.append(f"  - Background task enabled: {self.user_config.get('enable_background', False)}")
        self.results_text.append(f"  - Scheduled time: {self.user_config.get('background_time', '03:00')}")
        self.results_text.append(f"  - Property types: {', '.join(self.user_config.get('property_types', []))}")
        self.results_text.append(f"  - Location: {self.user_config.get('location', '')}")
        self.results_text.append(f"  - Websites: {', '.join(self.user_config.get('websites', []))}")
    
    def refresh_log(self):
        """Refresh the log display"""
        # New service logs to ~/.commercialrealestate/logs/service.log
        log_file = os.path.join(os.path.expanduser("~"), ".commercialrealestate", "logs", "service.log")
        
        try:
            # Check if log file exists
            if os.path.exists(log_file):
                # Read the last 100 lines
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    last_lines = lines[-100:] if len(lines) > 100 else lines
                    
                    # Display in the log text area
                    self.log_text.clear()
                    for line in last_lines:
                        self.log_text.append(line.strip())
                    
                    # Scroll to bottom
                    self.log_text.verticalScrollBar().setValue(
                        self.log_text.verticalScrollBar().maximum()
                    )
            else:
                self.log_text.clear()
                self.log_text.append(f"Log file not found at: {log_file}")
        
        except Exception as e:
            self.log_text.clear()
            self.log_text.append(f"Error reading log file: {str(e)}")
    
    def closeEvent(self, event):
        """Called when the window is closed"""
        # Stop the worker thread
        if hasattr(self, 'worker_thread'):
            self.worker_thread.stop()
        
        # Accept the event
        event.accept()

if __name__ == "__main__":
    # Create application
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec_()) 