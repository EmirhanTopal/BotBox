"""
Tests for LLMService
- Unit tests: _build_system_prompt, _build_prompt, _fallback_answer, _get_example
- Integration tests: generate_answer (Ollama mock'lanır)
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from chat.services.llm_integration import LLMService


class TestBuildSystemPrompt(TestCase):
    """_build_system_prompt testleri"""

    def setUp(self):
        self.service = LLMService()

    def test_base_prompt_always_present(self):
        prompt = self.service._build_system_prompt({})
        assert 'Acıbadem Üniversitesi' in prompt
        assert 'SADECE verilen verileri kullan' in prompt
        assert 'AKTS' in prompt

    def test_semester_intent_adds_instruction(self):
        context = {'intents': ['semester', 'course'], 'semester_courses': None}
        prompt = self.service._build_system_prompt(context)
        assert 'YARIYIL SORUSU' in prompt

    def test_all_semesters_adds_curriculum_instruction(self):
        context = {
            'intents': ['program_courses'],
            'semester_courses': {'all_semesters': True, 'courses': []}
        }
        prompt = self.service._build_system_prompt(context)
        assert 'MÜFREDAT SORUSU' in prompt

    def test_list_department_adds_format(self):
        context = {'intents': ['list', 'department'], 'semester_courses': None}
        prompt = self.service._build_system_prompt(context)
        assert 'FORMAT' in prompt
        assert 'Fakülteleri' in prompt

    def test_list_program_adds_format(self):
        context = {'intents': ['list', 'program'], 'semester_courses': None}
        prompt = self.service._build_system_prompt(context)
        assert 'FORMAT' in prompt
        assert 'Programları' in prompt

    def test_instructor_intent_adds_instruction(self):
        context = {'intents': ['instructor'], 'semester_courses': None}
        prompt = self.service._build_system_prompt(context)
        assert 'AKADEMİSYEN' in prompt

    def test_contact_intent_adds_instruction(self):
        context = {'intents': ['contact'], 'semester_courses': None}
        prompt = self.service._build_system_prompt(context)
        assert 'İLETİŞİM' in prompt

    def test_admission_intent_adds_instruction(self):
        context = {'intents': ['admission'], 'semester_courses': None}
        prompt = self.service._build_system_prompt(context)
        assert 'BAŞVURU' in prompt

    def test_scholarship_intent_adds_instruction(self):
        context = {'intents': ['scholarship'], 'semester_courses': None}
        prompt = self.service._build_system_prompt(context)
        assert 'BURS' in prompt

    def test_international_intent_adds_instruction(self):
        context = {'intents': ['international'], 'semester_courses': None}
        prompt = self.service._build_system_prompt(context)
        assert 'ULUSLARARASI' in prompt

    def test_career_intent_adds_instruction(self):
        context = {'intents': ['career'], 'semester_courses': None}
        prompt = self.service._build_system_prompt(context)
        assert 'KARİYER' in prompt

    def test_empty_intents(self):
        context = {'intents': [], 'semester_courses': None}
        prompt = self.service._build_system_prompt(context)
        assert 'Acıbadem' in prompt


class TestBuildPrompt(TestCase):
    """_build_prompt testleri"""

    def setUp(self):
        self.service = LLMService()

    def _base_context(self, **kwargs):
        ctx = {
            'intents': [],
            'semester_courses': None,
            'semantic': [],
            'departments': [],
            'programs': [],
            'courses': [],
            'instructors': [],
            'general_info': None,
            'sources': [],
        }
        ctx.update(kwargs)
        return ctx

    def test_prompt_contains_required_sections(self):
        context = self._base_context()
        prompt = self.service._build_prompt('test sorusu', context)
        assert '[YARIYIL DERSLERİ]' in prompt
        assert '[SEMANTİK ARAMA]' in prompt
        assert '[FAKÜLTELER]' in prompt
        assert '[AKADEMİSYENLER]' in prompt
        assert '[PROGRAMLAR]' in prompt
        assert '[DERSLER]' in prompt
        assert '[GENEL BİLGİ]' in prompt
        assert 'SORU: test sorusu' in prompt
        assert 'CEVAP:' in prompt

    def test_empty_sections_show_veri_yok(self):
        context = self._base_context()
        prompt = self.service._build_prompt('soru', context)
        assert '(veri yok)' in prompt

    def test_semester_courses_single_included(self):
        context = self._base_context(
            semester_courses={
                'semester': 1,
                'program': 'Bilgisayar Mühendisliği',
                'all_semesters': False,
                'courses': [
                    {'code': 'CSE 101', 'name': 'Programlama', 'credits': '6', 'type': 'Zorunlu'}
                ]
            }
        )
        prompt = self.service._build_prompt('1. yarıyıl', context)
        assert 'CSE 101' in prompt
        assert 'Programlama' in prompt
        assert '1. Yarıyıl' in prompt

    def test_semester_courses_all_semesters(self):
        context = self._base_context(
            semester_courses={
                'semester': None,
                'program': 'Hemşirelik',
                'all_semesters': True,
                'courses': [
                    {'code': 'HEM 101', 'name': 'Temel Hemşirelik', 'credits': '5', 'type': 'Zorunlu', 'semester': 1},
                    {'code': 'HEM 201', 'name': 'Klinik Hemşirelik', 'credits': '6', 'type': 'Zorunlu', 'semester': 2},
                ]
            }
        )
        prompt = self.service._build_prompt('müfredat', context)
        assert 'Hemşirelik' in prompt
        assert 'HEM 101' in prompt
        assert '1. Yarıyıl' in prompt
        assert '2. Yarıyıl' in prompt

    def test_programs_included(self):
        context = self._base_context(
            programs=[
                {'name': 'Bilgisayar Mühendisliği', 'level': 'Bachelor', 'department': 'Mühendislik', 'duration': '4 yıl'}
            ]
        )
        prompt = self.service._build_prompt('program', context)
        assert 'Bilgisayar Mühendisliği' in prompt

    def test_instructors_included(self):
        context = self._base_context(
            instructors=[
                {'name': 'Ahmet Bulut', 'title': 'Prof. Dr.', 'faculty': 'Mühendislik', 'department': 'Mühendislik'}
            ]
        )
        prompt = self.service._build_prompt('hocalar', context)
        assert 'Ahmet Bulut' in prompt
        assert 'Prof. Dr.' in prompt

    def test_departments_included(self):
        context = self._base_context(
            departments=[
                {'name': 'Mühendislik Fakültesi', 'description': 'Mühendislik bölümleri', 'email': '', 'phone': ''}
            ]
        )
        prompt = self.service._build_prompt('fakülteler', context)
        assert 'Mühendislik Fakültesi' in prompt

    def test_general_info_included(self):
        context = self._base_context(
            general_info={
                'description': 'Acıbadem Üniversitesi açıklaması',
                'phone': '0212 000 0000',
                'email': 'info@acibadem.edu.tr',
                'address': 'İstanbul',
                'website': 'https://www.acibadem.edu.tr',
            }
        )
        prompt = self.service._build_prompt('üniversite', context)
        assert 'Acıbadem Üniversitesi açıklaması' in prompt
        assert '0212 000 0000' in prompt

    def test_courses_included(self):
        context = self._base_context(
            courses=[
                {'code': 'MAT 111', 'name': 'Kalkülüs I', 'credits': '6', 'type': 'Zorunlu', 'semester': 1, 'program_name': 'Bilgisayar'}
            ]
        )
        prompt = self.service._build_prompt('dersler', context)
        assert 'MAT 111' in prompt
        assert 'Kalkülüs I' in prompt

    def test_semantic_results_included(self):
        context = self._base_context(
            semantic=[
                {'type': 'program', 'name': 'Psikoloji', 'level': 'Bachelor', 'desc': 'Psikoloji programı'},
                {'type': 'course', 'name': 'Genel Psikoloji', 'code': 'PSY 101'},
            ]
        )
        prompt = self.service._build_prompt('psikoloji', context)
        assert 'Psikoloji' in prompt


class TestGetExample(TestCase):
    """_get_example testleri"""

    def setUp(self):
        self.service = LLMService()

    def test_all_semesters_example(self):
        sc = {'all_semesters': True, 'courses': []}
        example = self.service._get_example(set(), sc)
        assert 'Yarıyıl' in example
        assert 'AKTS' in example

    def test_single_semester_example(self):
        example = self.service._get_example({'semester', 'course'}, None)
        assert 'Yarıyılında' in example
        assert 'AKTS' in example

    def test_department_list_example(self):
        example = self.service._get_example({'list', 'department'}, None)
        assert 'Fakülte' in example

    def test_program_list_example(self):
        example = self.service._get_example({'list', 'program'}, None)
        assert 'Fakülte' in example
        assert 'Lisans' in example

    def test_instructor_example(self):
        example = self.service._get_example({'instructor'}, None)
        assert 'Prof. Dr.' in example

    def test_contact_example(self):
        example = self.service._get_example({'contact'}, None)
        assert 'acibadem.edu.tr' in example

    def test_admission_example(self):
        example = self.service._get_example({'admission'}, None)
        assert 'YKS' in example

    def test_scholarship_example(self):
        example = self.service._get_example({'scholarship'}, None)
        assert 'burs' in example.lower()

    def test_default_example(self):
        example = self.service._get_example(set(), None)
        assert 'Acıbadem' in example


class TestFallbackAnswer(TestCase):
    """_fallback_answer testleri"""

    def setUp(self):
        self.service = LLMService()

    def test_fallback_with_semester_courses_single(self):
        context = {
            'intents': ['semester', 'course'],
            'sources': ['Curriculum Database'],
            'semester_courses': {
                'semester': 1,
                'program': 'Bilgisayar Mühendisliği',
                'all_semesters': False,
                'courses': [
                    {'code': 'CSE 101', 'name': 'Programlama', 'credits': '6', 'type': 'Zorunlu'},
                    {'code': 'MAT 111', 'name': 'Kalkülüs I', 'credits': '6', 'type': 'Zorunlu'},
                ]
            }
        }
        result = self.service._fallback_answer('1. yarıyıl', context)
        assert 'text' in result
        assert 'CSE 101' in result['text']
        assert 'MAT 111' in result['text']
        assert result['confidence'] == 0.5

    def test_fallback_with_all_semesters(self):
        context = {
            'intents': ['program_courses'],
            'sources': ['Curriculum Database'],
            'semester_courses': {
                'semester': None,
                'program': 'Hemşirelik',
                'all_semesters': True,
                'courses': [
                    {'code': 'HEM 101', 'name': 'Temel Hemşirelik', 'credits': '5', 'type': 'Zorunlu', 'semester': 1},
                ]
            }
        }
        result = self.service._fallback_answer('müfredat', context)
        assert 'HEM 101' in result['text']
        assert 'Hemşirelik' in result['text']

    def test_fallback_with_contact(self):
        context = {
            'intents': ['contact'],
            'sources': ['University Information'],
            'semester_courses': None,
            'general_info': {
                'phone': '0212 000 0000',
                'email': 'info@acibadem.edu.tr',
                'address': 'İstanbul',
            }
        }
        result = self.service._fallback_answer('iletişim', context)
        assert '0212 000 0000' in result['text']
        assert 'acibadem.edu.tr' in result['text']

    def test_fallback_with_programs(self):
        context = {
            'intents': ['program'],
            'sources': ['Programs Database'],
            'semester_courses': None,
            'programs': [
                {'name': 'Bilgisayar Mühendisliği', 'level': 'Bachelor', 'department': 'Mühendislik'}
            ]
        }
        result = self.service._fallback_answer('program', context)
        assert 'Bilgisayar Mühendisliği' in result['text']

    def test_fallback_with_instructors(self):
        context = {
            'intents': ['instructor'],
            'sources': ['Akademik Kadro'],
            'semester_courses': None,
            'instructors': [
                {'name': 'Ahmet Bulut', 'title': 'Prof. Dr.', 'faculty': 'Mühendislik'}
            ]
        }
        result = self.service._fallback_answer('hocalar', context)
        assert 'Ahmet Bulut' in result['text']
        assert 'Prof. Dr.' in result['text']

    def test_fallback_with_departments(self):
        context = {
            'intents': ['department'],
            'sources': ['Departments Database'],
            'semester_courses': None,
            'departments': [
                {'name': 'Mühendislik Fakültesi', 'description': 'Test'}
            ]
        }
        result = self.service._fallback_answer('fakülteler', context)
        assert 'Mühendislik Fakültesi' in result['text']

    def test_fallback_no_data_returns_default(self):
        context = {
            'intents': [],
            'sources': [],
            'semester_courses': None,
        }
        result = self.service._fallback_answer('bilinmeyen', context)
        assert 'acibadem.edu.tr' in result['text']
        assert result['confidence'] == 0.0

    def test_fallback_calculates_total_akts(self):
        context = {
            'intents': ['semester'],
            'sources': ['Curriculum Database'],
            'semester_courses': {
                'semester': 1,
                'program': 'Test',
                'all_semesters': False,
                'courses': [
                    {'code': 'A 101', 'name': 'Ders A', 'credits': '6', 'type': 'Zorunlu'},
                    {'code': 'B 101', 'name': 'Ders B', 'credits': '4', 'type': 'Zorunlu'},
                ]
            }
        }
        result = self.service._fallback_answer('yarıyıl', context)
        assert 'Toplam: 10 AKTS' in result['text']


class TestGenerateAnswer(TestCase):
    """generate_answer testleri — Ollama mock'lanır"""

    def setUp(self):
        self.service = LLMService()

    def _base_context(self):
        return {
            'intents': ['program'],
            'semester_courses': None,
            'semantic': [],
            'departments': [],
            'programs': [{'name': 'Test Programı', 'level': 'Bachelor', 'department': 'Test'}],
            'courses': [],
            'instructors': [],
            'general_info': None,
            'sources': ['Programs Database'],
        }

    def test_successful_response(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': {'content': 'Test cevabı'}
        }

        with patch('requests.post', return_value=mock_response):
            result = self.service.generate_answer('test sorusu', self._base_context())

        assert result['text'] == 'Test cevabı'
        assert result['confidence'] == 0.85
        assert 'Programs Database' in result['sources']

    def test_ollama_error_uses_fallback(self):
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('requests.post', return_value=mock_response):
            result = self.service.generate_answer('test sorusu', self._base_context())

        assert 'text' in result
        assert result['confidence'] < 0.85

    def test_timeout_uses_fallback(self):
        with patch('requests.post', side_effect=Exception('Read timed out')):
            result = self.service.generate_answer('test sorusu', self._base_context())

        assert 'text' in result
        assert result['confidence'] < 0.85

    def test_connection_error_uses_fallback(self):
        with patch('requests.post', side_effect=ConnectionError('Connection refused')):
            result = self.service.generate_answer('test sorusu', self._base_context())

        assert 'text' in result

    def test_returns_dict_with_required_keys(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': {'content': 'Cevap'}}

        with patch('requests.post', return_value=mock_response):
            result = self.service.generate_answer('soru', self._base_context())

        assert 'text' in result
        assert 'sources' in result
        assert 'confidence' in result

    def test_empty_response_content(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': {'content': ''}}

        with patch('requests.post', return_value=mock_response):
            result = self.service.generate_answer('soru', self._base_context())

        assert result['text'] == ''