SCRAPER_CONFIG = {
    'static_url': 'https://www.acibadem.edu.tr/en',
    'dynamic_url': 'https://obs.acibadem.edu.tr/oibs/bologna/index.aspx',
    'timeout': 15,
    'headless': True,
    'output_file': 'data/acibadem_complete_data.json',
    'request_delay': 0.5,
    'retries': 3
}

PLAYWRIGHT_CONFIG = {
    'browser_args': [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-blink-features=AutomationControlled'
    ],
    'default_timeout': 30000,   # ms
    'network_idle_timeout': 15000,
    'page_load_timeout': 30000
}