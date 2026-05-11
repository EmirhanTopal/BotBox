"""
Tests for DataLoader
- JSON loading (success, failure, missing file)
- DB loading (programs, courses, departments, instructors, university info)
- Duplicate handling (update_or_create)
- Edge cases (empty data, missing fields, invalid data)
"""
import json
import pytest
from django.test import TestCase
from chat.models import Program, Course, Department, UniversityInfo, Instructor
from scraper.data_loader import DataLoader


def make_sample_data(**overrides):
    """Test için örnek JSON verisi oluştur."""
    data = {
        "static_content": {
            "general_info": {
                "title": "Acıbadem Üniversitesi",
                "meta_description": "Test açıklaması",
                "mission": "Test misyon",
                "vision": "Test vizyon",
            },
            "contact_info": {
                "main_phone": "0212 000 0000",
                "main_email": "test@acibadem.edu.tr",
                "addresses": ["İstanbul, Türkiye"],
            },
            "departments": [
                {
                    "name": "Mühendislik Fakültesi",
                    "description": "Mühendislik bölümleri",
                    "email": "muhendislik@acibadem.edu.tr",
                    "phone": "0212 000 0001",
                    "link": "https://acibadem.edu.tr/muhendislik",
                    "source": "acibadem.edu.tr",
                }
            ],
        },
        "merged_data": {
            "all_programs": [
                {
                    "name": "Bilgisayar Mühendisliği (İngilizce)",
                    "level": "Bachelor",
                    "duration": "4 yıl",
                    "department": "Mühendislik Fakültesi",
                    "language": "İngilizce",
                    "description": "Bilgisayar mühendisliği programı",
                    "link": "https://acibadem.edu.tr/cse",
                    "source": "obs.acibadem.edu.tr",
                }
            ]
        },
        "dynamic_content": {
            "courses": [
                {
                    "code": "CSE 101",
                    "name": "Programlamaya Giriş",
                    "credits": "6",
                    "type": "Zorunlu",
                    "tul": "3+0+2",
                    "program_name": "Bilgisayar Mühendisliği (İngilizce)",
                    "program_level": "Bachelor",
                    "semester": 1,
                    "source": "obs.acibadem.edu.tr",
                }
            ],
            "instructors": [
                {
                    "name": "Ahmet Bulut",
                    "title": "Prof. Dr.",
                    "email": "ahmet@acibadem.edu.tr",
                    "department": "Mühendislik Fakültesi",
                    "faculty": "Mühendislik Fakültesi",
                    "expertise": "Yapay Zeka",
                    "profile_url": "https://acibadem.edu.tr/ahmet",
                    "level": "Lisans",
                    "source": "https://acibadem.edu.tr/akademik/lisans/muhendislik",
                }
            ],
        },
    }
    data.update(overrides)
    return data


class TestDataLoaderInit(TestCase):

    def test_init(self):
        loader = DataLoader('/tmp/test.json')
        assert loader.json_file == '/tmp/test.json'
        assert loader.data is None


class TestLoadJson(TestCase):

    def test_load_json_success(self, tmp_path=None):
        import tempfile, os
        data = make_sample_data()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            path = f.name
        try:
            loader = DataLoader(path)
            result = loader.load_json()
            assert result is True
            assert loader.data is not None
            assert 'static_content' in loader.data
        finally:
            os.unlink(path)

    def test_load_json_missing_file(self):
        loader = DataLoader('/nonexistent/path/file.json')
        result = loader.load_json()
        assert result is False
        assert loader.data is None

    def test_load_json_invalid_json(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{ invalid json }')
            path = f.name
        try:
            loader = DataLoader(path)
            result = loader.load_json()
            assert result is False
        finally:
            os.unlink(path)


class TestLoadIntoDb(TestCase):

    def setUp(self):
        import tempfile, os
        self.data = make_sample_data()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)
            self.json_path = f.name
        self.loader = DataLoader(self.json_path)
        self.loader.load_json()

    def tearDown(self):
        import os
        os.unlink(self.json_path)

    def test_load_into_db_returns_true(self):
        result = self.loader.load_into_db()
        assert result is True

    def test_load_into_db_without_load_json(self):
        loader = DataLoader('/tmp/test.json')
        result = loader.load_into_db()
        assert result is False

    def test_load_into_db_all_models_populated(self):
        self.loader.load_into_db()
        assert UniversityInfo.objects.count() == 1
        assert Department.objects.count() == 1
        assert Program.objects.count() == 1
        assert Course.objects.count() == 1
        assert Instructor.objects.count() == 1


class TestLoadGeneralInfo(TestCase):

    def setUp(self):
        import tempfile
        self.data = make_sample_data()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)
            self.json_path = f.name
        self.loader = DataLoader(self.json_path)
        self.loader.load_json()

    def tearDown(self):
        import os
        os.unlink(self.json_path)

    def test_loads_university_info(self):
        self.loader._load_general_info()
        uni = UniversityInfo.objects.get(id=1)
        assert uni.title == 'Acıbadem Üniversitesi'
        assert uni.description == 'Test açıklaması'
        assert uni.mission == 'Test misyon'
        assert uni.phone == '0212 000 0000'
        assert uni.email == 'test@acibadem.edu.tr'
        assert uni.address == 'İstanbul, Türkiye'
        assert uni.website == 'https://www.acibadem.edu.tr'

    def test_update_existing_university_info(self):
        self.loader._load_general_info()
        # İkinci kez çağırınca update etmeli
        self.loader.data['static_content']['general_info']['title'] = 'Güncellenmiş Üniversite'
        self.loader._load_general_info()
        assert UniversityInfo.objects.count() == 1
        uni = UniversityInfo.objects.get(id=1)
        assert uni.title == 'Güncellenmiş Üniversite'

    def test_returns_0_when_no_general_info(self):
        self.loader.data['static_content']['general_info'] = {}
        result = self.loader._load_general_info()
        assert result == 0

    def test_multiple_addresses_joined(self):
        self.loader.data['static_content']['contact_info']['addresses'] = ['Adres 1', 'Adres 2']
        self.loader._load_general_info()
        uni = UniversityInfo.objects.get(id=1)
        assert 'Adres 1' in uni.address
        assert 'Adres 2' in uni.address


class TestLoadDepartments(TestCase):

    def setUp(self):
        import tempfile
        self.data = make_sample_data()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)
            self.json_path = f.name
        self.loader = DataLoader(self.json_path)
        self.loader.load_json()

    def tearDown(self):
        import os
        os.unlink(self.json_path)

    def test_loads_department(self):
        count = self.loader._load_departments()
        assert count == 1
        dept = Department.objects.get(name='Mühendislik Fakültesi')
        assert dept.description == 'Mühendislik bölümleri'
        assert dept.email == 'muhendislik@acibadem.edu.tr'

    def test_skips_empty_name(self):
        self.loader.data['static_content']['departments'].append({'name': '', 'description': 'Boş'})
        count = self.loader._load_departments()
        assert count == 1

    def test_update_existing_department(self):
        self.loader._load_departments()
        self.loader.data['static_content']['departments'][0]['description'] = 'Güncellenmiş'
        self.loader._load_departments()
        assert Department.objects.count() == 1
        dept = Department.objects.get(name='Mühendislik Fakültesi')
        assert dept.description == 'Güncellenmiş'

    def test_empty_departments_list(self):
        self.loader.data['static_content']['departments'] = []
        count = self.loader._load_departments()
        assert count == 0


class TestLoadPrograms(TestCase):

    def setUp(self):
        import tempfile
        self.data = make_sample_data()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)
            self.json_path = f.name
        self.loader = DataLoader(self.json_path)
        self.loader.load_json()

    def tearDown(self):
        import os
        os.unlink(self.json_path)

    def test_loads_program(self):
        count = self.loader._load_programs()
        assert count == 1
        prog = Program.objects.get(name='Bilgisayar Mühendisliği (İngilizce)')
        assert prog.level == 'Bachelor'
        assert prog.duration == '4 yıl'
        assert prog.department == 'Mühendislik Fakültesi'
        assert prog.language == 'İngilizce'

    def test_skips_empty_name(self):
        self.loader.data['merged_data']['all_programs'].append({'name': '', 'level': 'Bachelor'})
        count = self.loader._load_programs()
        assert count == 1

    def test_skips_too_long_name(self):
        self.loader.data['merged_data']['all_programs'].append({'name': 'A' * 301, 'level': 'Bachelor'})
        count = self.loader._load_programs()
        assert count == 1

    def test_update_existing_program(self):
        self.loader._load_programs()
        self.loader.data['merged_data']['all_programs'][0]['duration'] = '5 yıl'
        self.loader._load_programs()
        assert Program.objects.count() == 1
        prog = Program.objects.get(name='Bilgisayar Mühendisliği (İngilizce)')
        assert prog.duration == '5 yıl'

    def test_sources_set_correctly(self):
        self.loader._load_programs()
        prog = Program.objects.get(name='Bilgisayar Mühendisliği (İngilizce)')
        assert prog.sources == ['obs.acibadem.edu.tr']

    def test_empty_programs_list(self):
        self.loader.data['merged_data']['all_programs'] = []
        count = self.loader._load_programs()
        assert count == 0


class TestLoadCourses(TestCase):

    def setUp(self):
        import tempfile
        self.data = make_sample_data()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)
            self.json_path = f.name
        self.loader = DataLoader(self.json_path)
        self.loader.load_json()

    def tearDown(self):
        import os
        os.unlink(self.json_path)

    def test_loads_course(self):
        count = self.loader._load_courses()
        assert count == 1
        course = Course.objects.get(code='CSE 101')
        assert course.name == 'Programlamaya Giriş'
        assert course.credits == '6'
        assert course.type == 'Zorunlu'
        assert course.semester == 1
        assert course.program_name == 'Bilgisayar Mühendisliği (İngilizce)'

    def test_deletes_existing_courses_before_load(self):
        Course.objects.create(code='OLD 101', name='Eski Ders', program_name='Eski Program')
        self.loader._load_courses()
        assert Course.objects.filter(code='OLD 101').count() == 0

    def test_skips_missing_code(self):
        self.loader.data['dynamic_content']['courses'].append({'code': '', 'name': 'Kodsuz Ders'})
        count = self.loader._load_courses()
        assert count == 1

    def test_skips_missing_name(self):
        self.loader.data['dynamic_content']['courses'].append({'code': 'TST 999', 'name': ''})
        count = self.loader._load_courses()
        assert count == 1

    def test_multiple_courses_same_code_different_program(self):
        self.loader.data['dynamic_content']['courses'].append({
            'code': 'CSE 101',
            'name': 'Programlamaya Giriş',
            'program_name': 'Farklı Program',
            'semester': 1,
        })
        count = self.loader._load_courses()
        assert count == 2
        assert Course.objects.filter(code='CSE 101').count() == 2

    def test_empty_courses_list(self):
        self.loader.data['dynamic_content']['courses'] = []
        count = self.loader._load_courses()
        assert count == 0

    def test_source_set_to_obs(self):
        self.loader._load_courses()
        course = Course.objects.get(code='CSE 101')
        assert course.source == 'obs.acibadem.edu.tr'


class TestLoadInstructors(TestCase):

    def setUp(self):
        import tempfile
        self.data = make_sample_data()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)
            self.json_path = f.name
        self.loader = DataLoader(self.json_path)
        self.loader.load_json()

    def tearDown(self):
        import os
        os.unlink(self.json_path)

    def test_loads_instructor(self):
        count = self.loader._load_instructors()
        assert count == 1
        inst = Instructor.objects.get(name='Ahmet Bulut')
        assert inst.title == 'Prof. Dr.'
        assert inst.faculty == 'Mühendislik Fakültesi'
        assert inst.department == 'Mühendislik Fakültesi'
        assert inst.level == 'Lisans'

    def test_deletes_existing_instructors_before_load(self):
        Instructor.objects.create(name='Eski Hoca', faculty='Eski Fakülte')
        self.loader._load_instructors()
        assert Instructor.objects.filter(name='Eski Hoca').count() == 0

    def test_skips_short_name(self):
        self.loader.data['dynamic_content']['instructors'].append({'name': 'AB', 'faculty': 'Test'})
        count = self.loader._load_instructors()
        assert count == 1

    def test_skips_empty_name(self):
        self.loader.data['dynamic_content']['instructors'].append({'name': '', 'faculty': 'Test'})
        count = self.loader._load_instructors()
        assert count == 1

    def test_update_existing_instructor(self):
        self.loader._load_instructors()
        self.loader.data['dynamic_content']['instructors'][0]['title'] = 'Doç. Dr.'
        self.loader._load_instructors()
        assert Instructor.objects.count() == 1
        inst = Instructor.objects.get(name='Ahmet Bulut')
        assert inst.title == 'Doç. Dr.'

    def test_same_name_different_faculty(self):
        self.loader.data['dynamic_content']['instructors'].append({
            'name': 'Ahmet Bulut',
            'title': 'Dr.',
            'faculty': 'Farklı Fakülte',
            'department': 'Farklı Bölüm',
        })
        count = self.loader._load_instructors()
        assert count == 2
        assert Instructor.objects.filter(name='Ahmet Bulut').count() == 2

    def test_empty_instructors_list(self):
        self.loader.data['dynamic_content']['instructors'] = []
        count = self.loader._load_instructors()
        assert count == 0