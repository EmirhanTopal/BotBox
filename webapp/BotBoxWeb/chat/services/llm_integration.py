"""LLM integration service"""

import requests
import logging
import os

logger = logging.getLogger(__name__)


class LLMService:
    """
    Integration with Ollama LLM service
    """

    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://ollama:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'mistral')

    def generate_answer(self, question: str, context: dict) -> dict:

        prompt = self._build_prompt(question, context)

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.2
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "text": result.get("response", "").strip(),
                    "sources": context.get("sources", []),
                    "confidence": 0.85
                }

            logger.error(f"Ollama error: {response.status_code}")
            return self._fallback_answer(question, context)

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return self._fallback_answer(question, context)

    def _build_prompt(self, question: str, context: dict) -> str:
        """
        Semantic ve structured veriden okunabilir bir prompt üretir.
        """

        # --- Semantic sonuçları okunabilir metne çevir ---
        semantic_lines = []
        for s in context.get("semantic", []):
            if s["type"] == "program":
                line = f"  - [Program] {s['name']}"
                if s.get("level"):
                    line += f" ({s['level']})"
                if s.get("desc"):
                    line += f": {s['desc'][:150]}"
                semantic_lines.append(line)
            elif s["type"] == "course":
                semantic_lines.append(f"  - [Course] {s['name']} — Kod: {s.get('code', '')}")
            elif s["type"] == "department":
                line = f"  - [Department] {s['name']}"
                if s.get("desc"):
                    line += f": {s['desc'][:150]}"
                semantic_lines.append(line)

        semantic_text = "\n".join(semantic_lines) if semantic_lines else "  (Semantic sonuç bulunamadı)"

        # --- Structured veriler ---
        programs_text = ""
        if context.get("programs"):
            programs_text = "\n".join([
                f"  - {p['name']} | {p.get('level', '')} | {p.get('department', '')}"
                for p in context["programs"]
            ])

        departments_text = ""
        if context.get("departments"):
            departments_text = "\n".join([
                f"  - {d['name']} | {d.get('email', '')} | {d.get('phone', '')}"
                for d in context["departments"]
            ])

        courses_text = ""
        if context.get("courses"):
            courses_text = "\n".join([
                f"  - {c['code']} {c['name']} ({c.get('credits', '')} kredi)"
                for c in context["courses"]
            ])

        general_text = ""
        if context.get("general_info"):
            g = context["general_info"]
            general_text = f"""  Üniversite: {g.get('title', '')}
  Açıklama: {g.get('description', '')[:200]}
  Misyon: {g.get('mission', '')[:150]}
  Vizyon: {g.get('vision', '')[:150]}
  Telefon: {g.get('phone', '')}
  E-posta: {g.get('email', '')}"""

        prompt = f"""Sen Acıbadem Üniversitesi'nin yapay zeka destekli asistanısın.

KURALLAR:
- Kullanıcının dilini (Türkçe veya İngilizce) otomatik algıla ve aynı dilde cevap ver.
- YALNIZCA aşağıda verilen verileri kullan. Bilmediğin şeyi uydurma.
- Spesifik sorulara spesifik cevap ver. Genel bilgi verme.
- Kısa ve net ol.

=======================
SEMANTİK ARAMA SONUÇLARI (en alakalı):
{semantic_text}

PROGRAMLAR:
{programs_text or "  (Veri yok)"}

BÖLÜMLER:
{departments_text or "  (Veri yok)"}

DERSLER:
{courses_text or "  (Veri yok)"}

ÜNİVERSİTE GENEL BİLGİ:
{general_text or "  (Veri yok)"}
=======================

SORU: {question}

CEVAP:"""

        return prompt

    def _fallback_answer(self, question: str, context: dict) -> dict:
        """Ollama erişilemezse veriden doğrudan cevap üretir."""

        parts = []

        # Semantic sonuçlardan cevap üret
        if context.get("semantic"):
            sem_parts = []
            for s in context["semantic"]:
                if s["type"] == "program":
                    sem_parts.append(f"{s['name']}" + (f" ({s.get('level', '')})" if s.get("level") else ""))
                elif s["type"] == "course":
                    sem_parts.append(f"{s['name']} ({s.get('code', '')})")
                elif s["type"] == "department":
                    sem_parts.append(s["name"])
            if sem_parts:
                parts.append("İlgili sonuçlar: " + ", ".join(sem_parts))

        if context.get("programs"):
            parts.append("Programlar: " + ", ".join([p["name"] for p in context["programs"][:5]]))

        if context.get("departments"):
            parts.append("Bölümler: " + ", ".join([d["name"] for d in context["departments"][:5]]))

        if context.get("courses"):
            parts.append("Dersler: " + ", ".join([c["name"] for c in context["courses"][:5]]))

        if context.get("general_info"):
            info = context["general_info"]
            parts.append(f"{info.get('title', '')} — {info.get('description', '')[:200]}")

        if parts:
            return {
                "text": "\n".join(parts),
                "sources": context.get("sources", []),
                "confidence": 0.5
            }

        return {
            "text": "Yeterli bilgi bulunamadı.",
            "sources": [],
            "confidence": 0.0
        }