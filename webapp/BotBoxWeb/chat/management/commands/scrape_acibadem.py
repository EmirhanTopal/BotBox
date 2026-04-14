"""
Django management command to scrape Acibadem University data
Usage: python manage.py scrape_acibadem
"""

from django.core.management.base import BaseCommand
from scraper.acibadem_dual_scraper import AcibademDualScraper
from scraper.data_loader import DataLoader
from chat.models import ScrapingLog
from django.utils import timezone
import logging
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Scrape Acibadem University data from both static and dynamic sources'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--headless',
            action='store_true',
            help='Run browser in headless mode'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Acibadem scraper...'))
        
        # Create log entry
        log = ScrapingLog.objects.create(status='running')
        
        try:
            # Run scraper
            scraper = AcibademDualScraper(use_headless=options['headless'])
            data = scraper.scrape_all()
            
            # Ensure data directory exists
            os.makedirs('data', exist_ok=True)
            scraper.save_to_json('data/acibadem_complete_data.json')
            
            # Load into database
            loader = DataLoader('data/acibadem_complete_data.json')
            loader.load_json()
            loader.load_into_db()
            
            # Update log
            log.status = 'success'
            log.end_time = timezone.now()
            log.items_scraped = (
                len(data['merged_data'].get('all_programs', [])) +
                len(data['merged_data'].get('all_departments', [])) +
                len(data['dynamic_content'].get('courses', []))
            )
            log.metadata = data.get('metadata', {})
            log.save()
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ Scraping completed! Items scraped: {log.items_scraped}'
            ))
        
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.end_time = timezone.now()
            log.save()
            
            self.stdout.write(self.style.ERROR(f'✗ Scraping failed: {e}'))