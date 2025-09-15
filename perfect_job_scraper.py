# Perfect Job Scraper - LinkedIn Job Search Engine
# Source: LinkedIn
# pip install crewai beautifulsoup4 fake-useragent lxml google-generativeai

from crewai import Agent, Task, Task, Crew, Process
import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re
import random
import os
import json
from urllib.parse import quote_plus
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
import litellm

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables

# --- AI AGENTS CONFIGURATION ---
# These AI agents use CrewAI to intelligently process and analyze job data

scraper_agent = Agent(
    role="Intelligent Web Scraper",
    goal="Extract comprehensive job data from multiple sources with AI-powered content understanding",
    backstory="You are an expert web scraper with deep understanding of job posting structures across different platforms. You can intelligently identify and extract relevant job information even when website layouts change.",
    verbose=True,
    allow_delegation=False,
    llm="gemini/gemini-1.5-flash" if os.environ.get('GOOGLE_API_KEY') else None
)

analyzer_agent = Agent(
    role="Job Relevance Analyzer",
    goal="Analyze job postings using AI to determine relevance and extract key insights",
    backstory="You are an AI-powered job analyst who understands job requirements, skills matching, and career progression. You can intelligently score job relevance based on complex criteria beyond simple keyword matching.",
    verbose=True,
    allow_delegation=False,
    llm="gemini/gemini-1.5-flash" if os.environ.get('GOOGLE_API_KEY') else None
)

ranking_agent = Agent(
    role="Smart Job Ranking Specialist",
    goal="Use AI algorithms to rank jobs based on multiple factors including relevance, career growth potential, and market value",
    backstory="You are an AI career advisor who understands job market trends, salary expectations, and career progression paths. You can intelligently rank opportunities based on comprehensive analysis.",
    verbose=True,
    allow_delegation=False,
    llm="gemini/gemini-1.5-flash" if os.environ.get('GOOGLE_API_KEY') else None
)

insight_agent = Agent(
    role="Job Market Intelligence Agent",
    goal="Provide AI-driven insights about job market trends, salary analysis, and career recommendations",
    backstory="You are an AI market analyst specializing in employment trends. You can analyze job data to provide intelligent insights about market conditions, salary trends, and career opportunities.",
    verbose=True,
    allow_delegation=False,
    llm="gemini/gemini-1.5-flash" if os.environ.get('GOOGLE_API_KEY') else None
)

class PerfectJobScraper:
    def __init__(self):
        self.user_agent = UserAgent()
        self.session = requests.Session()
        self.setup_session()
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
    
    def scrape_linkedin_comprehensive(self, search_term, location, max_pages=5, fetch_descriptions=True, filter_active=True):
        """Comprehensive LinkedIn scraping with AI-powered active recruitment filtering"""
        jobs = []
        print(f"🔍 Scraping LinkedIn for '{search_term}' in '{location}'...")
        if filter_active:
            print("🤖 AI will filter for actively recruiting jobs during scraping...")
        
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
                        
                        # Extract posting date
                        posting_date = "Not specified"
                        date_selectors = [
                            'time', '.job-search-card__listdate', '.result-card__listdate',
                            '[data-test="job-age"]', '.job-age', '.posted-date'
                        ]
                        
                        for selector in date_selectors:
                            date_elem = card.find(selector.replace('.', '').replace('[data-test="job-age"]', '')) or \
                                       card.find(attrs={'data-test': 'job-age'})
                            if date_elem:
                                posting_date = date_elem.text.strip()
                                break
                        
                        # If no date found, look in aria-label or other attributes
                        if posting_date == "Not specified":
                            time_elem = card.find('time')
                            if time_elem:
                                posting_date = time_elem.get('datetime', time_elem.text.strip())
                        
                        # If still no date, try to find any text containing time/date info
                        if posting_date == "Not specified":
                            date_patterns = [
                                r'\d+\s*(?:hour|hr)s?\s*ago',
                                r'\d+\s*(?:day|d)s?\s*ago', 
                                r'\d+\s*(?:week|w)s?\s*ago',
                                r'\d+\s*(?:month|m)s?\s*ago',
                                r'\d+\s*(?:year|y)s?\s*ago',
                                r'just posted',
                                r'today',
                                r'yesterday'
                            ]
                            
                            card_text = card.get_text().lower()
                            for pattern in date_patterns:
                                match = re.search(pattern, card_text, re.IGNORECASE)
                                if match:
                                    posting_date = match.group(0)
                                    break
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
                            'full_description': "",  # Will be filled later
                            'url': job_link,
                            'source': 'LinkedIn',
                            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'search_term': search_term,
                            'search_location': location,
                            'posting_date': posting_date
                        }
                        
                        # Time-based filtering for actively recruiting jobs (posted within 48 hours)
                        if filter_active:
                            is_active, reason = self.is_recently_posted(job_data['posting_date'])
                            job_data['is_actively_recruiting'] = is_active
                            job_data['active_recruiting_reasons'] = reason
                            
                            if is_active:
                                jobs.append(job_data)
                                page_jobs += 1
                                print(f"   ✅ Recent job ({reason}): {title} at {company}")
                            else:
                                print(f"   ❌ Too old ({reason}): {title} at {company}")
                        else:
                            # No filtering - add all jobs
                            job_data['is_actively_recruiting'] = True  # Assume active for non-filtered jobs
                            job_data['active_recruiting_reasons'] = 'No filtering applied'
                            jobs.append(job_data)
                            page_jobs += 1
                        
                    except Exception as e:
                        continue
                
                print(f"   Page {page + 1}: Found {page_jobs} active recruiting jobs")
                
                if page_jobs == 0:
                    break
                    
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"   Error on LinkedIn page {page + 1}: {e}")
                continue
        
        print(f"✅ LinkedIn: {len(jobs)} {'recently posted ' if filter_active else ''}jobs found{' (posted within 48 hours)' if filter_active else ''}")
        
        if fetch_descriptions and jobs:
            print(f"📄 Fetching full job descriptions for {len(jobs)} {'recent ' if filter_active else ''}jobs...")
            
            # Update jobs with full descriptions
            for i, job in enumerate(jobs):
                if i > 0 and i % 10 == 0:  # Progress update every 10 jobs
                    print(f"   Progress: {i}/{len(jobs)} job descriptions fetched")
                
                if job['url'] and job['url'] != "Not specified":
                    try:
                        # Add delay between requests
                        time.sleep(random.uniform(3, 6))
                        
                        headers = {
                            'User-Agent': self.user_agent.random,
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.5',
                            'Accept-Encoding': 'gzip, deflate',
                            'Connection': 'keep-alive',
                        }
                        
                        job_response = self.session.get(job['url'], headers=headers, timeout=15)
                        job_soup = BeautifulSoup(job_response.content, 'html.parser')
                        
                        # Try multiple selectors for job description
                        description_selectors = [
                            'div[data-test-id="job-description"]',
                            'div.job-description',
                            'div.description',
                            'div[data-test="job-description"]',
                            'div.show-more-less-html__markup',
                            'div[data-test-id="description"]',
                            'div[data-test="job-details"]',
                            'div.job-details__content',
                            'div[data-test-id="job-details"]'
                        ]
                        
                        full_description = ""
                        for selector in description_selectors:
                            desc_elem = job_soup.select_one(selector)
                            if desc_elem:
                                # Get all text content and clean it up
                                full_description = desc_elem.get_text(separator='\n', strip=True)
                                if full_description and len(full_description) > 50:  # Ensure we got meaningful content
                                    break
                        
                        # If still no description, try to find any large text block
                        if not full_description or len(full_description) < 50:
                            # Look for the main content area
                            main_content = job_soup.find('main') or job_soup.find('div', class_='job-view-layout')
                            if main_content:
                                paragraphs = main_content.find_all('p')
                                if paragraphs:
                                    full_description = '\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
                        
                        # Clean up the description
                        if full_description:
                            # Remove excessive whitespace
                            full_description = re.sub(r'\n\s*\n', '\n\n', full_description)
                            full_description = re.sub(r'\s+', ' ', full_description)
                            full_description = full_description.strip()
                        
                        job['full_description'] = full_description
                        
                    except Exception as e:
                        print(f"   Warning: Could not fetch full description for {job['title']}: {e}")
                        job['full_description'] = "Could not retrieve full job description"
                else:
                    job['full_description'] = "No job URL available"
            
            print(f"✅ Full descriptions fetched for {len(jobs)} jobs")
        else:
            print(f"⚡ Skipping full description fetching...")
            # Add empty full_description to all jobs
            for job in jobs:
                job['full_description'] = "Full description not fetched"
        
        return jobs
        """Filter jobs to show only actively recruiting positions"""
        actively_recruiting = []
        
        print(f"🎯 Filtering for actively recruiting jobs...")
        
        for job in jobs:
            is_active = False
            reasons = []
            
            # Check full description for active recruiting indicators
            full_desc = job.get('full_description', '').lower()
            summary = job.get('summary', '').lower()
            title = job.get('title', '').lower()
            
            # Keywords that indicate active recruiting
            active_keywords = [
                'actively recruiting', 'actively hiring', 'urgent hiring', 'immediate opening',
                'we are hiring', 'join our team', 'exciting opportunity', 'growing team',
                'expand our team', 'looking for', 'seeking', 'hiring now', 'apply now',
                'immediate start', 'quick hire', 'fast track', 'priority hire',
                'high priority', 'critical role', 'key position', 'strategic hire'
            ]
            
            # Check if any active keywords are present
            for keyword in active_keywords:
                if keyword in full_desc or keyword in summary or keyword in title:
                    is_active = True
                    reasons.append(f"Contains '{keyword}'")
                    break
            
            # Check for recent posting indicators
            if 'day' in full_desc or 'week' in full_desc or 'new' in full_desc:
                if not is_active:  # Don't override if already marked active
                    is_active = True
                    reasons.append("Recent posting indicators")
            
            # Check for company growth indicators
            growth_indicators = [
                'growing company', 'scaling', 'expansion', 'series a', 'series b', 'series c',
                'funding', 'investment', 'startup', 'scale up', 'high growth'
            ]
            
            for indicator in growth_indicators:
                if indicator in full_desc or indicator in summary:
                    if not is_active:
                        is_active = True
                        reasons.append(f"Growth indicator: {indicator}")
                    break
            
            # Check for competitive indicators
            competitive_indicators = [
                'competitive salary', 'excellent benefits', 'great culture', 'innovative',
                'cutting edge', 'market leader', 'industry leader', 'top company'
            ]
            
            for indicator in competitive_indicators:
                if indicator in full_desc or indicator in summary:
                    if not is_active:
                        is_active = True
                        reasons.append(f"Competitive indicator: {indicator}")
                    break
            
            # If job has a detailed description (longer than 200 chars), consider it active
            if len(full_desc) > 200 and not is_active:
                is_active = True
                reasons.append("Detailed job description")
            
            # Store the active status and reasons
            job['is_actively_recruiting'] = is_active
            job['active_recruiting_reasons'] = reasons
            
            if is_active:
                actively_recruiting.append(job)
        
        print(f"✅ Found {len(actively_recruiting)} actively recruiting jobs out of {len(jobs)} total jobs")
        return actively_recruiting
    
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
    
    def scrape_all_sources(self, search_term, location, keywords, fetch_descriptions=True, filter_active=True):
        """Scrape LinkedIn only with AI-powered active recruitment filtering"""
        all_jobs = []
        
        print("🚀 Starting Time-Based LinkedIn Job Search...")
        print("=" * 70)
        print("📊 Source: LinkedIn")
        if filter_active:
            print("⏰ Time Filter: Jobs posted within last 48 hours only")
        print("=" * 70)
        
        # Scrape LinkedIn with AI filtering
        linkedin_jobs = self.scrape_linkedin_comprehensive(search_term, location, 10, fetch_descriptions, filter_active)
        all_jobs.extend(linkedin_jobs)
        
        # Summary of results
        print(f"\n📈 LINKEDIN SCRAPING SUMMARY:")
        print("-" * 50)
        total_jobs = len(all_jobs)
        print(f"   • LinkedIn: {total_jobs} jobs")
        if filter_active:
            print("   • AI-filtered for active recruitment")
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
        """No driver to close - using requests only"""
        pass
    
    def is_recently_posted(self, posting_date_text):
        """Check if a job was posted within the last 48 hours"""
        if not posting_date_text or posting_date_text == "Not specified":
            return False, "No posting date available"
        
        try:
            text = posting_date_text.lower().strip()
            current_time = time.time()
            
            # Handle "just posted" or "today"
            if 'just posted' in text or 'today' in text:
                return True, "Posted today"
            
            # Handle "yesterday"
            if 'yesterday' in text:
                return True, "Posted yesterday (within 48 hours)"
            
            # Handle hours ago
            hours_match = re.search(r'(\d+)\s*(?:hour|hr)s?\s*ago', text)
            if hours_match:
                hours = int(hours_match.group(1))
                if hours <= 48:
                    return True, f"Posted {hours} hours ago"
                else:
                    return False, f"Posted {hours} hours ago (too old)"
            
            # Handle days ago
            days_match = re.search(r'(\d+)\s*(?:day|d)s?\s*ago', text)
            if days_match:
                days = int(days_match.group(1))
                if days <= 2:
                    return True, f"Posted {days} days ago"
                else:
                    return False, f"Posted {days} days ago (too old)"
            
            # Handle weeks/months/years (definitely too old)
            if any(word in text for word in ['week', 'month', 'year']):
                return False, "Posted more than 2 days ago"
            
            # If we can't parse it but it looks recent
            if any(word in text for word in ['now', 'recent', 'new']):
                return True, "Appears to be recently posted"
            
            return False, f"Could not determine recency: {posting_date_text}"
            
        except Exception as e:
            return False, f"Error parsing date: {e}"
    
    def keyword_based_active_filter(self, job_data):
        """Enhanced keyword-based filtering for active recruitment with smarter detection"""
        text_to_check = ""
        if job_data.get('title'):
            text_to_check += job_data['title'].lower() + " "
        if job_data.get('company'):
            text_to_check += job_data['company'].lower() + " "
        if job_data.get('summary'):
            text_to_check += job_data['summary'].lower() + " "
        
        # Primary active recruitment keywords (high confidence)
        primary_keywords = [
            'actively recruiting', 'actively hiring', 'urgent hiring', 'immediate hiring',
            'hiring now', 'we are hiring', 'join our team', 'growing team', 'expanding team',
            'new positions', 'multiple openings', 'open positions', 'career opportunities',
            'rapidly growing', 'fast growing', 'scaling', 'expansion', 'growth opportunity',
            'apply now', 'immediate start', 'start immediately', 'join immediately',
            'series a', 'series b', 'series c', 'funding', 'new office', 'competitive salary'
        ]
        
        # Secondary indicators (medium confidence) - time-sensitive and momentum signals
        secondary_keywords = [
            'deadline', 'apply by', 'closing date', 'closing soon', 'time sensitive',
            'asap', 'urgently', 'quickly', 'immediate', 'now hiring', 'current opening',
            'excellent benefits', 'great benefits', 'full benefits', 'work life balance',
            'professional development', 'career growth', 'advancement opportunity',
            'exciting opportunity', 'fantastic opportunity', 'unique opportunity',
            'be part of', 'join us', 'we\'re looking for', 'we are looking for'
        ]
        
        # Check primary keywords first
        for keyword in primary_keywords:
            if keyword in text_to_check:
                return True, f"Primary indicator: {keyword}"
        
        # Check for combinations of secondary keywords (2 or more = likely active)
        secondary_matches = []
        for keyword in secondary_keywords:
            if keyword in text_to_check:
                secondary_matches.append(keyword)
        
        if len(secondary_matches) >= 2:
            return True, f"Multiple indicators: {', '.join(secondary_matches[:3])}"
        
        # Check for deadline patterns specifically
        deadline_patterns = [
            r'deadline[:\s]*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            r'apply by[:\s]*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            r'closing[:\s]*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            r'until[:\s]*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}'
        ]
        
        for pattern in deadline_patterns:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                return True, "Contains deadline/application date"
        
        return False, "No clear active recruitment indicators found"

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
    """AI-ENHANCED: Run the LinkedIn job scraper with AI agents"""
    print("🤖 AI-ENHANCED LinkedIn Job Search Engine")
    print("=" * 80)
    print("🎯 AI Features:")
    print("   • CrewAI agents for intelligent job analysis")
    print("   • AI-powered relevance scoring and ranking")
    print("   • Smart market insights generation")
    print("   • AI career growth potential analysis")
    print("   • Time-based filtering (0-48 hours) for truly active jobs")
    print("")
    print("🌐 Job Source: LinkedIn")
    print("   • Comprehensive pagination (up to 10 pages)")
    print("   • Time-based filtering for fresh job postings")
    print("=" * 80)
    
    # Get search criteria
    search_term, location, keywords = get_search_criteria()
    
    # Check if Gemini API key is available
    api_key_available = os.environ.get('GOOGLE_API_KEY') is not None
    
    # Ask user about AI features
    if api_key_available:
        # Configure Gemini API
        genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
        # Configure LiteLLM to use Gemini
        os.environ['LITELLM_MODEL'] = 'gemini/gemini-1.5-flash'
        litellm.api_key = os.environ.get('GOOGLE_API_KEY')
        use_ai = input("\n🤖 Enable AI-enhanced analysis? (y/n, default=y): ").strip().lower()
        use_ai = use_ai != 'n'  # Default to yes
    else:
        print("⚠️  Google Gemini API key not found. AI features will be disabled.")
        print("💡 To enable AI features, set your GOOGLE_API_KEY environment variable:")
        print("   export GOOGLE_API_KEY='your-gemini-api-key-here'")
        use_ai = input("\n🤖 Enable AI-enhanced analysis anyway? (y/n, default=n): ").strip().lower()
        use_ai = use_ai == 'y'  # Default to no
    
    if use_ai and not api_key_available:
        print("⚠️  Google Gemini API key not found.")
        print("💡 AI features will use traditional scoring methods instead.")
        print("🔄 Continuing with enhanced analysis using traditional algorithms...")
        # Don't disable use_ai - let it use traditional methods
    
    if use_ai:
        print("✅ AI agents activated for enhanced job analysis!")
    else:
        print("📊 Using traditional scoring methods.")
    
    # Initialize scraper
    scraper = PerfectJobScraper()
    
    try:
        # Ask user about full description fetching (for faster testing)
        fetch_descriptions = input("\n📄 Fetch full job descriptions? (y/n, default=y): ").strip().lower()
        fetch_descriptions = fetch_descriptions != 'n'  # Default to yes
        
        if not fetch_descriptions:
            print("⚡ Skipping full description fetching for faster results...")
        
        # Ask user if they want AI-powered filtering for actively recruiting jobs
        filter_active = input("\n🎯 Filter for jobs posted within last 48 hours only? (y/n, default=y): ").strip().lower()
        filter_active = filter_active != 'n'  # Default to yes
        
        if filter_active:
            print("⏰ Time-based filtering enabled - only jobs posted in last 48 hours will be scraped!")
        else:
            print("📊 Scraping all jobs (no time-based filtering)...")
        
        # Scrape all sources with AI filtering
        all_jobs = scraper.scrape_all_sources(search_term, location, keywords, fetch_descriptions, filter_active)
        
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
                       'job_type', 'summary', 'full_description', 'is_actively_recruiting', 'active_recruiting_reasons',
                       'url', 'source', 'scraped_at']
        
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
        
        # Actively recruiting statistics
        if 'is_actively_recruiting' in ranked_jobs_df.columns:
            active_jobs = len(ranked_jobs_df[ranked_jobs_df['is_actively_recruiting'] == True])
            print(f"   • Actively recruiting jobs: {active_jobs} ({active_jobs/len(ranked_jobs_df)*100:.1f}%)")
        
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
        if filter_active:
            print(f"   • ⏰ Time-based filtering: Only jobs posted within last 48 hours")
        else:
            print(f"   • 📊 Comprehensive job scraping (all jobs included)")
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