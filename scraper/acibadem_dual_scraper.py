import json
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AcibademDualScraper:
    """
    Dual scraper for Acibadem University data:
    - Static content via BeautifulSoup
    - Dynamic content via Selenium
    """

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
        self.driver = None

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
    # SELENIUM
    # =========================================================

    def init_selenium_driver(self) -> bool:
        """Initialize Selenium WebDriver with Chrome/Chromium."""
        try:
            chrome_options = Options()
            if self.use_headless:
                chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            # Container'da chromium yolu varsa kullan
            possible_binaries = [
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/usr/bin/google-chrome",
            ]
            for binary in possible_binaries:
                try:
                    import os
                    if os.path.exists(binary):
                        chrome_options.binary_location = binary
                        break
                except Exception:
                    pass

            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Selenium WebDriver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            return False

    def close_selenium_driver(self) -> None:
        if self.driver:
            self.driver.quit()
            logger.info("Selenium WebDriver closed")

    # =========================================================
    # STATIC
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
            {
                "class": lambda c: c
                and any(x in " ".join(c) for x in ["hero", "banner", "slider", "intro"])
            },
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

                    departments.append(
                        {
                            "name": text,
                            "description": desc,
                            "link": link,
                            "email": "",
                            "phone": "",
                            "source": "acibadem.edu.tr",
                        }
                    )

        if not departments:
            logger.warning("academic-structure page empty, using fallback list")
            for fac in self.KNOWN_FACULTIES:
                departments.append(
                    {
                        "name": fac,
                        "description": "",
                        "link": "",
                        "email": "",
                        "phone": "",
                        "source": "acibadem.edu.tr",
                    }
                )

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

                keywords = [
                    "medicine",
                    "pharmacy",
                    "nursing",
                    "engineering",
                    "psychology",
                    "nutrition",
                    "physiotherapy",
                    "management",
                    "biology",
                    "genetics",
                ]
                if any(kw in text.lower() for kw in keywords):
                    programs.append(
                        {
                            "name": text[:150],
                            "level": "Undergraduate",
                            "duration": "",
                            "department": "",
                            "language": "",
                            "tuition": "",
                            "link": link,
                            "source": "acibadem.edu.tr/undergrad-programs",
                        }
                    )

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

    # =========================================================
    # DYNAMIC HELPERS
    # =========================================================

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "")).strip()

    def _abs_obs_url(self, url: str) -> str:
        return urljoin(self.URLS["obs_base"], url)

    def _save_progress(self, filename: Optional[str]) -> None:
        if filename:
            self.save_to_json(filename)

    def _level_from_url(self, url: str) -> str:
        if "type=lis" in url:
            return "Bachelor"
        if "type=myo" in url:
            return "Associate"
        if "type=yls" in url:
            return "Master"
        if "type=dok" in url:
            return "PhD"
        return ""

    def _is_department_heading(self, text: str) -> bool:
        keywords = [
            "Fakültesi",
            "Enstitüsü",
            "Meslek Yüksekokulu",
            "Yüksekokulu",
            "Faculty",
            "Institute",
            "School",
        ]
        return any(k in text for k in keywords)

    def _looks_like_program_name(self, text: str) -> bool:
        text = self._clean_text(text)
        if len(text) < 3 or len(text) > 180:
            return False

        blacklist = [
            "Bilgi Paketi",
            "EN",
            "https://",
            "http://",
            "Ana Sayfa",
            "Bologna Süreci",
        ]
        if any(x in text for x in blacklist):
            return False

        return True

    def _extract_program_links_from_unit_page(self, url: str) -> List[Dict]:
        if not self.driver:
            return []

        results = []
        seen: Set[str] = set()
        current_department = ""

        self.driver.get(url)
        time.sleep(4)
        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        anchors = soup.find_all("a", href=True)

        for a in anchors:
            text = self._clean_text(a.get_text(" ", strip=True))
            href = a.get("href", "")

            if not text:
                continue

            if self._is_department_heading(text):
                current_department = text
                continue

            # 🔥 ASIL FIX BURASI
            if "curOp=showPac" in href and self._looks_like_program_name(text):
                abs_href = self._abs_obs_url(href)  # zaten full URL

                key = f"{text.lower()}|{abs_href}"
                if key in seen:
                    continue
                seen.add(key)

                results.append(
                    {
                        "name": text,
                        "level": self._level_from_url(url),
                        "duration": "",
                        "department": current_department,
                        "language": "English" if "İngilizce" in text or "English" in text else "",
                        "tuition": "",
                        "link": abs_href,
                        "detail_url": abs_href,
                        "source": "obs.acibadem.edu.tr",
                    }
                )

        return results

    def _abs_obs_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        return "https://obs.acibadem.edu.tr/oibs/bologna/" + href.lstrip("/")

    def _extract_courses_from_program_detail(self, detail_url: str) -> List[Dict]:
        """
        Program detay sayfasından course benzeri satırları bulmaya çalışır.
        Bu kısım best-effort çalışır; site yapısına göre geliştirilebilir.
        """
        if not self.driver or not detail_url:
            return []

        courses = []
        seen: Set[str] = set()

        try:
            self.driver.get(detail_url)
            time.sleep(3)
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Tablo bazlı course extraction
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                for row in rows:
                    cols = [self._clean_text(td.get_text(" ", strip=True)) for td in row.find_all(["td", "th"])]
                    cols = [c for c in cols if c]
                    if len(cols) < 2:
                        continue

                    code = ""
                    name = ""

                    # Code pattern: ABC123 / TIP101 benzeri
                    for c in cols:
                        if re.search(r"[A-ZÇĞİÖŞÜ]{2,}\s*\d{2,3}", c):
                            code = c
                            break

                    if code:
                        for c in cols:
                            if c != code and len(c) > 3:
                                name = c
                                break

                    if code and name:
                        key = f"{code}|{name}"
                        if key in seen:
                            continue
                        seen.add(key)
                        courses.append(
                            {
                                "code": code,
                                "name": name,
                                "credits": "",
                                "type": "",
                                "source": "obs.acibadem.edu.tr",
                            }
                        )

            return courses
        except Exception as e:
            logger.error(f"Error scraping program detail courses from {detail_url}: {e}")
            return []

    # =========================================================
    # DYNAMIC SCRAPING
    # =========================================================

    def scrape_dynamic_obs_programs(self) -> List[Dict]:
        """OBS'den program listesini çek."""
        if not self.driver:
            logger.error("Selenium driver not initialized")
            return []

        programs = []
        seen: Set[str] = set()

        try:
            for url in self.OBS_UNIT_URLS:
                logger.info(f"Scraping OBS unit page: {url}")
                page_programs = self._extract_program_links_from_unit_page(url)

                for prog in page_programs:
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
        """OBS'den ders listesini çekmeye çalış."""
        if not self.driver:
            return []

        courses = []
        seen: Set[str] = set()

        try:
            # Eğer programlar henüz yoksa önce onları al
            if not self.all_data["dynamic_content"]["programs"]:
                self.all_data["dynamic_content"]["programs"] = self.scrape_dynamic_obs_programs()

            detail_urls = [
                p.get("detail_url", "")
                for p in self.all_data["dynamic_content"]["programs"]
                if p.get("detail_url")
            ]

            # Çok uzun sürmemesi için ilk etapta sınırlayabilirsin.
            # İstersen bu limiti sonra kaldır.
            for detail_url in detail_urls[:30]:
                page_courses = self._extract_courses_from_program_detail(detail_url)
                for course in page_courses:
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
    # MERGE
    # =========================================================

    def merge_and_deduplicate(self) -> Dict:
        merged = {
            "all_programs": [],
            "all_departments": [],
            "complete_info": [],
        }

        seen_programs: Set[str] = set()
        for prog in (
            self.all_data["static_content"]["programs"]
            + self.all_data["dynamic_content"]["programs"]
        ):
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
        logger.info(
            f"Merged: {len(merged['all_programs'])} programs, "
            f"{len(merged['all_departments'])} departments"
        )
        return merged

    # =========================================================
    # MAIN
    # =========================================================

    def scrape_all(self, autosave_filename: Optional[str] = None) -> Dict:
        logger.info("=" * 60)
        logger.info("Starting comprehensive dual-source scrape...")
        logger.info("=" * 60)

        logger.info("\n[1/4] Scraping static content (acibadem.edu.tr)...")
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

        logger.info("\n[2/4] Initializing Selenium for dynamic content...")
        if self.init_selenium_driver():
            logger.info("[3/4] Scraping dynamic content (obs.acibadem.edu.tr)...")
            programs = self.scrape_dynamic_obs_programs()
            self.all_data["dynamic_content"]["programs"] = programs
            self._save_progress(autosave_filename)

            courses = self.scrape_dynamic_obs_courses()
            self.all_data["dynamic_content"]["courses"] = courses
            self.all_data["metadata"]["dynamic_success"] = bool(programs or courses)
            self._save_progress(autosave_filename)

            self.close_selenium_driver()
            logger.info("✓ Dynamic content scraped")
        else:
            logger.warning("⚠ Selenium initialization failed, skipping dynamic content")

        logger.info("\n[4/4] Merging and deduplicating data...")
        self.merge_and_deduplicate()
        self._save_progress(autosave_filename)
        logger.info("✓ data merged")

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