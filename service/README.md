# Commercial Real Estate Scraper Service

A Windows service for automating the scraping of commercial real estate websites at scheduled times.

## Features

- Automatically scrapes commercial real estate listings based on configured parameters
- Runs as a background Windows service
- Supports scheduled execution at specific times
- Detects and executes missed runs (e.g., when computer was off)
- Supports manual trigger of scraping via "run now" functionality

## Installation and Usage

### Prerequisites

- Windows operating system
- Python 3.7 or higher
- Required Python packages:
  - pywin32
  - Other dependencies of the scraper

### Installing the Service

1. Open an elevated command prompt (Run as Administrator)
2. Navigate to the project directory
3. Run the installation command:

```
python -m service.service install
```

### Service Management

- **Start the service**:
  ```
  python -m service.service start
  ```

- **Stop the service**:
  ```
  python -m service.service stop
  ```

- **Remove the service**:
  ```
  python -m service.service remove
  ```

- **Run scraper immediately** (without waiting for scheduled time):
  ```
  python -m service.service run_now
  ```

### Configuration

The service uses the configuration from the main application's config file. 
You can modify the following settings that affect the service:

- `enable_background`: Set to `true` to enable scheduled scraping
- `background_time`: Time to run the scraper daily (format: "HH:MM")
- Other scraping parameters (property types, location, price range, etc.)

## Logs

The service logs are stored in `service/service.log`. Check this file for debugging or to verify operation.

## Troubleshooting

- If the service fails to start, check the Windows Event Viewer for error messages
- Ensure the config.json file exists and contains valid configuration
- Verify that the service has appropriate permissions to access the internet and file system 