import json
import logging
import os
import sys
import django

# Django setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'webapp', 'BotBoxWeb'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BotBoxWeb.settings')
django.setup()

from chat.models import UniversityInfo, Department, Program, Course

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads scraped JSON data into PostgreSQL via Django ORM.
    """

    def __init__(self, json_file: str = 'data/acibadem_complete_data.json'):
        self.json_file = json_file
        self.data = None

    def load_json(self) -> bool:
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            logger.info(f"✓ JSON loaded from {self.json_file}")
            return True
        except FileNotFoundError:
            logger.error(f"✗ File not found: {self.json_file}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"✗ JSON parse error: {e}")
            return False

    def load_university_info(self) -> int:
        general = self.data.get('static_content', {}).get('general_info', {})
        contact = self.data.get('static_content', {}).get('contact_info', {})

        if not general:
            logger.warning("⚠ No general info found")
            return 0

        obj, created = UniversityInfo.objects.update_or_create(
            title="Acıbadem University",
            defaults={
                'description': general.get('meta_description', ''),
                'mission': general.get('mission', ''),
                'vision': general.get('vision', ''),
                'phone': contact.get('main_phone', ''),
                'email': contact.get('main_email', ''),
            }
        )

        action = "created" if created else "updated"
        logger.info(f"✓ University info {action}")
        return 1

    def load_departments(self) -> int:
        departments = self.data.get('static_content', {}).get('departments', [])
        if not departments:
            logger.warning("⚠ No departments found")
            return 0

        count = 0
        for dept in departments:
            name = dept.get('name', '').strip()
            if not name:
                continue

            Department.objects.update_or_create(
                name=name,
                defaults={
                    'description': dept.get('description', ''),
                    'email': dept.get('email', ''),
                    'phone': dept.get('phone', ''),
                    'link': dept.get('link', ''),
                    'source': dept.get('source', 'acibadem.edu.tr'),
                }
            )
            count += 1

        logger.info(f"✓ {count} departments loaded")
        return count

    def load_programs(self) -> int:
        all_programs = self.data.get('merged_data', {}).get('all_programs', [])
        if not all_programs:
            logger.warning("⚠ No programs found")
            return 0

        count = 0
        for prog in all_programs:
            name = prog.get('name', '').strip()
            if not name:
                continue

            # Level normalize et
            level_raw = prog.get('level', 'Bachelor')
            level_map = {
                'undergraduate': 'Bachelor',
                'bachelor': 'Bachelor',
                'master': 'Master',
                'masters': 'Master',
                'phd': 'PhD',
                'doctorate': 'PhD',
                'associate': 'Certificate',
                'certificate': 'Certificate',
            }
            level = level_map.get(level_raw.lower(), 'Bachelor')

            Program.objects.update_or_create(
                name=name,
                defaults={
                    'level': level,
                    'duration': prog.get('duration', ''),
                    'department': prog.get('department', ''),
                    'description': prog.get('description', ''),
                    'sources': prog.get('sources', [prog.get('source', '')]),
                }
            )
            count += 1

        logger.info(f"✓ {count} programs loaded")
        return count

    def load_courses(self) -> int:
        courses = self.data.get('dynamic_content', {}).get('courses', [])
        if not courses:
            logger.warning("⚠ No courses found")
            return 0

        count = 0
        for course in courses:
            code = course.get('code', '').strip()
            name = course.get('name', '').strip()
            if not code or not name:
                continue

            Course.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'credits': course.get('credits', ''),
                    'type': course.get('type', ''),
                    'source': course.get('source', 'obs.acibadem.edu.tr'),
                }
            )
            count += 1

        logger.info(f"✓ {count} courses loaded")
        return count

    def load_all(self) -> bool:
        logger.info("=" * 50)
        logger.info("Starting data load into PostgreSQL...")
        logger.info("=" * 50)

        if not self.load_json():
            return False

        total = 0
        total += self.load_university_info()
        total += self.load_departments()
        total += self.load_programs()
        total += self.load_courses()

        logger.info("=" * 50)
        logger.info(f"✓ Done! Total {total} records loaded into DB")
        logger.info("=" * 50)
        return True


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Load scraped data into PostgreSQL')
    parser.add_argument(
        '--file',
        default='data/acibadem_complete_data.json',
        help='Path to JSON file'
    )
    args = parser.parse_args()

    loader = DataLoader(json_file=args.file)
    success = loader.load_all()
    sys.exit(0 if success else 1)