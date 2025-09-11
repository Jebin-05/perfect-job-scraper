
# Perfect Job Scraper

Perfect Job Scraper is an industry-grade, AI-powered multi-source job search and analytics engine. It scrapes, analyzes, and ranks job postings from leading job boards and APIs, providing actionable insights and market intelligence for job seekers and researchers.

## Features
- **Multi-Source Scraping:** Indeed, LinkedIn, Glassdoor, Monster, ZipRecruiter, CareerBuilder, and APIs (Remotive, GitHub Jobs, RemoteOK, WeWorkRemotely, AngelList, FlexJobs, Dice)
- **AI-Driven Analysis:** Uses CrewAI agents for intelligent scraping, job relevance analysis, ranking, and market insights
- **Advanced Ranking:** Ranks jobs by relevance, salary, growth potential, and market value
- **Market Insights:** Generates AI-powered reports on job trends, salaries, and opportunities
- **Robust Parsing:** Handles salary normalization, anti-bot evasion, and dynamic web content
- **Highly Configurable:** Easily adapt search terms, locations, and ranking criteria
- **Concurrent Scraping:** Fast, multi-threaded scraping for large-scale data collection

## Requirements
- Python 3.8+
- Google Chrome (for Selenium)

### Python Dependencies
All dependencies are listed in `requirements.txt`.

## Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/Jebin-05/perfect-job-scraper.git
   cd perfect-job-scraper
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. Edit `perfect_job_scraper.py` to set your search terms and locations, or call the relevant methods from your own script.
2. Run the scraper:
   ```bash
   python perfect_job_scraper.py
   ```
3. Output CSV and TXT files will be generated in the workspace directory.

## File Structure
- `perfect_job_scraper.py` — Main scraping and analysis engine
- `ai_jobs_*.csv` — Scraped job listings
- `ai_insights_*.txt` — AI-generated job market insights
- `requirements.txt` — Python dependencies
- `README.md` — Project documentation

## Best Practices & Critical Notes
- **Respect robots.txt and site terms.** This tool is for research and educational use. Do not use for commercial scraping without permission.
- **API Rate Limits:** Some APIs may enforce rate limits or require API keys.
- **Headless Browsing:** Selenium uses headless Chrome; ensure Chrome is installed and up to date.
- **Anti-Bot Evasion:** The scraper uses random user agents and stealth options, but sites may still block or throttle scraping.
- **Data Quality:** Job data is parsed heuristically; always validate before use in production.
- **Threading:** Multi-threaded scraping can stress both your system and target sites. Use responsibly.

## Contributing
Contributions are welcome! Please open issues for bugs or feature requests, and submit pull requests for improvements.

## License
MIT License. See `LICENSE` for details.
