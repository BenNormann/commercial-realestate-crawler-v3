# Commercial Real Estate Crawler

A web crawler for commercial real estate websites with a Windows service for scheduled execution.

## Overview

This application allows you to:
- Scrape commercial real estate listings from various websites
- Run the crawler on a schedule via a Windows service
- View and filter results in a user-friendly GUI
- Receive email notifications with new listings

## Installation

1. Make sure you have Python 3.8 or higher installed
2. Clone or download this repository
3. Install required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Starting the GUI

To start the application, run:

```
python launch_gui.py
```

### Windows Service

The application can run as a Windows service to perform scheduled crawling in the background, even when no user is logged in.

#### Service Setup

1. **Install the Service**:
   Click the "Install Service" button in the GUI.
   - This will request administrator privileges via a UAC prompt.
   - The service will be installed on your system.

2. **Start the Service**:
   Click the "Start Service" button in the GUI.
   - This will request administrator privileges via a UAC prompt.
   - The service will start and run in the background.

3. **Stop the Service**:
   Click the "Stop Service" button in the GUI.
   - This will request administrator privileges via a UAC prompt.
   - The service will stop.

4. **Remove the Service**:
   Click the "Remove Service" button in the GUI.
   - This will request administrator privileges via a UAC prompt.
   - The service will be uninstalled from your system.

### Manual Service Control

You can control the service directly from the command line using either Python commands or the included batch file:

#### Using Python:

```
# Install the service
python -m service.service_controller install

# Start the service
python -m service.service_controller start

# Stop the service
python -m service.service_controller stop

# Check service status
python -m service.service_controller status

# Remove the service
python -m service.service_controller remove
```

#### Using the Batch File (Windows only):

```
# Install the service
manage_service.bat install

# Start the service
manage_service.bat start

# Stop the service
manage_service.bat stop

# Check service status
manage_service.bat status

# Remove the service
manage_service.bat remove
```

## Configuration

You can configure the crawler through the GUI:

1. **Crawler Settings**:
   - Websites to crawl
   - Search criteria
   - Frequency of crawling

2. **Email Notifications**:
   - Enable/disable email notifications
   - Set up email credentials
   - Configure recipients

The configuration is saved in the `config/config.json` file.

## Troubleshooting

### Administrator Privileges

All service operations (install, start, stop, remove) require administrator privileges. If you encounter permission errors:

1. Make sure you're allowing the UAC prompts when requested
2. Try running the application as administrator
3. Check Windows Event Viewer for any service-related errors

### Service Not Starting

If the service fails to start:

1. Check the service log in `debug/service.log`
2. Verify that your Python environment has all required dependencies
3. Make sure the service isn't already installed or running

### Windows 10 Compatibility

This application is designed to work with all modern versions of Windows including Windows 10 and Windows 11. The service management utility (`service_controller.py`) uses PowerShell commands to elevate privileges instead of relying on win32api/win32con.

## Advanced Usage

### Command Line Interface

For advanced users, the crawler can be controlled via command line:

```
# Run the crawler directly (without service)
python -m scraper.scraper_manager
```

## Development

### Service Management

The service management functionality has been simplified and consolidated:

- All service management functions (install, remove, start, stop, status) are now in `service/service_controller.py`
- Eliminated redundant files (`install_service.py` and `service_control.py`)
- Added convenience batch file (`manage_service.bat`) for Windows users
- Service functions are now exposed at the package level through `service/__init__.py`

If you're upgrading from a previous version, you can run `cleanup.bat` to remove the obsolete files.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 