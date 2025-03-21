# Upwork Job Scraper

A robust, asynchronous Python tool for scraping and analyzing Upwork job listings to help freelancers find the best matches for their skills.

## 🚀 Features

- **Automated Scraping**: Collect job listings from Upwork search results
- **Multiple Scraper Backends**: Choose between Crawl4ai or Selenium implementations
- **Baserow Integration**: Store and manage scraped jobs in Baserow
- **Robust Authentication**: Handles Upwork login and session management
- **Command-line Interface**: Easy to use with customizable parameters
- **Configurable Search**: Filter jobs based on your preferences
- **Data Persistence**: Save jobs locally in JSON format

## 📋 Requirements

- Python 3.12+
- Dependencies listed in `requirements.txt`
- Upwork account credentials
- Baserow account and API key

## 🔧 Installation

```bash
# Clone the repository
git clone https://github.com/TrueMan777/upwork-scraper.git
cd upwork-scraper

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Configuration

Create a `.env` file in the project root with the following variables:

```
# Upwork credentials (optional if using cookies)
UPWORK_USERNAME=your_username
UPWORK_PASSWORD=your_password

# Baserow configuration
BASEROW_API_KEY=your_baserow_api_key
BASEROW_TABLE_ID=your_baserow_table_id
```

## 🖥️ Usage

### Basic Usage

```bash
python -m upwork_scraper.main --query "web scraping" --max-pages 2
```

### Advanced Options

```bash
python -m upwork_scraper.main \
  --scraper selenium \  # Choose between 'crawl4ai' or 'selenium'
  --query "python developer" \
  --max-pages 5 \
  --headless \  # Run in headless mode
  --days-to-keep 30  # Keep jobs in Baserow for 30 days
```

### Help

```bash
python -m upwork_scraper.main --help
```

## 📁 Project Structure

```
upwork_scraper/
├── auth/               # Authentication components
│   └── login.py        # Upwork login handler
├── data/               # Data storage components
│   └── baserow.py      # Baserow integration
├── scrapers/           # Job scrapers
│   ├── __init__.py     # Scraper factory
│   ├── jobs_scraper_crawl4ai.py  # Crawl4ai implementation
│   └── jobs_scraper_selenium.py  # Selenium implementation
├── utils/              # Utility functions
│   └── helpers.py      # Helper functions
├── main.py             # Main entry point
├── requirements.txt    # Dependencies
└── README.md           # This file
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational purposes only. Please review Upwork's Terms of Service before use and ensure your usage complies with their policies. The developers of this tool are not responsible for any misuse or violations of Upwork's terms.