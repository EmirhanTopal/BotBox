"""Information retrieval service"""

import logging
from django.db.models import Q
from chat.models import Program, Course, Department, UniversityInfo

logger = logging.getLogger(__name__)

class RetrievalService:
    """Retrieve relevant information from database"""
    
    def __init__(self):
        self.max_results = 5

    def _extract_academic_units(self):
        """Extract faculty/school names from scraped program names."""
        known_units = [
            'School of Medicine',
            'Faculty of Pharmacy',
            'Faculty of Health Sciences',
            'Faculty of Humanities and Social Sciences',
            'Faculty of Engineering and Natural Sciences',
        ]
        program_names = Program.objects.values_list('name', flat=True)
        found_units = []

        for unit in known_units:
            if any(unit.lower() in name.lower() for name in program_names):
                found_units.append(unit)

        return found_units
    
    def retrieve(self, question: str) -> dict:
        """
        Retrieve relevant information for a question
        """
        question_lower = question.lower()
        context = {
            'programs': [],
            'courses': [],
            'departments': [],
            'general_info': None,
            'summary': None,
            'sources': []
        }

        wants_count = any(word in question_lower for word in ['how many', 'count', 'number of', 'kaç', 'kac'])
        asks_faculties = any(word in question_lower for word in ['faculty', 'faculties', 'school', 'fakülte', 'fakulte'])

        if asks_faculties:
            units = self._extract_academic_units()
            faculty_department = Department.objects.filter(name__iexact='FACULTIES').first()

            context['departments'] = [
                {
                    'name': unit,
                    'description': '',
                    'email': '',
                    'phone': ''
                }
                for unit in units[:self.max_results]
            ]

            if not context['departments'] and faculty_department:
                context['departments'] = [{
                    'name': faculty_department.name,
                    'description': faculty_department.description,
                    'email': faculty_department.email,
                    'phone': faculty_department.phone
                }]

            if units:
                context['summary'] = (
                    f"Acibadem University has {len(units)} faculty/school units in the scraped data: "
                    f"{', '.join(units)}."
                )
                context['sources'].append('Programs Database')
            elif faculty_department:
                context['summary'] = (
                    f"The scraped departments data includes a FACULTIES record: "
                    f"{faculty_department.description}."
                )
                context['sources'].append('Departments Database')

            if wants_count and context['summary']:
                logger.info(f"Retrieved context for: {question}")
                return context
        
        # Search for programs
        if any(word in question_lower for word in ['program', 'degree', 'bachelor', 'master', 'phd']):
            programs = Program.objects.filter(
                Q(name__icontains=question_lower) |
                Q(description__icontains=question_lower) |
                Q(department__icontains=question_lower)
            )[:self.max_results]

            if not programs:
                programs = Program.objects.all()[:self.max_results]

            context['programs'] = [
                {
                    'name': p.name,
                    'level': p.level,
                    'department': p.department,
                    'description': p.description
                }
                for p in programs
            ]
            if context['programs']:
                context['sources'].append('Programs Database')
        
        # Search for courses
        if any(word in question_lower for word in ['course', 'class', 'subject']):
            courses = Course.objects.filter(
                Q(name__icontains=question_lower) |
                Q(code__icontains=question_lower)
            )[:self.max_results]
            context['courses'] = [
                {
                    'code': c.code,
                    'name': c.name,
                    'credits': c.credits,
                    'type': c.type
                }
                for c in courses
            ]
            if context['courses']:
                context['sources'].append('Courses Database')
        
        # Search for departments
        if any(word in question_lower for word in ['department', 'faculty', 'school']):
            depts = Department.objects.filter(
                Q(name__icontains=question_lower) |
                Q(description__icontains=question_lower)
            )[:self.max_results]

            if not depts and not context['departments']:
                depts = Department.objects.all()[:self.max_results]

            if depts:
                context['departments'] = [
                    {
                        'name': d.name,
                        'description': d.description,
                        'email': d.email,
                        'phone': d.phone
                    }
                    for d in depts
                ]
            if context['departments']:
                context['sources'].append('Departments Database')
        
        # Get general info for common questions
        if any(word in question_lower for word in ['where', 'location', 'contact', 'phone', 'email', 'university', 'about']):
            try:
                uni_info = UniversityInfo.objects.first()
                if uni_info:
                    context['general_info'] = {
                        'title': uni_info.title,
                        'description': uni_info.description,
                        'mission': uni_info.mission,
                        'vision': uni_info.vision,
                        'phone': uni_info.phone,
                        'email': uni_info.email
                    }
                    context['sources'].append('University Information')
            except:
                pass
        
        logger.info(f"Retrieved context for: {question}")
        return context
