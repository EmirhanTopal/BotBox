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

    # ── Gerçek URL'ler (search ile doğrulandı) ──────────────────────────
    URLS = {
        'home':         'https://www.acibadem.edu.tr/en',
        'academic_structure': 'https://www.acibadem.edu.tr/en/university/instructors-handbook/university-structure-and-management/academic-structure',
        'undergrad_programs': 'https://www.acibadem.edu.tr/en/international-office/international-students/programs/undergraduate',
        'contact':      'https://www.acibadem.edu.tr/en/university/about/administrative-departments',
        'admissions':   'https://www.acibadem.edu.tr/en/prospective-students',
        'obs':          'https://obs.acibadem.edu.tr/oibs/bologna/index.aspx',
    }

    # Fakülteler — scrape başarısız olursa bu statik liste fallback olarak kullanılır
    KNOWN_FACULTIES = [
        'School of Medicine',
        'Faculty of Pharmacy',
        'Faculty of Health Sciences',
        'Faculty of Arts and Sciences',
        'Faculty of Engineering and Natural Sciences',
    ]

    def __init__(self, use_headless=True):
        self.static_url = self.URLS['home']
        self.dynamic_url = self.URLS['obs']
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
            chrome_options.add_argument(
                'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Selenium WebDriver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            return False

    def close_selenium_driver(self):
        if self.driver:
            self.driver.quit()
            logger.info("Selenium WebDriver closed")

    # ===================== STATIC CONTENT SCRAPING =====================

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def scrape_static_homepage(self) -> Dict:
        """Extract general university information from homepage"""
        soup = self.fetch_page(self.URLS['home'])
        if not soup:
            return {}

        data = {
            'title': soup.title.string.strip() if soup.title else '',
            'meta_description': '',
            'hero_text': '',
            'mission': '',
            'vision': '',
            'founded_year': '2007',
            'campuses': ['Kerem Aydınlar Campus (Ataşehir, Istanbul)']
        }

        meta = soup.find('meta', {'name': 'description'})
        if meta:
            data['meta_description'] = meta.get('content', '')

        # Ana içerik bloklarından metin topla
        for tag in soup.find_all(['p', 'div', 'section']):
            text = tag.get_text(separator=' ', strip=True)
            if 'mission' in text.lower() and not data['mission']:
                data['mission'] = text[:500]
            if 'vision' in text.lower() and not data['vision']:
                data['vision'] = text[:500]

        # Hero/banner alanı
        hero = soup.find(['section', 'div'], {'class': lambda c: c and any(
            x in ' '.join(c) for x in ['hero', 'banner', 'slider', 'intro']
        )})
        if hero:
            data['hero_text'] = hero.get_text(separator=' ', strip=True)[:1000]

        return data

    def scrape_static_departments(self) -> List[Dict]:
        """
        Fakülteleri academic-structure sayfasından çek.
        Sayfa class tabanlı değil, metin içeriği ile dolu — tüm metin parse edilir.
        """
        soup = self.fetch_page(self.URLS['academic_structure'])
        departments = []

        if soup:
            # Sayfa içindeki tüm başlıkları ve paragrafları tara
            content_area = soup.find('main') or soup.find('div', {'class': lambda c: c and 'content' in ' '.join(c)}) or soup
            headings = content_area.find_all(['h1', 'h2', 'h3', 'h4'])

            for h in headings:
                text = h.get_text(strip=True)
                if len(text) > 5:  # Çok kısa başlıkları atla
                    desc_elem = h.find_next_sibling(['p', 'ul', 'div'])
                    desc = desc_elem.get_text(strip=True)[:300] if desc_elem else ''
                    link_elem = h.find('a') or h.find_next('a')
                    link = urljoin(self.URLS['home'], link_elem['href']) if link_elem and link_elem.get('href') else ''

                    departments.append({
                        'name': text,
                        'description': desc,
                        'link': link,
                        'email': '',
                        'phone': '',
                        'source': 'acibadem.edu.tr'
                    })

        # Sayfa boş geldiyse bilinen fakülteleri fallback olarak ekle
        if not departments:
            logger.warning("academic-structure sayfası boş geldi, statik liste kullanılıyor")
            for fac in self.KNOWN_FACULTIES:
                departments.append({
                    'name': fac,
                    'description': '',
                    'link': '',
                    'email': '',
                    'phone': '',
                    'source': 'acibadem.edu.tr'
                })

        return departments

    def scrape_static_programs(self) -> List[Dict]:
        """
        Lisans programlarını çek.
        Sayfa JavaScript ile render edilebilir; BeautifulSoup ile ulaşılabilecek
        tüm liste/kart elementleri taranır.
        """
        soup = self.fetch_page(self.URLS['undergrad_programs'])
        programs = []

        if soup:
            # <li>, <a>, <div> içinde program adı olabilir
            for elem in soup.find_all(['li', 'div', 'article']):
                # Çok uzun ya da çok kısa içerikleri atla
                text = elem.get_text(strip=True)
                if not (10 < len(text) < 200):
                    continue

                link_elem = elem.find('a')
                link = urljoin(self.URLS['home'], link_elem['href']) if link_elem and link_elem.get('href') else ''

                # Sadece program gibi görünen satırları ekle (içinde "program" veya bilinen kelimeler)
                keywords = ['medicine', 'pharmacy', 'nursing', 'engineering', 'psychology',
                            'nutrition', 'physiotherapy', 'management', 'biology', 'genetics']
                if any(kw in text.lower() for kw in keywords):
                    programs.append({
                        'name': text[:150],
                        'level': 'Undergraduate',
                        'duration': '',
                        'department': '',
                        'language': '',
                        'tuition': '',
                        'link': link,
                        'source': 'acibadem.edu.tr/undergrad-programs'
                    })

        logger.info(f"Static programs found: {len(programs)}")
        return programs

    def scrape_static_contact(self) -> Dict:
        """İdari birimler sayfasından iletişim bilgilerini çek"""
        soup = self.fetch_page(self.URLS['contact'])
        contact_data = {
            'main_phone': '+90 216 500 44 44',   # Sitede görünen ana numara
            'main_email': 'ik@acibadem.edu.tr',
            'addresses': ['Kayışdağı Cd. No:32, Ataşehir, İstanbul'],
            'social_media': {},
            'departments_contact': [],
            'source': 'acibadem.edu.tr'
        }

        if not soup:
            return contact_data

        # Telefon numaralarını bul (0216 veya +90 ile başlayanlar)
        import re
        phones = re.findall(r'(?:\+90|0)\s?[\d\s\-]{10,15}', soup.get_text())
        if phones:
            contact_data['main_phone'] = phones[0].strip()

        # E-posta adreslerini bul
        emails = re.findall(r'[\w\.\-]+@acibadem\.edu\.tr', soup.get_text())
        if emails:
            contact_data['main_email'] = emails[0]

        # Tüm departman iletişim satırlarını topla
        for row in soup.find_all(['tr', 'li', 'div', 'p']):
            text = row.get_text(separator=' ', strip=True)
            if '@acibadem.edu.tr' in text or '0216 500' in text:
                contact_data['departments_contact'].append(text[:200])

        return contact_data

    # ===================== DYNAMIC CONTENT SCRAPING =====================

    def scrape_dynamic_obs_programs(self) -> List[Dict]:
        """OBS'den program listesini çek (Selenium)"""
        if not self.driver:
            logger.error("Selenium driver not initialized")
            return []

        programs = []
        try:
            self.driver.get(self.dynamic_url)
            time.sleep(4)  # AJAX yüklenmesi için bekle

            # Sayfa içindeki tüm tabloları ve linkleri tara
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # OBS'de program listesi genellikle <select> veya <table> içinde olur
            for select in soup.find_all('select'):
                for option in select.find_all('option'):
                    text = option.get_text(strip=True)
                    if len(text) > 3:
                        programs.append({
                            'code': option.get('value', ''),
                            'name': text,
                            'credits': '',
                            'semester': '',
                            'type': '',
                            'prerequisite': '',
                            'source': 'obs.acibadem.edu.tr'
                        })

            # Tablolardan da çek
            for table in soup.find_all('table'):
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        name = cols[1].get_text(strip=True) if len(cols) > 1 else cols[0].get_text(strip=True)
                        if name:
                            programs.append({
                                'code': cols[0].get_text(strip=True),
                                'name': name,
                                'credits': cols[2].get_text(strip=True) if len(cols) > 2 else '',
                                'semester': '',
                                'type': '',
                                'prerequisite': '',
                                'source': 'obs.acibadem.edu.tr'
                            })

            logger.info(f"Extracted {len(programs)} programs from OBS")
            return programs

        except Exception as e:
            logger.error(f"Error scraping OBS programs: {e}")
            return []

    def scrape_dynamic_obs_courses(self) -> List[Dict]:
        """OBS'den ders listesini çek"""
        if not self.driver:
            return []

        courses = []
        try:
            self.driver.get(f"{self.dynamic_url}?lang=tr&curOp=showPac")
            time.sleep(3)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            for table in soup.find_all('table'):
                rows = table.find_all('tr')[1:]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        course_data = {
                            'code':    cols[0].get_text(strip=True),
                            'name':    cols[1].get_text(strip=True),
                            'credits': cols[2].get_text(strip=True) if len(cols) > 2 else '',
                            'type':    cols[3].get_text(strip=True) if len(cols) > 3 else '',
                            'source':  'obs.acibadem.edu.tr'
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
        merged = {
            'all_programs': [],
            'all_departments': [],
            'complete_info': []
        }

        seen_programs: Set[str] = set()
        for prog in (self.all_data['static_content']['programs'] +
                     self.all_data['dynamic_content']['programs']):
            key = prog.get('name', '').lower().strip()
            if key and key not in seen_programs:
                seen_programs.add(key)
                merged['all_programs'].append(prog)

        seen_depts: Set[str] = set()
        for dept in self.all_data['static_content']['departments']:
            key = dept.get('name', '').lower().strip()
            if key and key not in seen_depts:
                seen_depts.add(key)
                merged['all_departments'].append(dept)

        self.all_data['merged_data'] = merged
        logger.info(f"Merged: {len(merged['all_programs'])} programs, {len(merged['all_departments'])} departments")
        return merged

    # ===================== MAIN SCRAPE =====================

    def scrape_all(self) -> Dict:
        logger.info("=" * 60)
        logger.info("Starting comprehensive dual-source scrape...")
        logger.info("=" * 60)

        logger.info("\n[1/4] Scraping static content (acibadem.edu.tr)...")
        self.all_data['static_content']['general_info'] = self.scrape_static_homepage()
        self.all_data['static_content']['departments']  = self.scrape_static_departments()
        self.all_data['static_content']['programs']     = self.scrape_static_programs()
        self.all_data['static_content']['contact_info'] = self.scrape_static_contact()
        self.all_data['metadata']['static_success'] = True
        logger.info("✓ Static content scraped")

        logger.info("\n[2/4] Initializing Selenium for dynamic content...")
        if self.init_selenium_driver():
            logger.info("[3/4] Scraping dynamic content (obs.acibadem.edu.tr)...")
            self.all_data['dynamic_content']['programs'] = self.scrape_dynamic_obs_programs()
            self.all_data['dynamic_content']['courses']  = self.scrape_dynamic_obs_courses()
            self.all_data['metadata']['dynamic_success'] = True
            self.close_selenium_driver()
            logger.info("✓ Dynamic content scraped")
        else:
            logger.warning("⚠ Selenium initialization failed, skipping dynamic content")

        logger.info("\n[4/4] Merging and deduplicating data...")
        self.merge_and_deduplicate()
        logger.info("✓ Data merged")

        logger.info("\n" + "=" * 60)
        logger.info("SCRAPING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Static departments : {len(self.all_data['static_content']['departments'])}")
        logger.info(f"Static programs    : {len(self.all_data['static_content']['programs'])}")
        logger.info(f"Dynamic programs   : {len(self.all_data['dynamic_content']['programs'])}")
        logger.info(f"Dynamic courses    : {len(self.all_data['dynamic_content']['courses'])}")
        logger.info(f"Merged programs    : {len(self.all_data['merged_data']['all_programs'])}")
        logger.info(f"Merged departments : {len(self.all_data['merged_data']['all_departments'])}")
        logger.info("=" * 60 + "\n")

        return self.all_data

    def save_to_json(self, filename: str = 'acibadem_complete_data.json'):
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