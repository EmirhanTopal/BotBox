"""Information retrieval service"""

import re
import logging
from collections import defaultdict
from django.db.models import Q
from chat.models import Program, Course, Department, UniversityInfo
from rapidfuzz import fuzz
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self):
        self.max_results = 5
        self.vector_store = VectorStore()

    def _contains_any(self, text: str, keywords: list, threshold: int = 70) -> bool:
        text_lower = text.lower()
        words = text_lower.split()
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                return True
            for word in words:
                if fuzz.ratio(word, keyword_lower) >= threshold:
                    return True
        return False

    def _search_db_fuzzy(self, model, question: str, fields: list, max_results=None):
        limit = max_results or self.max_results
        q_filter = Q()
        for field in fields:
            q_filter |= Q(**{f"{field}__icontains": question})
        results = list(model.objects.filter(q_filter)[:limit])
        if results:
            return results

        all_items = model.objects.all()
        scored = []
        for item in all_items:
            score = 0
            for field in fields:
                val = getattr(item, field, '') or ''
                score = max(score, fuzz.partial_ratio(question.lower(), val.lower()))
            if score >= 50:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def _detect_intents(self, q: str) -> set:
        intents = set()

        list_keywords = [
            'listele', 'hepsini listele', 'hepsini göster', 'sırala',
            'tüm programlar', 'tüm dersler', 'tüm fakülteler', 'tüm bölümler',
            'list all', 'show all', 'all programs', 'all courses', 'all departments',
            'kaç tane', 'kaç adet', 'kaç fakülte', 'kaç bölüm', 'kaç program',
            'how many',
        ]
        if self._contains_any(q, list_keywords):
            intents.add('list')

        hangi_list = ['hangi fakülteler', 'hangi bölümler', 'hangi programlar',
                      'what faculties', 'what departments', 'what programs', 'what courses']
        if self._contains_any(q, hangi_list):
            intents.add('list')

        # Yarıyıl sorusu
        semester_keywords = [
            'yarıyıl', 'yariyil', 'dönem', 'donem', 'semester', 'term',
            '1.yarıyıl', '2.yarıyıl', '3.yarıyıl', '4.yarıyıl',
            '1. yarıyıl', '2. yarıyıl', 'birinci yarıyıl', 'ikinci yarıyıl',
            'first semester', 'second semester', 'hangi yarıyıl',
        ]
        if self._contains_any(q, semester_keywords):
            intents.add('semester')
            intents.add('course')

        # Program dersleri — yarıyıl belirtmeden
        program_course_keywords = [
            'hangi dersler', 'dersleri neler', 'dersler nelerdir', 'dersler var',
            'müfredatı', 'müfredat nedir', 'ders listesi', 'dersleri göster',
            'what courses', 'courses in', 'curriculum of', 'which courses',
        ]
        if self._contains_any(q, program_course_keywords):
            intents.add('program_courses')
            intents.add('course')

        program_keywords = [
            'program', 'degree', 'bachelor', 'master', 'phd', 'doctoral',
            'engineering', 'science', 'medicine', 'nursing', 'computer',
            'software', 'pharmacy', 'undergraduate', 'graduate',
            'lisans', 'yüksek lisans', 'doktora',
            'mühendislik', 'mühendisliği', 'bilgisayar', 'yazılım',
            'tıp', 'eczacılık', 'hemşirelik', 'psikoloji', 'beslenme',
            'fizik', 'kimya', 'matematik', 'biyoloji', 'mimarlık',
            'fizyoterapi', 'biyomedikal', 'moleküler', 'genetik',
            'biyokimya', 'eczane', 'programı', 'okuyabilir',
            'okumak', 'anestezi', 'radyoloji', 'ortopedi', 'nöroloji',
            'study', 'major', 'okumak istiyorum',
            'hakkında bilgi', 'about the program', 'tell me about',
        ]
        if self._contains_any(q, program_keywords):
            intents.add('program')

        dept_keywords = [
            'faculty', 'institute', 'college',
            'fakülte', 'enstitü', 'yüksekokul', 'meslek yüksekokulu',
            'akademik birim', 'birimler', 'units',
        ]
        if self._contains_any(q, dept_keywords):
            intents.add('department')

        course_keywords = [
            'course', 'class', 'lecture', 'subject', 'syllabus', 'credit', 'curriculum',
            'ders', 'kredi', 'müfredat', 'ders programı', 'ders listesi',
            'zorunlu ders', 'seçmeli ders', 'ders kodu', 'dersler',
            'kaç sene', 'kaç yıl', 'süre', 'duration',
        ]
        if self._contains_any(q, course_keywords):
            intents.add('course')

        general_keywords = [
            'university', 'about', 'location', 'history', 'founded', 'established',
            'üniversite', 'hakkında', 'tarihçe', 'kuruluş', 'ne zaman kuruldu',
            'nerede', 'nerededir', 'genel bilgi', 'acıbadem nedir',
            'acıbadem hakkında', 'misyon', 'vizyon', 'mission', 'vision',
        ]
        if self._contains_any(q, general_keywords):
            intents.add('general')

        contact_keywords = [
            'contact', 'phone', 'email', 'address', 'reach', 'call', 'website',
            'iletişim', 'telefon', 'e-posta', 'eposta', 'mail', 'adres',
            'ulaşmak', 'aramak', 'web sitesi',
        ]
        if self._contains_any(q, contact_keywords):
            intents.add('contact')
            intents.add('general')

        admission_keywords = [
            'admission', 'apply', 'application', 'requirement', 'entrance', 'enroll',
            'kabul', 'başvuru', 'kayıt', 'şart', 'koşul', 'nasıl girilir',
            'puan', 'taban puan', 'yks', 'sat', 'gre', 'gmat',
            'başvurmak', 'kabul şartları', 'girebilir miyim',
        ]
        if self._contains_any(q, admission_keywords):
            intents.add('admission')
            intents.add('general')

        scholarship_keywords = [
            'scholarship', 'bursary', 'financial aid', 'tuition', 'fee', 'cost',
            'burs', 'ücret', 'harç', 'ücretsiz', 'mali destek', 'indirim',
            'burs imkanı', 'burs var mı', 'ödeme', 'masraf',
        ]
        if self._contains_any(q, scholarship_keywords):
            intents.add('scholarship')
            intents.add('general')

        campus_keywords = [
            'campus', 'facility', 'facilities', 'library', 'dormitory',
            'housing', 'sport', 'cafeteria', 'laboratory', 'hospital', 'clinic',
            'kampüs', 'kütüphane', 'yurt', 'spor', 'kafeterya', 'laboratuvar',
            'hastane', 'klinik', 'sosyal imkan', 'tesis', 'olanak',
        ]
        if self._contains_any(q, campus_keywords):
            intents.add('campus')
            intents.add('general')

        international_keywords = [
            'international', 'foreign', 'exchange', 'erasmus', 'english medium',
            'english taught', 'abroad',
            'uluslararası', 'yabancı uyruklu', 'değişim programı',
            'ingilizce eğitim', 'yabancı öğrenci', 'çift diploma',
        ]
        if self._contains_any(q, international_keywords):
            intents.add('international')
            intents.add('general')

        career_keywords = [
            'career', 'job', 'employment', 'alumni', 'internship', 'placement',
            'kariyer', 'iş imkanı', 'istihdam', 'mezun', 'staj', 'iş bulma',
        ]
        if self._contains_any(q, career_keywords):
            intents.add('career')
            intents.add('general')

        research_keywords = [
            'research', 'publication', 'journal', 'project', 'scientific',
            'araştırma', 'yayın', 'proje', 'bilimsel', 'merkez', 'ar-ge',
        ]
        if self._contains_any(q, research_keywords):
            intents.add('research')
            intents.add('general')

        return intents

    def _get_faculty_program_map(self) -> list:
        all_programs = Program.objects.exclude(department='').exclude(department__isnull=True)
        grouped = defaultdict(list)
        for p in all_programs:
            grouped[p.department].append(p.name)
        result = []
        for dept_name in sorted(grouped.keys()):
            desc = ", ".join(grouped[dept_name])
            result.append({"name": dept_name, "description": desc, "email": "", "phone": ""})
        return result

    def _extract_semester_number(self, q: str) -> int | None:
        word_map = {
            'birinci': 1, 'first': 1, '1st': 1,
            'ikinci': 2, 'second': 2, '2nd': 2,
            'üçüncü': 3, 'third': 3, '3rd': 3,
            'dördüncü': 4, 'fourth': 4, '4th': 4,
            'beşinci': 5, 'fifth': 5, '5th': 5,
            'altıncı': 6, 'sixth': 6, '6th': 6,
            'yedinci': 7, 'seventh': 7, '7th': 7,
            'sekizinci': 8, 'eighth': 8, '8th': 8,
        }
        m = re.search(r'(\d+)\s*[.\-]?\s*(yarıyıl|dönem|semester|term)', q, re.IGNORECASE)
        if m:
            return int(m.group(1))
        for word, num in word_map.items():
            if word in q.lower():
                return num
        return None

    def _extract_program_name_from_query(self, q: str) -> str:
        """
        1. Tam substring eşleşmesi (en uzun olanı al)
        2. Fuzzy partial_ratio
        """
        all_program_names = list(
            Program.objects.values_list('name', flat=True).distinct()
        )
        if not all_program_names:
            return ""

        q_lower = q.lower()

        # 1. Exact substring — parantezi kaldırıp base adıyla karşılaştır
        exact_matches = []
        for prog_name in all_program_names:
            base_name = re.sub(r'\s*\(.*?\)', '', prog_name).strip()
            if base_name.lower() in q_lower:
                exact_matches.append((len(base_name), prog_name))

        if exact_matches:
            exact_matches.sort(reverse=True)
            chosen = exact_matches[0][1]
            logger.info(f"Exact match: '{chosen}'")
            return chosen

        # 2. Fuzzy partial_ratio — base adlarla karşılaştır
        best_name = ""
        best_score = 0
        for prog_name in all_program_names:
            base_name = re.sub(r'\s*\(.*?\)', '', prog_name).strip()
            score = fuzz.partial_ratio(q_lower, base_name.lower())
            if score > best_score:
                best_score = score
                best_name = prog_name

        logger.info(f"Fuzzy match: '{best_name}' score={best_score}")
        return best_name if best_score >= 70 else ""

    def _get_unique_semester_courses(self, course_filter: Q, limit: int = 50) -> list:
        """code+program_name bazında deduplicate et."""
        seen = set()
        unique = []
        for c in Course.objects.filter(course_filter).order_by('semester', 'type', 'code'):
            key = f"{c.code}|{c.program_name}|{c.semester}"
            if key not in seen:
                seen.add(key)
                unique.append(c)
            if len(unique) >= limit:
                break
        return unique

    def retrieve(self, question: str) -> dict:
        q = question.lower()

        context = {
            "programs": [], "courses": [], "departments": [],
            "general_info": None, "sources": [], "semantic": [],
            "intents": [], "semester_courses": None,
        }

        intents = self._detect_intents(q)
        context["intents"] = list(intents)
        logger.info(f"Detected intents: {intents}")

        # SEMANTIC — her zaman
        try:
            semantic_results = self.vector_store.search(question)
            for typ, obj in semantic_results:
                if typ == "program":
                    context["semantic"].append({
                        "type": "program", "name": obj.name,
                        "level": obj.level, "desc": obj.description or ""
                    })
                elif typ == "course":
                    context["semantic"].append({
                        "type": "course", "name": obj.name, "code": obj.code or ""
                    })
                elif typ == "department":
                    context["semantic"].append({
                        "type": "department", "name": obj.name, "desc": obj.description or ""
                    })
            if context["semantic"]:
                context["sources"].append("Semantic Search")
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")

        # CONTACT — erken dön
        if 'contact' in intents and 'list' not in intents:
            uni = UniversityInfo.objects.first()
            if uni:
                context["general_info"] = {
                    "title": uni.title, "description": uni.description,
                    "mission": uni.mission, "vision": uni.vision,
                    "phone": uni.phone, "email": uni.email,
                    "address": getattr(uni, 'address', ''),
                    "website": getattr(uni, 'website', 'https://www.acibadem.edu.tr'),
                }
                context["sources"].append("University Information")
            return context

        # =====================
        # YARIYIL SORUSU — spesifik yarıyıl
        # =====================
        if 'semester' in intents and 'course' in intents:
            sem_num = self._extract_semester_number(q)
            prog_name = self._extract_program_name_from_query(q)
            logger.info(f"Semester query: sem={sem_num}, prog='{prog_name}'")

            course_filter = Q()
            if sem_num:
                course_filter &= Q(semester=sem_num)
            if prog_name:
                course_filter &= Q(program_name=prog_name)

            unique_courses = self._get_unique_semester_courses(course_filter)

            if not unique_courses and prog_name:
                course_filter2 = Q(semester=sem_num) if sem_num else Q()
                course_filter2 &= Q(program_name__icontains=prog_name[:15])
                unique_courses = self._get_unique_semester_courses(course_filter2)

            if unique_courses:
                context["semester_courses"] = {
                    "semester": sem_num,
                    "program": prog_name,
                    "all_semesters": False,
                    "courses": [
                        {"code": c.code, "name": c.name, "credits": c.credits,
                         "type": c.type, "tul": getattr(c, 'tul', ''),
                         "program_name": c.program_name, "semester": c.semester}
                        for c in unique_courses
                    ]
                }
                context["sources"].append("Curriculum Database")

            if prog_name:
                prog_results = self._search_db_fuzzy(Program, prog_name, ['name'])
                if prog_results:
                    context["programs"] = [
                        {"name": p.name, "level": p.level,
                         "department": p.department, "description": p.description or ""}
                        for p in prog_results[:2]
                    ]
                    if "Programs Database" not in context["sources"]:
                        context["sources"].append("Programs Database")

        # =====================
        # PROGRAM DERSLERİ — yarıyıl belirtmeden tüm müfredat
        # =====================
        if 'program_courses' in intents and 'semester' not in intents:
            prog_name = self._extract_program_name_from_query(q)
            logger.info(f"Program courses query: prog='{prog_name}'")

            if prog_name:
                unique_courses = self._get_unique_semester_courses(
                    Q(program_name=prog_name), limit=60
                )
                if not unique_courses:
                    unique_courses = self._get_unique_semester_courses(
                        Q(program_name__icontains=prog_name[:15]), limit=60
                    )

                if unique_courses:
                    context["semester_courses"] = {
                        "semester": None,
                        "program": prog_name,
                        "all_semesters": True,
                        "courses": [
                            {"code": c.code, "name": c.name, "credits": c.credits,
                             "type": c.type, "tul": getattr(c, 'tul', ''),
                             "program_name": c.program_name, "semester": c.semester}
                            for c in unique_courses
                        ]
                    }
                    context["sources"].append("Curriculum Database")

                prog_results = self._search_db_fuzzy(Program, prog_name, ['name'])
                if prog_results:
                    context["programs"] = [
                        {"name": p.name, "level": p.level,
                         "department": p.department, "description": p.description or ""}
                        for p in prog_results[:2]
                    ]
                    if "Programs Database" not in context["sources"]:
                        context["sources"].append("Programs Database")

        # DEPARTMENT LIST
        if 'list' in intents and 'department' in intents:
            dept_list = self._get_faculty_program_map()
            if dept_list:
                context["departments"] = dept_list
                context["sources"].append("Fakülte ve Program Listesi")

        # PROGRAM LIST
        elif 'list' in intents and 'program' in intents:
            all_programs = Program.objects.all().order_by('level', 'name')
            context["programs"] = [
                {"name": p.name, "level": p.level,
                 "department": str(p.department), "description": p.description or ""}
                for p in all_programs[:30]
            ]
            if context["programs"]:
                context["sources"].append("Tüm Programlar")

        # PROGRAM SEARCH
        if 'program' in intents and 'list' not in intents:
            results = self._search_db_fuzzy(Program, q, ['name', 'description', 'department'])
            context["programs"] = [
                {"name": p.name, "level": p.level,
                 "department": str(p.department), "description": p.description or ""}
                for p in results
            ]
            if context["programs"]:
                if "Programs Database" not in context["sources"]:
                    context["sources"].append("Programs Database")

        # DEPARTMENT SEARCH
        if 'department' in intents and 'list' not in intents and 'contact' not in intents:
            results = self._search_db_fuzzy(Department, q, ['name', 'description'])
            if results:
                context["departments"] = [
                    {"name": d.name, "description": d.description or "",
                     "email": d.email or "", "phone": d.phone or ""}
                    for d in results
                ]
                context["sources"].append("Departments Database")
            if len(context["departments"]) < 3:
                faculty_map = self._get_faculty_program_map()
                existing = {x["name"] for x in context["departments"]}
                for f in faculty_map:
                    if f["name"] not in existing:
                        context["departments"].append(f)

        # COURSE SEARCH
        if 'course' in intents and 'semester' not in intents and 'program_courses' not in intents:
            if 'list' in intents:
                seen = set()
                unique = []
                for c in Course.objects.all().order_by('code'):
                    if c.code not in seen:
                        seen.add(c.code)
                        unique.append(c)
                    if len(unique) >= 40:
                        break
                context["courses"] = [
                    {"code": c.code, "name": c.name, "credits": c.credits,
                     "type": c.type, "program_name": c.program_name, "semester": c.semester}
                    for c in unique
                ]
            else:
                results = self._search_db_fuzzy(Course, q, ['name', 'code', 'program_name'])
                context["courses"] = [
                    {"code": c.code, "name": c.name, "credits": c.credits,
                     "type": c.type, "program_name": c.program_name, "semester": c.semester}
                    for c in results
                ]
            if context["courses"]:
                context["sources"].append("Courses Database")

        # GENERAL INFO
        if intents & {'general', 'admission', 'scholarship', 'campus',
                      'international', 'career', 'research'}:
            if not context["general_info"]:
                uni = UniversityInfo.objects.first()
                if uni:
                    context["general_info"] = {
                        "title": uni.title, "description": uni.description,
                        "mission": uni.mission, "vision": uni.vision,
                        "phone": uni.phone, "email": uni.email,
                        "address": getattr(uni, 'address', ''),
                        "website": getattr(uni, 'website', 'https://www.acibadem.edu.tr'),
                    }
                    context["sources"].append("University Information")

        # FALLBACK
        if not context["sources"]:
            uni = UniversityInfo.objects.first()
            if uni:
                context["general_info"] = {
                    "title": uni.title, "description": uni.description,
                    "mission": uni.mission, "vision": uni.vision,
                    "phone": uni.phone, "email": uni.email,
                    "address": getattr(uni, 'address', ''),
                    "website": getattr(uni, 'website', 'https://www.acibadem.edu.tr'),
                }
            context["programs"] = [
                {"name": p.name, "level": p.level,
                 "department": str(p.department), "description": p.description or ""}
                for p in Program.objects.all()[:5]
            ]
            context["sources"].append("Fallback Data")

        return context