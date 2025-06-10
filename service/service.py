import os
import sys
import time
import win32serviceutil
import win32service
import win32event
import servicemanager
import win32api
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scraper.scraper_manager import ScraperManager
import config

# Get the debug directory path
DEBUG_DIR = os.path.join(project_root, "debug")

class ScraperService(win32serviceutil.ServiceFramework):
    _svc_name_ = "CommercialRealEstateScraper"
    _svc_display_name_ = "Commercial Real Estate Scraper Service"
    _svc_description_ = "Performs scheduled scraping of commercial real estate websites"
    
    def __init__(self, args):
        # Make sure the debug directory exists
        os.makedirs(DEBUG_DIR, exist_ok=True)
        
        with open(os.path.join(DEBUG_DIR, "service_init.txt"), "a") as f:
            f.write(f"\n--- Service constructor called at {time.ctime()} ---\n")
            f.write(f"Args: {args}\n")
            f.write(f"Working directory: {os.getcwd()}\n")
            f.write(f"Python: {sys.executable}\n")
            f.write(f"Project root: {project_root}\n")
            
        # Initialize base service
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        self.scraper_manager = None
        
        # Load configuration
        self.config = self.load_config()
        
        # Schedule configuration
        self.schedule_interval = self.config.get('schedule_interval_hours', 24)  # Default: run daily
        self.last_run_time = None
        
    def load_config(self) -> Dict[str, Any]:
        """Load service configuration from the same config file as the GUI"""
        try:
            # Use the same configuration as the GUI
            if os.path.exists(config.CONFIG_FILE):
                with open(config.CONFIG_FILE, 'r') as f:
                    gui_config = json.load(f)
            else:
                gui_config = config.DEFAULT_CONFIG.copy()
            
            # Add service-specific defaults that aren't in the GUI config
            service_config = gui_config.copy()
            service_config.setdefault("schedule_interval_hours", 24)
            
            # Normalize property types to lowercase for consistency
            if 'property_types' in service_config:
                service_config['property_types'] = [pt.lower() for pt in service_config['property_types']]
            
            return service_config
        except Exception as e:
            with open(os.path.join(DEBUG_DIR, "service_config_error.txt"), "a") as f:
                f.write(f"\n--- Config load error at {time.ctime()} ---\n")
                f.write(f"Error: {str(e)}\n")
            # Return GUI defaults if config loading fails
            service_config = config.DEFAULT_CONFIG.copy()
            service_config["schedule_interval_hours"] = 24
            return service_config
    
    def SvcStop(self):
        # Log that we're stopping
        with open(os.path.join(DEBUG_DIR, "service_stop.txt"), "a") as f:
            f.write(f"\n--- Service stop called at {time.ctime()} ---\n")
        
        # Tell the SCM we're stopping
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.running = False
    
    def SvcDoRun(self):
        # Log that we're starting
        with open(os.path.join(DEBUG_DIR, "service_run.txt"), "a") as f:
            f.write(f"\n--- SvcDoRun called at {time.ctime()} ---\n")
            f.write(f"Working directory: {os.getcwd()}\n")
            f.write(f"Python path: {sys.path}\n")
        
        # Report that we're starting
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        
        # Notify the SCM that we're running
        try:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
        except Exception as e:
            with open(os.path.join(DEBUG_DIR, "service_error.txt"), "a") as f:
                f.write(f"\n--- Error logging service start at {time.ctime()} ---\n")
                f.write(f"Error: {str(e)}\n")
        
        # Report that we're now running
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        
        # Start the main service loop
        self.main()
    
    def should_run_scraping(self) -> bool:
        """Check if it's time to run scraping based on schedule"""
        # If background service is not enabled, don't run automatically
        if not self.config.get('enable_background', False):
            return False
            
        # If never run before, check if it's the right time of day
        if self.last_run_time is None:
            return self.is_scheduled_time()
        
        # Check if it's been more than 23 hours since last run AND it's the right time
        time_since_last_run = datetime.now() - self.last_run_time
        if time_since_last_run >= timedelta(hours=23) and self.is_scheduled_time():
            return True
            
        return False
    
    def is_scheduled_time(self) -> bool:
        """Check if current time matches the scheduled time"""
        try:
            # Legacy code - background_time is no longer used
            # Using scheduled_times array instead (handled by Task Scheduler)
            background_time = self.config.get('background_time', '03:00')
            scheduled_hour, scheduled_minute = map(int, background_time.split(':'))
            
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            
            # Allow a 5-minute window around the scheduled time
            scheduled_minutes_total = scheduled_hour * 60 + scheduled_minute
            current_minutes_total = current_hour * 60 + current_minute
            
            return abs(current_minutes_total - scheduled_minutes_total) <= 5
        except Exception as e:
            with open(os.path.join(DEBUG_DIR, "service_schedule_error.txt"), "a") as f:
                f.write(f"\n--- Schedule check error at {time.ctime()} ---\n")
                f.write(f"Error: {str(e)}\n")
            return False
    
    def trigger_immediate_scraping(self):
        """Trigger an immediate scraping operation (for GUI integration)"""
        try:
            with open(os.path.join(DEBUG_DIR, "service_manual_trigger.txt"), "a") as f:
                f.write(f"\n--- Manual trigger at {time.ctime()} ---\n")
            
            # Run scraping in a separate thread
            scraping_thread = threading.Thread(target=self.run_scraping)
            scraping_thread.daemon = True
            scraping_thread.start()
            return True
        except Exception as e:
            with open(os.path.join(DEBUG_DIR, "service_manual_trigger_error.txt"), "a") as f:
                f.write(f"\n--- Manual trigger error at {time.ctime()} ---\n")
                f.write(f"Error: {str(e)}\n")
            return False
    
    def run_scraping(self):
        """Execute the scraping operation"""
        try:
            with open(os.path.join(DEBUG_DIR, "service_scraping.txt"), "a") as f:
                f.write(f"\n--- Starting scraping at {time.ctime()} ---\n")
                f.write(f"Configuration: {self.config}\n")
            
            # Initialize scraper manager if not already done
            if self.scraper_manager is None:
                self.scraper_manager = ScraperManager(debug_mode=False)
            
            # Prepare parameters matching GUI format
            min_price = self.config.get('min_price', '')
            max_price = self.config.get('max_price', '')
            
            # Convert empty strings to None for scraper manager
            min_price = min_price if min_price and min_price.strip() else None
            max_price = max_price if max_price and max_price.strip() else None
            
            # Calculate start date based on days_back
            days_back = self.config.get('days_back', 1)
            start_date = datetime.now() - timedelta(days=days_back)
            
            # Run the scraping with configured parameters
            results = self.scraper_manager.search(
                property_types=self.config['property_types'],
                location=self.config['location'],
                min_price=min_price,
                max_price=max_price,
                start_date=start_date,
                websites=self.config.get('websites')
            )
            
            # Log results
            with open(os.path.join(DEBUG_DIR, "service_scraping.txt"), "a") as f:
                f.write(f"Scraping completed at {time.ctime()}\n")
                total_results = 0
                if isinstance(results, dict):
                    for website, website_results in results.items():
                        count = len(website_results) if website_results else 0
                        total_results += count
                        f.write(f"  {website}: {count} results\n")
                else:
                    total_results = len(results) if results else 0
                    f.write(f"  Total results: {total_results}\n")
                f.write(f"  Grand total: {total_results} results\n")
            
            # Update last run time
            self.last_run_time = datetime.now()
            
            # Save results to both debug directory and user config directory for GUI access
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save to debug directory
            debug_results_file = os.path.join(DEBUG_DIR, f"scraping_results_{timestamp}.json")
            with open(debug_results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            # Also save to user config directory for GUI access
            os.makedirs(config.CONFIG_DIR, exist_ok=True)
            gui_results_file = os.path.join(config.CONFIG_DIR, f"results_{timestamp}.json")
            with open(gui_results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            # Save last run info for GUI
            last_run_info = {
                "timestamp": timestamp,
                "datetime": datetime.now().isoformat(),
                "total_results": total_results,
                "websites": list(results.keys()) if isinstance(results, dict) else ["combined"],
                "config_used": self.config
            }
            last_run_file = os.path.join(config.CONFIG_DIR, "last_run.json")
            with open(last_run_file, 'w') as f:
                json.dump(last_run_info, f, indent=2, default=str)
            
        except Exception as e:
            with open(os.path.join(DEBUG_DIR, "service_scraping_error.txt"), "a") as f:
                f.write(f"\n--- Scraping error at {time.ctime()} ---\n")
                f.write(f"Error: {str(e)}\n")
                import traceback
                f.write(traceback.format_exc())
    
    def main(self):
        try:
            # Log that the main loop is starting
            with open(os.path.join(DEBUG_DIR, "service_main.txt"), "a") as f:
                f.write(f"\n--- Main loop starting at {time.ctime()} ---\n")
                f.write(f"Schedule interval: {self.schedule_interval} hours\n")
                f.write(f"Configuration: {self.config}\n")
            
            # Main service loop
            config_refresh_counter = 0
            while self.running:
                # Refresh configuration every 10 minutes (10 iterations of 1-minute loops)
                if config_refresh_counter % 10 == 0:
                    old_config = self.config.copy()
                    self.config = self.load_config()
                    if old_config != self.config:
                        with open(os.path.join(DEBUG_DIR, "service_config_refresh.txt"), "a") as f:
                            f.write(f"\n--- Configuration refreshed at {time.ctime()} ---\n")
                            f.write(f"New config: {self.config}\n")
                
                # Check if it's time to run scraping
                if self.should_run_scraping():
                    # Run scraping in a separate thread to avoid blocking the service
                    scraping_thread = threading.Thread(target=self.run_scraping)
                    scraping_thread.daemon = True
                    scraping_thread.start()
                
                # Wait for service stop signal with shorter timeout for more responsive scheduling
                rc = win32event.WaitForSingleObject(self.hWaitStop, 60000)  # 1 minute
                
                # Write a heartbeat file to show we're alive with better status info
                with open(os.path.join(DEBUG_DIR, "service_heartbeat.txt"), "a") as f:
                    status_info = {
                        "timestamp": time.ctime(),
                        "background_enabled": self.config.get('enable_background', False),
                        "scheduled_time": self.config.get('background_time', 'Not set'),  # Legacy - now using scheduled_times array
                        "last_run": self.last_run_time.isoformat() if self.last_run_time else "Never",
                        "location": self.config.get('location', 'Not set'),
                        "websites": self.config.get('websites', [])
                    }
                    f.write(f"Service heartbeat: {json.dumps(status_info)}\n")
                
                # Create/update status file for GUI
                try:
                    os.makedirs(config.CONFIG_DIR, exist_ok=True)
                    status_file = os.path.join(config.CONFIG_DIR, "service_status.json")
                    with open(status_file, 'w') as f:
                        status_info["running"] = True
                        status_info["installed"] = True
                        status_info["state"] = "running"
                        json.dump(status_info, f, indent=2)
                except Exception as e:
                    with open(os.path.join(DEBUG_DIR, "service_status_error.txt"), "a") as f:
                        f.write(f"Error writing status: {str(e)}\n")
                
                config_refresh_counter += 1
                
                # If stop requested
                if rc == win32event.WAIT_OBJECT_0:
                    # Log that we received a stop signal
                    with open(os.path.join(DEBUG_DIR, "service_main.txt"), "a") as f:
                        f.write(f"Stop signal received at {time.ctime()}\n")
                    break
            
            # Log that the main loop ended
            with open(os.path.join(DEBUG_DIR, "service_main.txt"), "a") as f:
                f.write(f"Main loop ended at {time.ctime()}\n")
                
        except Exception as e:
            # Log any errors
            with open(os.path.join(DEBUG_DIR, "service_error.txt"), "a") as f:
                f.write(f"\n--- Error in main loop at {time.ctime()} ---\n")
                f.write(f"Error: {str(e)}\n")
                import traceback
                f.write(traceback.format_exc())


def install():
    """Helper function to install the service"""
    try:
        # Make sure the debug directory exists
        os.makedirs(DEBUG_DIR, exist_ok=True)
        
        # Log that we're installing
        with open(os.path.join(DEBUG_DIR, "service_install.txt"), "a") as f:
            f.write(f"\n--- Service installation started at {time.ctime()} ---\n")
            f.write(f"Working directory: {os.getcwd()}\n")
            f.write(f"Python executable: {sys.executable}\n")
            f.write(f"Arguments: {sys.argv}\n")
        
        # Handle the command line
        win32serviceutil.HandleCommandLine(ScraperService)
        
    except Exception as e:
        # Log any installation errors
        with open(os.path.join(DEBUG_DIR, "service_install_error.txt"), "a") as f:
            f.write(f"\n--- Service installation error at {time.ctime()} ---\n")
            f.write(f"Error: {str(e)}\n")
            f.write(f"Working directory: {os.getcwd()}\n")
            f.write(f"Python executable: {sys.executable}\n")
            import traceback
            f.write(traceback.format_exc())
        
        # Re-raise the exception
        raise


def debug_run():
    """Run a simplified version of the service for debugging"""
    try:
        # Make sure the debug directory exists
        os.makedirs(DEBUG_DIR, exist_ok=True)
        
        with open(os.path.join(DEBUG_DIR, "service_debug.txt"), "a") as f:
            f.write(f"\n--- Debug run started at {time.ctime()} ---\n")
        
        print("Starting service in debug mode...")
        
        # Create a simpler version for debugging
        class SimpleService:
            def __init__(self):
                self.is_alive = True
                print("Service initialized")
                
            def run(self):
                print("Service running, press Ctrl+C to stop")
                try:
                    while self.is_alive:
                        # Write heartbeat
                        with open(os.path.join(DEBUG_DIR, "service_heartbeat.txt"), "a") as f:
                            f.write(f"Debug heartbeat at {time.ctime()}\n")
                        time.sleep(5)
                except KeyboardInterrupt:
                    print("Service stopped by user")
                except Exception as e:
                    with open(os.path.join(DEBUG_DIR, "service_error.txt"), "a") as f:
                        f.write(f"\n--- Debug run error at {time.ctime()} ---\n")
                        f.write(f"Error: {str(e)}\n")
                        import traceback
                        f.write(traceback.format_exc())
        
        # Run the simple service
        svc = SimpleService()
        svc.run()
        
    except Exception as e:
        with open(os.path.join(DEBUG_DIR, "service_error.txt"), "a") as f:
            f.write(f"\n--- Debug setup error at {time.ctime()} ---\n")
            f.write(f"Error: {str(e)}\n")
            import traceback
            f.write(traceback.format_exc())


if __name__ == '__main__':
    # Make sure the debug directory exists
    os.makedirs(DEBUG_DIR, exist_ok=True)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        # Run in simplified debug mode
        debug_run()
    else:
        # Normal service operation
        try:
            win32serviceutil.HandleCommandLine(ScraperService)
        except Exception as e:
            with open(os.path.join(DEBUG_DIR, "service_cmdline_error.txt"), "a") as f:
                f.write(f"\n--- Command line error at {time.ctime()} ---\n")
                f.write(f"Error: {str(e)}\n")
                f.write(f"Arguments: {sys.argv}\n")
                import traceback
                f.write(traceback.format_exc())
