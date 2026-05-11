import pytest
from unittest.mock import patch, MagicMock
from scraper.acibadem_dual_scraper import AcibademDualScraper
from bs4 import BeautifulSoup


class TestAcibademDualScraper:
    """Test suite for dual scraper (static + dynamic)"""

    @pytest.fixture
    def scraper(self):
        return AcibademDualScraper(use_headless=True)

    # ==================== INITIALIZATION TESTS ====================

    def test_scraper_initialization(self, scraper):
        """Test scraper initializes with correct configuration"""
        assert scraper.headers is not None
        assert 'User-Agent' in scraper.headers
        assert 'obs_base' in scraper.URLS
        assert 'home' in scraper.URLS

    def test_data_structure_initialization(self, scraper):
        """Test all_data structure is properly initialized"""
        assert 'static_content' in scraper.all_data
        assert 'dynamic_content' in scraper.all_data
        assert 'merged_data' in scraper.all_data
        assert 'metadata' in scraper.all_data

    def test_dynamic_content_has_instructors_key(self, scraper):
        """Test dynamic_content includes instructors list"""
        assert 'instructors' in scraper.all_data['dynamic_content']
        assert isinstance(scraper.all_data['dynamic_content']['instructors'], list)

    # ==================== STATIC CONTENT TESTS ====================

    def test_fetch_page_success(self, scraper):
        """Test successful page fetch"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.content = b'<html><title>Test</title></html>'
            mock_get.return_value = mock_response

            soup = scraper.fetch_page('https://example.com')
            assert soup is not None
            assert soup.title.string == 'Test'

    def test_fetch_page_failure(self, scraper):
        """Test page fetch failure handling"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection error")

            soup = scraper.fetch_page('https://example.com')
            assert soup is None

    def test_scrape_static_homepage_structure(self, scraper):
        """Test homepage data has required fields"""
        with patch.object(scraper, 'fetch_page') as mock_fetch:
            html = '<html><title>ACU</title><meta name="description" content="Univ"></html>'
            mock_fetch.return_value = BeautifulSoup(html, 'html.parser')

            data = scraper.scrape_static_homepage()
            assert 'title' in data
            assert 'meta_description' in data
            assert 'mission' in data
            assert 'vision' in data

    def test_scrape_static_departments_returns_list(self, scraper):
        """Test departments returns list of dicts"""
        with patch.object(scraper, 'fetch_page') as mock_fetch:
            html = '''
            <html>
                <div class="department">
                    <h3>Engineering</h3>
                    <div class="description">Desc</div>
                    <a href="/eng">Link</a>
                </div>
            </html>
            '''
            mock_fetch.return_value = BeautifulSoup(html, 'html.parser')

            depts = scraper.scrape_static_departments()
            assert isinstance(depts, list)
            assert len(depts) > 0
            assert 'name' in depts[0]
            assert 'source' in depts[0]
            assert depts[0]['source'] == 'acibadem.edu.tr'

    def test_scrape_static_programs_structure(self, scraper):
        """Test programs data structure"""
        with patch.object(scraper, 'fetch_page') as mock_fetch:
            html = '''
            <html>
                <div class="program">
                    <h3>Computer Science</h3>
                    <span class="level">Bachelor</span>
                </div>
            </html>
            '''
            mock_fetch.return_value = BeautifulSoup(html, 'html.parser')

            progs = scraper.scrape_static_programs()
            assert isinstance(progs, list)
            if len(progs) > 0:
                assert 'name' in progs[0]
                assert 'level' in progs[0]

    def test_scrape_static_contact(self, scraper):
        """Test contact info extraction"""
        with patch.object(scraper, 'fetch_page') as mock_fetch:
            html = '''
            <html>
                <span class="phone">+90 212 123 4567</span>
                <a>test@acibadem.edu.tr</a>
                <div class="address">Istanbul, Turkey</div>
            </html>
            '''
            mock_fetch.return_value = BeautifulSoup(html, 'html.parser')

            contact = scraper.scrape_static_contact()
            assert 'main_phone' in contact
            assert 'main_email' in contact
            assert 'addresses' in contact
            assert contact['source'] == 'acibadem.edu.tr'

    # ==================== PLAYWRIGHT DRIVER TESTS ====================

    def test_playwright_driver_initialization(self, scraper):
        """Test Playwright driver initialization"""
        with patch('scraper.acibadem_dual_scraper.sync_playwright') as mock_pw:
            mock_playwright = MagicMock()
            mock_browser = MagicMock()
            mock_page = MagicMock()
            mock_pw.return_value.__enter__ = MagicMock(return_value=mock_playwright)
            mock_pw.return_value.start = MagicMock(return_value=mock_playwright)
            mock_playwright.chromium.launch.return_value = mock_browser
            mock_browser.new_page.return_value = mock_page

            result = scraper.init_playwright_driver()
            assert isinstance(result, bool)

    def test_playwright_driver_initialization_failure(self, scraper):
        """Test graceful handling of Playwright initialization failure"""
        with patch('scraper.acibadem_dual_scraper.sync_playwright') as mock_pw:
            mock_pw.return_value.start.side_effect = Exception("Playwright not found")

            result = scraper.init_playwright_driver()
            assert result is False

    def test_close_playwright_driver(self, scraper):
        """Test Playwright driver closes properly"""
        scraper._browser = MagicMock()
        scraper._playwright = MagicMock()
        scraper.close_playwright_driver()
        scraper._browser.close.assert_called_once()
        scraper._playwright.stop.assert_called_once()

    def test_get_page_source_no_driver(self, scraper):
        """Test _get_page_source returns None when no driver"""
        scraper._page = None
        result = scraper._get_page_source('https://example.com')
        assert result is None

    # ==================== INSTRUCTOR SCRAPING TESTS ====================

    def test_parse_instructor_page_empty(self, scraper):
        """Test instructor page parsing with no cards"""
        html = '<html><body><div class="content"></div></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = scraper._parse_instructor_page(soup, 'Test Fakültesi', 'Lisans', 'https://test.com')
        assert isinstance(result, list)
        assert len(result) == 0

    def test_parse_instructor_page_with_cards(self, scraper):
        """Test instructor page parsing with card-title divs"""
        html = '''
        <html><body>
            <div class="card-title">
                <div class="departman text-grey-60 fs-14"><span></span></div>
                <span>Prof. Dr. Ahmet Yılmaz</span>
            </div>
            <div class="card-title">
                <div class="departman text-grey-60 fs-14"><span></span></div>
                <span>Dr. Öğr. Üyesi Ayşe Kaya</span>
            </div>
        </body></html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        result = scraper._parse_instructor_page(soup, 'Test Fakültesi', 'Lisans', 'https://test.com')
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['name'] == 'Ahmet Yılmaz'
        assert result[0]['title'] == 'Prof. Dr.'
        assert result[0]['faculty'] == 'Test Fakültesi'
        assert result[1]['name'] == 'Ayşe Kaya'
        assert result[1]['title'] == 'Dr. Öğr. Üyesi'

    def test_instructor_title_prefixes(self, scraper):
        """Test all title prefixes are correctly parsed"""
        titles = [
            ('Prof. Dr. Ali Veli', 'Prof. Dr.', 'Ali Veli'),
            ('Doç. Dr. Fatma Can', 'Doç. Dr.', 'Fatma Can'),
            ('Dr. Öğr. Üyesi Hasan Ak', 'Dr. Öğr. Üyesi', 'Hasan Ak'),
            ('Öğr. Gör. Dr. Zeynep Su', 'Öğr. Gör. Dr.', 'Zeynep Su'),
            ('Arş. Gör. Mehmet Öz', 'Arş. Gör.', 'Mehmet Öz'),
        ]
        for raw, expected_title, expected_name in titles:
            html = f'<html><body><div class="card-title"><div class="departman text-grey-60 fs-14"><span></span></div><span>{raw}</span></div></body></html>'
            soup = BeautifulSoup(html, 'html.parser')
            result = scraper._parse_instructor_page(soup, 'Fakülte', 'Lisans', 'https://test.com')
            assert len(result) == 1
            assert result[0]['title'] == expected_title
            assert result[0]['name'] == expected_name

    # ==================== MERGING & DEDUPLICATION TESTS ====================

    def test_merge_and_deduplicate(self, scraper):
        """Test data merging and deduplication"""
        scraper.all_data['static_content']['programs'] = [
            {'name': 'Computer Science', 'level': 'Bachelor', 'source': 'acibadem.edu.tr'},
            {'name': 'Engineering', 'level': 'Master', 'source': 'acibadem.edu.tr'}
        ]
        scraper.all_data['dynamic_content']['programs'] = [
            {'name': 'Computer Science', 'code': 'CS101', 'source': 'obs.acibadem.edu.tr'},
            {'name': 'Business', 'code': 'BUS201', 'source': 'obs.acibadem.edu.tr'}
        ]

        merged = scraper.merge_and_deduplicate()

        assert 'all_programs' in merged
        assert isinstance(merged['all_programs'], list)
        names = [p['name'].lower() for p in merged['all_programs']]
        assert len(names) == len(set(names))

    def test_merge_deduplication_keeps_unique(self, scraper):
        """Test deduplication keeps unique programs"""
        scraper.all_data['static_content']['programs'] = [
            {'name': 'Program A', 'level': 'Bachelor', 'source': 'static'},
        ]
        scraper.all_data['dynamic_content']['programs'] = [
            {'name': 'Program B', 'level': 'Master', 'source': 'dynamic'},
        ]
        merged = scraper.merge_and_deduplicate()
        assert len(merged['all_programs']) == 2

    # ==================== FULL SCRAPE TESTS ====================

    def test_scrape_all_returns_dict(self, scraper):
        """Test full scrape returns proper structure"""
        with patch.object(scraper, 'scrape_static_homepage', return_value={'title': 'ACU'}):
            with patch.object(scraper, 'scrape_static_departments', return_value=[]):
                with patch.object(scraper, 'scrape_static_programs', return_value=[]):
                    with patch.object(scraper, 'scrape_static_contact', return_value={}):
                        with patch.object(scraper, 'init_playwright_driver', return_value=False):
                            result = scraper.scrape_all()

                            assert isinstance(result, dict)
                            assert 'static_content' in result
                            assert 'metadata' in result

    def test_scrape_all_metadata_updated(self, scraper):
        """Test scrape_all updates metadata"""
        with patch.object(scraper, 'scrape_static_homepage', return_value={'title': 'ACU'}):
            with patch.object(scraper, 'scrape_static_departments', return_value=[]):
                with patch.object(scraper, 'scrape_static_programs', return_value=[]):
                    with patch.object(scraper, 'scrape_static_contact', return_value={}):
                        with patch.object(scraper, 'init_playwright_driver', return_value=False):
                            result = scraper.scrape_all()
                            assert 'static_success' in result['metadata']

    # ==================== DATA PERSISTENCE TESTS ====================

    def test_save_to_json_success(self, scraper, tmp_path):
        """Test successful JSON export"""
        filepath = tmp_path / "test_data.json"
        scraper.save_to_json(str(filepath))

        assert filepath.exists()

        import json
        with open(filepath, 'r') as f:
            data = json.load(f)

        assert 'metadata' in data
        assert 'scrape_date' in data['metadata']

    def test_save_to_json_creates_file(self, scraper, tmp_path):
        """Test JSON file is created with correct structure"""
        filepath = tmp_path / "output.json"
        result = scraper.save_to_json(str(filepath))
        assert result is True
        assert filepath.exists()

    def test_clean_text(self, scraper):
        """Test _clean_text removes extra whitespace"""
        assert scraper._clean_text("  hello   world  ") == "hello world"
        assert scraper._clean_text("a\n\nb") == "a b"
        assert scraper._clean_text("normal") == "normal"