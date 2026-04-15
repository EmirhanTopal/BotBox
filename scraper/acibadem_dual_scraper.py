import json
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Browser, Page

logging.basicConfig(level=logging.INFO)
#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AcibademDualScraper:
    URLS = {
        "home": "https://www.acibadem.edu.tr/en",
        "academic_structure": "https://www.acibadem.edu.tr/en/university/instructors-handbook/university-structure-and-management/academic-structure",
        "undergrad_programs": "https://www.acibadem.edu.tr/en/international-office/international-students/programs/undergraduate",
        "contact": "https://www.acibadem.edu.tr/en/university/about/administrative-departments",
        "admissions": "https://www.acibadem.edu.tr/en/prospective-students",
        "obs": "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx",
        "obs_base": "https://obs.acibadem.edu.tr/oibs/bologna/",
    }

    OBS_UNIT_URLS = [
        "https://obs.acibadem.edu.tr/oibs/bologna/unitSelection.aspx?type=lis&lang=tr",
        "https://obs.acibadem.edu.tr/oibs/bologna/unitSelection.aspx?type=myo&lang=tr",
        "https://obs.acibadem.edu.tr/oibs/bologna/unitSelection.aspx?type=yls&lang=tr",
        "https://obs.acibadem.edu.tr/oibs/bologna/unitSelection.aspx?type=dok&lang=tr",
    ]

    KNOWN_FACULTIES = [
        "School of Medicine",
        "Faculty of Pharmacy",
        "Faculty of Health Sciences",
        "Faculty of Arts and Sciences",
        "Faculty of Engineering and Natural Sciences",
    ]

    def __init__(self, use_headless: bool = True):
        self.static_url = self.URLS["home"]
        self.dynamic_url = self.URLS["obs"]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.use_headless = use_headless
        
        # Playwright nesneleri
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

        self.all_data = {
            "static_content": {
                "general_info": {},
                "departments": [],
                "programs": [],
                "admissions": {},
                "contact_info": {},
                "campus_facilities": [],
                "pages": [],
            },
            "dynamic_content": {
                "programs": [],
                "courses": [],
                "curriculum": [],
                "requirements": [],
            },
            "merged_data": {
                "all_programs": [],
                "all_courses": [],
                "all_departments": [],
            },
            "metadata": {
                "scrape_date": "",
                "sources": ["acibadem.edu.tr", "obs.acibadem.edu.tr"],
                "static_success": False,
                "dynamic_success": False,
            },
        }

    # =========================================================
    # PLAYWRIGHT
    # =========================================================

    def init_playwright_driver(self) -> bool:
        """Initialize Playwright browser."""
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.use_headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            self._page = self._browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            # Playwright'ın kendi timeout'u
            self._page.set_default_timeout(30_000)  # ms
            logger.info("Playwright browser initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            return False

    def close_playwright_driver(self) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("Playwright browser closed")

    def _get_page_source(self, url: str, wait_seconds: int = 4) -> Optional[BeautifulSoup]:
        """Playwright ile sayfaya git, HTML'i al, BeautifulSoup döndür."""
        if not self._page:
            return None
        try:
            self._page.goto(url, wait_until="networkidle")
            # networkidle çoğu zaman yeterli, ama JS-heavy sayfalarda biraz daha bekle
            if wait_seconds > 0:
                self._page.wait_for_timeout(wait_seconds * 1000)
            return BeautifulSoup(self._page.content(), "html.parser")
        except Exception as e:
            logger.error(f"Playwright failed to load {url}: {e}")
            return None

    # =========================================================
    # STATIC (değişmedi)
    # =========================================================

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def scrape_static_homepage(self) -> Dict:
        soup = self.fetch_page(self.URLS["home"])
        if not soup:
            return {}

        data = {
            "title": soup.title.string.strip() if soup.title else "",
            "meta_description": "",
            "hero_text": "",
            "mission": "",
            "vision": "",
            "founded_year": "2007",
            "campuses": ["Kerem Aydınlar Campus (Ataşehir, Istanbul)"],
        }

        meta = soup.find("meta", {"name": "description"})
        if meta:
            data["meta_description"] = meta.get("content", "")

        for tag in soup.find_all(["p", "div", "section"]):
            text = tag.get_text(separator=" ", strip=True)
            if "mission" in text.lower() and not data["mission"]:
                data["mission"] = text[:500]
            if "vision" in text.lower() and not data["vision"]:
                data["vision"] = text[:500]

        hero = soup.find(
            ["section", "div"],
            {"class": lambda c: c and any(x in " ".join(c) for x in ["hero", "banner", "slider", "intro"])},
        )
        if hero:
            data["hero_text"] = hero.get_text(separator=" ", strip=True)[:1000]

        return data

    def scrape_static_departments(self) -> List[Dict]:
        soup = self.fetch_page(self.URLS["academic_structure"])
        departments = []

        if soup:
            content_area = (
                soup.find("main")
                or soup.find("div", {"class": lambda c: c and "content" in " ".join(c)})
                or soup
            )
            headings = content_area.find_all(["h1", "h2", "h3", "h4"])

            for h in headings:
                text = h.get_text(strip=True)
                if len(text) > 5:
                    desc_elem = h.find_next_sibling(["p", "ul", "div"])
                    desc = desc_elem.get_text(strip=True)[:300] if desc_elem else ""
                    link_elem = h.find("a") or h.find_next("a")
                    link = (
                        urljoin(self.URLS["home"], link_elem["href"])
                        if link_elem and link_elem.get("href")
                        else ""
                    )
                    departments.append({
                        "name": text, "description": desc, "link": link,
                        "email": "", "phone": "", "source": "acibadem.edu.tr",
                    })

        if not departments:
            logger.warning("academic-structure page empty, using fallback list")
            for fac in self.KNOWN_FACULTIES:
                departments.append({
                    "name": fac, "description": "", "link": "",
                    "email": "", "phone": "", "source": "acibadem.edu.tr",
                })

        return departments

    def scrape_static_programs(self) -> List[Dict]:
        soup = self.fetch_page(self.URLS["undergrad_programs"])
        programs = []

        if soup:
            for elem in soup.find_all(["li", "div", "article"]):
                text = elem.get_text(strip=True)
                if not (10 < len(text) < 200):
                    continue
                link_elem = elem.find("a")
                link = (
                    urljoin(self.URLS["home"], link_elem["href"])
                    if link_elem and link_elem.get("href")
                    else ""
                )
                keywords = ["medicine", "pharmacy", "nursing", "engineering", "psychology",
                            "nutrition", "physiotherapy", "management", "biology", "genetics"]
                if any(kw in text.lower() for kw in keywords):
                    programs.append({
                        "name": text[:150], "level": "Undergraduate", "duration": "",
                        "department": "", "language": "", "tuition": "",
                        "link": link, "source": "acibadem.edu.tr/undergrad-programs",
                    })

        logger.info(f"Static programs found: {len(programs)}")
        return programs

    def scrape_static_contact(self) -> Dict:
        soup = self.fetch_page(self.URLS["contact"])
        contact_data = {
            "main_phone": "+90 216 500 44 44",
            "main_email": "ik@acibadem.edu.tr",
            "addresses": ["Kayışdağı Cd. No:32, Ataşehir, İstanbul"],
            "social_media": {},
            "departments_contact": [],
            "source": "acibadem.edu.tr",
        }

        if not soup:
            return contact_data

        phones = re.findall(r"(?:\+90|0)\s?[\d\s\-]{10,15}", soup.get_text())
        if phones:
            contact_data["main_phone"] = phones[0].strip()

        emails = re.findall(r"[\w\.\-]+@acibadem\.edu\.tr", soup.get_text())
        if emails:
            contact_data["main_email"] = emails[0]

        for row in soup.find_all(["tr", "li", "div", "p"]):
            text = row.get_text(separator=" ", strip=True)
            if "@acibadem.edu.tr" in text or "0216 500" in text:
                contact_data["departments_contact"].append(text[:200])

        return contact_data
    

    def scrape_dynamic_obs_courses(self) -> List[Dict]:
        courses = []
        seen: Set[str] = set()

        if not self.all_data["dynamic_content"]["programs"]:
            self.all_data["dynamic_content"]["programs"] = self.scrape_dynamic_obs_programs()

        for prog in self.all_data["dynamic_content"]["programs"]:
            sunit = parse_qs(urlparse(prog['detail_url']).query).get('curSunit', [None])[0]
            if not sunit:
                continue

            courses_url = f"https://obs.acibadem.edu.tr/oibs/bologna/progCourses.aspx?lang=tr&curSunit={sunit}"
            
            # 1. PostBack ile ID'leri topla
            course_ids = self._collect_course_ids_from_courses_page(courses_url)
            
            # 2. Her ID için detay sayfasını fetch et
            for item in course_ids:
                key = item['kod'].lower()
                if key in seen:
                    continue
                seen.add(key)

                details = self._extract_course_details(item['detail_url'])
                if details:
                    details['program'] = prog.get('name', '')
                    details['program_level'] = prog.get('level', '')
                    courses.append(details)

        logger.info(f"Extracted {len(courses)} courses with details")
        return courses

    # =========================================================
    # DYNAMIC HELPERS
    # =========================================================

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "")).strip()

    def _abs_obs_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        return "https://obs.acibadem.edu.tr/oibs/bologna/" + href.lstrip("/")

    def _save_progress(self, filename: Optional[str]) -> None:
        if filename:
            self.save_to_json(filename)

    def _level_from_url(self, url: str) -> str:
        if "type=lis" in url: return "Bachelor"
        if "type=myo" in url: return "Associate"
        if "type=yls" in url: return "Master"
        if "type=dok" in url: return "PhD"
        return ""

    def _is_department_heading(self, text: str) -> bool:
        keywords = ["Fakültesi", "Enstitüsü", "Meslek Yüksekokulu",
                    "Yüksekokulu", "Faculty", "Institute", "School"]
        return any(k in text for k in keywords)

    def _looks_like_program_name(self, text: str) -> bool:
        text = self._clean_text(text)
        if len(text) < 3 or len(text) > 180:
            return False
        blacklist = ["Bilgi Paketi", "EN", "https://", "http://", "Ana Sayfa", "Bologna Süreci"]
        if any(x in text for x in blacklist):
            return False
        return True
    
    def _collect_course_ids_from_courses_page(self, courses_url: str) -> List[Dict]:
        """progCourses sayfasındaki her ders için curCourse ID'sini PostBack ile yakala."""
        if not self._page:
            return []

        result = []
        caught_urls = []

        def on_request(req):
            if 'progCourseDetails' in req.url:
                caught_urls.append(req.url)

        self._page.on('request', on_request)

        try:
            self._page.goto(courses_url, wait_until='networkidle')
            self._page.wait_for_timeout(3000)
            soup = BeautifulSoup(self._page.content(), 'html.parser')

            # Her btnDersAyrinti linkini topla
            items = []
            for a in soup.find_all('a', id=re.compile(r'btnDersAyrinti')):
                tr = a.find_parent('tr')
                kod_a = tr.find('a', id=re.compile(r'btnDersKod')) if tr else None
                kod = kod_a.get_text(strip=True) if kod_a else ''
                postback = re.search(r"__doPostBack\('([^']+)'", a.get('href', ''))
                if postback:
                    items.append({'kod': kod, 'postback': postback.group(1)})

            logger.info(f"[course_ids] {courses_url} → {len(items)} ders bulundu")

            for item in items:
                caught_urls.clear()
                try:
                    pb = item['postback'].replace('$', r'\$')
                    self._page.evaluate(f"__doPostBack('{pb}', '')")
                    self._page.wait_for_timeout(1500)
                    self._page.go_back(wait_until='networkidle')
                    self._page.wait_for_timeout(1500)

                    if caught_urls:
                        m = re.search(r'curCourse=(\d+)', caught_urls[0])
                        if m:
                            result.append({
                                'kod': item['kod'],
                                'curCourse': m.group(1),
                                'detail_url': f"https://obs.acibadem.edu.tr/oibs/bologna/progCourseDetails.aspx?curCourse={m.group(1)}&lang=tr"
                            })
                except Exception as e:
                    logger.warning(f"PostBack hatası {item['kod']}: {e}")
                    continue

        except Exception as e:
            logger.error(f"ID toplama hatası {courses_url}: {e}")

        self._page.remove_listener('request', on_request)
        logger.info(f"[course_ids] {len(result)} ID toplandı")
        return result


    def _extract_course_details(self, detail_url: str) -> Dict:
        """progCourseDetails sayfasından tüm bilgileri çek."""
        soup = self._get_page_source(detail_url, wait_seconds=2)
        if not soup:
            return {}

        details = {}

        # Table 3: key-value çiftleri (Dersin Dili, Türü, Amacı, İçeriği...)
        KEY_MAP = {
            'Dersin Dili': 'dil',
            'Dersin Düzeyi': 'duzey',
            'Bölümü / Programı': 'program',
            'Öğrenim Türü': 'ogretim_turu',
            'Dersin Türü': 'ders_turu',
            'Dersin Öğretim Şekli': 'ogretim_sekli',
            'Dersin Amacı': 'amac',
            'Dersin İçeriği': 'icerik',
            'Dersin Yöntem ve Teknikleri': 'yontem',
            'Ön Koşulları': 'on_kosul',
            'Dersin Koordinatörü': 'koordinator',
            'Dersi Verenler': 'ogretmenler',
            'Dersin Yardımcıları': 'yardimcilar',
            'Dersin Staj Durumu': 'staj',
            'Kaynaklar': 'kaynaklar',
            'Ders Notları': 'ders_notlari',
            'Dökümanlar': 'dokumanlar',
            'Ödevler': 'odevler',
            'Sınavlar': 'sinavlar',
        }

        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows:
                cols = [self._clean_text(td.get_text(' ', strip=True))
                        for td in row.find_all(['td', 'th'])]
                cols = [c for c in cols if c]
                if len(cols) == 2 and cols[0] in KEY_MAP:
                    details[KEY_MAP[cols[0]]] = cols[1]

        # Table 1: temel bilgiler (Yarıyıl, Kod, Adı, AKTS...)
        tables = soup.find_all('table')
        if len(tables) > 1:
            rows = tables[1].find_all('tr')
            if len(rows) > 1:
                cols = [self._clean_text(td.get_text(' ', strip=True))
                        for td in rows[1].find_all(['td', 'th'])]
                if len(cols) >= 6:
                    details['yaryil'] = cols[0]
                    details['kod'] = cols[1]
                    details['ad'] = cols[2]
                    details['tul'] = cols[3]
                    details['kredi'] = cols[4]
                    details['akts'] = cols[5]

        # Table 6: yarıyıl çalışmaları (vize/final katkı)
        if len(tables) > 6:
            sinav_rows = tables[6].find_all('tr')[1:]  # başlığı atla
            sinavlar = []
            for row in sinav_rows:
                cols = [self._clean_text(td.get_text(' ', strip=True))
                        for td in row.find_all(['td', 'th'])]
                cols = [c for c in cols if c]
                if len(cols) >= 3 and 'Toplam' not in cols[0]:
                    sinavlar.append({'tur': cols[0], 'sayi': cols[1], 'katki': cols[2]})
            if sinavlar:
                details['sinav_katki'] = sinavlar

        # Table 9: haftalık plan
        if len(tables) > 9:
            hafta_rows = tables[9].find_all('tr')[1:]  # başlığı atla
            haftalik = []
            for row in hafta_rows:
                cols = [self._clean_text(td.get_text(' ', strip=True))
                        for td in row.find_all(['td', 'th'])]
                cols = [c for c in cols if c]
                if len(cols) >= 2:
                    haftalik.append({'hafta': cols[0], 'konu': cols[1]})
            if haftalik:
                details['haftalik_plan'] = haftalik

        details['detail_url'] = detail_url
        return details


    def _extract_program_links_from_unit_page(self, url: str) -> List[Dict]:
        results = []
        seen: Set[str] = set()
        current_department = ""

        # ✅ Selenium driver.get() → Playwright _get_page_source()
        soup = self._get_page_source(url, wait_seconds=4)
        if not soup:
            return []

        for a in soup.find_all("a", href=True):
            text = self._clean_text(a.get_text(" ", strip=True))
            href = a.get("href", "")

            if not text:
                continue
            if self._is_department_heading(text):
                current_department = text
                continue
            if "curOp=showPac" in href and self._looks_like_program_name(text):
                abs_href = self._abs_obs_url(href)
                key = f"{text.lower()}|{abs_href}"
                if key in seen:
                    continue
                seen.add(key)
                results.append({
                    "name": text,
                    "level": self._level_from_url(url),
                    "duration": "",
                    "department": current_department,
                    "language": "English" if "İngilizce" in text or "English" in text else "",
                    "tuition": "",
                    "link": abs_href,
                    "detail_url": abs_href,
                    "source": "obs.acibadem.edu.tr",
                })

        return results

    from urllib.parse import urlparse, parse_qs

    def _courses_url_from_detail(self, detail_url: str) -> str:
        """detail_url'den progCourses.aspx URL'i oluştur."""
        params = parse_qs(urlparse(detail_url).query)
        sunit = params.get('curSunit', [None])[0]
        lang = params.get('lang', ['tr'])[0]
        if sunit:
            return f"https://obs.acibadem.edu.tr/oibs/bologna/progCourses.aspx?lang={lang}&curSunit={sunit}"
        return ""

    def _extract_courses_from_program_detail(self, detail_url: str) -> List[Dict]:
        if not detail_url:
            return []

        courses_url = self._courses_url_from_detail(detail_url)
        if not courses_url:
            logger.warning(f"curSunit parse edilemedi: {detail_url}")
            return []

        courses = []
        seen: Set[str] = set()

        try:
            soup = self._get_page_source(courses_url, wait_seconds=3)
            if not soup:
                return []

            tables = soup.find_all("table")
            logger.debug(f"[courses] {courses_url} → {len(tables)} table")

            # Table 2 (index 1) ders tablosu, ama hepsini tara
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cols = [self._clean_text(td.get_text(" ", strip=True))
                            for td in row.find_all(["td", "th"])]
                    cols = [c for c in cols if c]

                    # Başlık satırlarını atla
                    if not cols or cols[0] in ("Ders Kodu", "Course Code", ""):
                        continue
                    # "X.Yarıyıl" gibi bölüm başlıklarını atla
                    if len(cols) == 1 or "Yarıyıl" in cols[0] or "Semester" in cols[0]:
                        continue

                    # Sütun yapısı: Ders Kodu | Ders Adı | T+U+L | Zorunlu/Seçmeli | AKTS | ...
                    if len(cols) >= 2:
                        code = cols[0]
                        name = cols[1]

                        # Geçerli ders kodu formatı: "MBG 109", "ATA 101" vb.
                        if not re.search(r"[A-ZÇĞİÖŞÜ]{2,}\s*\d{2,3}", code):
                            continue

                        credits = cols[4] if len(cols) > 4 else ""
                        course_type = cols[3] if len(cols) > 3 else ""  # Zorunlu/Seçmeli
                        tul = cols[2] if len(cols) > 2 else ""          # T+U+L

                        key = f"{code}|{name}"
                        if key not in seen:
                            seen.add(key)
                            courses.append({
                                "code": code,
                                "name": name,
                                "credits": credits,
                                "type": course_type,
                                "tul": tul,
                                "source": "obs.acibadem.edu.tr",
                            })

            logger.debug(f"[courses] {len(courses)} ders çekildi: {courses_url}")
            return courses

        except Exception as e:
            logger.error(f"Error scraping courses from {courses_url}: {e}")
            return []
    # =========================================================
    # DYNAMIC SCRAPING
    # =========================================================

    def scrape_dynamic_obs_programs(self) -> List[Dict]:
        programs = []
        seen: Set[str] = set()

        try:
            for url in self.OBS_UNIT_URLS:
                logger.info(f"Scraping OBS unit page: {url}")
                for prog in self._extract_program_links_from_unit_page(url):
                    key = prog.get("name", "").lower().strip()
                    if key and key not in seen:
                        seen.add(key)
                        programs.append(prog)

            logger.info(f"Extracted {len(programs)} programs from OBS")
            return programs
        except Exception as e:
            logger.error(f"Error scraping OBS programs: {e}")
            return []

    def scrape_dynamic_obs_courses(self) -> List[Dict]:
        courses = []
        seen: Set[str] = set()

        try:
            if not self.all_data["dynamic_content"]["programs"]:
                self.all_data["dynamic_content"]["programs"] = self.scrape_dynamic_obs_programs()

            detail_urls = [
                p.get("detail_url", "")
                for p in self.all_data["dynamic_content"]["programs"]
                if p.get("detail_url")
            ]

            for detail_url in detail_urls[:30]:
                for course in self._extract_courses_from_program_detail(detail_url):
                    key = f"{course.get('code','').lower()}|{course.get('name','').lower()}"
                    if key not in seen and course.get("name"):
                        seen.add(key)
                        courses.append(course)

            logger.info(f"Extracted {len(courses)} courses from OBS")
            return courses
        except Exception as e:
            logger.error(f"Error scraping OBS courses: {e}")
            return []

    # =========================================================
    # MERGE + MAIN (değişmedi)
    # =========================================================

    def merge_and_deduplicate(self) -> Dict:
        merged = {"all_programs": [], "all_departments": [], "complete_info": []}
        seen_programs: Set[str] = set()
        for prog in (self.all_data["static_content"]["programs"]
                     + self.all_data["dynamic_content"]["programs"]):
            key = prog.get("name", "").lower().strip()
            if key and key not in seen_programs:
                seen_programs.add(key)
                merged["all_programs"].append(prog)

        seen_depts: Set[str] = set()
        for dept in self.all_data["static_content"]["departments"]:
            key = dept.get("name", "").lower().strip()
            if key and key not in seen_depts:
                seen_depts.add(key)
                merged["all_departments"].append(dept)

        self.all_data["merged_data"] = merged
        logger.info(f"Merged: {len(merged['all_programs'])} programs, "
                    f"{len(merged['all_departments'])} departments")
        return merged

    def scrape_all(self, autosave_filename: Optional[str] = None) -> Dict:
        logger.info("=" * 60)
        logger.info("Starting comprehensive dual-source scrape...")
        logger.info("=" * 60)

        logger.info("\n[1/4] Scraping static content...")
        self.all_data["static_content"]["general_info"] = self.scrape_static_homepage()
        self.all_data["static_content"]["departments"] = self.scrape_static_departments()
        self.all_data["static_content"]["programs"] = self.scrape_static_programs()
        self.all_data["static_content"]["contact_info"] = self.scrape_static_contact()
        self.all_data["metadata"]["static_success"] = bool(
            self.all_data["static_content"]["general_info"]
            or self.all_data["static_content"]["departments"]
            or self.all_data["static_content"]["programs"]
        )
        self._save_progress(autosave_filename)
        logger.info("✓ Static content scraped")

        logger.info("\n[2/4] Initializing Playwright...")
        # ✅ init_selenium_driver → init_playwright_driver
        if self.init_playwright_driver():
            logger.info("[3/4] Scraping dynamic content (obs.acibadem.edu.tr)...")
            programs = self.scrape_dynamic_obs_programs()
            self.all_data["dynamic_content"]["programs"] = programs
            self._save_progress(autosave_filename)

            courses = self.scrape_dynamic_obs_courses()
            self.all_data["dynamic_content"]["courses"] = courses
            self.all_data["metadata"]["dynamic_success"] = bool(programs or courses)
            self._save_progress(autosave_filename)

            # ✅ close_selenium_driver → close_playwright_driver
            self.close_playwright_driver()
            logger.info("✓ Dynamic content scraped")
        else:
            logger.warning("⚠ Playwright initialization failed, skipping dynamic content")

        logger.info("\n[4/4] Merging and deduplicating data...")
        self.merge_and_deduplicate()
        self._save_progress(autosave_filename)

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

    def save_to_json(self, filename: str = "acibadem_complete_data.json") -> bool:
        self.all_data["metadata"]["scrape_date"] = datetime.now().isoformat()
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.all_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ data saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            return False