"""
Load scraped data into PostgreSQL database.
Course modeli artık program_name, program_level, semester alanlarına sahip.
NOT: Aynı ders kodu farklı programlarda farklı kayıt olarak tutulur.
     Bu nedenle Course.code artık unique değil — migration gerekebilir.
"""

import json
import logging
from chat.models import Program, Course, Department, UniversityInfo

logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(self, json_file):
        self.json_file = json_file
        self.data = None

    def load_json(self) -> bool:
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            logger.info(f"JSON loaded: {self.json_file}")
            return True
        except Exception as e:
            logger.error(f"JSON load error: {e}")
            return False

    def load_into_db(self) -> bool:
        if not self.data:
            logger.error("No data. Call load_json() first.")
            return False
        try:
            counts = {
                "uni":      self._load_general_info(),
                "depts":    self._load_departments(),
                "programs": self._load_programs(),
                "courses":  self._load_courses(),
            }
            logger.info(f"DB load complete: {counts}")
            return True
        except Exception as e:
            logger.error(f"DB load error: {e}")
            return False

    def _load_general_info(self) -> int:
        general = self.data.get('static_content', {}).get('general_info', {})
        contact = self.data.get('static_content', {}).get('contact_info', {})
        if not general:
            return 0
        addresses = contact.get('addresses', [])
        address_str = ", ".join(addresses) if addresses else ""
        UniversityInfo.objects.update_or_create(
            id=1,
            defaults={
                'title':       general.get('title', ''),
                'description': general.get('meta_description', ''),
                'mission':     general.get('mission', ''),
                'vision':      general.get('vision', ''),
                'phone':       contact.get('main_phone', ''),
                'email':       contact.get('main_email', ''),
                'address':     address_str,
                'website':     'https://www.acibadem.edu.tr',
            }
        )
        return 1

    def _load_departments(self) -> int:
        depts = self.data.get('static_content', {}).get('departments', [])
        count = 0
        for dept in depts:
            name = dept.get('name', '').strip()
            if not name:
                continue
            Department.objects.update_or_create(
                name=name,
                defaults={
                    'description': dept.get('description', ''),
                    'email':       dept.get('email', ''),
                    'phone':       dept.get('phone', ''),
                    'link':        dept.get('link', ''),
                    'source':      dept.get('source', 'acibadem.edu.tr'),
                }
            )
            count += 1
        return count

    def _load_programs(self) -> int:
        programs = self.data.get('merged_data', {}).get('all_programs', [])
        count = 0
        for prog in programs:
            name = prog.get('name', '').strip()
            if not name or len(name) > 300:
                continue
            Program.objects.update_or_create(
                name=name,
                defaults={
                    'level':       prog.get('level', ''),
                    'duration':    prog.get('duration', ''),
                    'department':  prog.get('department', ''),
                    'language':    prog.get('language', ''),
                    'description': prog.get('description', ''),
                    'link':        prog.get('link', ''),
                    'sources':     [prog.get('source', 'unknown')],
                }
            )
            count += 1
        return count

    def _load_courses(self) -> int:
        courses = self.data.get('dynamic_content', {}).get('courses', [])
        count = 0
        # Önce tüm dersleri sil, temiz yükle
        Course.objects.all().delete()
        
        for course in courses:
            code = course.get('code', '').strip()
            name = course.get('name', '').strip()
            program_name = course.get('program_name', '').strip()
            if not code or not name:
                continue
            try:
                Course.objects.create(
                    code=code,
                    name=name,
                    credits=course.get('credits', ''),
                    type=course.get('type', ''),
                    tul=course.get('tul', ''),
                    program_name=program_name,
                    program_level=course.get('program_level', ''),
                    semester=course.get('semester'),
                    source='obs.acibadem.edu.tr',
                )
                count += 1
            except Exception as e:
                logger.debug(f"Course skip {code}/{program_name}: {e}")
        
        logger.info(f"Courses loaded: {count}")
        return count
