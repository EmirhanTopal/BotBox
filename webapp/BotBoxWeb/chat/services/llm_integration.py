"""LLM integration service"""

import requests
import logging
import os
from collections import defaultdict

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://ollama:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')

    def generate_answer(self, question: str, context: dict) -> dict:
        prompt = self._build_prompt(question, context)
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self._build_system_prompt(context)},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 1500, "num_ctx": 4096}
                },
                timeout=180
            )
            if response.status_code == 200:
                result = response.json()
                answer_text = result.get("message", {}).get("content", "").strip()
                return {"text": answer_text, "sources": context.get("sources", []), "confidence": 0.85}
            logger.error(f"Ollama error: {response.status_code}")
            return self._fallback_answer(question, context)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return self._fallback_answer(question, context)

    def _build_system_prompt(self, context: dict) -> str:
        intents = set(context.get("intents", []))
        sc = context.get("semester_courses")

        base = """Sen Acıbadem Üniversitesi'nin resmi yapay zeka asistanısın.

KURALLAR:
- Kullanıcının dilini algıla (Türkçe/İngilizce) ve aynı dilde cevap ver.
- SADECE verilen verileri kullan. Uydurma.
- Veri yoksa: "Bu konuda bilgim bulunmuyor. www.acibadem.edu.tr adresini ziyaret edin."
- Doğal ve akıcı yaz. Türkçe dilbilgisi hatası yapma.

TERMİNOLOJİ: Fakülte=ana birim | Enstitü=lisansüstü | MYO=ön lisans | Bölüm=alt birim | Program=derece | AKTS=Avrupa Kredi Transfer Sistemi"""

        if sc and sc.get("all_semesters"):
            base += "\n\nMÜFREDAT SORUSU: YARIYIL DERSLERİ bölümündeki dersleri yarıyıllara göre gruplandırarak listele. Her yarıyıl için ayrı başlık aç. Zorunlu/seçmeli ayrımını belirt."
        elif 'semester' in intents and 'course' in intents:
            base += "\n\nYARIYIL SORUSU: YARIYIL DERSLERİ bölümündeki dersleri numaralı liste olarak ver. Her satırda: ders kodu, ders adı, AKTS kredi, zorunlu/seçmeli. Başa programa ve yarıyıla ait olduğunu belirten giriş cümlesi ekle. Toplam AKTS'yi yaz."

        if 'list' in intents and 'department' in intents:
            base += "\n\nFORMAT: Fakülteleri numaralı listele. Her fakültenin altına programlarını yaz."
        elif 'list' in intents and 'program' in intents:
            base += "\n\nFORMAT: Programları numaralı listele. Fakülte ve seviyeyi belirt."

        if 'instructor' in intents:
            base += "\n\nAKADEMİSYEN: AKADEMİSYENLER bölümündeki isimleri unvanlarıyla listele. Her satırda unvan ve isim yaz."

        if 'contact' in intents:
            base += "\n\nİLETİŞİM: Sadece verideki bilgileri ver. www.acibadem.edu.tr/iletisim'e yönlendir."
        if 'admission' in intents:
            base += "\n\nBAŞVURU: Kesin puan/tarih verme. www.acibadem.edu.tr'ye yönlendir."
        if 'scholarship' in intents:
            base += "\n\nBURS: Kesin miktar verme. www.acibadem.edu.tr'ye yönlendir."
        if 'international' in intents:
            base += "\n\nULUSLARARASI: İngilizce programları ve Erasmus fırsatlarını vurgula."
        if 'career' in intents:
            base += "\n\nKARİYER: Acıbadem Hastaneleri ağını ve sağlık sektörü fırsatlarını vurgula."

        return base

    def _build_prompt(self, question: str, context: dict) -> str:
        intents = set(context.get("intents", []))
        sc = context.get("semester_courses")

        # ── Yarıyıl / Müfredat dersleri ──
        semester_text = ""
        if sc:
            prog_label = sc.get("program", "")
            all_sems = sc.get("all_semesters", False)

            if all_sems:
                # Tüm müfredat — yarıyıllara göre grupla
                by_sem = defaultdict(list)
                for c in sc.get("courses", []):
                    sem_key = c.get("semester") or 0
                    by_sem[sem_key].append(c)

                lines = [f"[{prog_label} — Tüm Müfredat]"]
                for sem in sorted(by_sem.keys()):
                    label = f"{sem}. Yarıyıl" if sem else "Yarıyıl Belirsiz"
                    lines.append(f"  [{label}]")

                    courses = by_sem[sem]
                    # Zorunluları önce al, hepsini göster
                    zorunlu = [c for c in courses if c.get('type') == 'Zorunlu']
                    secmeli = []

                    for c in zorunlu:
                        lines.append(
                            f"    {c['code']} | {c['name']} | {c.get('credits','-')} AKTS | {c.get('type','-')}"
                        )
                semester_text = "\n".join(lines)
            else:
                # Tek yarıyıl
                sem_label = f"{sc['semester']}. Yarıyıl" if sc.get("semester") else "Yarıyıl"
                header = f"{prog_label} — {sem_label}" if prog_label else sem_label
                lines = [f"[{header}]"]
                for c in sc.get("courses", []):
                    lines.append(
                        f"  {c['code']} | {c['name']} | {c.get('credits','-')} AKTS | {c.get('type','-')}"
                    )
                semester_text = "\n".join(lines)

        # ── Semantic ──
        semantic_lines = []
        for s in context.get("semantic", [])[:5]:
            if s["type"] == "program":
                line = f"- {s['name']} ({s.get('level','')})"
                if s.get("desc"):
                    line += f": {s['desc'][:80]}"
                semantic_lines.append(line)
            elif s["type"] == "course":
                semantic_lines.append(f"- {s['name']} [{s.get('code','')}]")
            elif s["type"] == "department":
                semantic_lines.append(f"- {s['name']}")
        semantic_text = "\n".join(semantic_lines) if semantic_lines else "(yok)"

        # ── Fakülteler ──
        departments_text = ""
        if context.get("departments"):
            lines = []
            for d in context["departments"]:
                line = f"- {d['name']}"
                if d.get("description"):
                    line += f" → {d['description'][:200]}"
                if d.get("email"):
                    line += f" | email: {d['email']}"
                if d.get("phone"):
                    line += f" | tel: {d['phone']}"
                lines.append(line)
            departments_text = "\n".join(lines)

        # ── Programlar ──
        programs_text = ""
        if context.get("programs"):
            programs_text = "\n".join([
                f"- {p['name']} | {p.get('level','-')} | {p.get('department','-')}"
                for p in context["programs"][:10]
            ])

        # ── Akademisyenler ──
        instructors_text = ""
        if context.get("instructors"):
            lines = []
            for inst in context["instructors"][:20]:
                line = f"- {inst.get('title', '')} {inst['name']}"
                if inst.get('department') and inst.get('department') != inst.get('faculty'):
                    line += f" | {inst['department']}"
                line += f" | {inst.get('faculty', '')}"
                lines.append(line)
            instructors_text = "\n".join(lines)

        # ── Dersler (genel arama) ──
        courses_text = ""
        if context.get("courses"):
            courses_text = "\n".join([
                f"- {c.get('code','-')} | {c['name']} | {c.get('credits','-')} AKTS | {c.get('type','-')}"
                + (f" | {c.get('semester','')}.Yarıyıl" if c.get('semester') else "")
                + (f" | {c.get('program_name','')}" if c.get('program_name') else "")
                for c in context["courses"][:10]
            ])

        # ── Genel bilgi ──
        general_text = ""
        if context.get("general_info"):
            g = context["general_info"]
            parts = []
            if g.get("description"):
                parts.append(f"Açıklama: {g['description'][:250]}")
            if g.get("phone"):
                parts.append(f"Tel: {g['phone']}")
            if g.get("email"):
                parts.append(f"Email: {g['email']}")
            if g.get("address"):
                parts.append(f"Adres: {g['address']}")
            if g.get("website"):
                parts.append(f"Web: {g['website']}")
            general_text = "\n".join(parts)

        example = self._get_example(intents, sc)

        prompt = f"""Acıbadem Üniversitesi verileri (YALNIZCA bu verileri kullan):

[YARIYIL DERSLERİ]
{semester_text or "(veri yok)"}

[SEMANTİK ARAMA]
{semantic_text}

[FAKÜLTELER]
{departments_text or "(veri yok)"}

[AKADEMİSYENLER]
{instructors_text or "(veri yok)"}

[PROGRAMLAR]
{programs_text or "(veri yok)"}

[DERSLER]
{courses_text or "(veri yok)"}

[GENEL BİLGİ]
{general_text or "(veri yok)"}

{example}
SORU: {question}
CEVAP:"""

        return prompt

    def _get_example(self, intents: set, sc: dict = None) -> str:
        # Tüm müfredat
        if sc and sc.get("all_semesters"):
            return """ÖRNEK CEVAP:
Tıp Mühendisliği programının müfredatı:

1. Yarıyıl (Zorunlu dersler):
  - MAT 111 — Kalkülüs I | 6 AKTS | Zorunlu
  - PHY 101 — Fizik I | 6 AKTS | Zorunlu
  - CHE 101 — Genel Kimya | 6 AKTS | Zorunlu

2. Yarıyıl:
  - MAT 112 — Kalkülüs II | 6 AKTS | Zorunlu
  ...
"""
        # Tek yarıyıl
        if 'semester' in intents and 'course' in intents:
            return """ÖRNEK CEVAP:
Bilgisayar Mühendisliği programının 1. Yarıyılında şu dersler bulunmaktadır:
1. CHE 101 — Genel Kimya | 6 AKTS | Zorunlu
2. CSE 101 — Programlamaya Giriş | 6 AKTS | Zorunlu
3. ENG 105 — Akademik Amaçlı İngilizce I | 5 AKTS | Zorunlu
4. MAT 111 — Kalkülüs I | 6 AKTS | Zorunlu
5. PHY 101 — Fizik I | 6 AKTS | Zorunlu
6. TUR 101 — Türk Dili I | 2 AKTS | Zorunlu
Toplam: 31 AKTS
"""
        if 'list' in intents and 'department' in intents:
            return """ÖRNEK CEVAP:
1. Mühendislik Fakültesi → Bilgisayar Mühendisliği (İngilizce), Tıp Mühendisliği (İngilizce)
2. Sağlık Bilimleri Fakültesi → Hemşirelik, Fizyoterapi
"""
        if 'list' in intents and 'program' in intents:
            return """ÖRNEK CEVAP:
1. Bilgisayar Mühendisliği (İngilizce) — Mühendislik Fakültesi — Lisans
2. Hemşirelik — Sağlık Bilimleri Fakültesi — Lisans
"""

        if 'instructor' in intents:
            return """ÖRNEK CEVAP:
        Mühendislik ve Doğa Bilimleri Fakültesi akademik kadrosu:
        1. Prof. Dr. Ahmet Bulut | Mühendislik ve Doğa Bilimleri Fakültesi
        2. Dr. Öğr. Üyesi Mehmet Serkan Apaydın | Mühendislik ve Doğa Bilimleri Fakültesi
        """
        if 'contact' in intents:
            return "ÖRNEK CEVAP:\n📞 021-2022 | ✉️ tanitim@acibadem.edu.tr | 🌐 www.acibadem.edu.tr\n"
        if 'admission' in intents:
            return "ÖRNEK CEVAP:\nTürk öğrenciler YKS, yabancı öğrenciler SAT ile başvurabilir. Detaylar: www.acibadem.edu.tr\n"
        if 'scholarship' in intents:
            return "ÖRNEK CEVAP:\nAcıbadem Üniversitesi başarı ve ihtiyaç bursu sunmaktadır. Detaylar: www.acibadem.edu.tr\n"
        if 'campus' in intents:
            return "ÖRNEK CEVAP:\nÜniversite İstanbul Ataşehir'deki Kerem Aydınlar Kampüsü'nde eğitim vermektedir.\n"
        if 'career' in intents:
            return "ÖRNEK CEVAP:\nMezunlar Acıbadem Hastaneleri ve uluslararası sağlık sektöründe kariyer fırsatlarına sahiptir.\n"
        if 'course' in intents:
            return "ÖRNEK CEVAP:\nMAT 111 — Kalkülüs I | 6 AKTS | Zorunlu | Bilgisayar Mühendisliği — 1. Yarıyıl\n"
        return "ÖRNEK CEVAP:\nAcıbadem Üniversitesi'nde Bilgisayar Mühendisliği lisans programı İngilizce olarak Mühendislik Fakültesi bünyesinde sunulmaktadır.\n"

    def _fallback_answer(self, question: str, context: dict) -> dict:
        lines = []
        intents = set(context.get("intents", []))
        sc = context.get("semester_courses")

        if sc:
            prog_label = sc.get("program", "")
            all_sems = sc.get("all_semesters", False)

            if all_sems:
                # Yarıyıllara göre grupla
                by_sem = defaultdict(list)
                for c in sc.get("courses", []):
                    by_sem[c.get("semester") or 0].append(c)
                lines.append(f"{prog_label} — Müfredat:")
                for sem in sorted(by_sem.keys()):
                    label = f"{sem}. Yarıyıl" if sem else "Yarıyıl Belirsiz"
                    lines.append(f"\n{label}:")
                    for c in by_sem[sem]:
                        lines.append(f"  • {c['code']} — {c['name']} | {c.get('credits','-')} AKTS | {c.get('type','-')}")
            else:
                sem_label = f"{sc['semester']}. Yarıyıl" if sc.get("semester") else "Yarıyıl"
                header = f"{prog_label} — {sem_label}" if prog_label else sem_label
                lines.append(f"{header} Dersleri:")
                total_akts = 0
                for c in sc.get("courses", []):
                    lines.append(f"• {c['code']} — {c['name']} | {c.get('credits','-')} AKTS | {c.get('type','-')}")
                    try:
                        total_akts += int(c.get('credits', 0))
                    except:
                        pass
                if total_akts:
                    lines.append(f"\nToplam: {total_akts} AKTS")

        elif 'contact' in intents and context.get("general_info"):
            g = context["general_info"]
            lines.append("İletişim Bilgileri:")
            if g.get("phone"):
                lines.append(f"📞 {g['phone']}")
            if g.get("email"):
                lines.append(f"✉️ {g['email']}")
            if g.get("address"):
                lines.append(f"📍 {g['address']}")
            lines.append("🌐 www.acibadem.edu.tr")

        elif context.get("departments"):
            lines.append("Fakülte ve Birimler:")
            for d in context["departments"][:8]:
                line = f"• {d['name']}"
                if d.get("description"):
                    line += f"\n  → {d['description'][:150]}"
                lines.append(line)

        elif context.get("programs"):
            lines.append("Programlar:")
            for p in context["programs"][:10]:
                lvl = f" ({p['level']})" if p.get("level") else ""
                dept = f" — {p['department']}" if p.get("department") else ""
                lines.append(f"• {p['name']}{lvl}{dept}")

        elif context.get("instructors"):
            lines.append("Akademik Kadro:")
            for inst in context["instructors"][:20]:
                title = inst.get('title', '')
                name = inst.get('name', '')
                faculty = inst.get('faculty', '')
                lines.append(f"• {title} {name} | {faculty}")

        elif context.get("courses"):
            lines.append("Dersler:")
            for c in context["courses"][:10]:
                sem = f" | {c['semester']}.Yarıyıl" if c.get("semester") else ""
                lines.append(f"• {c.get('code','-')} {c['name']} ({c.get('credits','-')} AKTS){sem}")

        elif context.get("semantic"):
            lines.append("İlgili sonuçlar:")
            for s in context["semantic"][:5]:
                if s["type"] == "program":
                    lines.append(f"• {s['name']} ({s.get('level','')})")
                elif s["type"] == "course":
                    lines.append(f"• {s['name']} [{s.get('code','-')}]")
                elif s["type"] == "department":
                    lines.append(f"• {s['name']}")

        elif context.get("general_info"):
            g = context["general_info"]
            if g.get("description"):
                lines.append(g["description"][:300])
            if g.get("phone"):
                lines.append(f"Tel: {g['phone']}")
            if g.get("email"):
                lines.append(f"Email: {g['email']}")

        if lines:
            return {"text": "\n".join(lines), "sources": context.get("sources", []), "confidence": 0.5}
        return {
            "text": "Bu konuda yeterli bilgiye ulaşamadım. Lütfen www.acibadem.edu.tr adresini ziyaret edin.",
            "sources": [], "confidence": 0.0
        }