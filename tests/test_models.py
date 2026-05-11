"""
Tests for Django models
- __str__ metodları
- Field defaults ve constraints
- unique_together / unique constraints
- Meta ordering
"""
from django.test import TestCase
from django.db import IntegrityError
from chat.models import (
    UniversityInfo, Department, Program, Course,
    Instructor, ChatMessage, ScrapingLog, ChatSession, Message
)


class TestUniversityInfo(TestCase):

    def test_str(self):
        uni = UniversityInfo.objects.create(
            title='Acıbadem Üniversitesi',
            description='Test açıklaması'
        )
        assert str(uni) == 'Acıbadem Üniversitesi'

    def test_default_website(self):
        uni = UniversityInfo.objects.create(
            title='Test',
            description='Test'
        )
        assert uni.website == 'https://www.acibadem.edu.tr'

    def test_optional_fields_blank(self):
        uni = UniversityInfo.objects.create(
            title='Test',
            description='Test'
        )
        assert uni.mission == ''
        assert uni.vision == ''
        assert uni.phone == ''
        assert uni.email == ''
        assert uni.address == ''

    def test_created_at_auto_set(self):
        uni = UniversityInfo.objects.create(title='T', description='D')
        assert uni.created_at is not None

    def test_updated_at_auto_set(self):
        uni = UniversityInfo.objects.create(title='T', description='D')
        assert uni.updated_at is not None


class TestDepartment(TestCase):

    def test_str(self):
        dept = Department.objects.create(name='Mühendislik Fakültesi')
        assert str(dept) == 'Mühendislik Fakültesi'

    def test_default_source(self):
        dept = Department.objects.create(name='Test Fakülte')
        assert dept.source == 'acibadem.edu.tr'

    def test_unique_name(self):
        Department.objects.create(name='Benzersiz Fakülte')
        with self.assertRaises(IntegrityError):
            Department.objects.create(name='Benzersiz Fakülte')

    def test_optional_fields_blank(self):
        dept = Department.objects.create(name='Test')
        assert dept.description == ''
        assert dept.email == ''
        assert dept.phone == ''
        assert dept.link == ''

    def test_ordering_by_name(self):
        Department.objects.create(name='Z Fakültesi')
        Department.objects.create(name='A Fakültesi')
        depts = list(Department.objects.all())
        assert depts[0].name == 'A Fakültesi'
        assert depts[1].name == 'Z Fakültesi'


class TestProgram(TestCase):

    def test_str(self):
        prog = Program.objects.create(name='Bilgisayar Mühendisliği', level='Bachelor')
        assert str(prog) == 'Bilgisayar Mühendisliği (Bachelor)'

    def test_unique_name(self):
        Program.objects.create(name='Benzersiz Program', level='Bachelor')
        with self.assertRaises(IntegrityError):
            Program.objects.create(name='Benzersiz Program', level='Master')

    def test_default_sources_empty_list(self):
        prog = Program.objects.create(name='Test Program', level='Bachelor')
        assert prog.sources == []

    def test_optional_fields_blank(self):
        prog = Program.objects.create(name='Test', level='Bachelor')
        assert prog.duration == ''
        assert prog.department == ''
        assert prog.language == ''
        assert prog.description == ''
        assert prog.link == ''

    def test_ordering_by_level_then_name(self):
        Program.objects.create(name='Z Program', level='Bachelor')
        Program.objects.create(name='A Program', level='Bachelor')
        Program.objects.create(name='M Program', level='Master')
        progs = list(Program.objects.all())
        bachelor_progs = [p for p in progs if p.level == 'Bachelor']
        assert bachelor_progs[0].name == 'A Program'
        assert bachelor_progs[1].name == 'Z Program'


class TestCourse(TestCase):

    def test_str_with_semester_and_program(self):
        course = Course.objects.create(
            code='CSE 101',
            name='Programlamaya Giriş',
            semester=1,
            program_name='Bilgisayar Mühendisliği'
        )
        result = str(course)
        assert 'CSE 101' in result
        assert 'Programlamaya Giriş' in result
        assert '1.Yarıyıl' in result
        assert 'Bilgisayar Mühendisliği' in result

    def test_str_without_semester(self):
        course = Course.objects.create(code='MAT 101', name='Matematik')
        result = str(course)
        assert 'MAT 101' in result
        assert 'Matematik' in result
        assert 'Yarıyıl' not in result

    def test_default_source(self):
        course = Course.objects.create(code='TST 101', name='Test')
        assert course.source == 'obs.acibadem.edu.tr'

    def test_semester_nullable(self):
        course = Course.objects.create(code='TST 102', name='Test 2')
        assert course.semester is None

    def test_optional_fields_blank(self):
        course = Course.objects.create(code='TST 103', name='Test 3')
        assert course.credits == ''
        assert course.type == ''
        assert course.tul == ''
        assert course.program_name == ''
        assert course.program_level == ''

    def test_duplicate_codes_allowed(self):
        """Aynı ders kodu farklı programlarda olabilir"""
        Course.objects.create(code='CSE 101', name='Ders A', program_name='Program A')
        Course.objects.create(code='CSE 101', name='Ders A', program_name='Program B')
        assert Course.objects.filter(code='CSE 101').count() == 2


class TestInstructor(TestCase):

    def test_str(self):
        inst = Instructor.objects.create(
            name='Ahmet Bulut',
            title='Prof. Dr.',
            department='Bilgisayar Mühendisliği',
            faculty='Mühendislik Fakültesi'
        )
        assert 'Prof. Dr.' in str(inst)
        assert 'Ahmet Bulut' in str(inst)
        assert 'Bilgisayar Mühendisliği' in str(inst)

    def test_unique_together_name_faculty(self):
        Instructor.objects.create(
            name='Ali Veli',
            faculty='Mühendislik Fakültesi'
        )
        with self.assertRaises(IntegrityError):
            Instructor.objects.create(
                name='Ali Veli',
                faculty='Mühendislik Fakültesi'
            )

    def test_same_name_different_faculty_allowed(self):
        """Aynı isim farklı fakültede olabilir"""
        Instructor.objects.create(name='Ali Veli', faculty='Fakülte A')
        Instructor.objects.create(name='Ali Veli', faculty='Fakülte B')
        assert Instructor.objects.filter(name='Ali Veli').count() == 2

    def test_default_source(self):
        inst = Instructor.objects.create(name='Test Hoca', faculty='Test')
        assert inst.source == 'acibadem.edu.tr'

    def test_optional_fields_blank(self):
        inst = Instructor.objects.create(name='Test', faculty='Test F')
        assert inst.title == ''
        assert inst.email == ''
        assert inst.department == ''
        assert inst.expertise == ''
        assert inst.profile_url == ''
        assert inst.level == ''

    def test_ordering(self):
        Instructor.objects.create(name='Z Hoca', faculty='A Fakülte', department='A Bölüm')
        Instructor.objects.create(name='A Hoca', faculty='A Fakülte', department='A Bölüm')
        instructors = list(Instructor.objects.all())
        assert instructors[0].name == 'A Hoca'
        assert instructors[1].name == 'Z Hoca'


class TestChatMessage(TestCase):

    def test_str(self):
        msg = ChatMessage.objects.create(
            question='Bilgisayar Mühendisliği programı nedir?',
            answer='Test cevabı'
        )
        result = str(msg)
        assert 'Q:' in result
        assert 'Bilgisayar' in result

    def test_str_truncates_long_question(self):
        long_question = 'A' * 100
        msg = ChatMessage.objects.create(question=long_question, answer='Cevap')
        assert len(str(msg)) < len(long_question) + 10

    def test_default_confidence(self):
        msg = ChatMessage.objects.create(question='Soru', answer='Cevap')
        assert msg.confidence == 0.0

    def test_default_sources_empty(self):
        msg = ChatMessage.objects.create(question='Soru', answer='Cevap')
        assert msg.sources == []

    def test_ordering_newest_first(self):
        msg1 = ChatMessage.objects.create(question='İlk', answer='Cevap 1')
        msg2 = ChatMessage.objects.create(question='İkinci', answer='Cevap 2')
        messages = list(ChatMessage.objects.all())
        assert messages[0].question == 'İkinci'
        assert messages[1].question == 'İlk'


class TestScrapingLog(TestCase):

    def test_str(self):
        log = ScrapingLog.objects.create(status='success')
        result = str(log)
        assert 'success' in result

    def test_default_status(self):
        log = ScrapingLog.objects.create()
        assert log.status == 'pending'

    def test_status_choices(self):
        for status in ['pending', 'running', 'success', 'failed']:
            log = ScrapingLog.objects.create(status=status)
            assert log.status == status

    def test_default_items_scraped(self):
        log = ScrapingLog.objects.create()
        assert log.items_scraped == 0

    def test_default_metadata_empty_dict(self):
        log = ScrapingLog.objects.create()
        assert log.metadata == {}

    def test_end_time_nullable(self):
        log = ScrapingLog.objects.create()
        assert log.end_time is None

    def test_ordering_newest_first(self):
        log1 = ScrapingLog.objects.create(status='success')
        log2 = ScrapingLog.objects.create(status='failed')
        logs = list(ScrapingLog.objects.all())
        assert logs[0].status == 'failed'
        assert logs[1].status == 'success'


class TestChatSession(TestCase):

    def test_str(self):
        session = ChatSession.objects.create(title='Test Sohbet')
        assert str(session) == 'Test Sohbet'

    def test_default_title(self):
        session = ChatSession.objects.create()
        assert session.title == 'Yeni Sohbet'

    def test_ordering_newest_first(self):
        s1 = ChatSession.objects.create(title='İlk')
        s2 = ChatSession.objects.create(title='İkinci')
        sessions = list(ChatSession.objects.all())
        assert sessions[0].title == 'İkinci'


class TestMessage(TestCase):

    def setUp(self):
        self.session = ChatSession.objects.create(title='Test Session')

    def test_str(self):
        msg = Message.objects.create(
            session=self.session,
            role='user',
            content='Merhaba, bilgi almak istiyorum'
        )
        result = str(msg)
        assert '[user]' in result
        assert 'Merhaba' in result

    def test_role_choices(self):
        user_msg = Message.objects.create(session=self.session, role='user', content='Soru')
        bot_msg = Message.objects.create(session=self.session, role='bot', content='Cevap')
        assert user_msg.role == 'user'
        assert bot_msg.role == 'bot'

    def test_cascade_delete(self):
        Message.objects.create(session=self.session, role='user', content='Test')
        session_id = self.session.id
        self.session.delete()
        assert Message.objects.filter(session_id=session_id).count() == 0

    def test_ordering_by_created_at(self):
        msg1 = Message.objects.create(session=self.session, role='user', content='İlk')
        msg2 = Message.objects.create(session=self.session, role='bot', content='İkinci')
        messages = list(Message.objects.filter(session=self.session))
        assert messages[0].content == 'İlk'
        assert messages[1].content == 'İkinci'

    def test_related_name_messages(self):
        Message.objects.create(session=self.session, role='user', content='Test 1')
        Message.objects.create(session=self.session, role='bot', content='Test 2')
        assert self.session.messages.count() == 2