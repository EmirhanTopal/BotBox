from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import requests
import logging
import os
from .models import ChatMessage, Program, Course, Department, ChatSession, Message
from .services.retrieval import RetrievalService
from .services.llm_integration import LLMService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def chat(request, session_id=None):
    """Main chat endpoint - handles chat messages"""
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        
        if not question:
            return JsonResponse({
                'error': 'Question is required'
            }, status=400)
        
        # Get or create session if session_id provided
        session = None
        if session_id:
            session = get_object_or_404(ChatSession, id=session_id)
        
        logger.info(f"Processing question: {question}")
        
        # 1. Retrieve relevant information from database
        retrieval = RetrievalService()
        context = retrieval.retrieve(question)
        logger.info(f"Retrieved context with sources: {context.get('sources', [])}")
        
        # 2. Generate answer using LLM (Ollama)
        llm = LLMService()
        logger.info(f"Calling LLM service with Ollama URL: {llm.ollama_url}")
        
        answer = llm.generate_answer(question, context)
        logger.info(f"LLM Response received: {answer.get('text', '')[:100]}...")
        
        # 3. Store messages in database
        chat_msg = ChatMessage.objects.create(
            question=question,
            answer=answer['text'],
            sources=answer.get('sources', []),
            confidence=answer.get('confidence', 0.0)
        )
        
        # 4. If session exists, also store in session messages
        if session:
            Message.objects.create(
                session=session,
                role='user',
                content=question
            )
            Message.objects.create(
                session=session,
                role='bot',
                content=answer['text']
            )
            session.save()
        
        logger.info(f"Chat completed successfully. Message ID: {chat_msg.id}")
        
        return JsonResponse({
            'id': chat_msg.id,
            'question': question,
            'answer': answer['text'],
            'sources': answer.get('sources', []),
            'confidence': answer.get('confidence', 0.0)
        }, status=200)
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Cannot connect to Ollama: {e}")
        return JsonResponse({
            'error': 'Cannot connect to LLM service. Please ensure Ollama is running.',
            'details': str(e)
        }, status=503)
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e) if os.getenv('DEBUG') == 'True' else 'Server error'
        }, status=500)


@require_http_methods(["GET"])
def index(request):
    """Main index page - list all sessions"""
    sessions = ChatSession.objects.all()
    return render(request, 'chat/index.html', {
        'sessions': sessions,
        'current_session': None,
        'messages': []
    })

@csrf_exempt
@require_http_methods(["POST"])
def new_session(request):
    """Create a new chat session"""
    if request.method == 'POST':
        # Create new session
        session = ChatSession.objects.create(title='Yeni Sohbet')
        #logger.info(f"Created new session: {session.id}")
        return JsonResponse({
            'session_id': session.id,
            'status': 'created'
        })
    else:
        # GET request - redirect to index
        return JsonResponse({'error': 'Use POST to create session'}, status=400)


@require_http_methods(["GET"])
def session_detail(request, session_id):
    """Get session details and messages"""
    session = get_object_or_404(ChatSession, id=session_id)
    messages = session.messages.all().order_by('created_at')
    
    # If GET request, return HTML
    if request.path.endswith('.json'):
        # API call
        return JsonResponse({
            'session_id': session.id,
            'title': session.title,
            'messages': [
                {
                    'id': msg.id,
                    'role': msg.role,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat()
                }
                for msg in messages
            ]
        })
    else:
        # HTML render
        sessions = ChatSession.objects.all()
        return render(request, 'chat/index.html', {
            'sessions': sessions,
            'current_session': session,
            'messages': messages
        })


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request, session_id):
    """Session-based chat endpoint"""
    return chat(request, session_id=session_id)


@require_http_methods(["GET"])
def programs_list(request):
    """Return all programs as JSON."""
    programs = list(Program.objects.all().values())
    return JsonResponse({
        'programs': programs
    }, json_dumps_params={'ensure_ascii': False})


@require_http_methods(["GET"])
def courses_list(request):
    """Return all courses as JSON."""
    courses = list(Course.objects.all().values())
    return JsonResponse({
        'courses': courses
    }, json_dumps_params={'ensure_ascii': False})


@require_http_methods(["GET"])
def departments_list(request):
    """Return all departments as JSON."""
    departments = list(Department.objects.all().values())
    return JsonResponse({
        'departments': departments
    }, json_dumps_params={'ensure_ascii': False})


@require_http_methods(["GET"])
def health(request):
    """Simple health check endpoint."""
    return JsonResponse({
        'status': 'ok'
    })
