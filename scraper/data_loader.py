"""
Load scraped data into PostgreSQL database
"""

import json
import logging
from django.core.management.base import BaseCommand
from chat.models import Program, Course, Department, UniversityInfo

logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, json_file):
        self.json_file = json_file
        self.data = None
    
    def load_json(self):
        """Load JSON data from file"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            logger.info(f"Loaded data from {self.json_file}")
            return True
        except Exception as e:
            logger.error(f"Error loading JSON: {e}")
            return False
    
    def load_into_db(self):
        """Load all data into database"""
        if not self.data:
            logger.error("No data loaded. Call load_json() first.")
            return False
        
        try:
            # Load university info
            self._load_general_info()
            
            # Load departments
            self._load_departments()
            
            # Load programs
            self._load_programs()
            
            # Load courses
            self._load_courses()
            
            logger.info("All data loaded into database successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading data into database: {e}")
            return False
    
    def _load_general_info(self):
        """Load general university information"""
        general = self.data.get('static_content', {}).get('general_info', {})
        contact = self.data.get('static_content', {}).get('contact_info', {})
        
        if general:
            UniversityInfo.objects.update_or_create(
                id=1,
                defaults={
                    'title': general.get('title', ''),
                    'description': general.get('meta_description', ''),
                    'mission': general.get('mission', ''),
                    'vision': general.get('vision', ''),
                    'phone': contact.get('main_phone', ''),
                    'email': contact.get('main_email', ''),
                }
            )
    
    def _load_departments(self):
        """Load departments"""
        depts = self.data.get('static_content', {}).get('departments', [])
        
        for dept in depts:
            Department.objects.update_or_create(
                name=dept.get('name', ''),
                defaults={
                    'description': dept.get('description', ''),
                    'email': dept.get('email', ''),
                    'phone': dept.get('phone', ''),
                    'link': dept.get('link', ''),
                    'source': dept.get('source', 'acibadem.edu.tr')
                }
            )
    
    def _load_programs(self):
        """Load programs from merged data"""
        programs = self.data.get('merged_data', {}).get('all_programs', [])
        
        for prog in programs:
            Program.objects.update_or_create(
                name=prog.get('name', ''),
                defaults={
                    'level': prog.get('level', ''),
                    'duration': prog.get('duration', ''),
                    'department': prog.get('department', ''),
                    'description': prog.get('description', ''),
                    'sources': [prog.get('source', 'unknown')]
                }
            )
    
    def _load_courses(self):
        """Load courses from dynamic content"""
        courses = self.data.get('dynamic_content', {}).get('courses', [])
        
        for course in courses:
            Course.objects.update_or_create(
                code=course.get('code', ''),
                defaults={
                    'name': course.get('name', ''),
                    'credits': course.get('credits', ''),
                    'type': course.get('type', ''),
                    'source': 'obs.acibadem.edu.tr'
                }
            )