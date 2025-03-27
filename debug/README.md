# Browser Recorder Tools for Scraper Development

This directory contains tools to help with developing web scrapers by recording and analyzing browser interactions.

## Overview

The tools in this directory help you:

1. Record your browser interactions while navigating websites
2. Capture HTML and screenshots for analysis
3. Generate scraper templates based on your interactions
4. Automatically identify key elements and page structures

## Tools Included

### 1. Browser Recorder (`browser_recorder.py`)

Records your browser interactions, capturing HTML, screenshots, and element interactions.

#### Usage:

```bash
python browser_recorder.py https://www.loopnet.com
```

#### Options:

- `url`: Starting URL for the recording session
- `--headless`: Run in headless mode (no visible browser)
- `--output-dir`: Output directory for recording data (default: debug)

#### During recording:

- Navigate the website as you normally would
- Fill out search forms
- Click on results
- Navigate to detail pages

The tool will record all your interactions and save the HTML/screenshots.

#### Commands during recording:

- `snapshot`: Take a manual snapshot of the current page
- `note <text>`: Add a note to the recording log
- `hover <selector>`: Hover over an element
- `highlight <selector>`: Highlight an element
- `wait <seconds>`: Wait for a specific number of seconds
- `save`: Save the current session
- `quit`: End the recording session

### 2. Scraper Generator (`scraper_generator.py`)

Analyzes a recording session and generates a scraper template.

#### Usage:

```bash
python scraper_generator.py debug/session_20230324_123456
```

#### Options:

- `session_path`: Path to the session data directory or session_data.json file
- `--output`: Custom output file for the scraper template

## Workflow for Creating Scrapers

1. **Record a session**:
   ```bash
   python browser_recorder.py https://www.loopnet.com
   ```

2. **Review the session**:
   Open the generated `index.html` in the session directory to review your interactions.

3. **Generate a scraper template**:
   ```bash
   python scraper_generator.py debug/session_20230324_123456
   ```

4. **Customize the generated scraper**:
   Edit the generated Python file to adapt it to your specific needs.

## Example for LoopNet and CommercialMLS

To create scrapers for LoopNet and CommercialMLS:

1. Record a session for LoopNet:
   ```bash
   python browser_recorder.py https://www.loopnet.com
   ```

2. Record a session for CommercialMLS:
   ```bash
   python browser_recorder.py https://www.commercialmls.com
   ```

3. Generate scraper templates:
   ```bash
   python scraper_generator.py debug/session_loopnet --output scraper/loopnet_selenium_scraper.py
   python scraper_generator.py debug/session_commercialmls --output scraper/commercialmls_selenium_scraper.py
   ```

4. Review and customize the generated scrapers.

## Tips for Better Results

1. **Use the note command** to add context during recording:
   ```
   note This is the search form for LoopNet
   note This element contains property details
   ```

2. **Take manual snapshots** at important points:
   ```
   snapshot
   ```

3. **Highlight key elements** to help with later analysis:
   ```
   highlight .property-price
   ```

4. **Use consistent navigation patterns** for both websites to help generate similar scraper structures.

5. **When filling forms**, do it slowly and methodically so all inputs are properly recorded.

## Scraper Template Structure

The generated scraper templates include:

- A `WebScraper` class with the following methods:
  - `search()`: Execute a search using parameters
  - `get_listing_details()`: Get details from a listing page
  - Various helper methods for form filling and data extraction

You'll need to customize these templates based on the specific structure of the target websites.

## Troubleshooting

- If elements aren't being detected during recording, try using the `highlight` command to see if selectors are working.
- If the generated scraper can't find elements, check the session's HTML snapshots to verify selectors.
- For elements loaded via JavaScript, you may need to add explicit waits in the generated scrapers.
- If CAPTCHA issues occur, consider using undetectable-chromedriver or similar tools that can help evade bot detection. 