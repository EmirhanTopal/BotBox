from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import logging
import os

from .models import ChatMessage, Program, Course, Department, ChatSession, Message
from .services.retrieval import RetrievalService
from .services.llm_integration import LLMService

logger = logging.getLogger(__name__)


# =====================
# CHAT ENDPOINT
# =====================
@csrf_exempt
@require_http_methods(["POST"])
def chat(request, session_id=None):
    """Main chat endpoint"""

    try:
        data = json.loads(request.body)
        question = data.get("question", "").strip()

        if not question:
            return JsonResponse({"error": "Question is required"}, status=400)

        # =====================
        # SESSION FIX (CRITICAL)
        # =====================
        if session_id:
            session, _ = ChatSession.objects.get_or_create(id=session_id)
            # İlk mesajda başlığı güncelle
            if session.title in ('Yeni Sohbet', '', None):
                session.title = question[:50]
                session.save(update_fields=['title'])
        else:
            session = None

        logger.info(f"Question: {question}")

        # =====================
        # RETRIEVAL
        # =====================
        retrieval = RetrievalService()
        context = retrieval.retrieve(question)

        logger.info(f"Sources: {context.get('sources', [])}")

        # =====================
        # LLM
        # =====================
        llm = LLMService()
        answer = llm.generate_answer(question, context)

        logger.info(f"LLM answer: {answer.get('text', '')[:100]}")

        # =====================
        # SAVE CHAT MESSAGE
        # =====================
        chat_msg = ChatMessage.objects.create(
            question=question,
            answer=answer["text"],
            sources=answer.get("sources", []),
            confidence=answer.get("confidence", 0.0)
        )

        # =====================
        # SESSION MESSAGES
        # =====================
        if session:
            Message.objects.create(
                session=session,
                role="user",
                content=question
            )
            Message.objects.create(
                session=session,
                role="bot",
                content=answer["text"]
            )

        return JsonResponse({
            "id": chat_msg.id,
            "question": question,
            "answer": answer["text"],
            "sources": answer.get("sources", []),
            "confidence": answer.get("confidence", 0.0)
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return JsonResponse({
            "error": "Internal server error",
            "details": str(e) if os.getenv("DEBUG") == "True" else None
        }, status=500)


# =====================
# INDEX PAGE
# =====================
@require_http_methods(["GET"])
def index(request):
    sessions = ChatSession.objects.all()
    return render(request, "chat/index.html", {
        "sessions": sessions,
        "current_session": None,
        "messages": []
    })


# =====================
# CREATE SESSION
# =====================
@csrf_exempt
@require_http_methods(["POST"])
def new_session(request):
    """Create a new chat session"""

    session = ChatSession.objects.create(title="Yeni Sohbet")

    return JsonResponse({
        "session_id": session.id,
        "status": "created"
    })


# =====================
# SESSION DETAIL
# =====================
@require_http_methods(["GET"])
def session_detail(request, session_id):

    session = get_object_or_404(ChatSession, id=session_id)
    messages = session.messages.all().order_by("created_at")

    if request.path.endswith(".json"):
        return JsonResponse({
            "session_id": session.id,
            "title": session.title,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat()
                }
                for m in messages
            ]
        })

    sessions = ChatSession.objects.all()

    return render(request, "chat/index.html", {
        "sessions": sessions,
        "current_session": session,
        "messages": messages
    })


# =====================
# CHAT API (SESSION BASED)
# =====================
@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request, session_id):
    return chat(request, session_id=session_id)


# =====================
# DATA ENDPOINTS
# =====================
@require_http_methods(["GET"])
def programs_list(request):
    return JsonResponse({
        "programs": list(Program.objects.all().values())
    }, json_dumps_params={"ensure_ascii": False})


@require_http_methods(["GET"])
def courses_list(request):
    return JsonResponse({
        "courses": list(Course.objects.all().values())
    }, json_dumps_params={"ensure_ascii": False})


@require_http_methods(["GET"])
def departments_list(request):
    return JsonResponse({
        "departments": list(Department.objects.all().values())
    }, json_dumps_params={"ensure_ascii": False})


# =====================
# HEALTH CHECK
# =====================
@require_http_methods(["GET"])
def health(request):
    return JsonResponse({"status": "ok"})