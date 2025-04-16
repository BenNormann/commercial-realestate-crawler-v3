# Commercial Real Estate Crawler Windows Service

This module provides a Windows service that runs in the background and executes real estate scraping tasks at scheduled times.

## Features

- Runs as a Windows service in the background
- Starts automatically with Windows
- Can be controlled through the GUI or command-line
- Executes scraping tasks at configured times
- Sends email notifications with results

## Usage

### Through the GUI

The Commercial Real Estate Crawler GUI provides controls to install, remove, start, and stop the service.

### Command-Line

You can also manage the service using the `service_launcher.py` script:

```bash
# Install the service
python -m service.service_launcher --install

# Start the service
python -m service.service_launcher --start

# Stop the service
python -m service.service_launcher --stop

# Remove the service
python -m service.service_launcher --remove

# Check service status
python -m service.service_launcher --status

# Run directly (for testing)
python -m service.service_launcher --run
```

## Configuration

The service reads configuration from the user's configuration file at `~/.commercialrealestate/config.json`.

Key configuration options:

- `enable_background`: Whether to enable background task execution
- `background_time`: Time of day to execute the task (format: "HH:MM")
- `send_email`: Whether to send email notifications
- Other scraping configuration options (property types, location, etc.)

## Logs

The service logs to `~/.commercialrealestate/logs/service.log`. 