import os
import sys
import time
import logging
import json
from datetime import datetime, timedelta
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import threading

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import project modules
from scraper.scraper_manager import ScraperManager
import config

class ScraperService(win32serviceutil.ServiceFramework):
    """Windows service for scheduled web scraping"""
    
    _svc_name_ = "CommercialRealEstateScraper"
    _svc_display_name_ = "Commercial Real Estate Scraper Service"
    _svc_description_ = "Performs scheduled scraping of commercial real estate websites"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = False
        self.run_now_event = threading.Event()
        
        # Configure logging
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service.log")
        self.logger = self._setup_logging(log_path)
        
        self.logger.debug("Service initialized")
    
    def _setup_logging(self, log_path):
        """Set up logging for the service"""
        logger = logging.getLogger("ScraperService")
        logger.setLevel(logging.DEBUG)
        
        # Create file handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter and add to handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(file_handler)
        
        return logger
    
    def SvcStop(self):
        """Called when the service is asked to stop"""
        self.logger.info("Service stop requested")
        self.running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
    
    def SvcDoRun(self):
        """Main service entry point when the service starts"""
        self.logger.info("Service starting")
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()
    
    def main(self):
        """Main service logic"""
        self.running = True
        self.logger.info("Service main loop started")
        
        while self.running:
            try:
                # Check if service should scrape now
                if self.run_now_event.is_set():
                    self.logger.info("Run now requested")
                    self.run_scraper()
                    self.run_now_event.clear()
                    self.logger.info("Run now completed")
                
                # Check if it's time to run a scheduled task
                self.check_scheduled_run()
                
                # Wait for events (stop request or run now request)
                # Use a short timeout to periodically check schedule
                timeout = win32event.WaitForSingleObject(self.hWaitStop, 60 * 1000)  # 60 seconds
                
                if timeout == win32event.WAIT_OBJECT_0:
                    # Stop event received
                    break
                    
            except Exception as e:
                self.logger.error(f"Error in service main loop: {str(e)}", exc_info=True)
                time.sleep(60)  # Wait before retrying
        
        self.logger.info("Service stopped")
    
    def check_scheduled_run(self):
        """Check if it's time to run a scheduled scrape"""
        try:
            # Load config
            with open(config.CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                
            # Check if background mode is enabled
            if not cfg.get('enable_background', False):
                return
                
            # Get scheduled time
            scheduled_time = cfg.get('background_time', '03:00')
            hour, minute = map(int, scheduled_time.split(':'))
            
            # Get current time
            now = datetime.now()
            current_hour, current_minute = now.hour, now.minute
            
            # Get the last run time (create file if doesn't exist)
            last_run_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_run.txt")
            
            if not os.path.exists(last_run_file):
                # First run, create file
                self.logger.info("Last run file not found, creating...")
                self._update_last_run(last_run_file)
                return
                
            # Read last run time
            with open(last_run_file, 'r') as f:
                last_run_str = f.read().strip()
                last_run = datetime.fromisoformat(last_run_str) if last_run_str else None
                
            # Check for missed runs
            if last_run:
                # Calculate when the next run should have been
                days_since_last_run = (now - last_run).days
                
                if days_since_last_run >= 1:
                    # If more than a day has passed, check if we missed today's run
                    scheduled_datetime = datetime(now.year, now.month, now.day, hour, minute)
                    
                    # If current time is past scheduled time, we missed it
                    if now > scheduled_datetime and (now - scheduled_datetime).total_seconds() < 24 * 60 * 60:
                        self.logger.info("Detected missed run, executing now")
                        self.run_scraper()
                        self._update_last_run(last_run_file)
                        return
            
            # Check if it's time for today's scheduled run
            if current_hour == hour and current_minute == minute:
                self.logger.info("Scheduled run time reached")
                self.run_scraper()
                self._update_last_run(last_run_file)
                
        except Exception as e:
            self.logger.error(f"Error checking scheduled run: {str(e)}", exc_info=True)
    
    def _update_last_run(self, last_run_file):
        """Update the last run time file"""
        with open(last_run_file, 'w') as f:
            f.write(datetime.now().isoformat())
    
    def run_scraper(self):
        """Run the web scraping task"""
        try:
            self.logger.info("Starting web scraping")
            
            # Load config
            with open(config.CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                
            # Get scraping parameters
            property_types = cfg.get('property_types', ['Office', 'Retail', 'Industrial'])
            min_price = cfg.get('min_price', '')
            max_price = cfg.get('max_price', '')
            location = cfg.get('location', 'Seattle, WA')
            websites = cfg.get('websites', ['commercialmls.com', 'loopnet.com'])
            days_back = cfg.get('days_back', 1)
            
            # Calculate start date
            start_date = datetime.now() - timedelta(days=days_back)
            
            # Initialize scraper manager with headless mode
            scraper_manager = ScraperManager(debug_mode=False)  # False = headless mode
            
            # Run the scraper
            self.logger.info(f"Running scraper with params: {property_types}, {location}, {min_price}, {max_price}")
            results = scraper_manager.search(
                property_types=property_types,
                location=location,
                min_price=min_price,
                max_price=max_price,
                start_date=start_date,
                websites=websites
            )
            
            # Log results
            total_results = sum(len(site_results) for site_results in results.values()) if isinstance(results, dict) else len(results)
            self.logger.info(f"Scraping completed. Found {total_results} results")
            
        except Exception as e:
            self.logger.error(f"Error running scraper: {str(e)}", exc_info=True)
    
    def run_now(self):
        """Trigger immediate scraping"""
        self.run_now_event.set()
        self.logger.info("Run now flag set")


def install():
    """Helper function to install the service"""
    win32serviceutil.HandleCommandLine(ScraperService)


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'run_now':
        # Trigger run now functionality
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ScraperService)
        service = ScraperService([])
        service.run_scraper()
    else:
        # Normal service operations
        win32serviceutil.HandleCommandLine(ScraperService)
