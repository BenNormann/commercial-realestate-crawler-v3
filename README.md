# Commercial Real Estate Crawler

A Python application to search and monitor commercial real estate listings across multiple websites.

## Features

- **Multi-platform search**: Search both commercialmls.com and loopnet.com simultaneously
- **Property type filtering**: Select from Office, Retail, Industrial, Multi-Family, Land, or Hotel properties
- **Price range filtering**: Set minimum and maximum price constraints
- **Location-based search**: Currently optimized for Seattle, WA
- **Time-based filtering**: Search for listings from the last X days
- **Email notifications**: Receive search results via email
- **Daily monitoring**: Schedule automated daily searches with email reports
- **Modern UI**: Clean, responsive interface with dark mode support

## Prerequisites

- Python 3.8 or higher
- Chrome browser (for Selenium-based scraping)
- Chrome WebDriver matching your Chrome version

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/commercial-realestate-crawler.git
cd commercial-realestate-crawler
```

2. Create a virtual environment and activate it:
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required dependencies:
```
pip install -r requirements.txt
```

4. Run the application:
```
python main.py
```

## Usage

1. Select the property types you're interested in
2. Enter an optional price range
3. Verify the location is set to your desired area
4. Select which websites to search
5. Specify how many days back to search
6. Optionally enter your email credentials for email notifications
7. Click "Search Now" to execute the search

## Email Configuration

For email functionality, you'll need to:
1. Enter your email address
2. Enter your email password or app password
3. Check "Send Results by Email" to receive current search results
4. Check "Save Email Credentials" to enable daily email reports

**Note**: For Gmail, you may need to create an App Password if you have 2FA enabled. See Google's documentation on [App Passwords](https://support.google.com/accounts/answer/185833).

## Scheduled Searches

When credentials are saved, the application will run a daily search at 9 AM for new listings from the previous day based on your saved search parameters. You must keep the application running for this feature to work.

## Extending

To add support for additional real estate websites:

1. Create a new scraper class in the `scraper` directory
2. Inherit from `BaseScraper` and implement the `search` method
3. Add the new scraper to the `scrapers` dictionary in `ScraperManager`

## Selenium Scrapers

The application includes Selenium-based scrapers for commercial real estate websites:

### CommercialMLS Scraper

The CommercialMLSScraper uses Selenium to automate searches on commercialmls.com with the following workflow:
1. Navigates to commercialmls.com/search/
2. Selects location by entering a city name
3. Selects property types and "For Sale" filter
4. Sets price range filters
5. Sets date filters to find recent listings
6. Extracts property information including title, address, price, and URL

### LoopNet Scraper

The ImprovedLoopNetScraper uses Selenium to automate searches on loopnet.com with the following workflow:
1. Navigates to loopnet.com
2. Enters location search
3. Changes listing type to "For Sale"
4. Selects appropriate property types
5. Sets price range filters
6. Uses "All Filters" to set date filters
7. Extracts property information and handles popup dialogs

### Usage

Both scrapers are integrated with the main application through the ScraperManager. When you perform a search in the GUI, the scrapers run in parallel threads to collect listings from both websites simultaneously.

To run the scrapers, you'll need to have Chrome installed as well as the appropriate ChromeDriver for your Chrome version.

### Testing the Scrapers

You can test the scrapers independently using the debug script:

```bash
python debug/test_scrapers.py
```

This will run both scrapers with sample search parameters and display the results.

## License

MIT

## Disclaimer

This application is for educational purposes only. Be sure to review and respect the terms of service for any website you interact with using this tool. 