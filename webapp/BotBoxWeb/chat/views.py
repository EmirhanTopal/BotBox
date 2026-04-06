from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import requests
import logging
from .models import ChatMessage, Program, Course, Department
from .services.retrieval import RetrievalService
from .services.llm_integration import LLMService

logger = logging.getLogger(__name__)

class ChatAPIView:
    """Chat API endpoints"""
    
    def __init__(self):
        self.retrieval = RetrievalService()
        self.llm = LLMService()
    
    @csrf_exempt
    @require_http_methods(["POST"])
    def chat(request):
        """Main chat endpoint"""
        try:
            data = json.loads(request.body)
            question = data.get('question', '').strip()
            
            if not question:
                return JsonResponse({
                    'error': 'Question is required'
                }, status=400)
            
            # Retrieve relevant information
            chat_view = ChatAPIView()
            context = chat_view.retrieval.retrieve(question)
            
            # Generate answer using LLM
            answer = chat_view.llm.generate_answer(question, context)
            
            # Store in database
            chat_msg = ChatMessage.objects.create(
                question=question,
                answer=answer['text'],
                sources=answer.get('sources', []),
                confidence=answer.get('confidence', 0.0)
            )
            
            return JsonResponse({
                'id': chat_msg.id,
                'question': question,
                'answer': answer['text'],
                'sources': answer.get('sources', []),
                'confidence': answer.get('confidence', 0.0)
            }, status=200)
        
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return JsonResponse({
                'error': 'Internal server error'
            }, status=500)


@csrf_exempt
def chat(request):
    """Chat endpoint"""
    return ChatAPIView.chat(request)


@require_http_methods(["GET"])
def programs_list(request):
    """List all programs"""
    programs = Program.objects.all().values('id', 'name', 'level', 'department')
    return JsonResponse({
        'count': programs.count(),
        'programs': list(programs)
    })


@require_http_methods(["GET"])
def courses_list(request):
    """List all courses"""
    courses = Course.objects.all().values('id', 'code', 'name', 'credits')
    return JsonResponse({
        'count': courses.count(),
        'courses': list(courses)
    })


@require_http_methods(["GET"])
def departments_list(request):
    """List all departments"""
    depts = Department.objects.all().values('id', 'name', 'email', 'phone')
    return JsonResponse({
        'count': depts.count(),
        'departments': list(depts)
    })


@require_http_methods(["GET"])
def health(request):
    """Health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'programs': Program.objects.count(),
        'courses': Course.objects.count(),
        'departments': Department.objects.count()
    })

@require_http_methods(["GET"])
def index(request):
    """Ana sayfa"""
    return JsonResponse({'status': 'ok', 'message': 'BotBox API'})


@require_http_methods(["GET", "POST"])
def new_session(request):
    """Yeni oturum"""
    return JsonResponse({'session_id': 1})


@require_http_methods(["GET"])
def session_detail(request, session_id):
    """Oturum detayı"""
    return JsonResponse({'session_id': session_id})


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request, session_id):
    """Session bazlı chat endpoint"""
    return ChatAPIView.chat(request)