
# 🚀 Perfect Job Scraper

[![Python Version](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/Jebin-05/perfect-job-scraper)](https://github.com/Jebin-05/perfect-job-scraper/issues)
[![GitHub Stars](https://img.shields.io/github/stars/Jebin-05/perfect-job-scraper)](https://github.com/Jebin-05/perfect-job-scraper/stargazers)

**Perfect Job Scraper** is an industry-grade, AI-powered multi-source job search and analytics engine. It scrapes, analyzes, and ranks job postings from leading job boards and APIs, providing actionable insights and market intelligence for job seekers, researchers, and HR professionals.

## 📋 Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Output](#output)
- [Best Practices](#best-practices)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## ✨ Features

- **🔍 Multi-Source Scraping:** Indeed, LinkedIn, Glassdoor, Monster, ZipRecruiter, CareerBuilder, and APIs (Remotive, GitHub Jobs, RemoteOK, WeWorkRemotely, AngelList, FlexJobs, Dice)
- **🤖 AI-Driven Analysis:** Uses Google Gemini AI for intelligent job relevance analysis, ranking, and market insights
- **📊 Advanced Ranking:** Ranks jobs by relevance, salary, growth potential, and market value
- **📈 Market Insights:** Generates AI-powered reports on job trends, salaries, and opportunities
- **🛡️ Robust Parsing:** Handles salary normalization, anti-bot evasion, and dynamic web content
- **⚙️ Highly Configurable:** Easily adapt search terms, locations, and ranking criteria
- **⚡ Concurrent Scraping:** Fast, multi-threaded scraping for large-scale data collection
- **📅 Time-Based Filtering:** Focuses on recently posted jobs (within 7 days) for active recruitment

## 📋 Requirements

- Python 3.8 or higher
- Google Chrome (for Selenium-based scraping)
- Google Gemini API key (for AI analysis)

### Python Dependencies

All required dependencies are listed in `requirements.txt`:

```
requests
beautifulsoup4
pandas
selenium
google-generativeai
crewai
python-dotenv
lxml
```

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Jebin-05/perfect-job-scraper.git
   cd perfect-job-scraper
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   - Create a `.env` file in the root directory
   - Add your Google Gemini API key:
     ```
     GOOGLE_API_KEY=your_api_key_here
     ```

## 🚀 Usage

### Basic Usage

1. **Run the scraper with default settings:**
   ```bash
   python perfect_job_scraper.py
   ```

2. **Follow the interactive prompts** to specify:
   - Job title (e.g., "Data Scientist")
   - Location (e.g., "Coimbatore")
   - Number of jobs to scrape

### Advanced Usage

You can also modify the script directly or import functions for custom workflows:

```python
from perfect_job_scraper import scrape_linkedin_comprehensive, process_and_rank_jobs

# Scrape jobs
jobs = scrape_linkedin_comprehensive("Data Scientist", "Coimbatore", 50)

# Process and rank with AI
ranked_jobs = process_and_rank_jobs(jobs, "Data Scientist")
```

## ⚙️ Configuration

### Search Parameters

- **Job Title:** Specify the role you're interested in
- **Location:** Target city or region
- **Job Count:** Number of jobs to scrape (recommended: 50-100 for optimal performance)

### AI Analysis

The scraper uses Google Gemini AI for:
- Job relevance scoring
- Career potential analysis
- Market insights generation

Ensure your `.env` file contains a valid `GOOGLE_API_KEY`.

## 📊 Output

### CSV Files
Generated job listings with the following columns:
- Job Title
- Company
- Location
- Salary Range
- Job Description
- Application Link
- Posted Date

### AI Insights Files
Text reports containing:
- Market analysis
- Salary trends
- Career recommendations
- Job market insights

### File Naming Convention
- `ai_jobs_[job_title]_[location]_[timestamp].csv`
- `ai_insights_[job_title]_[location]_[timestamp].txt`

## 📚 Best Practices & Critical Notes

### ⚖️ Ethical Usage
- **Respect robots.txt and site terms.** This tool is for research and educational use only.
- **Do not use for commercial scraping** without explicit permission from websites.
- **Rate limiting:** Implement delays between requests to avoid overwhelming servers.

### 🔧 Technical Considerations
- **API Rate Limits:** Some job APIs may enforce rate limits or require API keys.
- **Headless Browsing:** Selenium uses headless Chrome; ensure Chrome is installed and up-to-date.
- **Anti-Bot Evasion:** The scraper uses random user agents and stealth options, but sites may still block or throttle scraping.
- **Data Quality:** Job data is parsed heuristically; always validate before use in production.
- **Threading:** Multi-threaded scraping can stress both your system and target sites. Use responsibly.

### 🚨 Important Warnings
- **Legal Compliance:** Ensure compliance with local laws regarding web scraping.
- **Data Privacy:** Be mindful of data protection regulations (GDPR, CCPA, etc.).
- **Resource Usage:** Large-scale scraping may consume significant CPU and memory.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### How to Contribute
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Setup
```bash
git clone https://github.com/Jebin-05/perfect-job-scraper.git
cd perfect-job-scraper
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues:** [GitHub Issues](https://github.com/Jebin-05/perfect-job-scraper/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Jebin-05/perfect-job-scraper/discussions)
- **Email:** For private inquiries, please use GitHub issues

---

**Made with ❤️ by [Jebin-05](https://github.com/Jebin-05)**

*Star this repo if you find it useful!* ⭐
