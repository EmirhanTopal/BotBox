"""
Acıbadem University Dual Scraper
Kaynaklar:
  - acibadem.edu.tr  (statik: genel bilgi, fakülteler, programlar, iletişim)
  - obs.acibadem.edu.tr/oibs/bologna (dinamik: programlar, dersler, müfredat)

Yenilikler:
  - Her ders artık program_name, program_level, semester alanlarına sahip
  - Yarıyıl başlıkları atlanmıyor; ders hangi yarıyılda ise o bilgi kaydediliyor
  - Program → Ders ilişkisi kuruldu (bir ders birden fazla programda olabilir)
  - Müfredat (curriculum) ayrıca kaydediliyor: {program, semester, courses[]}
"""

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
        ("lis", "Bachelor",   "https://obs.acibadem.edu.tr/oibs/bologna/unitSelection.aspx?type=lis&lang=tr"),
        ("myo", "Associate",  "https://obs.acibadem.edu.tr/oibs/bologna/unitSelection.aspx?type=myo&lang=tr"),
        ("yls", "Master",     "https://obs.acibadem.edu.tr/oibs/bologna/unitSelection.aspx?type=yls&lang=tr"),
        ("dok", "PhD",        "https://obs.acibadem.edu.tr/oibs/bologna/unitSelection.aspx?type=dok&lang=tr"),
    ]

    def __init__(self, use_headless: bool = True):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        self.use_headless = use_headless
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
                "programs": [],       # OBS'den çekilen program listesi
                "courses": [],        # Tüm dersler (program+semester bilgisiyle)
                "curriculum": [],     # Program → yarıyıl → dersler ağacı
                "requirements": [],
            },
            "merged_data": {
                "all_programs": [],
                "all_departments": [],
                "complete_info": [],
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
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox",
                      "--disable-dev-shm-usage", "--disable-gpu"],
            )
            self._page = self._browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            self._page.set_default_timeout(30_000)
            logger.info("Playwright initialized")
            return True
        except Exception as e:
            logger.error(f"Playwright init failed: {e}")
            return False

    def close_playwright_driver(self) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("Playwright closed")

    def _get_page_source(self, url: str, wait_seconds: int = 3) -> Optional[BeautifulSoup]:
        if not self._page:
            return None
        try:
            self._page.goto(url, wait_until="networkidle")
            if wait_seconds > 0:
                self._page.wait_for_timeout(wait_seconds * 1000)
            return BeautifulSoup(self._page.content(), "html.parser")
        except Exception as e:
            logger.error(f"Playwright failed {url}: {e}")
            return None

    # =========================================================
    # STATIC SCRAPING
    # =========================================================

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            r.raise_for_status()
            return BeautifulSoup(r.content, "html.parser")
        except Exception as e:
            logger.error(f"fetch_page failed {url}: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

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
        return data

    def scrape_static_departments(self) -> List[Dict]:
        soup = self.fetch_page(self.URLS["academic_structure"])
        departments = []
        if soup:
            content = soup.find("main") or soup.find("div", {"class": "content"}) or soup
            for heading in content.find_all(["h2", "h3", "h4"]):
                text = self._clean_text(heading.get_text())
                if len(text) > 3:
                    description_parts = []
                    for sib in heading.find_next_siblings():
                        if sib.name in ["h2", "h3", "h4"]:
                            break
                        description_parts.append(self._clean_text(sib.get_text(" ", strip=True)))
                    departments.append({
                        "name": text,
                        "description": " ".join(description_parts)[:500],
                        "email": "",
                        "phone": "",
                        "link": self.URLS["academic_structure"],
                        "source": "acibadem.edu.tr",
                    })
        logger.info(f"Static departments: {len(departments)}")
        return departments

    def scrape_static_programs(self) -> List[Dict]:
        soup = self.fetch_page(self.URLS["undergrad_programs"])
        programs = []
        if soup:
            for a in soup.find_all("a", href=True):
                text = self._clean_text(a.get_text())
                href = a["href"]
                if text and len(text) > 5 and ("program" in href.lower() or "faculty" in href.lower()):
                    full_url = urljoin(self.URLS["home"], href)
                    programs.append({
                        "name": text,
                        "level": "Undergraduate",
                        "duration": "",
                        "department": "",
                        "language": "English" if "İngilizce" in text or "English" in text else "",
                        "link": full_url,
                        "source": "acibadem.edu.tr/undergrad-programs",
                    })
        logger.info(f"Static programs: {len(programs)}")
        return programs

    def scrape_static_contact(self) -> Dict:
        soup = self.fetch_page(self.URLS["contact"])
        contact = {
            "main_phone": "021-2022",
            "main_email": "tanitim@acibadem.edu.tr",
            "addresses": ["Kayışdağı Cd. No:32, Ataşehir, İstanbul"],
            "social_media": {},
            "departments_contact": [],
            "source": "acibadem.edu.tr",
        }
        if soup:
            # Telefon
            phone_pattern = re.compile(r'(\+90[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}|\d{3,4}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2})')
            for tag in soup.find_all(string=phone_pattern):
                m = phone_pattern.search(tag)
                if m:
                    contact["main_phone"] = m.group(0)
                    break
            # Email
            email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
            for tag in soup.find_all(string=email_pattern):
                m = email_pattern.search(tag)
                if m and "acibadem.edu.tr" in m.group(0):
                    contact["main_email"] = m.group(0)
                    break
        return contact

    # =========================================================
    # OBS DYNAMIC SCRAPING — PROGRAMLAR
    # =========================================================

    def _looks_like_program_name(self, text: str) -> bool:
        if len(text) < 4 or len(text) > 200:
            return False
        skip = ["ana sayfa", "home", "geri", "back", "menu", "login", "search",
                "türkçe", "english", "bologna", "ects"]
        if any(s in text.lower() for s in skip):
            return False
        return True

    def _is_department_heading(self, text: str) -> bool:
        keywords = ["fakülte", "enstitü", "yüksekokul", "meslek", "faculty",
                    "institute", "school", "college", "department"]
        return any(k in text.lower() for k in keywords) and len(text) < 100

    def _abs_obs_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        return urljoin(self.URLS["obs_base"], href)

    def _level_from_type(self, type_code: str) -> str:
        return {"lis": "Bachelor", "myo": "Associate", "yls": "Master", "dok": "PhD"}.get(type_code, "")

    def _extract_program_links_from_unit_page(self, type_code: str, level: str, url: str) -> List[Dict]:
        results = []
        seen: Set[str] = set()
        current_department = ""

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
                key = text.lower().strip()
                if key in seen:
                    continue
                seen.add(key)
                # Dil tespiti
                language = "İngilizce" if ("İngilizce" in text or "(English)" in text) else "Türkçe"
                results.append({
                    "name": text,
                    "level": level,
                    "type_code": type_code,
                    "duration": "4 yıl" if level == "Bachelor" else
                                "2 yıl" if level == "Associate" else
                                "2 yıl" if level == "Master" else
                                "4 yıl" if level == "PhD" else "",
                    "department": current_department,
                    "language": language,
                    "tuition": "",
                    "link": abs_href,
                    "detail_url": abs_href,
                    "source": "obs.acibadem.edu.tr",
                })

        logger.info(f"  {level} ({type_code}): {len(results)} program")
        return results

    def scrape_dynamic_obs_programs(self) -> List[Dict]:
        programs = []
        seen: Set[str] = set()
        for type_code, level, url in self.OBS_UNIT_URLS:
            logger.info(f"Scraping OBS programs: {level} — {url}")
            for prog in self._extract_program_links_from_unit_page(type_code, level, url):
                key = prog["name"].lower().strip()
                if key and key not in seen:
                    seen.add(key)
                    programs.append(prog)
        logger.info(f"Total OBS programs: {len(programs)}")
        return programs

    # =========================================================
    # OBS DYNAMIC SCRAPING — DERSLER + MÜFREDAT
    # =========================================================

    def _courses_url_from_detail(self, detail_url: str) -> str:
        params = parse_qs(urlparse(detail_url).query)
        sunit = params.get("curSunit", [None])[0]
        lang = params.get("lang", ["tr"])[0]
        if sunit:
            return f"https://obs.acibadem.edu.tr/oibs/bologna/progCourses.aspx?lang={lang}&curSunit={sunit}"
        return ""

    def _extract_curriculum_from_program(self, program: Dict) -> Dict:
        """
        Bir programın müfredatını çeker.
        Döner:
          {
            program_name: str,
            program_level: str,
            semesters: [
              { semester: int, courses: [ {code, name, credits, type, tul} ] }
            ]
          }
        """
        detail_url = program.get("detail_url", "")
        program_name = program.get("name", "")
        program_level = program.get("level", "")

        result = {
            "program_name": program_name,
            "program_level": program_level,
            "program_department": program.get("department", ""),
            "program_language": program.get("language", ""),
            "semesters": [],
        }

        courses_url = self._courses_url_from_detail(detail_url)
        if not courses_url:
            logger.warning(f"curSunit parse edilemedi: {detail_url}")
            return result

        try:
            soup = self._get_page_source(courses_url, wait_seconds=3)
            if not soup:
                return result

            tables = soup.find_all("table")
            current_semester = None
            semester_dict: Dict[int, List[Dict]] = {}

            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cols = [self._clean_text(td.get_text(" ", strip=True))
                            for td in row.find_all(["td", "th"])]
                    cols = [c for c in cols if c]

                    if not cols:
                        continue

                    # Başlık satırı atla
                    if cols[0] in ("Ders Kodu", "Course Code"):
                        continue

                    # Yarıyıl başlığı — "1.Yarıyıl", "2. Semester" vb.
                    if len(cols) == 1 and ("yarıyıl" in cols[0].lower() or
                                           "semester" in cols[0].lower() or
                                           "dönem" in cols[0].lower()):
                        m = re.search(r'(\d+)', cols[0])
                        current_semester = int(m.group(1)) if m else None
                        continue

                    # Toplam satırı atla
                    if "toplam" in cols[0].lower() or "total" in cols[0].lower():
                        continue

                    # Ders satırı — geçerli ders kodu formatı
                    if len(cols) >= 2 and re.search(r"[A-ZÇĞİÖŞÜ]{2,}\s*\d{2,3}", cols[0]):
                        code = cols[0]
                        name = cols[1]
                        tul = cols[2] if len(cols) > 2 else ""
                        course_type = cols[3] if len(cols) > 3 else ""
                        credits = cols[4] if len(cols) > 4 else ""

                        course_entry = {
                            "code": code,
                            "name": name,
                            "credits": credits,
                            "type": course_type,
                            "tul": tul,
                        }

                        sem = current_semester or 0
                        if sem not in semester_dict:
                            semester_dict[sem] = []
                        semester_dict[sem].append(course_entry)

            # semester_dict'i sıralı listeye çevir
            for sem_num in sorted(semester_dict.keys()):
                result["semesters"].append({
                    "semester": sem_num,
                    "courses": semester_dict[sem_num],
                })

            total_courses = sum(len(s["courses"]) for s in result["semesters"])
            logger.info(f"  [{program_name}] {len(result['semesters'])} yarıyıl, {total_courses} ders")

        except Exception as e:
            logger.error(f"Curriculum scrape error for {program_name}: {e}")

        return result

    def scrape_dynamic_obs_curriculum(self) -> tuple:
        """
        Tüm programların müfredatını çeker.
        Döner: (curriculum_list, flat_courses_list)
          - curriculum_list: [{program_name, semesters: [{semester, courses}]}]
          - flat_courses_list: [{code, name, credits, type, tul, program_name, program_level, semester}]
        """
        curriculum_list = []
        flat_courses: List[Dict] = []
        seen_courses: Set[str] = set()

        programs = self.all_data["dynamic_content"]["programs"]
        logger.info(f"Scraping curriculum for {len(programs)} programs...")

        for i, program in enumerate(programs):
            prog_name = program.get("name", "")
            prog_level = program.get("level", "")
            logger.info(f"  [{i+1}/{len(programs)}] {prog_name}")

            curriculum = self._extract_curriculum_from_program(program)
            curriculum_list.append(curriculum)

            # Düz ders listesine ekle (program+semester bilgisiyle)
            for sem_data in curriculum.get("semesters", []):
                sem_num = sem_data.get("semester")
                for course in sem_data.get("courses", []):
                    # Unique key: kod + program (aynı ders farklı programlarda olabilir)
                    flat_key = f"{course['code']}|{prog_name}"
                    if flat_key not in seen_courses:
                        seen_courses.add(flat_key)
                        flat_courses.append({
                            "code": course["code"],
                            "name": course["name"],
                            "credits": course["credits"],
                            "type": course["type"],
                            "tul": course.get("tul", ""),
                            "program_name": prog_name,
                            "program_level": prog_level,
                            "semester": sem_num,
                            "source": "obs.acibadem.edu.tr",
                        })

        logger.info(f"Total curriculum entries: {len(curriculum_list)}")
        logger.info(f"Total flat courses: {len(flat_courses)}")
        return curriculum_list, flat_courses

    # =========================================================
    # MERGE
    # =========================================================

    def merge_and_deduplicate(self) -> Dict:
        merged = {"all_programs": [], "all_departments": [], "complete_info": []}
        seen_programs: Set[str] = set()

        for prog in (self.all_data["static_content"]["programs"] +
                     self.all_data["dynamic_content"]["programs"]):
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

    def _save_progress(self, filename: Optional[str] = None) -> None:
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(self.all_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Progress save failed: {e}")

    # =========================================================
    # MAIN SCRAPE
    # =========================================================

    def scrape_all(self, autosave_filename: Optional[str] = None) -> Dict:
        logger.info("=" * 60)
        logger.info("Starting comprehensive dual-source scrape...")
        logger.info("=" * 60)

        # 1. STATIC
        logger.info("\n[1/4] Scraping static content...")
        self.all_data["static_content"]["general_info"] = self.scrape_static_homepage()
        self.all_data["static_content"]["departments"] = self.scrape_static_departments()
        self.all_data["static_content"]["programs"] = self.scrape_static_programs()
        self.all_data["static_content"]["contact_info"] = self.scrape_static_contact()
        self.all_data["metadata"]["static_success"] = bool(
            self.all_data["static_content"]["general_info"]
        )
        self._save_progress(autosave_filename)
        logger.info("✓ Static content done")

        # 2. PLAYWRIGHT
        logger.info("\n[2/4] Initializing Playwright...")
        if not self.init_playwright_driver():
            logger.warning("⚠ Playwright failed, skipping dynamic content")
        else:
            # 3. DYNAMIC — PROGRAMLAR
            logger.info("[3/4] Scraping OBS programs...")
            programs = self.scrape_dynamic_obs_programs()
            self.all_data["dynamic_content"]["programs"] = programs
            self._save_progress(autosave_filename)

            # 4. DYNAMIC — MÜF REDAT + DERSLER
            logger.info("[4/4] Scraping OBS curriculum & courses...")
            curriculum_list, flat_courses = self.scrape_dynamic_obs_curriculum()
            self.all_data["dynamic_content"]["curriculum"] = curriculum_list
            self.all_data["dynamic_content"]["courses"] = flat_courses
            self.all_data["metadata"]["dynamic_success"] = bool(programs or flat_courses)
            self._save_progress(autosave_filename)

            self.close_playwright_driver()
            logger.info("✓ Dynamic content done")

        # MERGE
        self.merge_and_deduplicate()
        self._save_progress(autosave_filename)

        # SUMMARY
        logger.info("\n" + "=" * 60)
        logger.info("SCRAPING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Static departments : {len(self.all_data['static_content']['departments'])}")
        logger.info(f"Static programs    : {len(self.all_data['static_content']['programs'])}")
        logger.info(f"Dynamic programs   : {len(self.all_data['dynamic_content']['programs'])}")
        logger.info(f"Curriculum entries : {len(self.all_data['dynamic_content']['curriculum'])}")
        logger.info(f"Flat courses       : {len(self.all_data['dynamic_content']['courses'])}")
        logger.info(f"Merged programs    : {len(self.all_data['merged_data']['all_programs'])}")
        logger.info("=" * 60 + "\n")

        return self.all_data

    def save_to_json(self, filename: str = "acibadem_complete_data.json") -> bool:
        self.all_data["metadata"]["scrape_date"] = datetime.now().isoformat()
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.all_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Data saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False


if __name__ == "__main__":
    scraper = AcibademDualScraper(use_headless=True)
    data = scraper.scrape_all(autosave_filename="acibadem_complete_data.json")
    scraper.save_to_json("acibadem_complete_data.json")