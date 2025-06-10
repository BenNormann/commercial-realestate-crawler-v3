"""
Launcher for the Commercial Real Estate Crawler GUI.
"""

import os
import sys
import logging
import subprocess
import ctypes
import time
import argparse
from pathlib import Path

# Add project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from debug.logger import setup_logger

logger = setup_logger('gui_launcher')

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
            # Already admin, just run the command directly
            logger.info("Already admin, running directly")
            return subprocess.run(cmd, shell=True, check=True)
        else:
            # Need to elevate - use ShellExecute directly with the command
            logger.info("Not admin, elevating privileges")
            if cmd.startswith('-c'):
                # For Python commands, use sys.executable
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, cmd, None, 1
                )
            else:
                # For system commands like 'net start', use cmd.exe
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "cmd.exe", f"/c {cmd}", None, 1
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
        
        # Removed service status logging since we're using Task Scheduler now
        # logger.info(f"Service status: installed={installed}, running={running}")
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
        if is_admin():
            # Already admin, run the command directly and capture output
            logger.info("Already admin, running net start directly")
            
            try:
                result = subprocess.run(
                    "net start CommercialRealEstateScraper", 
                    shell=True, 
                    capture_output=True,
                    text=True,
                    check=False  # Don't raise exception so we can log the error
                )
                
                if result.returncode != 0:
                    logger.error(f"Service start failed with return code {result.returncode}")
                    if result.stderr:
                        logger.error(f"Error output: {result.stderr}")
                    if result.stdout:
                        logger.error(f"Standard output: {result.stdout}")
                else:
                    logger.info("Service start command returned successfully")
                    if result.stdout:
                        logger.info(f"Service start output: {result.stdout}")
            except Exception as e:
                logger.error(f"Exception running net start directly: {str(e)}")
                
        else:
            # Need to elevate - use ShellExecute directly with the command
            logger.info("Not admin, elevating privileges for net start")
            
            # Create a script to capture the output after elevation
            temp_dir = os.environ.get('TEMP', '')
            output_file = os.path.join(temp_dir, 'service_start_output.txt')
            
            # Create a batch file to run the command and capture output
            batch_file = os.path.join(temp_dir, 'start_service.bat')
            with open(batch_file, 'w') as f:
                f.write(f'@echo off\n')
                f.write(f'echo Starting service at %time% >> "{output_file}"\n')
                f.write(f'net start CommercialRealEstateScraper >> "{output_file}" 2>&1\n')
                f.write(f'echo Exit code: %errorlevel% >> "{output_file}"\n')
                f.write(f'pause\n')
            
            # Use ShellExecute to run with elevation
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", batch_file, None, None, 1
            )
            
            logger.info(f"Elevated command execution initiated. Output will be in {output_file}")
        
        # Add a delay to wait for start
        time.sleep(3)
        
        # Check if it was successful
        installed, running = check_service_status()
        
        # If not running, try to read the output file if it exists
        if not running and os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    output = f.read()
                    logger.info(f"Service start output: {output}")
            except Exception as e:
                logger.error(f"Could not read service start output: {str(e)}")
        
        return running
    
    except Exception as e:
        logger.error(f"Error starting service: {str(e)}", exc_info=True)
        return False

def prompt_service_install_only():
    """Prompt user with GUI dialog to install the service if needed, but don't prompt to start it"""
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
                        "The service was installed successfully.\n\n"
                        "Note: The service is not started automatically.\n"
                        "You can start it manually from the Service Control panel in the application."
                    )
                else:
                    QMessageBox.warning(
                        None,
                        "Installation Issue",
                        "There may have been an issue with the installation.\n\n"
                        "Check the logs for more details."
                    )
        
        # We don't prompt to start the service anymore, even if it's installed but not running
    
    except Exception as e:
        logger.error(f"Error during service install prompt: {str(e)}")
        # Fall back to console if GUI fails
        print(f"Error showing service dialog: {str(e)}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Commercial Real Estate Crawler GUI Launcher")
    parser.add_argument('--debug', action='store_true', help='Run in debug mode (shows console and browser)')
    args = parser.parse_args()
    
    # Hide console window unless in debug mode
    if not args.debug:
        # Hide the console window
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE
    
    try:
        # Check if we have admin privileges, and if not, restart with elevation
        if not is_admin():
            logger.info("Not running as admin, requesting elevation...")
            if args.debug:
                print("Requesting administrator privileges...")
            
            # Get the current script path and arguments
            script_path = os.path.abspath(__file__)
            cmd_args = ' '.join(sys.argv[1:])  # Get any command line args (including --debug)
            
            # Use ShellExecuteW to restart with admin privileges
            try:
                ctypes.windll.shell32.ShellExecuteW(
                    None, 
                    "runas", 
                    sys.executable, 
                    f'"{script_path}" {cmd_args}', 
                    None, 
                    1  # SW_SHOWNORMAL
                )
                # Exit this non-admin instance
                sys.exit(0)
            except Exception as e:
                logger.error(f"Failed to restart with admin privileges: {e}")
                if args.debug:
                    print(f"Failed to request admin privileges: {e}")
                    print("The application may not work properly without administrator rights.")
                    input("Press Enter to continue anyway...")
        else:
            logger.info("Running with administrator privileges")
            if args.debug:
                print("Running with administrator privileges")
        
        # Suppress Qt warnings and MIME database errors unless in debug mode
        if not args.debug:
            os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'
        
        # Try to import PyQt5 first to make sure it's available
        from PyQt5.QtWidgets import QApplication, QMessageBox
        
        # Import the GUI application and pass debug flag
        from gui.app import MainWindow
        
        # Create and run the application
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            
        window = MainWindow(debug_mode=args.debug)
        window.show()
        
        # Run the application
        sys.exit(app.exec_())
        
    except ImportError as e:
        logger.error(f"Missing dependencies: {str(e)}")
        if args.debug:
            print(f"Error: Missing dependencies - {str(e)}")
            print("Please install the required dependencies with: pip install -r requirements.txt")
            input("Press Enter to exit...")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Error starting GUI: {str(e)}")
        if args.debug:
            print(f"Error starting GUI: {str(e)}")
            input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main() 