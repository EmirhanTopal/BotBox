import json
import requests
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import ChatSession, Message


def index(request):
    sessions = ChatSession.objects.all()
    return render(request, 'chat/index.html', {'sessions': sessions})


def session_detail(request, session_id):
    sessions = ChatSession.objects.all()
    current = get_object_or_404(ChatSession, id=session_id)
    messages = current.messages.all()
    return render(request, 'chat/index.html', {
        'sessions': sessions,
        'current_session': current,
        'messages': messages,
    })


@csrf_exempt
def new_session(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST gerekli'}, status=405)
    session = ChatSession.objects.create()
    return JsonResponse({'session_id': session.id})


@csrf_exempt
def chat_api(request, session_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST gerekli'}, status=405)

    session = get_object_or_404(ChatSession, id=session_id)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON'}, status=400)

    question = data.get('question', '').strip()
    if not question:
        return JsonResponse({'error': 'Soru boş olamaz'}, status=400)

    if not session.messages.exists():
        session.title = question[:60]
        session.save()

    Message.objects.create(session=session, role='user', content=question)

    answer = ask_llm(session, question)

    Message.objects.create(session=session, role='bot', content=answer)

    return JsonResponse({'answer': answer})


def ask_llm(session, question):
    history = session.messages.order_by('created_at')
    history_text = ""
    for msg in history:
        prefix = "Kullanıcı" if msg.role == 'user' else "Asistan"
        history_text += f"{prefix}: {msg.content}\n"

    prompt = f"""Sen Acıbadem Üniversitesi hakkında bilgi veren yardımcı bir asistansın.
Soruları Türkçe olarak yanıtla.

{history_text}
Asistan:"""

    try:
        response = requests.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120
        )
        if response.status_code == 200:
            return response.json().get("response", "Yanıt alınamadı.")
        return f"LLM servisi hata döndürdü (HTTP {response.status_code})."
    except requests.exceptions.ConnectionError:
        return "⚠️ LLM servisi şu anda çalışmıyor."
    except requests.exceptions.Timeout:
        return "⚠️ LLM zaman aşımına uğradı, tekrar deneyin."
    except Exception as e:
        return f"⚠️ Hata: {str(e)}"