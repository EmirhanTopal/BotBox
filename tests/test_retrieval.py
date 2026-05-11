"""
Tests for RetrievalService
- Unit tests: DB gerektirmeyen (_detect_intents, _extract_semester_number, _contains_any)
- Integration tests: DB gerektiren (program matching, course filtering)
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from chat.models import Program, Course, Department, UniversityInfo, Instructor


class TestContainsAny(TestCase):
    """_contains_any metodu testleri"""

    def setUp(self):
        with patch('chat.services.vector_store.VectorStore.__init__', return_value=None):
            from chat.services.retrieval import RetrievalService
            self.service = RetrievalService.__new__(RetrievalService)
            self.service.max_results = 5

    def test_exact_match(self):
        assert self.service._contains_any('yarıyıl dersleri', ['yarıyıl']) is True

    def test_no_match(self):
        assert self.service._contains_any('merhaba dünya', ['semester']) is False

    def test_case_insensitive(self):
        assert self.service._contains_any('YARIYIL', ['yarıyıl']) is True

    def test_fuzzy_match(self):
        assert self.service._contains_any('yarıyıl', ['yariyil'], threshold=70) is True

    def test_multiple_keywords(self):
        assert self.service._contains_any('ders listesi', ['program', 'ders']) is True

    def test_empty_text(self):
        assert self.service._contains_any('', ['yarıyıl']) is False

    def test_empty_keywords(self):
        assert self.service._contains_any('yarıyıl', []) is False


class TestExtractSemesterNumber(TestCase):
    """_extract_semester_number metodu testleri"""

    def setUp(self):
        with patch('chat.services.vector_store.VectorStore.__init__', return_value=None):
            from chat.services.retrieval import RetrievalService
            self.service = RetrievalService.__new__(RetrievalService)

    def test_numeric_with_dot(self):
        assert self.service._extract_semester_number('3. yarıyıl dersleri') == 3

    def test_numeric_with_space(self):
        assert self.service._extract_semester_number('5 yarıyıl') == 5

    def test_word_birinci(self):
        assert self.service._extract_semester_number('birinci yarıyıl') == 1

    def test_word_ikinci(self):
        assert self.service._extract_semester_number('ikinci dönem') == 2

    def test_word_first(self):
        assert self.service._extract_semester_number('first semester') == 1

    def test_word_second(self):
        assert self.service._extract_semester_number('second semester') == 2

    def test_all_numbers(self):
        expected = {
            'birinci': 1, 'ikinci': 2, 'üçüncü': 3, 'dördüncü': 4,
            'beşinci': 5, 'altıncı': 6, 'yedinci': 7, 'sekizinci': 8,
        }
        for word, num in expected.items():
            assert self.service._extract_semester_number(f'{word} yarıyıl') == num

    def test_no_semester(self):
        assert self.service._extract_semester_number('bilgisayar mühendisliği dersleri') is None

    def test_semester_in_english(self):
        assert self.service._extract_semester_number('3rd semester') == 3


class TestDetectIntents(TestCase):
    """_detect_intents metodu testleri — DB mock'lanır"""

    def setUp(self):
        with patch('chat.services.vector_store.VectorStore.__init__', return_value=None):
            from chat.services.retrieval import RetrievalService
            self.service = RetrievalService.__new__(RetrievalService)
            self.service.max_results = 5

    def _detect(self, q):
        """Instructor DB sorgusunu mock'layarak intent tespiti yap."""
        with patch('chat.models.Instructor.objects') as mock_mgr:
            mock_mgr.filter.return_value.exists.return_value = False
            return self.service._detect_intents(q)

    # Yarıyıl
    def test_semester_intent(self):
        intents = self._detect('bilgisayar mühendisliği 3. yarıyıl')
        assert 'semester' in intents
        assert 'course' in intents

    def test_semester_in_english(self):
        intents = self._detect('first semester courses')
        assert 'semester' in intents

    # Program
    def test_program_intent(self):
        intents = self._detect('bilgisayar mühendisliği programı hakkında')
        assert 'program' in intents

    def test_program_english(self):
        intents = self._detect('computer engineering program')
        assert 'program' in intents

    # Ders
    def test_course_intent(self):
        intents = self._detect('hangi dersler var')
        assert 'course' in intents

    def test_program_courses_intent(self):
        intents = self._detect('hemşirelik dersleri nelerdir')
        assert 'program_courses' in intents
        assert 'course' in intents

    # Seçmeli
    def test_elective_intent(self):
        intents = self._detect('bilgisayar mühendisliği seçmeli dersler')
        assert 'elective' in intents

    def test_elective_not_program_courses(self):
        """Seçmeli sorgusunda program_courses tetiklenmemeli"""
        intents = self._detect('seçmeli dersler nelerdir')
        assert 'elective' in intents
        assert 'program_courses' not in intents

    def test_general_elective_intent(self):
        intents = self._detect('genel seçmeli dersler neler')
        assert 'general_elective' in intents

    # İletişim
    def test_contact_intent(self):
        intents = self._detect('iletişim bilgileri nedir')
        assert 'contact' in intents
        assert 'general' in intents

    # Fakülte
    def test_department_intent(self):
        intents = self._detect('fakülteler nelerdir')
        assert 'department' in intents

    # Liste
    def test_list_intent(self):
        intents = self._detect('tüm programları listele')
        assert 'list' in intents

    def test_list_departments(self):
        intents = self._detect('hangi fakülteler var')
        assert 'list' in intents

    # Akademisyen
    def test_instructor_keyword(self):
        intents = self._detect('akademik kadro kimlerden oluşuyor')
        assert 'instructor' in intents

    def test_instructor_by_name(self):
        """İsim DB'de bulunursa instructor intent eklenmeli"""
        with patch('chat.models.Instructor.objects') as mock_mgr:
            mock_mgr.filter.return_value.exists.return_value = True
            intents = self.service._detect_intents('ahmet bulut kimdir')
        assert 'instructor' in intents

    # Başvuru / Burs
    def test_admission_intent(self):
        intents = self._detect('başvuru şartları nelerdir')
        assert 'admission' in intents

    def test_scholarship_intent(self):
        intents = self._detect('burs imkanları var mı')
        assert 'scholarship' in intents

    # Kampüs
    def test_campus_intent(self):
        intents = self._detect('kütüphane var mı')
        assert 'campus' in intents

    # Kariyer
    def test_career_intent(self):
        intents = self._detect('mezunlar nerede çalışıyor')
        assert 'career' in intents


class TestExtractProgramName(TestCase):
    """_extract_program_name_from_query testleri — DB gerektirir"""

    def setUp(self):
        with patch('chat.services.vector_store.VectorStore.__init__', return_value=None):
            from chat.services.retrieval import RetrievalService
            self.service = RetrievalService.__new__(RetrievalService)
            self.service.max_results = 5

        # Test programları oluştur
        Program.objects.create(name='Bilgisayar Mühendisliği (İngilizce)', level='Bachelor', department='Mühendislik')
        Program.objects.create(name='Hemşirelik', level='Bachelor', department='Sağlık Bilimleri')
        Program.objects.create(name='Hemşirelik (İngilizce)', level='Bachelor', department='Sağlık Bilimleri')
        Program.objects.create(name='Psikoloji', level='Bachelor', department='Fen Edebiyat')
        Program.objects.create(name='Psikoloji (İngilizce)', level='Bachelor', department='Fen Edebiyat')

    def test_exact_match_turkish(self):
        result = self.service._extract_program_name_from_query('hemşirelik 1. yarıyıl')
        assert result == 'Hemşirelik'

    def test_exact_match_english_version(self):
        result = self.service._extract_program_name_from_query('hemşirelik ingilizce 1. yarıyıl')
        assert result == 'Hemşirelik (İngilizce)'

    def test_exact_match_longest(self):
        result = self.service._extract_program_name_from_query('bilgisayar mühendisliği dersleri')
        assert 'Bilgisayar Mühendisliği' in result

    def test_prefers_turkish_over_english(self):
        result = self.service._extract_program_name_from_query('psikoloji programı')
        assert result == 'Psikoloji'

    def test_english_keyword_selects_english(self):
        result = self.service._extract_program_name_from_query('psikoloji ingilizce')
        assert result == 'Psikoloji (İngilizce)'

    def test_no_match_returns_empty(self):
        result = self.service._extract_program_name_from_query('xyz123 bilinmeyen program')
        assert result == ''

    def test_empty_query(self):
        result = self.service._extract_program_name_from_query('')
        assert result == ''


class TestGetProgramPrefixes(TestCase):
    """_get_program_prefixes testleri"""

    def setUp(self):
        with patch('chat.services.vector_store.VectorStore.__init__', return_value=None):
            from chat.services.retrieval import RetrievalService
            self.service = RetrievalService.__new__(RetrievalService)

        # Test dersleri oluştur
        Course.objects.create(code='CSE 101', name='Programlamaya Giriş', type='Zorunlu', program_name='Bilgisayar Mühendisliği', semester=1)
        Course.objects.create(code='CSE 102', name='Programlama Pratiği', type='Zorunlu', program_name='Bilgisayar Mühendisliği', semester=2)
        Course.objects.create(code='MAT 111', name='Kalkülüs I', type='Zorunlu', program_name='Bilgisayar Mühendisliği', semester=1)
        Course.objects.create(code='MEG 102', name='Biyolojik Bilimler', type='Zorunlu', program_name='Bilgisayar Mühendisliği', semester=2)
        Course.objects.create(code='ACU 101', name='Seçmeli', type='Seçmeli', program_name='Bilgisayar Mühendisliği', semester=1)

    def test_returns_program_specific_prefixes(self):
        prefixes = self.service._get_program_prefixes('Bilgisayar Mühendisliği')
        assert 'CSE' in prefixes
        assert 'MEG' in prefixes

    def test_excludes_common_prefixes(self):
        prefixes = self.service._get_program_prefixes('Bilgisayar Mühendisliği')
        assert 'MAT' not in prefixes
        assert 'ACU' not in prefixes

    def test_empty_program_returns_empty(self):
        prefixes = self.service._get_program_prefixes('Olmayan Program')
        assert prefixes == []


class TestGetUniqueSemesterCourses(TestCase):
    """_get_unique_semester_courses testleri"""

    def setUp(self):
        with patch('chat.services.vector_store.VectorStore.__init__', return_value=None):
            from chat.services.retrieval import RetrievalService
            self.service = RetrievalService.__new__(RetrievalService)

        from django.db.models import Q
        self.Q = Q

        # Zorunlu dersler
        Course.objects.create(code='CSE 101', name='Programlamaya Giriş', type='Zorunlu', program_name='Bilgisayar Mühendisliği', semester=1)
        Course.objects.create(code='MAT 111', name='Kalkülüs I', type='Zorunlu', program_name='Bilgisayar Mühendisliği', semester=1)
        # Ortak havuz — filtrelenmeli
        Course.objects.create(code='ACU 101', name='Genel Seçmeli', type='Seçmeli', program_name='Bilgisayar Mühendisliği', semester=1)
        Course.objects.create(code='ADS 2001', name='Alan Dışı Seçmeli', type='Seçmeli', program_name='Bilgisayar Mühendisliği', semester=1)
        # Placeholder seçmeli — gösterilmeli
        Course.objects.create(code='CSE 4001', name='Teknik Seçmeli', type='Seçmeli', program_name='Bilgisayar Mühendisliği', semester=7)
        # semester=None — filtrelenmeli
        Course.objects.create(code='CSE 999', name='Belirsiz', type='Zorunlu', program_name='Bilgisayar Mühendisliği', semester=None)

    def test_filters_acу_prefix(self):
        courses = self.service._get_unique_semester_courses(
            self.Q(program_name='Bilgisayar Mühendisliği'),
            prog_name='Bilgisayar Mühendisliği'
        )
        codes = [c.code for c in courses]
        assert 'ACU 101' not in codes

    def test_filters_ads_prefix(self):
        courses = self.service._get_unique_semester_courses(
            self.Q(program_name='Bilgisayar Mühendisliği'),
            prog_name='Bilgisayar Mühendisliği'
        )
        codes = [c.code for c in courses]
        assert 'ADS 2001' not in codes

    def test_filters_null_semester(self):
        courses = self.service._get_unique_semester_courses(
            self.Q(program_name='Bilgisayar Mühendisliği'),
            prog_name='Bilgisayar Mühendisliği'
        )
        codes = [c.code for c in courses]
        assert 'CSE 999' not in codes

    def test_includes_mandatory_courses(self):
        courses = self.service._get_unique_semester_courses(
            self.Q(program_name='Bilgisayar Mühendisliği', semester=1),
            prog_name='Bilgisayar Mühendisliği'
        )
        codes = [c.code for c in courses]
        assert 'CSE 101' in codes

    def test_includes_placeholder_elective(self):
        courses = self.service._get_unique_semester_courses(
            self.Q(program_name='Bilgisayar Mühendisliği', semester=7),
            prog_name='Bilgisayar Mühendisliği'
        )
        codes = [c.code for c in courses]
        assert 'CSE 4001' in codes

    def test_limit_respected(self):
        for i in range(10):
            Course.objects.create(
                code=f'CSE {200+i}', name=f'Ders {i}',
                type='Zorunlu', program_name='Bilgisayar Mühendisliği', semester=3
            )
        courses = self.service._get_unique_semester_courses(
            self.Q(program_name='Bilgisayar Mühendisliği'),
            limit=3,
            prog_name='Bilgisayar Mühendisliği'
        )
        assert len(courses) <= 3


class TestRetrieveContext(TestCase):
    """retrieve() metodu integration testleri"""

    def setUp(self):
        with patch('chat.services.vector_store.VectorStore') as mock_vs:
            mock_vs.return_value.search.return_value = []
            from chat.services.retrieval import RetrievalService
            self.service = RetrievalService()
            self.service.vector_store = MagicMock()
            self.service.vector_store.search.return_value = []

        Program.objects.create(name='Bilgisayar Mühendisliği (İngilizce)', level='Bachelor', department='Mühendislik Fakültesi')
        UniversityInfo.objects.create(
            title='Acıbadem Üniversitesi',
            description='Test açıklaması',
            phone='0212 000 0000',
            email='test@acibadem.edu.tr',
        )

    def test_returns_dict_with_required_keys(self):
        with patch('chat.models.Instructor.objects') as mock_mgr:
            mock_mgr.filter.return_value.exists.return_value = False
            context = self.service.retrieve('merhaba')
        assert 'programs' in context
        assert 'courses' in context
        assert 'departments' in context
        assert 'sources' in context
        assert 'intents' in context
        assert 'instructors' in context

    def test_fallback_when_no_match(self):
        with patch('chat.models.Instructor.objects') as mock_mgr:
            mock_mgr.filter.return_value.exists.return_value = False
            context = self.service.retrieve('xyzabc bilinmeyen soru')
        # UniversityInfo varsa University Information, yoksa Fallback Data gelir
        # Her iki durumda da sources boş olmamalı
        assert len(context['sources']) > 0

    def test_contact_returns_early(self):
        with patch('chat.models.Instructor.objects') as mock_mgr:
            mock_mgr.filter.return_value.exists.return_value = False
            context = self.service.retrieve('iletişim bilgileri')
        assert context['general_info'] is not None
        assert 'University Information' in context['sources']

    def test_program_list_bachelor_filter(self):
        Program.objects.create(name='Hemşirelik', level='Bachelor', department='Sağlık')
        Program.objects.create(name='Tıp YL', level='Master', department='Sağlık')

        with patch('chat.models.Instructor.objects') as mock_mgr:
            mock_mgr.filter.return_value.exists.return_value = False
            context = self.service.retrieve('tüm lisans programlarını listele')

        program_levels = [p['level'] for p in context['programs']]
        assert all(l in ['Bachelor', 'Undergraduate'] for l in program_levels)
        assert 'Master' not in program_levels