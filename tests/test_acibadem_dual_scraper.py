import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from scraper.acibadem_dual_scraper import AcibademDualScraper
from bs4 import BeautifulSoup
import time

class TestAcibademDualScraper:
    """Test suite for dual scraper (static + dynamic)"""
    
    @pytest.fixture
    def scraper(self):
        return AcibademDualScraper(use_headless=True)
    
    # ==================== INITIALIZATION TESTS ====================
    
    def test_scraper_initialization(self, scraper):
        """Test scraper initializes with correct configuration"""
        assert scraper.static_url == "https://www.acibadem.edu.tr/en"
        assert scraper.dynamic_url == "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx"
        assert scraper.headers is not None
        assert 'User-Agent' in scraper.headers
    
    def test_data_structure_initialization(self, scraper):
        """Test all_data structure is properly initialized"""
        assert 'static_content' in scraper.all_data
        assert 'dynamic_content' in scraper.all_data
        assert 'merged_data' in scraper.all_data
        assert 'metadata' in scraper.all_data
    
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
                assert progs[0]['source'] == 'acibadem.edu.tr'
    
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
    
    # ==================== DYNAMIC CONTENT TESTS ====================
    
    def test_selenium_driver_initialization(self, scraper):
        """Test Selenium driver initialization"""
        with patch('scraper.acibadem_dual_scraper.webdriver.Chrome'):
            result = scraper.init_selenium_driver()
            assert isinstance(result, bool)
    
    def test_selenium_driver_initialization_failure(self, scraper):
        """Test graceful handling of Selenium initialization failure"""
        with patch('scraper.acibadem_dual_scraper.webdriver.Chrome') as mock_chrome:
            mock_chrome.side_effect = Exception("Chrome not found")
            
            result = scraper.init_selenium_driver()
            assert result is False
    
    def test_close_selenium_driver(self, scraper):
        """Test Selenium driver closes properly"""
        scraper.driver = MagicMock()
        scraper.close_selenium_driver()
        scraper.driver.quit.assert_called_once()
    
    def test_scrape_dynamic_no_driver(self, scraper):
        """Test dynamic scraping handles missing driver"""
        scraper.driver = None
        
        programs = scraper.scrape_dynamic_obs_programs()
        courses = scraper.scrape_dynamic_obs_courses()
        
        assert programs == []
        assert courses == []
    
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
    
    # ==================== FULL SCRAPE TESTS ====================
    
    def test_scrape_all_returns_dict(self, scraper):
        """Test full scrape returns proper structure"""
        with patch.object(scraper, 'scrape_static_homepage') as mock_home:
            with patch.object(scraper, 'scrape_static_departments') as mock_depts:
                with patch.object(scraper, 'scrape_static_programs') as mock_progs:
                    with patch.object(scraper, 'scrape_static_contact') as mock_contact:
                        with patch.object(scraper, 'init_selenium_driver', return_value=False):
                            mock_home.return_value = {'title': 'ACU'}
                            mock_depts.return_value = []
                            mock_progs.return_value = []
                            mock_contact.return_value = {}
                            
                            result = scraper.scrape_all()
                            
                            assert isinstance(result, dict)
                            assert 'static_content' in result
                            assert 'metadata' in result
    
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