import os
import sys
import subprocess
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from debug.logger import setup_logger
from scraper.scraper_manager import ScraperManager

# Configuration constants
if getattr(sys, 'frozen', False):
    # Running as executable - use directory where exe is located
    exe_dir = os.path.dirname(sys.executable)
    CONFIG_DIR = os.path.join(exe_dir, "config")
else:
    # Running as script - use project root
    CONFIG_DIR = os.path.join(project_root, "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

logger = setup_logger("task_scheduler")

class TaskSchedulerManager:
    """Manages Windows Task Scheduler for commercial real estate scraping"""
    
    def __init__(self):
        self.task_name = "CommercialRealEstateScraper"
        
        # CRITICAL: When running as EXE, scheduled task must run the EXE, not extracted Python files
        if getattr(sys, 'frozen', False):
            # Running as EXE - Task should run the EXE with argument, not extracted Python files
            self.command = sys.executable  # Path to the actual EXE file
            self.arguments = "--execute-scraping"
        else:
            # Running as script - Task should run Python with this file
            current_exe = sys.executable
            if current_exe.endswith('python.exe'):
                self.command = current_exe.replace('python.exe', 'pythonw.exe')
            elif 'anaconda' in current_exe.lower() or 'conda' in current_exe.lower():
                python_dir = os.path.dirname(current_exe)
                pythonw_path = os.path.join(python_dir, 'pythonw.exe')
                if os.path.exists(pythonw_path):
                    self.command = pythonw_path
                else:
                    self.command = current_exe
            else:
                self.command = current_exe
            self.arguments = f'"{os.path.abspath(__file__)}" --execute-scraping'
        
    def run_scraping(self):
        """Run scheduled scraping - called by Windows Task Scheduler"""
        logger.info("=== Running scheduled scraping ===")
        return self.execute_scraping()
    
    def execute_scraping(self):
        """Execute the scraping operation using configuration file"""
        try:
            logger.info("Starting scheduled scraping execution")
            
            # Load configuration using EXACT SAME logic as GUI for ALL modes
            task_manager_file = os.path.abspath(__file__)
            absolute_project_root = os.path.dirname(os.path.dirname(task_manager_file))
            absolute_config_dir = os.path.join(absolute_project_root, "config")
            absolute_config_file = os.path.join(absolute_config_dir, "config.json")
            
            # Load user configuration
            user_config = None
            if os.path.exists(absolute_config_file):
                logger.info(f"Loading config from: {absolute_config_file}")
                with open(absolute_config_file, 'r') as f:
                    user_config = json.load(f)
            elif os.path.exists(CONFIG_FILE):
                logger.info(f"Loading config from fallback: {CONFIG_FILE}")
                with open(CONFIG_FILE, 'r') as f:
                    user_config = json.load(f)
            else:
                logger.error("No configuration file found - cannot run scheduled scraping")
                return False
            
            logger.info(f"Loaded config: {user_config}")
            
            # Extract search parameters from config
            property_types = []
            saved_types = user_config.get('property_types', [])
            for prop_type in saved_types:
                # Handle legacy "Investment" -> "Multifamily" mapping
                if prop_type == 'Investment':
                    property_types.append('multifamily')
                else:
                    property_types.append(prop_type.lower())
            
            location = user_config.get('location', '').strip()
            min_price = user_config.get('min_price', '') or None
            max_price = user_config.get('max_price', '') or None
            websites = user_config.get('websites', [])
            days_back = user_config.get('days_back', 1)
            
            # Validate configuration
            if not location:
                logger.error("No location specified in configuration")
                return False
            if not property_types:
                logger.error("No property types specified in configuration")
                return False
            if not websites:
                logger.error("No websites specified in configuration")
                return False
            
            logger.info(f"Scheduled scraping parameters:")
            logger.info(f"  Location: {location}")
            logger.info(f"  Property Types: {property_types}")
            logger.info(f"  Websites: {websites}")
            logger.info(f"  Price Range: {min_price} - {max_price}")
            logger.info(f"  Days Back: {days_back}")
            
            # Calculate start date
            start_date = datetime.now() - timedelta(days=days_back)
            
            # Execute search using ScraperManager
            manager = ScraperManager(debug_mode=False)
            logger.info("Executing scraper search...")
            results = manager.search(
                property_types=property_types,
                location=location,
                min_price=min_price,
                max_price=max_price,
                start_date=start_date,
                websites=websites
            )
            
            # Calculate total results
            total_results = 0
            if isinstance(results, dict):
                for website, website_results in results.items():
                    count = len(website_results) if website_results else 0
                    total_results += count
                    logger.info(f"Found {count} results on {website}")
            else:
                total_results = len(results) if results else 0
                logger.info(f"Found {total_results} total results")
            
            # Save to latest results file using same pattern as GUI
            os.makedirs(CONFIG_DIR, exist_ok=True)
            latest_results_file = os.path.join(CONFIG_DIR, "latest_results.json")
            results_data = {
                "results": results,
                "total_results": total_results,
                "datetime": datetime.now().isoformat(),
                "trigger": "scheduled"
            }
            
            with open(latest_results_file, 'w') as f:
                json.dump(results_data, f, indent=2, default=str)
            logger.info(f"=== Scheduled scraping completed successfully! Total results: {total_results} ===")
            
            # Send email notification if enabled
            try:
                self.send_email_notification(results, total_results)
            except Exception as e:
                logger.error(f"Error sending email notification: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during scheduled scraping execution: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get_email_credentials(self):
        """Get email credentials from JSON file using same path logic as main config"""
        try:
            # Use EXACT SAME logic as GUI for ALL modes
            task_manager_file = os.path.abspath(__file__)
            absolute_project_root = os.path.dirname(os.path.dirname(task_manager_file))
            absolute_config_dir = os.path.join(absolute_project_root, "config")
            
            email_credentials_file = os.path.join(absolute_config_dir, "email_credentials.json")
            
            if os.path.exists(email_credentials_file):
                with open(email_credentials_file, 'r') as f:
                    data = json.load(f)
                    return data.get('email', ''), data.get('password', '')
            elif os.path.exists(os.path.join(CONFIG_DIR, "email_credentials.json")):
                # Fallback to original path
                with open(os.path.join(CONFIG_DIR, "email_credentials.json"), 'r') as f:
                    data = json.load(f)
                    return data.get('email', ''), data.get('password', '')
        except Exception as e:
            logger.error(f"Error reading email credentials: {e}")
        return '', ''

    def send_email_notification(self, results, total_results):
        """Send email notification for scheduled run results"""
        try:
            from utils.email_sender import EmailSender
            
            # Use EXACT SAME logic as GUI for ALL modes
            task_manager_file = os.path.abspath(__file__)
            absolute_project_root = os.path.dirname(os.path.dirname(task_manager_file))
            absolute_config_dir = os.path.join(absolute_project_root, "config")
            
            absolute_config_file = os.path.join(absolute_config_dir, "config.json")
            
            # Load configuration to check if email is enabled
            if os.path.exists(absolute_config_file):
                with open(absolute_config_file, 'r') as f:
                    user_config = json.load(f)
            elif os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    user_config = json.load(f)
            else:
                logger.debug("No config file found, skipping email")
                return
            
            # Check if email notifications are enabled
            if not user_config.get('send_email', False):
                logger.debug("Email notifications disabled, skipping email send")
                return
            
            # Check if credentials are saved
            email, password = self.get_email_credentials()
            if not email or not password:
                logger.warning("Email credentials not configured, skipping email send")
                return
            
            # Prepare email content
            run_time = datetime.now().isoformat()
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
                                email_body += "\n".join(listing_details)
                                email_body += "\n\n" + "-"*40 + "\n\n"
                elif isinstance(results, list):
                    # Single website or combined results format
                    email_body += f"{'='*50}\n"
                    email_body += f"SEARCH RESULTS - {len(results)} Properties\n"
                    email_body += f"{'='*50}\n\n"
                    
                    for i, listing in enumerate(results, 1):
                        email_body += f"[{i}] "
                        listing_details = self.format_listing_details(listing)
                        email_body += "\n".join(listing_details)
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
                logger.info(f"Scheduled scraping results email sent successfully to {email}")
            else:
                logger.error("Failed to send scheduled scraping results email")
                
        except Exception as e:
            logger.error(f"Error sending scheduled scraping results email: {str(e)}")
    
    def format_listing_details(self, listing):
        """Format listing details for email (same as GUI but without emojis)"""
        details = []
        
        # Title/address
        title = listing.get('title', listing.get('address', 'No title'))
        details.append(title)
        
        # Price
        price = listing.get('price')
        if price:
            details.append(f"Price: {price}")
        
        # Property type
        prop_type = listing.get('type', listing.get('property_type'))
        if prop_type:
            details.append(f"Type: {prop_type}")
        
        # Size
        size = listing.get('size')
        if size:
            details.append(f"Size: {size}")
        
        # Location
        location = listing.get('location')
        if location and location != title:
            details.append(f"Location: {location}")
        
        # Description
        description = listing.get('description')
        if description:
            # Truncate long descriptions
            max_desc_length = 200
            if len(description) > max_desc_length:
                description = description[:max_desc_length] + "..."
            details.append(f"Description: {description}")
        
        # URL
        url = listing.get('url')
        if url:
            details.append(f"URL: {url}")
        
        # Date
        date = listing.get('date')
        if date:
            details.append(f"Date: {date}")
        
        return details
    
    def is_task_installed(self) -> bool:
        """Check if the scheduled task exists"""
        try:
            result = subprocess.run(
                f'schtasks /query /tn "{self.task_name}"',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking task installation: {str(e)}")
            return False
    
    def get_task_status(self) -> Dict[str, Any]:
        """Get detailed task status information"""
        try:
            if not self.is_task_installed():
                return {
                    "installed": False,
                    "enabled": False,
                    "last_run": "Never",
                    "next_run": "Not scheduled",
                    "state": "Not Installed"
                }
            
            # Get basic task info first (shows current state)
            basic_result = subprocess.run(
                f'schtasks /query /tn "{self.task_name}"',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            status_info = {
                "installed": True,
                "enabled": False,
                "last_run": "Never",
                "next_run": "Not scheduled",
                "state": "Unknown"
            }
            
            if basic_result.returncode == 0:
                basic_output = basic_result.stdout.strip()
                
                # Parse the basic output for state and next run time
                # Format: TaskName  Next Run Time  Status
                lines = basic_output.split('\n')
                for line in lines:
                    if self.task_name in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            # Extract state (last part)
                            state = parts[-1].strip()
                            status_info["state"] = state
                            
                            # If state is Ready, Queued, or Running, task is enabled
                            # If state is Disabled, task is disabled
                            if state.lower() in ['ready', 'queued', 'running']:
                                status_info["enabled"] = True
                            elif state.lower() == 'disabled':
                                status_info["enabled"] = False
                            else:
                                # For other states, assume enabled if we have a next run time
                                status_info["enabled"] = True
                            
                            # Extract next run time (everything except first and last part)
                            if len(parts) > 2:
                                next_run_parts = parts[1:-1]  # Skip task name and status
                                next_run = ' '.join(next_run_parts)
                                if next_run and next_run != 'N/A':
                                    status_info["next_run"] = next_run
                            
                            break
            
            # Get detailed task info for last run time
            detailed_result = subprocess.run(
                f'schtasks /query /tn "{self.task_name}" /v /fo list',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if detailed_result.returncode == 0:
                detailed_output = detailed_result.stdout
                
                # Extract last run time from verbose output
                import re
                last_run_match = re.search(r'Last Run Time:\s*(.+?)(?:\n|$)', detailed_output)
                if last_run_match:
                    last_run = last_run_match.group(1).strip()
                    if last_run and last_run != 'N/A' and last_run != 'Never':
                        status_info["last_run"] = last_run
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting task status: {str(e)}")
            return {
                "installed": False,
                "enabled": False,
                "last_run": "Error",
                "next_run": "Error",
                "state": "Error",
                "error": str(e)
            }
    
    def install_task(self) -> bool:
        """Create the basic scheduled task (disabled by default)"""
        try:
            # Set appropriate working directory
            if getattr(sys, 'frozen', False):
                # When running as EXE, use the directory containing the EXE
                working_dir = os.path.dirname(self.command)
            else:
                # When running as script, use project root
                working_dir = project_root

            # Create a basic task (disabled initially)
            xml_content = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Commercial Real Estate Scraper - Automated web scraping</Description>
    <Author>Commercial Real Estate Crawler</Author>
  </RegistrationInfo>
  <Triggers></Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>false</Enabled>
    <Hidden>true</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>"{self.command}"</Command>
      <Arguments>{self.arguments}</Arguments>
      <WorkingDirectory>{working_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
            
            # Save XML to temp file
            temp_xml = os.path.join(project_root, "temp_task.xml")
            with open(temp_xml, 'w', encoding='utf-16') as f:
                f.write(xml_content)
            
            # Create the task
            result = subprocess.run(
                f'schtasks /create /tn "{self.task_name}" /xml "{temp_xml}" /f',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Clean up temp file
            try:
                os.remove(temp_xml)
            except:
                pass
                
            if result.returncode == 0:
                logger.info(f"Task '{self.task_name}' created successfully")
                return True
            else:
                logger.error(f"Failed to create task: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing task: {str(e)}")
            return False
    
    def schedule_times(self, times: List[str]) -> bool:
        """Schedule the task to run at specified times daily"""
        try:
            if not self.is_task_installed():
                logger.error("Task not installed")
                return False
            
            # Delete existing task and recreate with new schedule
            if not self.delete_task():
                logger.error("Failed to delete existing task")
                return False
            
            # Create triggers XML for each time
            triggers_xml = ""
            for i, time_str in enumerate(times):
                hour, minute = time_str.split(':')
                triggers_xml += f'''
    <CalendarTrigger>
      <StartBoundary>2024-01-01T{hour}:{minute}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>'''
            
            # Set appropriate working directory  
            if getattr(sys, 'frozen', False):
                # When running as EXE, use the directory containing the EXE
                working_dir = os.path.dirname(self.command)
            else:
                # When running as script, use project root
                working_dir = project_root

            # Create new task with triggers
            xml_content = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Commercial Real Estate Scraper - Automated web scraping</Description>
    <Author>Commercial Real Estate Crawler</Author>
  </RegistrationInfo>
  <Triggers>{triggers_xml}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>6</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>"{self.command}"</Command>
      <Arguments>{self.arguments}</Arguments>
      <WorkingDirectory>{working_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
            
            # Save XML to temp file
            temp_xml = os.path.join(project_root, "temp_task.xml")
            with open(temp_xml, 'w', encoding='utf-16') as f:
                f.write(xml_content)
            
            # Create the task
            result = subprocess.run(
                f'schtasks /create /tn "{self.task_name}" /xml "{temp_xml}" /f',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Clean up temp file
            try:
                os.remove(temp_xml)
            except:
                pass
                
            if result.returncode == 0:
                logger.info(f"Task scheduled for times: {times}")
                return True
            else:
                logger.error(f"Failed to schedule task: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error scheduling times: {str(e)}")
            return False
    
    def run_now(self) -> bool:
        """Run the task immediately via Task Scheduler"""
        try:
            result = subprocess.run(
                f'schtasks /run /tn "{self.task_name}"',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                logger.info("Task started successfully")
                return True
            else:
                logger.error(f"Failed to run task: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error running task: {str(e)}")
            return False
    
    def run_now_direct(self) -> bool:
        """Run scraping directly without Task Scheduler (for immediate execution)"""
        try:
            logger.info("Running scraping directly (not via Task Scheduler)")
            return self.execute_scraping()
        except Exception as e:
            logger.error(f"Error running direct scraping: {str(e)}")
            return False
    
    def delete_task(self) -> bool:
        """Delete the scheduled task"""
        try:
            result = subprocess.run(
                f'schtasks /delete /tn "{self.task_name}" /f',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                logger.info(f"Task '{self.task_name}' deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete task: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting task: {str(e)}")
            return False
    

if __name__ == "__main__":
    """Handle command line execution for Task Scheduler"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Commercial Real Estate Task Scheduler Manager")
    parser.add_argument('--execute-scraping', action='store_true', 
                       help='Execute scraping operation (called by Task Scheduler)')
    
    args = parser.parse_args()
    
    if args.execute_scraping:
        # This is called by the Windows Task Scheduler
        manager = TaskSchedulerManager()
        success = manager.execute_scraping()
        sys.exit(0 if success else 1)
    else:
        print("Task Scheduler Manager")
        print("Use --execute-scraping to run scraping operation")
    
 