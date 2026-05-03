"""
API endpoints for data management and scraping
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.csrf import csrf_exempt
import logging
import json
import os
from scraper.acibadem_dual_scraper import AcibademDualScraper
from scraper.data_loader import DataLoader
from chat.models import ScrapingLog
from django.utils import timezone

logger = logging.getLogger(__name__)

def admin_required(view_func):
    """Decorator to require admin or development mode"""
    def wrapped_view(request, *args, **kwargs):
        if os.getenv('DEBUG') == 'True' or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    return wrapped_view

@require_http_methods(["POST"])
@admin_required
@csrf_exempt
def trigger_scrape(request):
    """
    Trigger scraping and data loading
    POST /api/scrape/trigger/
    """
    try:
        # Start scraping in background
        log = ScrapingLog.objects.create(status='running')
        
        # Run scraper
        scraper = AcibademDualScraper(use_headless=True)
        data = scraper.scrape_all()
        
        # Save data
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
        
        return JsonResponse({
            'status': 'success',
            'message': 'Scraping completed',
            'items_scraped': log.items_scraped,
            'log_id': log.id
        })
    
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        log.status = 'failed'
        log.error_message = str(e)
        log.end_time = timezone.now()
        log.save()
        
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@require_http_methods(["GET"])
@admin_required
def scrape_status(request):
    """
    Get scraping status
    GET /api/scrape/status/
    """
    try:
        latest_log = ScrapingLog.objects.latest('start_time')
        return JsonResponse({
            'status': latest_log.status,
            'items_scraped': latest_log.items_scraped,
            'start_time': latest_log.start_time.isoformat(),
            'end_time': latest_log.end_time.isoformat() if latest_log.end_time else None,
            'error': latest_log.error_message
        })
    except ScrapingLog.DoesNotExist:
        return JsonResponse({
            'status': 'never_run',
            'message': 'No scraping has been run yet'
        })

@require_http_methods(["GET"])
def data_stats(request):
    """
    Get database statistics
    GET /api/data/stats/
    """
    from chat.models import Program, Course, Department, UniversityInfo
    
    return JsonResponse({
        'programs': Program.objects.count(),
        'courses': Course.objects.count(),
        'departments': Department.objects.count(),
        'university_info': UniversityInfo.objects.count(),
        'timestamp': timezone.now().isoformat()
    })
