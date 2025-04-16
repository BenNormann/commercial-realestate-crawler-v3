"""
Launcher for the Commercial Real Estate Crawler GUI.
"""

import os
import sys
import logging
import subprocess
import ctypes
import time
from pathlib import Path

# Configure logging
log_dir = os.path.join(os.path.dirname(__file__), 'debug')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'gui.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('gui_launcher')

def is_admin():
    """Check if the current process has admin privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

def run_as_admin(cmd):
    """Run a command with admin privileges"""
    if isinstance(cmd, list):
        cmd = ' '.join(cmd)
    
    try:
        logger.info(f"Running with admin privileges: {cmd}")
        if is_admin():
            # Already admin, just run the command
            return subprocess.run(cmd, shell=True, check=True)
        else:
            # Need to elevate
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, cmd, None, 1
            )
        return True
    except Exception as e:
        logger.error(f"Error running as admin: {e}")
        return False

def check_service_status():
    """Check if the service is installed and running"""
    try:
        # Use SC command to check service status
        process = subprocess.run(
            ["sc", "query", "CommercialRealEstateScraper"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True, 
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        output = process.stdout.lower()
        logger.debug(f"Service status raw output: {output}")
        
        # Check if service is installed
        installed = "commercialrealestate" in output and "specified service does not exist" not in output
        
        # Check if service is running
        running = "running" in output
        
        logger.info(f"Service status: installed={installed}, running={running}")
        return installed, running
    
    except Exception as e:
        logger.error(f"Error checking service status: {str(e)}")
        return False, False

def install_service():
    """Install the Windows service with admin elevation"""
    logger.info("Installing service...")
    
    try:
        # Get path to current directory and service module
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Command to install service
        install_cmd = f'-c "import sys; sys.path.append(r\'{current_dir}\'); from service.service import ScraperService; import win32serviceutil; win32serviceutil.HandleCommandLine(ScraperService, argv=[\'\', \'install\'])"'
        
        # Run the command with admin privileges
        success = run_as_admin(install_cmd)
        
        # Add a delay to wait for installation
        time.sleep(2)
        
        # Check if it was successful
        installed, _ = check_service_status()
        return installed
    
    except Exception as e:
        logger.error(f"Error during service installation: {str(e)}", exc_info=True)
        return False

def start_service():
    """Start the Windows service with admin elevation"""
    logger.info("Starting service...")
    
    try:
        # Run the net start command with admin privileges
        success = run_as_admin("net start CommercialRealEstateScraper")
        
        # Add a delay to wait for start
        time.sleep(2)
        
        # Check if it was successful
        _, running = check_service_status()
        return running
    
    except Exception as e:
        logger.error(f"Error starting service: {str(e)}")
        return False

def prompt_service_action_gui():
    """Prompt user with GUI dialogs to install or start the service if needed"""
    # Import PyQt here to avoid circular imports
    from PyQt5.QtWidgets import QApplication, QMessageBox
    
    try:
        # Create a temporary QApplication instance if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        installed, running = check_service_status()
        
        if not installed:
            result = QMessageBox.question(
                None, 
                "Service Not Installed",
                "The Real Estate Crawler service is not installed.\n\n"
                "Would you like to install it now? (Requires admin privileges)",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                success = install_service()
                
                if success:
                    QMessageBox.information(
                        None,
                        "Service Installed",
                        "The service was installed successfully."
                    )
                else:
                    QMessageBox.warning(
                        None,
                        "Installation Issue",
                        "There may have been an issue with the installation.\n\n"
                        "Check the logs for more details."
                    )
        
        elif not running:
            result = QMessageBox.question(
                None, 
                "Service Not Running",
                "The Real Estate Crawler service is installed but not running.\n\n"
                "Would you like to start it now? (Requires admin privileges)",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                success = start_service()
                
                if success:
                    QMessageBox.information(
                        None,
                        "Service Started",
                        "The service was started successfully."
                    )
                else:
                    QMessageBox.warning(
                        None,
                        "Start Issue",
                        "There may have been an issue starting the service.\n\n"
                        "Check the logs for more details."
                    )
    
    except Exception as e:
        logger.error(f"Error during service prompt GUI: {str(e)}")
        # Fall back to console if GUI fails
        print(f"Error showing service dialog: {str(e)}")

def main():
    try:
        # Try to import PyQt5 first to make sure it's available
        from PyQt5.QtWidgets import QApplication, QMessageBox
        
        # Ask about service status using GUI
        prompt_service_action_gui()
        
        # Import the GUI application
        from gui.app import MainWindow
        
        # Create and run the application
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            
        window = MainWindow()
        window.show()
        
        # Run the application
        sys.exit(app.exec_())
        
    except ImportError as e:
        logger.error(f"Missing dependencies: {str(e)}")
        print(f"Error: Missing dependencies - {str(e)}")
        print("Please install the required dependencies with: pip install -r requirements.txt")
        input("Press Enter to exit...")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Error starting GUI: {str(e)}")
        print(f"Error starting GUI: {str(e)}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main() 