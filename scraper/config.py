"""
Scraper configuration settings
"""

SCRAPER_CONFIG = {
    'static_url': 'https://www.acibadem.edu.tr/en',
    'dynamic_url': 'https://obs.acibadem.edu.tr/oibs/bologna/index.aspx',
    'timeout': 15,
    'headless': True,
    'output_file': 'data/acibadem_complete_data.json',
    'request_delay': 0.5,
    'retries': 3
}

SELENIUM_CONFIG = {
    'chrome_options': [
        '--headless',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-blink-features=AutomationControlled'
    ],
    'wait_timeout': 15,
    'page_load_timeout': 30
}