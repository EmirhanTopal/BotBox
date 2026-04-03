import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import logging
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AcibademDualScraper:
    """
    Dual scraper for Acibadem University data:
    - Static content via BeautifulSoup
    - Dynamic content via Selenium
    """
    
    def __init__(self, use_headless=True):
        self.static_url = "https://www.acibadem.edu.tr/en"
        self.dynamic_url = "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.use_headless = use_headless
        self.driver = None
        self.all_data = {
            'static_content': {
                'general_info': {},
                'departments': [],
                'programs': [],
                'admissions': {},
                'contact_info': {},
                'campus_facilities': [],
                'pages': []
            },
            'dynamic_content': {
                'programs': [],
                'courses': [],
                'curriculum': [],
                'requirements': []
            },
            'merged_data': {
                'all_programs': [],
                'all_courses': [],
                'all_departments': []
            },
            'metadata': {
                'scrape_date': '',
                'sources': ['acibadem.edu.tr', 'obs.acibadem.edu.tr'],
                'static_success': False,
                'dynamic_success': False
            }
        }
    
    def init_selenium_driver(self):
        """Initialize Selenium WebDriver with Chrome"""
        try:
            chrome_options = Options()
            if self.use_headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Selenium WebDriver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            return False
    
    def close_selenium_driver(self):
        """Close Selenium WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("Selenium WebDriver closed")
    
    # ===================== STATIC CONTENT SCRAPING =====================
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse webpage"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def scrape_static_homepage(self) -> Dict:
        """Extract general university information"""
        soup = self.fetch_page(self.static_url)
        if not soup:
            return {}
        
        data = {
            'title': soup.title.string if soup.title else '',
            'meta_description': '',
            'hero_text': '',
            'mission': '',
            'vision': '',
            'founded_year': '',
            'campuses': []
        }
        
        meta = soup.find('meta', {'name': 'description'})
        if meta:
            data['meta_description'] = meta.get('content', '')
        
        # Find mission/vision sections
        for section in soup.find_all(['section', 'div'], {'class': ['mission', 'vision', 'about']}):
            text = section.get_text(strip=True)
            if 'mission' in section.get('class', []):
                data['mission'] = text
            elif 'vision' in section.get('class', []):
                data['vision'] = text
        
        return data
    
    def scrape_static_departments(self) -> List[Dict]:
        """Extract departments from static site"""
        soup = self.fetch_page(urljoin(self.static_url, '/academics'))
        if not soup:
            return []
        
        departments = []
        dept_containers = soup.find_all(['div', 'article'], {'class': ['department', 'faculty']})
        
        for dept in dept_containers:
            dept_data = {
                'name': '',
                'description': '',
                'link': '',
                'email': '',
                'phone': '',
                'source': 'acibadem.edu.tr'
            }
            
            name_elem = dept.find(['h2', 'h3', 'h4'])
            if name_elem:
                dept_data['name'] = name_elem.get_text(strip=True)
            
            desc_elem = dept.find(['p', 'div'], {'class': 'description'})
            if desc_elem:
                dept_data['description'] = desc_elem.get_text(strip=True)
            
            link_elem = dept.find('a')
            if link_elem and link_elem.get('href'):
                dept_data['link'] = urljoin(self.static_url, link_elem.get('href'))
            
            if dept_data['name']:
                departments.append(dept_data)
                time.sleep(0.3)
        
        return departments
    
    def scrape_static_programs(self) -> List[Dict]:
        """Extract programs from static site"""
        soup = self.fetch_page(urljoin(self.static_url, '/programs'))
        if not soup:
            return []
        
        programs = []
        prog_containers = soup.find_all(['div', 'article'], {'class': ['program', 'degree']})
        
        for prog in prog_containers:
            prog_data = {
                'name': '',
                'level': '',
                'duration': '',
                'department': '',
                'language': '',
                'tuition': '',
                'source': 'acibadem.edu.tr'
            }
            
            name_elem = prog.find(['h3', 'h4'])
            if name_elem:
                prog_data['name'] = name_elem.get_text(strip=True)
            
            level_elem = prog.find(['span', 'p'], {'class': ['level', 'degree-type']})
            if level_elem:
                prog_data['level'] = level_elem.get_text(strip=True)
            
            if prog_data['name']:
                programs.append(prog_data)
                time.sleep(0.3)
        
        return programs
    
    def scrape_static_contact(self) -> Dict:
        """Extract contact information"""
        soup = self.fetch_page(urljoin(self.static_url, '/contact'))
        if not soup:
            return {}
        
        contact_data = {
            'main_phone': '',
            'main_email': '',
            'addresses': [],
            'social_media': {},
            'source': 'acibadem.edu.tr'
        }
        
        phone_elem = soup.find(['a', 'span'], {'class': 'phone'})
        if phone_elem:
            contact_data['main_phone'] = phone_elem.get_text(strip=True)
        
        email_elem = soup.find(['a', 'span'], string=lambda x: x and '@' in x)
        if email_elem:
            contact_data['main_email'] = email_elem.get_text(strip=True)
        
        for addr in soup.find_all(['div', 'p'], {'class': 'address'}):
            contact_data['addresses'].append(addr.get_text(strip=True))
        
        return contact_data
    
    # ===================== DYNAMIC CONTENT SCRAPING =====================
    
    def scrape_dynamic_obs_programs(self) -> List[Dict]:
        """
        Scrape OBS (Student Information System) for programs
        OBS uses JavaScript extensively, requires Selenium
        """
        if not self.driver:
            logger.error("Selenium driver not initialized")
            return []
        
        programs = []
        try:
            # Navigate to OBS
            self.driver.get(self.dynamic_url)
            
            # Wait for main content to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "program"))
            )
            
            # Get rendered page source
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract program data
            prog_elements = soup.find_all(['tr', 'div'], {'class': ['program', 'course-item']})
            
            for elem in prog_elements:
                prog_data = {
                    'code': '',
                    'name': '',
                    'credits': '',
                    'semester': '',
                    'type': '',
                    'prerequisite': '',
                    'source': 'obs.acibadem.edu.tr'
                }
                
                # Extract code (usually first column)
                code_elem = elem.find(['td', 'span'], string=lambda x: x and len(str(x)) < 10)
                if code_elem:
                    prog_data['code'] = code_elem.get_text(strip=True)
                
                # Extract name
                name_elem = elem.find(['td', 'span', 'a'])
                if name_elem:
                    prog_data['name'] = name_elem.get_text(strip=True)
                
                # Extract credits
                credits_elem = elem.find(['td', 'span'], string=lambda x: x and any(char.isdigit() for char in str(x)))
                if credits_elem:
                    prog_data['credits'] = credits_elem.get_text(strip=True)
                
                if prog_data['name']:
                    programs.append(prog_data)
            
            logger.info(f"Extracted {len(programs)} programs from OBS")
            return programs
            
        except Exception as e:
            logger.error(f"Error scraping OBS programs: {e}")
            return []
    
    def scrape_dynamic_obs_courses(self) -> List[Dict]:
        """
        Scrape course information from OBS
        May require clicking through dropdown menus
        """
        if not self.driver:
            return []
        
        courses = []
        try:
            # Navigate to courses section
            self.driver.get(urljoin(self.dynamic_url, "?lang=tr&curOp=showPac"))
            
            # Wait for AJAX loading
            time.sleep(3)
            
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
            )
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find course tables
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        course_data = {
                            'code': cols[0].get_text(strip=True),
                            'name': cols[1].get_text(strip=True),
                            'credits': cols[2].get_text(strip=True) if len(cols) > 2 else '',
                            'type': cols[3].get_text(strip=True) if len(cols) > 3 else '',
                            'source': 'obs.acibadem.edu.tr'
                        }
                        
                        if course_data['name']:
                            courses.append(course_data)
            
            logger.info(f"Extracted {len(courses)} courses from OBS")
            return courses
            
        except Exception as e:
            logger.error(f"Error scraping OBS courses: {e}")
            return []
    
    # ===================== DATA MERGING & DEDUPLICATION =====================
    
    def merge_and_deduplicate(self) -> Dict:
        """Merge data from both sources and remove duplicates"""
        merged = {
            'all_programs': [],
            'all_departments': [],
            'complete_info': []
        }
        
        # Merge programs
        seen_programs = set()
        for prog in self.all_data['static_content']['programs']:
            prog_key = prog['name'].lower()
            if prog_key not in seen_programs:
                seen_programs.add(prog_key)
                merged['all_programs'].append(prog)
        
        for prog in self.all_data['dynamic_content']['programs']:
            prog_key = prog.get('name', '').lower()
            if prog_key not in seen_programs:
                seen_programs.add(prog_key)
                merged['all_programs'].append(prog)
        
        # Merge departments
        seen_depts = set()
        for dept in self.all_data['static_content']['departments']:
            dept_key = dept['name'].lower()
            if dept_key not in seen_depts:
                seen_depts.add(dept_key)
                merged['all_departments'].append(dept)
        
        self.all_data['merged_data'] = merged
        logger.info(f"Merged: {len(merged['all_programs'])} programs, {len(merged['all_departments'])} departments")
        
        return merged
    
    def scrape_all(self) -> Dict:
        """Execute full dual-source scraping"""
        logger.info("=" * 60)
        logger.info("Starting comprehensive dual-source scrape...")
        logger.info("=" * 60)
        
        # Static content
        logger.info("\n[1/4] Scraping static content (acibadem.edu.tr)...")
        self.all_data['static_content']['general_info'] = self.scrape_static_homepage()
        self.all_data['static_content']['departments'] = self.scrape_static_departments()
        self.all_data['static_content']['programs'] = self.scrape_static_programs()
        self.all_data['static_content']['contact_info'] = self.scrape_static_contact()
        self.all_data['metadata']['static_success'] = True
        logger.info("✓ Static content scraped")
        
        # Dynamic content
        logger.info("\n[2/4] Initializing Selenium for dynamic content...")
        if self.init_selenium_driver():
            logger.info("[3/4] Scraping dynamic content (obs.acibadem.edu.tr)...")
            self.all_data['dynamic_content']['programs'] = self.scrape_dynamic_obs_programs()
            self.all_data['dynamic_content']['courses'] = self.scrape_dynamic_obs_courses()
            self.all_data['metadata']['dynamic_success'] = True
            self.close_selenium_driver()
            logger.info("✓ Dynamic content scraped")
        else:
            logger.warning("⚠ Selenium initialization failed, skipping dynamic content")
        
        # Merge data
        logger.info("\n[4/4] Merging and deduplicating data...")
        self.merge_and_deduplicate()
        logger.info("✓ Data merged")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("SCRAPING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Static departments: {len(self.all_data['static_content']['departments'])}")
        logger.info(f"Static programs: {len(self.all_data['static_content']['programs'])}")
        logger.info(f"Dynamic programs: {len(self.all_data['dynamic_content']['programs'])}")
        logger.info(f"Dynamic courses: {len(self.all_data['dynamic_content']['courses'])}")
        logger.info(f"Merged programs: {len(self.all_data['merged_data']['all_programs'])}")
        logger.info(f"Merged departments: {len(self.all_data['merged_data']['all_departments'])}")
        logger.info("=" * 60 + "\n")
        
        return self.all_data
    
    def save_to_json(self, filename: str = 'acibadem_complete_data.json'):
        """Save all scraped data to JSON"""
        from datetime import datetime
        self.all_data['metadata']['scrape_date'] = datetime.now().isoformat()
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.all_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Data saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            return False