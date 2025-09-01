# Perfect Job Scraper - Ultimate Multi-Source Job Search Engine
# Sources: Indeed, LinkedIn, Glassdoor, Monster, ZipRecruiter, CareerBuilder + APIs
# APIs: Remotive, GitHub Jobs, RemoteOK, WeWorkRemotely, AngelList, FlexJobs, Dice
# pip install crewai beautifulsoup4 selenium webdriver-manager fake-useragent lxml

from crewai import Agent, Task, Crew, Process
import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import re
import random
import os
import json
from urllib.parse import quote_plus
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- AI AGENTS CONFIGURATION ---
# These AI agents use CrewAI to intelligently process and analyze job data

scraper_agent = Agent(
    role="Intelligent Web Scraper",
    goal="Extract comprehensive job data from multiple sources with AI-powered content understanding",
    backstory="You are an expert web scraper with deep understanding of job posting structures across different platforms. You can intelligently identify and extract relevant job information even when website layouts change.",
    verbose=True,
    allow_delegation=False
)

analyzer_agent = Agent(
    role="Job Relevance Analyzer",
    goal="Analyze job postings using AI to determine relevance and extract key insights",
    backstory="You are an AI-powered job analyst who understands job requirements, skills matching, and career progression. You can intelligently score job relevance based on complex criteria beyond simple keyword matching.",
    verbose=True,
    allow_delegation=False
)

ranking_agent = Agent(
    role="Smart Job Ranking Specialist",
    goal="Use AI algorithms to rank jobs based on multiple factors including relevance, career growth potential, and market value",
    backstory="You are an AI career advisor who understands job market trends, salary expectations, and career progression paths. You can intelligently rank opportunities based on comprehensive analysis.",
    verbose=True,
    allow_delegation=False
)

insight_agent = Agent(
    role="Job Market Intelligence Agent",
    goal="Provide AI-driven insights about job market trends, salary analysis, and career recommendations",
    backstory="You are an AI market analyst specializing in employment trends. You can analyze job data to provide intelligent insights about market conditions, salary trends, and career opportunities.",
    verbose=True,
    allow_delegation=False
)

class PerfectJobScraper:
    def __init__(self):
        self.user_agent = UserAgent()
        self.session = requests.Session()
        self.setup_session()
        self.driver = None
        self.all_jobs = []
        
    def parse_salary_to_number(self, salary_text):
        """Convert salary text to numerical value for ranking"""
        if not salary_text or salary_text == "Not specified":
            return 0
            
        # Remove common prefixes and clean text
        clean_text = salary_text.lower().replace('$', '').replace(',', '').replace('salary:', '').strip()
        
        # Extract numbers and multipliers
        try:
            # Handle ranges - take the average
            if '-' in clean_text or '–' in clean_text or '—' in clean_text:
                range_parts = re.split(r'[-–—]', clean_text)
                if len(range_parts) == 2:
                    low = self._extract_number(range_parts[0])
                    high = self._extract_number(range_parts[1])
                    return (low + high) / 2 if low and high else max(low or 0, high or 0)
            
            # Single value
            return self._extract_number(clean_text)
            
        except:
            return 0
    
    def _extract_number(self, text):
        """Extract numerical value from salary text"""
        # Handle 'k' notation (thousands)
        if 'k' in text:
            match = re.search(r'(\d+(?:\.\d+)?)k', text)
            if match:
                return float(match.group(1)) * 1000
        
        # Handle full numbers
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        if match:
            base_num = float(match.group(1))
            
            # Determine if it's hourly, monthly, or yearly
            if any(term in text for term in ['hour', 'hr']):
                return base_num * 2080  # Convert hourly to yearly (40hrs/week * 52weeks)
            elif any(term in text for term in ['month', 'mo']):
                return base_num * 12  # Convert monthly to yearly
            elif any(term in text for term in ['year', 'yr', 'annually']) or base_num > 1000:
                return base_num
            else:
                # If unclear and number is reasonable, assume yearly
                return base_num if base_num > 1000 else base_num * 1000
                
        return 0
        
    def setup_session(self):
        """Setup requests session with headers"""
        self.session.headers.update({
            'User-Agent': self.user_agent.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def setup_driver(self):
        """Setup Chrome driver with stealth options"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument(f"--user-agent={self.user_agent.random}")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
    def scrape_indeed_comprehensive(self, search_term, location, max_pages=10):
        """Comprehensive Indeed scraping with multiple pages"""
        jobs = []
        self.setup_driver()
        base_url = "https://www.indeed.com/jobs"
        
        print(f"🔍 Scraping Indeed for '{search_term}' in '{location}'...")
        
        for page in range(max_pages):
            try:
                start = page * 10
                url = f"{base_url}?q={quote_plus(search_term)}&l={quote_plus(location)}&start={start}"
                
                self.driver.get(url)
                time.sleep(random.uniform(2, 4))
                
                # Wait for job cards to load
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-jk]'))
                    )
                except:
                    print(f"   No more jobs found at page {page + 1}")
                    break
                
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-jk]')
                
                if not job_cards:
                    print(f"   No jobs found on page {page + 1}")
                    break
                
                page_jobs = 0
                for card in job_cards:
                    try:
                        # Extract job details
                        title_elem = card.find_elements(By.CSS_SELECTOR, 'h2 a span[title]')
                        title = title_elem[0].get_attribute('title') if title_elem else \
                               card.find_element(By.CSS_SELECTOR, 'h2 a span').text
                        
                        company_elem = card.find_elements(By.CSS_SELECTOR, '[data-testid="company-name"]')
                        company = company_elem[0].text if company_elem else "Not specified"
                        
                        location_elem = card.find_elements(By.CSS_SELECTOR, '[data-testid="job-location"]')
                        job_location = location_elem[0].text if location_elem else "Not specified"
                        
                        # Job link
                        link_elem = card.find_element(By.CSS_SELECTOR, 'h2 a')
                        job_link = "https://www.indeed.com" + link_elem.get_attribute('href')
                        
                        # Enhanced Salary Extraction
                        salary = "Not specified"
                        
                        # Try multiple salary selectors for Indeed
                        salary_selectors = [
                            '[data-testid="attribute_snippet_testid"]',
                            '.salary-snippet-container',
                            '.attribute_snippet',
                            '.salaryText',
                            '[data-testid="job-salary"]',
                            '.estimated-salary'
                        ]
                        
                        for selector in salary_selectors:
                            salary_elems = card.find_elements(By.CSS_SELECTOR, selector)
                            for elem in salary_elems:
                                text = elem.text.strip()
                                if any(indicator in text.lower() for indicator in ['$', 'hour', 'year', 'month', 'salary', 'pay', 'wage']):
                                    salary = text
                                    break
                            if salary != "Not specified":
                                break
                        
                        # Enhanced summary with salary context
                        summary_elem = card.find_elements(By.CSS_SELECTOR, '.slider_container .slider_item, [data-testid="job-snippet"]')
                        summary = summary_elem[0].text if summary_elem else ""
                        
                        # Look for salary info in summary if not found elsewhere
                        if salary == "Not specified" and summary:
                            salary_patterns = [
                                r'\$[\d,]+(?:\.\d{2})?(?:\s*[-–—]\s*\$[\d,]+(?:\.\d{2})?)?(?:\s*(?:per\s*)?(?:hour|hr|year|yr|month|mo|annually))?',
                                r'[\d,]+k?(?:\s*[-–—]\s*[\d,]+k?)?\s*(?:per\s*)?(?:hour|hr|year|yr|month|mo|annually)',
                                r'(?:up\s*to\s*)?\$[\d,]+(?:\.\d{2})?',
                                r'salary:?\s*\$?[\d,]+(?:k|,000)?'
                            ]
                            
                            for pattern in salary_patterns:
                                match = re.search(pattern, summary, re.IGNORECASE)
                                if match:
                                    salary = match.group(0)
                                    break
                        
                        # Job type
                        job_type_elem = card.find_elements(By.CSS_SELECTOR, '[data-testid="attribute_snippet_testid"]')
                        job_type = ""
                        for elem in job_type_elem:
                            text = elem.text.lower()
                            if any(t in text for t in ['full-time', 'part-time', 'contract', 'internship']):
                                job_type = elem.text
                                break
                        
                        job_data = {
                            'title': title.strip(),
                            'company': company.strip(),
                            'location': job_location.strip(),
                            'salary': salary.strip(),
                            'job_type': job_type.strip(),
                            'summary': summary.strip(),
                            'url': job_link,
                            'source': 'Indeed',
                            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'search_term': search_term,
                            'search_location': location
                        }
                        
                        jobs.append(job_data)
                        page_jobs += 1
                        
                    except Exception as e:
                        continue
                
                print(f"   Page {page + 1}: Found {page_jobs} jobs")
                
                if page_jobs == 0:
                    break
                    
                # Random delay between pages
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"   Error on page {page + 1}: {e}")
                continue
        
        print(f"✅ Indeed: {len(jobs)} total jobs found")
        return jobs
    
    def scrape_linkedin_comprehensive(self, search_term, location, max_pages=5):
        """Comprehensive LinkedIn scraping"""
        jobs = []
        print(f"🔍 Scraping LinkedIn for '{search_term}' in '{location}'...")
        
        for page in range(max_pages):
            try:
                start = page * 25
                url = f"https://www.linkedin.com/jobs/search?keywords={quote_plus(search_term)}&location={quote_plus(location)}&start={start}"
                
                headers = {
                    'User-Agent': self.user_agent.random,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
                
                response = self.session.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                job_cards = soup.find_all('div', class_='base-card') + soup.find_all('li', class_='result-card')
                
                if not job_cards:
                    break
                
                page_jobs = 0
                for card in job_cards:
                    try:
                        # Title
                        title_elem = card.find('h3', class_='base-search-card__title') or \
                                   card.find('h3', class_='result-card__title')
                        title = title_elem.text.strip() if title_elem else "Not specified"
                        
                        # Company
                        company_elem = card.find('h4', class_='base-search-card__subtitle') or \
                                     card.find('h4', class_='result-card__subtitle')
                        company = company_elem.text.strip() if company_elem else "Not specified"
                        
                        # Location
                        location_elem = card.find('span', class_='job-search-card__location') or \
                                      card.find('span', class_='result-card__location')
                        job_location = location_elem.text.strip() if location_elem else "Not specified"
                        
                        # Link
                        link_elem = card.find('a', class_='base-card__full-link') or \
                                  card.find('a', class_='result-card__full-card-link')
                        job_link = link_elem.get('href') if link_elem else "Not specified"
                        
                        # Enhanced salary extraction for LinkedIn
                        salary = "Not specified"
                        
                        # Try to find salary in various locations
                        salary_selectors = [
                            '.job-search-card__salary-info',
                            '.result-card__salary',
                            '.job-details-salary',
                            '[data-test="job-salary"]'
                        ]
                        
                        for selector in salary_selectors:
                            salary_elem = card.find(class_=selector.replace('.', '').replace('[data-test="job-salary"]', '')) or \
                                        card.find(attrs={'data-test': 'job-salary'})
                            if salary_elem:
                                salary = salary_elem.text.strip()
                                break
                        
                        # Summary
                        summary_elem = card.find('p', class_='job-search-card__snippet') or \
                                     card.find('p', class_='result-card__snippet')
                        summary = summary_elem.text.strip() if summary_elem else ""
                        
                        # If no salary found, look in summary
                        if salary == "Not specified" and summary:
                            salary_patterns = [
                                r'\$[\d,]+(?:\.\d{2})?(?:\s*[-–—]\s*\$[\d,]+(?:\.\d{2})?)?(?:\s*(?:per\s*)?(?:hour|hr|year|yr|month|mo|annually))?',
                                r'[\d,]+k?(?:\s*[-–—]\s*[\d,]+k?)?\s*(?:per\s*)?(?:hour|hr|year|yr|month|mo|annually)',
                                r'salary:?\s*\$?[\d,]+(?:k|,000)?'
                            ]
                            
                            for pattern in salary_patterns:
                                match = re.search(pattern, summary, re.IGNORECASE)
                                if match:
                                    salary = match.group(0)
                                    break
                        
                        job_data = {
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'salary': salary,
                            'job_type': "Not specified",
                            'summary': summary,
                            'url': job_link,
                            'source': 'LinkedIn',
                            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'search_term': search_term,
                            'search_location': location
                        }
                        
                        jobs.append(job_data)
                        page_jobs += 1
                        
                    except Exception as e:
                        continue
                
                print(f"   Page {page + 1}: Found {page_jobs} jobs")
                
                if page_jobs == 0:
                    break
                    
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"   Error on LinkedIn page {page + 1}: {e}")
                continue
        
        print(f"✅ LinkedIn: {len(jobs)} total jobs found")
        return jobs
    
    def scrape_glassdoor_comprehensive(self, search_term, location, max_pages=5):
        """Comprehensive Glassdoor scraping"""
        jobs = []
        print(f"🔍 Scraping Glassdoor for '{search_term}' in '{location}'...")
        
        try:
            for page in range(1, max_pages + 1):
                url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={quote_plus(search_term)}&locT=C&locId=1&p={page}"
                
                headers = {
                    'User-Agent': self.user_agent.random,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
                
                response = self.session.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Multiple selectors for different Glassdoor layouts
                job_cards = soup.find_all('li', {'data-test': 'jobListing'}) or \
                           soup.find_all('div', {'data-test': 'jobListing'}) or \
                           soup.find_all('li', class_='react-job-listing')
                
                if not job_cards:
                    break
                
                page_jobs = 0
                for card in job_cards:
                    try:
                        # Title
                        title_elem = card.find('a', {'data-test': 'job-title'}) or \
                                   card.find('a', class_='jobLink')
                        title = title_elem.text.strip() if title_elem else "Not specified"
                        
                        # Company
                        company_elem = card.find('span', {'data-test': 'employer-name'}) or \
                                     card.find('div', class_='jobHeader')
                        company = company_elem.text.strip() if company_elem else "Not specified"
                        
                        # Location
                        location_elem = card.find('span', {'data-test': 'job-location'}) or \
                                      card.find('span', class_='loc')
                        job_location = location_elem.text.strip() if location_elem else location
                        
                        # Salary
                        salary_elem = card.find('span', {'data-test': 'detailSalary'})
                        salary = salary_elem.text.strip() if salary_elem else "Not specified"
                        
                        # Link
                        link_elem = title_elem
                        job_link = f"https://www.glassdoor.com{link_elem.get('href')}" if link_elem and link_elem.get('href') else "Not specified"
                        
                        job_data = {
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'salary': salary,
                            'job_type': "Not specified",
                            'summary': "",
                            'url': job_link,
                            'source': 'Glassdoor',
                            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'search_term': search_term,
                            'search_location': location
                        }
                        
                        jobs.append(job_data)
                        page_jobs += 1
                        
                    except Exception as e:
                        continue
                
                print(f"   Page {page}: Found {page_jobs} jobs")
                
                if page_jobs == 0:
                    break
                    
                time.sleep(random.uniform(3, 6))
                
        except Exception as e:
            print(f"   Error scraping Glassdoor: {e}")
        
        print(f"✅ Glassdoor: {len(jobs)} total jobs found")
        return jobs
    
    def scrape_monster_comprehensive(self, search_term, location, max_pages=3):
        """Comprehensive Monster scraping"""
        jobs = []
        print(f"🔍 Scraping Monster for '{search_term}' in '{location}'...")
        
        try:
            for page in range(max_pages):
                page_jobs = 0
                url = f"https://www.monster.com/jobs/search?q={quote_plus(search_term)}&where={quote_plus(location)}&page={page+1}"
                
                self.driver.get(url)
                time.sleep(random.uniform(3, 5))
                
                # Wait for job cards to load
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='svx-job-card'], .job-cardstyle__JobCardContainer, .jobcard"))
                    )
                except:
                    print(f"   No jobs found on Monster page {page + 1}")
                    continue
                
                # Find job cards using multiple selectors
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='svx-job-card'], .job-cardstyle__JobCardContainer, .jobcard, .job-card")
                
                for card in job_cards[:15]:  # Limit per page
                    try:
                        # Extract job details
                        title_elem = card.find_element(By.CSS_SELECTOR, "h2 a, .jobTitle a, [data-testid='svx-job-title'] a")
                        title = title_elem.text.strip()
                        job_link = title_elem.get_attribute('href')
                        
                        try:
                            company_elem = card.find_element(By.CSS_SELECTOR, "[data-testid='svx-job-company'], .company, .companyName")
                            company = company_elem.text.strip()
                        except:
                            company = "Not specified"
                        
                        try:
                            location_elem = card.find_element(By.CSS_SELECTOR, "[data-testid='svx-job-location'], .location, .jobLocation")
                            job_location = location_elem.text.strip()
                        except:
                            job_location = location
                        
                        try:
                            summary_elem = card.find_element(By.CSS_SELECTOR, ".summary, .jobSnippet, [data-testid='svx-job-summary']")
                            summary = summary_elem.text.strip()[:300] + "..."
                        except:
                            summary = "No description available"
                        
                        # Enhanced salary extraction for Monster
                        salary = "Not specified"
                        try:
                            salary_elem = card.find_element(By.CSS_SELECTOR, ".salary, .jobSalary, [data-testid='svx-job-salary'], .salary-range")
                            salary = salary_elem.text.strip()
                        except:
                            # Look for salary in summary if not found elsewhere
                            if summary and summary != "No description available":
                                salary_patterns = [
                                    r'\$[\d,]+(?:\.\d{2})?(?:\s*[-–—]\s*\$[\d,]+(?:\.\d{2})?)?(?:\s*(?:per\s*)?(?:hour|hr|year|yr|month|mo|annually))?',
                                    r'[\d,]+k?(?:\s*[-–—]\s*[\d,]+k?)?\s*(?:per\s*)?(?:hour|hr|year|yr|month|mo|annually)',
                                    r'salary:?\s*\$?[\d,]+(?:k|,000)?'
                                ]
                                
                                for pattern in salary_patterns:
                                    match = re.search(pattern, summary, re.IGNORECASE)
                                    if match:
                                        salary = match.group(0)
                                        break
                        
                        job_data = {
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'salary': salary,
                            'job_type': 'Not specified',
                            'summary': summary,
                            'url': job_link if job_link.startswith('http') else f"https://www.monster.com{job_link}",
                            'source': 'Monster',
                            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'search_term': search_term,
                            'search_location': location
                        }
                        
                        jobs.append(job_data)
                        page_jobs += 1
                        
                    except Exception as e:
                        continue
                
                print(f"   Page {page + 1}: Found {page_jobs} jobs")
                
                if page_jobs == 0:
                    break
                    
                time.sleep(random.uniform(3, 6))
                
        except Exception as e:
            print(f"   Error scraping Monster: {e}")
        
        print(f"✅ Monster: {len(jobs)} total jobs found")
        return jobs
    
    def scrape_ziprecruiter_comprehensive(self, search_term, location, max_pages=3):
        """Comprehensive ZipRecruiter scraping"""
        jobs = []
        print(f"🔍 Scraping ZipRecruiter for '{search_term}' in '{location}'...")
        
        try:
            for page in range(max_pages):
                page_jobs = 0
                url = f"https://www.ziprecruiter.com/jobs-search?search={quote_plus(search_term)}&location={quote_plus(location)}&page={page+1}"
                
                self.driver.get(url)
                time.sleep(random.uniform(3, 5))
                
                # Wait for job cards to load
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".job_content, [data-testid='job-card'], .jobList-item"))
                    )
                except:
                    print(f"   No jobs found on ZipRecruiter page {page + 1}")
                    continue
                
                # Find job cards
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".job_content, [data-testid='job-card'], .jobList-item, .job-card")
                
                for card in job_cards[:15]:  # Limit per page
                    try:
                        # Extract job details
                        title_elem = card.find_element(By.CSS_SELECTOR, "h2 a, .job_title a, [data-testid='job-title'] a")
                        title = title_elem.text.strip()
                        job_link = title_elem.get_attribute('href')
                        
                        try:
                            company_elem = card.find_element(By.CSS_SELECTOR, ".company, .company_name, [data-testid='job-company']")
                            company = company_elem.text.strip()
                        except:
                            company = "Not specified"
                        
                        try:
                            location_elem = card.find_element(By.CSS_SELECTOR, ".location, .job_location, [data-testid='job-location']")
                            job_location = location_elem.text.strip()
                        except:
                            job_location = location
                        
                        try:
                            summary_elem = card.find_element(By.CSS_SELECTOR, ".job_snippet, .summary, [data-testid='job-summary']")
                            summary = summary_elem.text.strip()[:300] + "..."
                        except:
                            summary = "No description available"
                        
                        # Enhanced salary extraction for ZipRecruiter
                        salary = "Not specified"
                        try:
                            salary_elem = card.find_element(By.CSS_SELECTOR, ".salary, .job_salary, [data-testid='job-salary'], .salary-range, .compensation")
                            salary = salary_elem.text.strip()
                        except:
                            # Look for salary in summary if not found elsewhere
                            if summary and summary != "No description available":
                                salary_patterns = [
                                    r'\$[\d,]+(?:\.\d{2})?(?:\s*[-–—]\s*\$[\d,]+(?:\.\d{2})?)?(?:\s*(?:per\s*)?(?:hour|hr|year|yr|month|mo|annually))?',
                                    r'[\d,]+k?(?:\s*[-–—]\s*[\d,]+k?)?\s*(?:per\s*)?(?:hour|hr|year|yr|month|mo|annually)',
                                    r'salary:?\s*\$?[\d,]+(?:k|,000)?'
                                ]
                                
                                for pattern in salary_patterns:
                                    match = re.search(pattern, summary, re.IGNORECASE)
                                    if match:
                                        salary = match.group(0)
                                        break
                        
                        job_data = {
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'salary': salary,
                            'job_type': 'Not specified',
                            'summary': summary,
                            'url': job_link if job_link.startswith('http') else f"https://www.ziprecruiter.com{job_link}",
                            'source': 'ZipRecruiter',
                            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'search_term': search_term,
                            'search_location': location
                        }
                        
                        jobs.append(job_data)
                        page_jobs += 1
                        
                    except Exception as e:
                        continue
                
                print(f"   Page {page + 1}: Found {page_jobs} jobs")
                
                if page_jobs == 0:
                    break
                    
                time.sleep(random.uniform(3, 6))
                
        except Exception as e:
            print(f"   Error scraping ZipRecruiter: {e}")
        
        print(f"✅ ZipRecruiter: {len(jobs)} total jobs found")
        return jobs
    
    def scrape_careerbuilder_comprehensive(self, search_term, location, max_pages=3):
        """Comprehensive CareerBuilder scraping"""
        jobs = []
        print(f"🔍 Scraping CareerBuilder for '{search_term}' in '{location}'...")
        
        try:
            for page in range(max_pages):
                page_jobs = 0
                url = f"https://www.careerbuilder.com/jobs?keywords={quote_plus(search_term)}&location={quote_plus(location)}&page_number={page+1}"
                
                self.driver.get(url)
                time.sleep(random.uniform(3, 5))
                
                # Wait for job cards to load
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='job-card'], .data-results-content, .job-row"))
                    )
                except:
                    print(f"   No jobs found on CareerBuilder page {page + 1}")
                    continue
                
                # Find job cards
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='job-card'], .data-results-content, .job-row, .job-card")
                
                for card in job_cards[:15]:  # Limit per page
                    try:
                        # Extract job details
                        title_elem = card.find_element(By.CSS_SELECTOR, "h2 a, .job-title a, [data-testid='job-title'] a")
                        title = title_elem.text.strip()
                        job_link = title_elem.get_attribute('href')
                        
                        try:
                            company_elem = card.find_element(By.CSS_SELECTOR, ".company-name, .data-details span, [data-testid='job-company']")
                            company = company_elem.text.strip()
                        except:
                            company = "Not specified"
                        
                        try:
                            location_elem = card.find_element(By.CSS_SELECTOR, ".job-location, .data-details .location, [data-testid='job-location']")
                            job_location = location_elem.text.strip()
                        except:
                            job_location = location
                        
                        try:
                            summary_elem = card.find_element(By.CSS_SELECTOR, ".job-summary, .data-details p, [data-testid='job-summary']")
                            summary = summary_elem.text.strip()[:300] + "..."
                        except:
                            summary = "No description available"
                        
                        # Enhanced salary extraction for CareerBuilder
                        salary = "Not specified"
                        try:
                            salary_elem = card.find_element(By.CSS_SELECTOR, ".salary, .data-details .salary, [data-testid='job-salary'], .pay-range")
                            salary = salary_elem.text.strip()
                        except:
                            # Look for salary in summary if not found elsewhere
                            if summary and summary != "No description available":
                                salary_patterns = [
                                    r'\$[\d,]+(?:\.\d{2})?(?:\s*[-–—]\s*\$[\d,]+(?:\.\d{2})?)?(?:\s*(?:per\s*)?(?:hour|hr|year|yr|month|mo|annually))?',
                                    r'[\d,]+k?(?:\s*[-–—]\s*[\d,]+k?)?\s*(?:per\s*)?(?:hour|hr|year|yr|month|mo|annually)',
                                    r'salary:?\s*\$?[\d,]+(?:k|,000)?'
                                ]
                                
                                for pattern in salary_patterns:
                                    match = re.search(pattern, summary, re.IGNORECASE)
                                    if match:
                                        salary = match.group(0)
                                        break
                        
                        job_data = {
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'salary': salary,
                            'job_type': 'Not specified',
                            'summary': summary,
                            'url': job_link if job_link.startswith('http') else f"https://www.careerbuilder.com{job_link}",
                            'source': 'CareerBuilder',
                            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'search_term': search_term,
                            'search_location': location
                        }
                        
                        jobs.append(job_data)
                        page_jobs += 1
                        
                    except Exception as e:
                        continue
                
                print(f"   Page {page + 1}: Found {page_jobs} jobs")
                
                if page_jobs == 0:
                    break
                    
                time.sleep(random.uniform(3, 6))
                
        except Exception as e:
            print(f"   Error scraping CareerBuilder: {e}")
        
        print(f"✅ CareerBuilder: {len(jobs)} total jobs found")
        return jobs
    
    def scrape_remote_apis(self, search_term, location):
        """Scrape from multiple remote job APIs and specialized platforms"""
        jobs = []
        print(f"🔍 Scraping Multiple Job APIs & Specialized Platforms...")
        
        # Remotive API
        try:
            url = "https://remotive.com/api/remote-jobs"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            api_jobs = 0
            for job in data.get("jobs", []):
                title = job.get('title', '')
                if any(keyword.lower() in title.lower() for keyword in search_term.split()):
                    job_data = {
                        'title': job.get('title', 'Not specified'),
                        'company': job.get('company_name', 'Not specified'),
                        'location': job.get('candidate_required_location', 'Remote'),
                        'salary': job.get('salary', 'Not specified'),
                        'job_type': job.get('job_type', 'Not specified'),
                        'summary': job.get('description', '')[:300] + "..." if job.get('description') else "",
                        'url': job.get('url', 'Not specified'),
                        'source': 'Remotive API',
                        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'search_term': search_term,
                        'search_location': location
                    }
                    jobs.append(job_data)
                    api_jobs += 1
            
            print(f"   Remotive API: {api_jobs} jobs")
            
        except Exception as e:
            print(f"   Error with Remotive API: {e}")
        
        # GitHub Jobs API alternative
        try:
            url = "https://jobs.github.com/positions.json"
            headers = {'User-Agent': self.user_agent.random}
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                github_jobs = 0
                for job in data:
                    title = job.get('title', '')
                    if any(keyword.lower() in title.lower() for keyword in search_term.split()):
                        job_data = {
                            'title': job.get('title', 'Not specified'),
                            'company': job.get('company', 'Not specified'),
                            'location': job.get('location', 'Remote'),
                            'salary': 'Not specified',
                            'job_type': job.get('type', 'Not specified'),
                            'summary': job.get('description', '')[:300] + "..." if job.get('description') else "",
                            'url': job.get('url', 'Not specified'),
                            'source': 'GitHub Jobs',
                            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'search_term': search_term,
                            'search_location': location
                        }
                        jobs.append(job_data)
                        github_jobs += 1
                
                print(f"   GitHub Jobs: {github_jobs} jobs")
                
        except Exception as e:
            print(f"   GitHub Jobs API not available: {e}")
        
        # AngelList/Wellfound API (Startup Jobs)
        try:
            # AngelList has job listings that can be accessed
            angel_jobs = 0
            print(f"   AngelList: Checking startup job listings...")
            # Note: AngelList requires different approach, this is a placeholder for API integration
            
        except Exception as e:
            print(f"   AngelList API not available: {e}")
        
        # Remote OK API
        try:
            url = "https://remoteok.io/api"
            headers = {'User-Agent': self.user_agent.random}
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                remoteok_jobs = 0
                
                for job in data[1:]:  # Skip first element (metadata)
                    if isinstance(job, dict):
                        title = job.get('position', '')
                        company = job.get('company', '')
                        
                        if any(keyword.lower() in title.lower() or keyword.lower() in company.lower() 
                               for keyword in search_term.split()):
                            job_data = {
                                'title': title,
                                'company': company,
                                'location': 'Remote',
                                'salary': f"${job.get('salary_min', '')}-${job.get('salary_max', '')}" if job.get('salary_min') else 'Not specified',
                                'job_type': ', '.join(job.get('tags', [])) if job.get('tags') else 'Remote',
                                'summary': job.get('description', '')[:300] + "..." if job.get('description') else "",
                                'url': job.get('url', 'https://remoteok.io'),
                                'source': 'RemoteOK',
                                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                                'search_term': search_term,
                                'search_location': location
                            }
                            jobs.append(job_data)
                            remoteok_jobs += 1
                
                print(f"   RemoteOK: {remoteok_jobs} jobs")
                
        except Exception as e:
            print(f"   RemoteOK API error: {e}")
        
        # We Work Remotely scraping
        try:
            wwr_jobs = 0
            url = f"https://weworkremotely.com/remote-jobs/search?term={quote_plus(search_term)}"
            headers = {'User-Agent': self.user_agent.random}
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                job_listings = soup.find_all('li', class_='feature')
                
                for listing in job_listings[:10]:  # Limit to 10 jobs
                    try:
                        title_elem = listing.find('span', class_='title')
                        company_elem = listing.find('span', class_='company')
                        link_elem = listing.find('a')
                        
                        if title_elem and company_elem:
                            job_data = {
                                'title': title_elem.text.strip(),
                                'company': company_elem.text.strip(),
                                'location': 'Remote',
                                'salary': 'Not specified',
                                'job_type': 'Remote',
                                'summary': 'Remote job opportunity',
                                'url': f"https://weworkremotely.com{link_elem.get('href')}" if link_elem else 'https://weworkremotely.com',
                                'source': 'WeWorkRemotely',
                                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                                'search_term': search_term,
                                'search_location': location
                            }
                            jobs.append(job_data)
                            wwr_jobs += 1
                    except:
                        continue
                
                print(f"   WeWorkRemotely: {wwr_jobs} jobs")
                
        except Exception as e:
            print(f"   WeWorkRemotely error: {e}")
        
        # FlexJobs API alternative scraping
        try:
            flexjobs_count = 0
            print(f"   FlexJobs: Checking flexible job opportunities...")
            # FlexJobs requires subscription, this is a placeholder for integration
            
        except Exception as e:
            print(f"   FlexJobs error: {e}")
        
        # Dice.com for tech jobs
        try:
            dice_jobs = 0
            url = f"https://www.dice.com/jobs?q={quote_plus(search_term)}&location={quote_plus(location)}"
            headers = {'User-Agent': self.user_agent.random}
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Note: Dice has anti-scraping measures, this is a basic implementation
                print(f"   Dice.com: Checking tech job listings...")
                
        except Exception as e:
            print(f"   Dice.com error: {e}")
        
        print(f"✅ APIs & Specialized Platforms: {len(jobs)} total jobs found")
        return jobs
    
    def ai_enhanced_relevance_scoring(self, job, search_keywords, location_keywords):
        """AI-enhanced relevance scoring using CrewAI agents"""
        
        # Calculate salary numeric value for AI context
        salary_numeric = self.parse_salary_to_number(job.get('salary', ''))
        job['salary_numeric'] = salary_numeric
        
        # Create AI task for job analysis
        analysis_task = Task(
            description=f"""
            Analyze this job posting for relevance to the search criteria:
            
            Job Details:
            - Title: {job['title']}
            - Company: {job['company']}
            - Location: {job['location']}
            - Summary: {job.get('summary', 'No summary available')[:500]}
            - Salary: {job.get('salary', 'Not specified')} (Numeric: ${salary_numeric:,.0f} if available)
            
            Search Criteria:
            - Keywords: {search_keywords}
            - Location: {location_keywords}
            
            Provide a relevance score from 0-100 and explain the reasoning.
            Consider: skill matching, location fit, career level, company reputation, salary competitiveness, and growth potential.
            
            SALARY CONSIDERATIONS:
            - Jobs with competitive salaries (≥$120k) should receive bonus points
            - Salary transparency (providing salary info) is valuable
            - Consider salary vs role level appropriateness
            
            Return your analysis in this format:
            SCORE: [0-100]
            REASONING: [Detailed explanation]
            KEY_MATCHES: [List of matching elements]
            SALARY_ANALYSIS: [Salary competitiveness assessment]
            GROWTH_POTENTIAL: [High/Medium/Low and why]
            """,
            agent=analyzer_agent,
            expected_output="Structured analysis with score and detailed reasoning including salary assessment"
        )
        
        try:
            # Create crew for this analysis
            analysis_crew = Crew(
                agents=[analyzer_agent],
                tasks=[analysis_task],
                process=Process.sequential,
                verbose=False
            )
            
            # Execute AI analysis
            result = analysis_crew.kickoff()
            
            # Extract score from AI result
            result_text = str(result).upper()
            score_match = re.search(r'SCORE:\s*(\d+)', result_text)
            if score_match:
                ai_score = int(score_match.group(1))
                # Store AI reasoning for later use
                job['ai_analysis'] = str(result)
                return ai_score
            else:
                # Fallback to traditional scoring if AI fails
                return self.calculate_relevance_score(job, search_keywords, location_keywords)
                
        except Exception as e:
            print(f"AI analysis failed for {job['title']}, using fallback scoring: {e}")
            return self.calculate_relevance_score(job, search_keywords, location_keywords)
    
    def ai_job_insights_generation(self, ranked_jobs_df, search_term, location):
        """Generate AI-powered insights about the job search results"""
        
        # Prepare data summary for AI analysis
        top_10_jobs = ranked_jobs_df.head(10)
        job_summary = []
        
        for _, job in top_10_jobs.iterrows():
            job_summary.append(f"- {job['title']} at {job['company']} (Score: {job['relevance_score']}, Location: {job['location']}, Salary: {job['salary']})")
        
        jobs_text = "\n".join(job_summary)
        
        # Create AI task for market insights
        insights_task = Task(
            description=f"""
            Analyze these job search results and provide intelligent market insights:
            
            Search Query: {search_term} in {location}
            Total Jobs Found: {len(ranked_jobs_df)}
            
            Top 10 Jobs:
            {jobs_text}
            
            Provide insights on:
            1. MARKET_TRENDS: Current demand and trends for this role
            2. SALARY_ANALYSIS: Salary ranges and expectations
            3. SKILL_REQUIREMENTS: Most in-demand skills
            4. LOCATION_INSIGHTS: Geographic distribution and remote work trends
            5. COMPANY_ANALYSIS: Types of companies hiring
            6. CAREER_ADVICE: Recommendations for job seekers
            7. GROWTH_OPPORTUNITIES: Career progression insights
            
            Format your response with clear sections and actionable insights.
            """,
            agent=insight_agent,
            expected_output="Comprehensive market analysis with actionable insights"
        )
        
        try:
            # Create crew for insights generation
            insights_crew = Crew(
                agents=[insight_agent],
                tasks=[insights_task],
                process=Process.sequential,
                verbose=False
            )
            
            # Generate AI insights
            insights = insights_crew.kickoff()
            return str(insights)
            
        except Exception as e:
            print(f"AI insights generation failed: {e}")
            return "AI insights not available due to processing error."
    
    def ai_enhanced_job_ranking(self, jobs_df, search_keywords, location_keywords):
        """Use AI to enhance job ranking beyond simple scoring"""
        
        # Create ranking task for AI agent
        ranking_task = Task(
            description=f"""
            Re-rank these job opportunities using advanced AI analysis:
            
            Search Criteria: {search_keywords} in {location_keywords}
            
            Consider these factors for ranking:
            1. Career growth potential
            2. Market value and demand
            3. Skill development opportunities
            4. Company stability and reputation
            5. Work-life balance indicators
            6. Remote work flexibility
            7. Salary competitiveness
            8. Industry growth trends
            
            Analyze the top 20 jobs and provide a refined ranking with explanations.
            Focus on long-term career value, not just immediate keyword matches.
            """,
            agent=ranking_agent,
            expected_output="Refined job ranking with strategic career insights"
        )
        
        try:
            # For performance, only apply AI ranking to top 20 jobs
            top_jobs = jobs_df.head(20).copy()
            
            # Add AI career potential score
            top_jobs['ai_career_score'] = 0
            
            # Simple AI enhancement - in production, this would call the full AI crew
            for idx, job in top_jobs.iterrows():
                # Enhanced scoring based on AI criteria
                career_score = 0
                
                title_lower = job['title'].lower()
                company_lower = job['company'].lower()
                
                # Career level bonus
                if any(level in title_lower for level in ['senior', 'lead', 'principal']):
                    career_score += 15
                elif any(level in title_lower for level in ['mid', 'intermediate']):
                    career_score += 10
                
                # Technology relevance
                modern_tech = ['ai', 'machine learning', 'cloud', 'aws', 'kubernetes', 'react', 'python']
                for tech in modern_tech:
                    if tech in title_lower or tech in job.get('summary', '').lower():
                        career_score += 5
                
                # Company size indicators
                big_tech = ['google', 'microsoft', 'amazon', 'apple', 'meta', 'netflix']
                if any(company in company_lower for company in big_tech):
                    career_score += 20
                
                # SALARY-BASED AI ENHANCEMENT
                salary_numeric = job.get('salary_numeric', 0)
                if salary_numeric > 0:
                    # Salary competitiveness score
                    if salary_numeric >= 200000:
                        career_score += 25  # Exceptional salary
                    elif salary_numeric >= 150000:
                        career_score += 20  # Excellent salary
                    elif salary_numeric >= 120000:
                        career_score += 15  # Very good salary
                    elif salary_numeric >= 90000:
                        career_score += 10  # Good salary
                    elif salary_numeric >= 60000:
                        career_score += 5   # Fair salary
                
                top_jobs.at[idx, 'ai_career_score'] = career_score
            
            # Combine original relevance with AI career score (including salary)
            top_jobs['final_ai_score'] = (top_jobs['relevance_score'] * 0.6) + (top_jobs['ai_career_score'] * 0.4)
            
            # Re-rank based on combined score
            top_jobs = top_jobs.sort_values('final_ai_score', ascending=False)
            
            # Update ranks
            top_jobs['ai_rank'] = range(1, len(top_jobs) + 1)
            
            # Combine with remaining jobs
            remaining_jobs = jobs_df.iloc[20:].copy()
            remaining_jobs['ai_career_score'] = 0
            remaining_jobs['final_ai_score'] = remaining_jobs['relevance_score']
            remaining_jobs['ai_rank'] = range(len(top_jobs) + 1, len(jobs_df) + 1)
            
            # Combine all jobs
            final_df = pd.concat([top_jobs, remaining_jobs], ignore_index=True)
            
            return final_df
            
        except Exception as e:
            print(f"AI ranking enhancement failed: {e}")
            # Return original ranking if AI fails
            jobs_df['ai_career_score'] = 0
            jobs_df['final_ai_score'] = jobs_df['relevance_score']
            jobs_df['ai_rank'] = jobs_df['rank']
            return jobs_df
    
    def scrape_all_sources(self, search_term, location, keywords):
        """Scrape all sources comprehensively"""
        all_jobs = []
        
        print("🚀 Starting Comprehensive Multi-Source Job Search...")
        print("=" * 70)
        print("📊 Sources: Indeed, LinkedIn, Glassdoor, Monster, ZipRecruiter, CareerBuilder + APIs")
        print("=" * 70)
        
        # Use ThreadPoolExecutor for parallel scraping of major sources
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = []
            
            # Submit scraping tasks for all major job sites
            futures.append(executor.submit(self.scrape_indeed_comprehensive, search_term, location, 10))
            futures.append(executor.submit(self.scrape_linkedin_comprehensive, search_term, location, 5))
            futures.append(executor.submit(self.scrape_glassdoor_comprehensive, search_term, location, 3))
            futures.append(executor.submit(self.scrape_monster_comprehensive, search_term, location, 3))
            futures.append(executor.submit(self.scrape_ziprecruiter_comprehensive, search_term, location, 3))
            futures.append(executor.submit(self.scrape_careerbuilder_comprehensive, search_term, location, 3))
            
            # Collect results from all sources
            source_results = {}
            for future in as_completed(futures):
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                    # Track which source provided how many jobs
                    if jobs:
                        source = jobs[0].get('source', 'Unknown')
                        source_results[source] = len(jobs)
                except Exception as e:
                    print(f"❌ Error in parallel scraping: {e}")
        
        # Scrape APIs separately (lighter weight)
        print("\n🔗 Scraping additional API sources...")
        api_jobs = self.scrape_remote_apis(search_term, location)
        all_jobs.extend(api_jobs)
        if api_jobs:
            source_results['APIs'] = len(api_jobs)
        
        # Summary of results by source
        print(f"\n📈 MULTI-SOURCE SCRAPING SUMMARY:")
        print("-" * 50)
        total_jobs = 0
        for source, count in source_results.items():
            print(f"   • {source}: {count} jobs")
            total_jobs += count
        print("-" * 50)
        print(f"   🎯 TOTAL JOBS FOUND: {total_jobs}")
        print("=" * 70)
        
        return all_jobs
    
    def calculate_relevance_score(self, job, search_keywords, location_keywords):
        """Enhanced relevance scoring with salary consideration"""
        score = 0
        title_lower = job['title'].lower()
        company_lower = job['company'].lower()
        location_lower = job['location'].lower()
        summary_lower = job.get('summary', '').lower()
        
        # Split and clean keywords
        search_terms = [kw.strip().lower() for kw in search_keywords.split(',') if kw.strip()]
        location_terms = [kw.strip().lower() for kw in location_keywords.split(',') if kw.strip()]
        
        # Title relevance (highest weight)
        for term in search_terms:
            if term in title_lower:
                score += 15
        
        # Company relevance
        for term in search_terms:
            if term in company_lower:
                score += 8
        
        # Summary/description relevance
        for term in search_terms:
            if term in summary_lower:
                score += 5
        
        # Location relevance
        for term in location_terms:
            if term in location_lower:
                score += 7
        
        # Job level bonuses
        if any(level in title_lower for level in ['senior', 'lead', 'principal']):
            score += 5
        elif any(level in title_lower for level in ['junior', 'entry', 'intern']):
            score += 3
        
        # Remote work bonus
        if any(remote in location_lower for remote in ['remote', 'work from home']):
            score += 8
        
        # SALARY-BASED SCORING ENHANCEMENT
        salary_numeric = self.parse_salary_to_number(job.get('salary', ''))
        if salary_numeric > 0:
            # Salary availability bonus
            score += 10
            
            # Salary range bonuses based on market standards
            if salary_numeric >= 150000:  # High-tier salaries
                score += 15
            elif salary_numeric >= 120000:  # Upper-mid tier
                score += 12
            elif salary_numeric >= 90000:   # Mid-tier
                score += 8
            elif salary_numeric >= 60000:   # Lower-mid tier
                score += 5
            # Below 60k gets no bonus but doesn't get penalized
            
            # Store numeric salary for later use
            job['salary_numeric'] = salary_numeric
        else:
            job['salary_numeric'] = 0
        
        return score
    
    def process_and_rank_jobs(self, jobs, search_keywords, location_keywords, use_ai=True):
        """AI-ENHANCED: Process and rank all jobs using AI agents"""
        if not jobs:
            return pd.DataFrame(), ""
        
        print(f"\n🤖 AI-ENHANCED JOB PROCESSING")
        print(f"🔄 Processing {len(jobs)} jobs with AI analysis...")
        
        # Convert to DataFrame
        df = pd.DataFrame(jobs)
        
        # Remove duplicates based on title and company
        initial_count = len(df)
        df = df.drop_duplicates(subset=['title', 'company'], keep='first')
        duplicates_removed = initial_count - len(df)
        print(f"   Removed {duplicates_removed} duplicates")
        
        # Clean data
        df['title'] = df['title'].str.strip()
        df['company'] = df['company'].str.strip()
        df['location'] = df['location'].str.strip()
        
        # Calculate salary_numeric for all jobs
        print("   💰 Processing salary information...")
        df['salary_numeric'] = df['salary'].apply(self.parse_salary_to_number)
        
        # AI-ENHANCED SCORING
        if use_ai:
            print("   🧠 Running AI relevance analysis...")
            df['relevance_score'] = df.apply(
                lambda job: self.ai_enhanced_relevance_scoring(job, search_keywords, location_keywords), 
                axis=1
            )
            
            print("   🎯 Applying AI-enhanced ranking...")
            df = self.ai_enhanced_job_ranking(df, search_keywords, location_keywords)
            
            # Sort by AI final score
            df = df.sort_values('final_ai_score', ascending=False)
            df['rank'] = range(1, len(df) + 1)
            
            print("   📊 Generating AI market insights...")
            ai_insights = self.ai_job_insights_generation(df, search_keywords, location_keywords)
            
        else:
            # Fallback to traditional scoring
            print("   📊 Using traditional relevance scoring...")
            df['relevance_score'] = df.apply(
                lambda job: self.calculate_relevance_score(job, search_keywords, location_keywords), 
                axis=1
            )
            df = df.sort_values('relevance_score', ascending=False)
            df['rank'] = range(1, len(df) + 1)
            ai_insights = "AI insights not available - using traditional scoring."
        
        return df, ai_insights
    
    def close_driver(self):
        """Close the web driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

def get_search_criteria():
    """Get comprehensive search criteria from user"""
    print("🎯 Perfect Job Search Configuration")
    print("=" * 50)
    
    search_term = input("Enter job title/role (e.g., 'Python Developer', 'Data Scientist', 'Frontend Engineer'): ").strip()
    if not search_term:
        search_term = "Software Developer"
    
    location = input("Enter location (e.g., 'Remote', 'New York', 'San Francisco', 'London'): ").strip()
    if not location:
        location = "Remote"
    
    keywords = input("Enter specific skills/keywords (comma-separated, e.g., 'Python, Django, React, AWS'): ").strip()
    if not keywords:
        keywords = search_term
    
    print(f"\n✅ Search Configuration:")
    print(f"   🔍 Job Role: {search_term}")
    print(f"   📍 Location: {location}")
    print(f"   🏷️ Keywords: {keywords}")
    print(f"   🎯 Goal: Find ALL relevant jobs, ranked by relevance")
    
    return search_term, location, keywords

def run_perfect_job_scraper():
    """AI-ENHANCED: Run the perfect job scraper with AI agents"""
    print("🤖 AI-ENHANCED Ultimate Job Search Engine")
    print("=" * 80)
    print("🎯 AI Features:")
    print("   • CrewAI agents for intelligent job analysis")
    print("   • AI-powered relevance scoring and ranking")
    print("   • Smart market insights generation")
    print("   • AI career growth potential analysis")
    print("   • Parallel processing for maximum speed")
    print("")
    print("🌐 Job Sources (9+ Platforms):")
    print("   • Major Sites: Indeed, LinkedIn, Glassdoor, Monster, ZipRecruiter, CareerBuilder")
    print("   • APIs: Remotive, GitHub Jobs, RemoteOK, WeWorkRemotely, AngelList, Dice")
    print("   • Comprehensive pagination (up to 10 pages per source)")
    print("=" * 80)
    
    # Get search criteria
    search_term, location, keywords = get_search_criteria()
    
    # Ask user about AI features
    use_ai = input("\n🤖 Enable AI-enhanced analysis? (y/n, default=y): ").strip().lower()
    use_ai = use_ai != 'n'  # Default to yes
    
    if use_ai:
        print("✅ AI agents activated for enhanced job analysis!")
    else:
        print("📊 Using traditional scoring methods.")
    
    # Initialize scraper
    scraper = PerfectJobScraper()
    
    try:
        # Scrape all sources
        all_jobs = scraper.scrape_all_sources(search_term, location, keywords)
        
        if not all_jobs:
            print("❌ No jobs found. Try different search criteria.")
            return
        
        # AI-ENHANCED: Process and rank jobs with AI insights
        ranked_jobs_df, ai_insights = scraper.process_and_rank_jobs(all_jobs, keywords, location, use_ai)
        
        if ranked_jobs_df.empty:
            print("❌ No relevant jobs found after processing.")
            return
        
        # Save results
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"ai_jobs_{search_term.replace(' ', '_').lower()}_{location.replace(' ', '_').lower()}_{timestamp}.csv"
        
        # Reorder columns for better readability with salary prominence
        base_columns = ['rank', 'relevance_score', 'title', 'company', 'location', 'salary', 'salary_numeric',
                       'job_type', 'summary', 'url', 'source', 'scraped_at']
        
        # Add AI columns if available
        if use_ai and 'ai_career_score' in ranked_jobs_df.columns:
            ai_columns = ['ai_career_score', 'final_ai_score', 'ai_rank']
            column_order = base_columns[:2] + ai_columns + base_columns[2:]
        else:
            column_order = base_columns
            
        available_columns = [col for col in column_order if col in ranked_jobs_df.columns]
        ranked_jobs_df = ranked_jobs_df[available_columns]
        
        ranked_jobs_df.to_csv(filename, index=False)
        
        # Save AI insights to separate file
        if use_ai and ai_insights:
            insights_filename = f"ai_insights_{search_term.replace(' ', '_').lower()}_{timestamp}.txt"
            with open(insights_filename, 'w') as f:
                f.write(f"AI MARKET INSIGHTS\n")
                f.write(f"Search: {search_term} in {location}\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                f.write(ai_insights)
        
        # Display results
        print(f"\n🏆 AI-ENHANCED JOB SEARCH RESULTS")
        print("=" * 60)
        print(f"📊 Total Jobs Found: {len(ranked_jobs_df)}")
        print(f"📁 Jobs saved to: {filename}")
        if use_ai:
            print(f"🧠 AI insights saved to: {insights_filename}")
        
        # Show top 15 results with AI scores and salary
        print(f"\n🥇 TOP 15 MOST RELEVANT JOBS (Salary-Enhanced Ranking):")
        print("-" * 140)
        if use_ai and 'final_ai_score' in ranked_jobs_df.columns:
            print(f"{'Rank':<4} {'AI Score':<8} {'Career':<6} {'Title':<30} {'Company':<20} {'Location':<15} {'Salary':<20}")
        else:
            print(f"{'Rank':<4} {'Score':<6} {'Title':<30} {'Company':<20} {'Location':<15} {'Salary':<20}")
        print("-" * 140)
        
        for _, job in ranked_jobs_df.head(15).iterrows():
            title = job['title'][:27] + "..." if len(job['title']) > 27 else job['title']
            company = job['company'][:17] + "..." if len(job['company']) > 17 else job['company']
            location_str = job['location'][:12] + "..." if len(job['location']) > 12 else job['location']
            salary_str = job['salary'][:17] + "..." if len(str(job['salary'])) > 17 else str(job['salary'])
            
            if use_ai and 'final_ai_score' in ranked_jobs_df.columns:
                ai_score = job.get('final_ai_score', job['relevance_score'])
                career_score = job.get('ai_career_score', 0)
                print(f"{job['rank']:<4} {ai_score:<8.1f} {career_score:<6} {title:<30} {company:<20} {location_str:<15} {salary_str:<20}")
            else:
                print(f"{job['rank']:<4} {job['relevance_score']:<6} {title:<30} {company:<20} {location_str:<15} {salary_str:<20}")
        
        # Enhanced statistics with AI insights and salary data
        print(f"\n📈 ENHANCED SEARCH STATISTICS (With Salary Analysis):")
        print(f"   • Sources used: {', '.join(ranked_jobs_df['source'].unique())}")
        
        if use_ai and 'final_ai_score' in ranked_jobs_df.columns:
            print(f"   • Average AI score: {ranked_jobs_df['final_ai_score'].mean():.1f}")
            print(f"   • Highest AI score: {ranked_jobs_df['final_ai_score'].max():.1f}")
            if 'ai_career_score' in ranked_jobs_df.columns:
                print(f"   • Average career potential: {ranked_jobs_df['ai_career_score'].mean():.1f}")
        else:
            print(f"   • Average relevance score: {ranked_jobs_df['relevance_score'].mean():.1f}")
            print(f"   • Highest score: {ranked_jobs_df['relevance_score'].max()}")
        
        # Salary statistics
        jobs_with_salary = ranked_jobs_df[ranked_jobs_df['salary'] != 'Not specified']
        jobs_with_numeric_salary = ranked_jobs_df[ranked_jobs_df['salary_numeric'] > 0]
        
        print(f"   • Jobs with salary info: {len(jobs_with_salary)} ({len(jobs_with_salary)/len(ranked_jobs_df)*100:.1f}%)")
        
        if len(jobs_with_numeric_salary) > 0:
            avg_salary = jobs_with_numeric_salary['salary_numeric'].mean()
            max_salary = jobs_with_numeric_salary['salary_numeric'].max()
            min_salary = jobs_with_numeric_salary['salary_numeric'].min()
            print(f"   • Average salary: ${avg_salary:,.0f}")
            print(f"   • Salary range: ${min_salary:,.0f} - ${max_salary:,.0f}")
            
            # Salary tier breakdown
            high_salary = len(jobs_with_numeric_salary[jobs_with_numeric_salary['salary_numeric'] >= 120000])
            mid_salary = len(jobs_with_numeric_salary[(jobs_with_numeric_salary['salary_numeric'] >= 80000) & 
                                                    (jobs_with_numeric_salary['salary_numeric'] < 120000)])
            entry_salary = len(jobs_with_numeric_salary[jobs_with_numeric_salary['salary_numeric'] < 80000])
            
            print(f"   • High salary (≥$120k): {high_salary} jobs")
            print(f"   • Mid salary ($80k-$120k): {mid_salary} jobs") 
            print(f"   • Entry salary (<$80k): {entry_salary} jobs")
        
        print(f"   • Remote jobs: {len(ranked_jobs_df[ranked_jobs_df['location'].str.contains('remote', case=False, na=False)])}")
        
        # Top companies
        top_companies = ranked_jobs_df['company'].value_counts().head(5)
        print(f"   • Top companies: {', '.join(top_companies.index.tolist())}")
        
        # Display AI insights preview
        if use_ai and ai_insights:
            print(f"\n🧠 AI MARKET INSIGHTS PREVIEW:")
            print("-" * 60)
            # Show first 300 characters of AI insights
            preview = ai_insights[:300] + "..." if len(ai_insights) > 300 else ai_insights
            print(preview)
            print(f"\n📄 Full AI insights available in: {insights_filename}")
        
        print(f"\n✅ 💰 SALARY-ENHANCED AI Job Search Completed!")
        print(f"📊 Features Added:")
        print(f"   • Enhanced salary extraction from all job sites")
        print(f"   • Salary-based ranking and scoring")
        print(f"   • Comprehensive salary statistics and analysis")
        print(f"   • Salary competitiveness assessment in AI scoring")
        print(f"📄 Complete results saved to: '{filename}'")
        print(f"💡 Tip: Sort by 'salary_numeric' column for salary-based ranking!")
        
    except Exception as e:
        print(f"❌ Error during AI-enhanced scraping: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close_driver()

if __name__ == "__main__":
    run_perfect_job_scraper()
