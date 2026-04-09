from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from .models import ChatMessage, ChatSession, Message, Program, Course, Department
from .services.retrieval import RetrievalService
from .services.llm_integration import LLMService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    """Ana chat endpoint - session'sız"""
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()

        if not question:
            return JsonResponse({'error': 'Question is required'}, status=400)

        retrieval = RetrievalService()
        llm = LLMService()

        context = retrieval.retrieve(question)
        answer = llm.generate_answer(question, context)

        # ChatMessage olarak kaydet
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
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def new_session(request):
    """Yeni chat session oluştur"""
    try:
        data = json.loads(request.body) if request.body else {}
        title = data.get('title', 'Yeni Sohbet')

        session = ChatSession.objects.create(title=title)

        return JsonResponse({
            'session_id': session.id,
            'title': session.title,
            'created_at': session.created_at.isoformat()
        }, status=201)

    except Exception as e:
        logger.error(f"New session error: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request, session_id):
    """Session bazlı chat endpoint"""
    try:
        # Session'ı bul
        try:
            session = ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)

        data = json.loads(request.body)
        question = data.get('question', '').strip()

        if not question:
            return JsonResponse({'error': 'Question is required'}, status=400)

        # Kullanıcı mesajını kaydet
        Message.objects.create(
            session=session,
            role='user',
            content=question
        )

        # Cevap üret
        retrieval = RetrievalService()
        llm = LLMService()

        context = retrieval.retrieve(question)
        answer = llm.generate_answer(question, context)
        answer_text = answer['text']

        # Bot cevabını kaydet
        Message.objects.create(
            session=session,
            role='bot',
            content=answer_text
        )

        # Session title'ı güncelle (ilk mesajdan)
        if session.title == 'Yeni Sohbet':
            session.title = question[:50]
            session.save()

        return JsonResponse({
            'session_id': session_id,
            'question': question,
            'answer': answer_text,
            'sources': answer.get('sources', []),
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@require_http_methods(["GET"])
def session_detail(request, session_id):
    """Session geçmişini getir"""
    try:
        session = ChatSession.objects.get(id=session_id)
        messages = session.messages.all().values('role', 'content', 'created_at')

        return JsonResponse({
            'session_id': session_id,
            'title': session.title,
            'messages': [
                {
                    'role': m['role'],
                    'content': m['content'],
                    'created_at': m['created_at'].isoformat()
                }
                for m in messages
            ]
        })

    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Session detail error: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@require_http_methods(["GET"])
def sessions_list(request):
    """Tüm session'ları listele"""
    sessions = ChatSession.objects.all().values('id', 'title', 'created_at', 'updated_at')
    return JsonResponse({
        'count': sessions.count(),
        'sessions': [
            {
                'id': s['id'],
                'title': s['title'],
                'created_at': s['created_at'].isoformat(),
                'updated_at': s['updated_at'].isoformat()
            }
            for s in sessions
        ]
    })


@require_http_methods(["GET"])
def index(request):
    """Ana sayfa"""
    return render(request, 'chat/index.html')


@require_http_methods(["GET"])
def programs_list(request):
    programs = Program.objects.all().values('id', 'name', 'level', 'department')
    return JsonResponse({'count': programs.count(), 'programs': list(programs)})


@require_http_methods(["GET"])
def courses_list(request):
    courses = Course.objects.all().values('id', 'code', 'name', 'credits')
    return JsonResponse({'count': courses.count(), 'courses': list(courses)})


@require_http_methods(["GET"])
def departments_list(request):
    depts = Department.objects.all().values('id', 'name', 'email', 'phone')
    return JsonResponse({'count': depts.count(), 'departments': list(depts)})


@require_http_methods(["GET"])
def health(request):
    return JsonResponse({
        'status': 'healthy',
        'programs': Program.objects.count(),
        'courses': Course.objects.count(),
        'departments': Department.objects.count(),
        'sessions': ChatSession.objects.count(),
        'messages': Message.objects.count(),
    })