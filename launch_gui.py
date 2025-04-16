"""
Launcher for the Commercial Real Estate Crawler GUI.
"""

import os
import sys
import logging
import subprocess
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

def check_service_status():
    """Check if the service is installed and running"""
    try:
        # Path to batch file
        batch_file = os.path.join(os.path.dirname(__file__), 'service_runner.bat')
        
        if not os.path.exists(batch_file):
            logger.warning(f"Service batch file not found: {batch_file}")
            return False, False
        
        # Run the status command
        process = subprocess.run([batch_file, 'status'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True, 
                               creationflags=subprocess.CREATE_NO_WINDOW)
        
        output = process.stdout.lower()
        logger.info(f"Service status output: {output}")
        
        # Check if service is installed
        installed = "installed: true" in output or "'installed': True" in output
        
        # Check if service is running
        running = "running: true" in output or "'running': True" in output
        
        logger.info(f"Service status: installed={installed}, running={running}")
        return installed, running
    
    except Exception as e:
        logger.error(f"Error checking service status: {str(e)}")
        return False, False

def run_service_command(command):
    """Run a service command and wait for it to complete"""
    try:
        batch_file = os.path.join(os.path.dirname(__file__), 'service_runner.bat')
        
        # Create a direct command window that stays open if there are errors
        process = subprocess.Popen([batch_file, command], 
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True)
        
        # Wait for process to complete with timeout
        stdout, stderr = process.communicate(timeout=30)
        
        logger.info(f"Service {command} completed with exit code {process.returncode}")
        logger.info(f"Service {command} stdout: {stdout}")
        
        if process.returncode != 0:
            logger.error(f"Service {command} stderr: {stderr}")
            return False, stderr
        
        return True, stdout
    
    except subprocess.TimeoutExpired:
        logger.warning(f"Service {command} is taking longer than expected")
        # Don't kill the process - let it continue in the background
        return True, "Command is still executing..."
    
    except Exception as e:
        logger.error(f"Error running service {command}: {str(e)}")
        return False, str(e)

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
                "Would you like to install it now?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                logger.info("Installing service...")
                
                batch_file = os.path.join(os.path.dirname(__file__), 'service_runner.bat')
                
                # Launch with administrator privileges
                subprocess.Popen([
                    'powershell', 'Start-Process', 
                    f'"{batch_file}"', '-ArgumentList', 'install',
                    '-Verb', 'RunAs'
                ])
                
                # Wait a bit for the admin prompt and installation to happen
                time.sleep(5)
                
                # Check if installation was successful
                installed, _ = check_service_status()
                if installed:
                    QMessageBox.information(
                        None,
                        "Service Installed",
                        "The service was installed successfully."
                    )
                else:
                    QMessageBox.warning(
                        None,
                        "Installation Pending",
                        "The service installation was initiated. Please check the console window for details."
                    )
        
        elif not running:
            result = QMessageBox.question(
                None, 
                "Service Not Running",
                "The Real Estate Crawler service is installed but not running.\n\n"
                "Would you like to start it now?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                logger.info("Starting service...")
                
                batch_file = os.path.join(os.path.dirname(__file__), 'service_runner.bat')
                
                # Launch with administrator privileges
                subprocess.Popen([
                    'powershell', 'Start-Process', 
                    f'"{batch_file}"', '-ArgumentList', 'start',
                    '-Verb', 'RunAs'
                ])
                
                # Wait a bit for the admin prompt and service to start
                time.sleep(5)
                
                # Check if service started successfully
                _, running = check_service_status()
                if running:
                    QMessageBox.information(
                        None,
                        "Service Started",
                        "The service was started successfully."
                    )
                else:
                    QMessageBox.warning(
                        None,
                        "Start Pending",
                        "The service start was initiated. Please check the console window for details."
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