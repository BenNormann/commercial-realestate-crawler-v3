# Commercial Real Estate Crawler v3

A modern desktop application for automatically scraping commercial real estate listings from multiple websites with intelligent scheduling and email notifications.

## 🏢 Overview

This application provides a comprehensive solution for monitoring commercial real estate markets:

- **🕷️ Multi-Website Scraping**: Automatically scrapes listings from LoopNet.com and CommercialMLS.com
- **⏰ Smart Scheduling**: Uses Windows Task Scheduler for reliable background execution
- **📧 Email Notifications**: Sends detailed email reports with new listings
- **🎨 Modern GUI**: Clean, dark-themed desktop interface built with PyQt5
- **📊 Detailed Results**: View property details including price, type, size, location, and descriptions
- **🔧 Easy Configuration**: Set search criteria, schedule times, and email preferences through the GUI
- **📦 Standalone Executable**: Can be compiled into a portable .exe file

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Windows 10/11 (for Task Scheduler integration)

### Setup
1. Clone or download this repository
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

### Starting the Application

**For Development/Testing:**
```bash
python launch_gui.py
```

**For Production/Clean Launch (No Console Window):**
```bash
pythonw launch_gui.py
```

> **💡 Pro Tip**: Use `pythonw` instead of `python` to launch the GUI without showing a console window. This provides a cleaner user experience.

### Configuration

1. **Search Parameters**:
   - Select property types (Office, Retail, Industrial, Multifamily)
   - Set location (e.g., "Seattle, WA")
   - Define price range (optional)
   - Choose websites to search
   - Set how many days back to search

2. **Email Notifications**:
   - Enter your Gmail address
   - Generate and enter a Gmail App Password (not your regular password)
   - Enable email notifications
   - Save credentials for scheduled runs

3. **Scheduling**:
   - Enable background scheduling
   - Add one or more daily run times
   - Save configuration to install/update the scheduled task

### Main Features

#### ⚡ Run Now
- Immediately executes a search with current parameters
- Shows progress in the Results tab
- Sends email notification if configured

#### 💾 Save Search Parameters
- Saves current configuration
- Installs/updates Windows scheduled task
- Enables automatic daily runs at specified times

#### 📋 Results Tab
- View detailed listings from recent searches
- See property details: price, type, size, location, description, URL
- Refresh to load latest results

#### 📊 Status Tab
- Monitor scheduled task status
- View last run time and next scheduled run
- Check total results from last search

#### 📝 Logs Tab
- View application logs for troubleshooting
- Monitor scraping activity and errors

## 🗓️ Scheduling System

The application uses **Windows Task Scheduler** for reliable background execution:

- **Automatic Installation**: Tasks are created automatically when you save configuration
- **Multiple Times**: Schedule multiple daily run times
- **Background Operation**: Runs even when GUI is closed or user is logged out
- **Email Integration**: Scheduled runs automatically send email notifications
- **Robust Execution**: Built-in error handling and logging

### Task Management
- Tasks are automatically installed/updated when you save configuration
- Task name: "CommercialRealEstateScraper"
- Uses `pythonw.exe` for silent execution
- Runs with user privileges (no admin required)

## 📧 Email Setup

### Gmail App Password Setup
1. Go to your [Google Account](https://myaccount.google.com/)
2. Click **Security** in the left menu
3. Under "Signing in to Google", click **2-Step Verification**
4. Enable 2-Step Verification if not already enabled
5. Go back to Security, scroll down to **App passwords**
6. Click **App passwords**
7. Select **Mail** and **Windows Computer**
8. Click **Generate**
9. Copy the 16-character password (example: "abcd efgh ijkl mnop")
10. Paste it in the App Password field in the application

> **⚠️ Important**: Use your App Password, NOT your regular Gmail password!

## 📦 Building Executable

Create a standalone .exe file that can run on any Windows machine:

```bash
# Install PyInstaller (if not already installed)
pip install pyinstaller

# Build the executable
pyinstaller build_exe.spec
```

The executable will be created in `dist/CommercialRealEstateCrawler.exe`

### Executable Features
- **Self-contained**: Includes all dependencies
- **No Python required**: Runs on machines without Python installed
- **Secure**: Excludes debug files and credentials from the build
- **Portable**: Single file that can be distributed easily

## 🔧 Configuration Files

- `config/config.json`: Main application settings (auto-saved)
- `userinfo.py`: Email credentials (excluded from executable builds)
- `config/latest_results.json`: Most recent search results
- `debug/*.log`: Application logs

## 🐛 Troubleshooting

### Common Issues

**Console Window Keeps Appearing**:
- Use `pythonw launch_gui.py` instead of `python launch_gui.py`

**Scheduled Task Not Running**:
- Check Status tab for task status
- Ensure "Enable Background Scheduling" is checked
- Verify at least one scheduled time is set

**Email Notifications Not Working**:
- Verify Gmail App Password (not regular password)
- Check that "Send email notifications" is enabled
- Ensure credentials are saved
- Check logs for SMTP errors

**Scraping Not Finding Results**:
- Verify search parameters (location, property types)
- Check if websites are accessible
- Review logs for scraping errors
- Try reducing the search scope

### Log Files
Check `debug/` folder for detailed logs:
- `gui.log`: GUI application logs
- `task_runner.log`: Scheduled task execution logs
- `scraper_manager.log`: Web scraping logs

## 🏗️ Development

### Project Structure
```
commercial-realestate-crawler-v3/
├── gui/                    # PyQt5 GUI application
├── scraper/               # Web scraping modules
├── task_scheduler/        # Windows Task Scheduler integration
├── utils/                 # Email and utility functions
├── debug/                 # Log files
├── config/                # Configuration and results
├── launch_gui.py          # Main entry point
├── build_exe.spec         # PyInstaller configuration
└── requirements.txt       # Python dependencies
```

### Key Components
- **GUI**: Modern PyQt5 interface with dark theme
- **Scraper Manager**: Coordinates multiple website scrapers
- **Task Scheduler**: Windows integration for background execution
- **Email System**: SMTP-based notifications with detailed formatting

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**⭐ Star this repository if you find it useful!** 