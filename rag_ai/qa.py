# rag_ai/qa.py
import numpy as np
from django.conf import settings
import google.generativeai as genai
import re
from django.conf import settings
from django.db import connection
from rag_ai.models import Chunk

EMBED_DIM = 768  # لازم يطابق vector(dimensions=768)

# --- Embedding ---------------------------------------------------------------

def _ensure_float32_row(vec: np.ndarray) -> np.ndarray:
    if vec.ndim == 1:
        vec = vec.reshape(1, -1)
    return vec.astype("float32")

def embed_query(text: str) -> np.ndarray:
    """
    يحوّل نص الاستعلام إلى متجه (float32) باستخدام Gemini (نفس الموديل اللي كنت بتستخدمه).
    """
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty query")
    res = genai.embed_content(
        model=settings.GEMINI_EMBED_MODEL,
        content=text,
        task_type="retrieval_query",
    )
    vec = np.array(res["embedding"], dtype=np.float32)
    return _ensure_float32_row(vec)  # (1, EMBED_DIM)

# --- Vector search via pgvector ---------------------------------------------

def _to_vec_literal(vec: np.ndarray) -> str:
    """
    يحوّل np.ndarray إلى literal مفهوم من pgvector: "[0.1,0.2,...]".
    """
    row = vec.reshape(-1).astype("float32")
    return "[" + ",".join(f"{float(x):.6f}" for x in row.tolist()) + "]"

def search_top_k(query_text: str, k: int = 5):
    """
    بحث ANN باستخدام pgvector + ivfflat (cosine).
    بيرجّع: [(distance, Chunk), ...] بترتيب الصعود (أقرب أولاً).
    """
    qv = embed_query(query_text)            # (1, EMBED_DIM)
    vec_lit = _to_vec_literal(qv)           # "[...]"

    # استعلام مباشر على PostgreSQL
    with connection.cursor() as cur:
        # probes أعلى = دقة أعلى (وسرعة أبطأ قليلاً). 10 قيمة معقولة كبداية.
        cur.execute("SET LOCAL ivfflat.probes = %s;", [10])

        cur.execute(
            """
            SELECT id, (embedding_vec <=> %s::vector) AS distance
            FROM rag_ai_chunk
            WHERE embedding_vec IS NOT NULL
            ORDER BY embedding_vec <=> %s::vector
            LIMIT %s
            """,
            [vec_lit, vec_lit, k],
        )
        rows = cur.fetchall()   # [(id, distance), ...]

    if not rows:
        return []

    ids_in_order = [r[0] for r in rows]
    dist_by_id = {r[0]: float(r[1]) for r in rows}

    # هات الـ objects مرة واحدة وحافظ على ترتيب الـ ids
    chunks = {c.id: c for c in Chunk.objects.filter(id__in=ids_in_order)}
    ordered = [(dist_by_id[_id], chunks[_id]) for _id in ids_in_order if _id in chunks]
    return ordered

# --- Context building & LLM answer ------------------------------------------

def build_context(chunks, max_chars=2500):
    """
    يستخلص نصوص المقاطع بالحد الأقصى للأحرف.
    chunks: [(distance, Chunk), ...]
    """
    ctx = []
    total = 0
    for _, c in chunks:
        seg = f"[{c.file_name}#{c.chunk_index}] {c.content}".strip()
        if total + len(seg) > max_chars:
            break
        ctx.append(seg)
        total += len(seg)
    return "\n\n".join(ctx)

from django.conf import settings
import requests, re

def answer_with_gemini(question: str, context: str, student_name: str = "Student" , history=None) -> str:
    if not context or not context.strip():
        return "No references matched your question. (context is empty)"
    
    history = history or []
    
     # نحولها لتكست بسيط
    convo_lines = []
    for turn in history[-10:]:
        role = turn.get("role", "user").lower()
        if role in ("user", "student"):
            prefix = "Student"
        elif role in ("bot", "assistant", "tutor"):
            prefix = "Tutor"
        else:
            prefix = "Student"

        content = (turn.get("content") or "").strip()
        if content:
            convo_lines.append(f"{prefix}: {content}")
    convo_text = "\n".join(convo_lines).strip()

    convo_block = f"Conversation so far:\n{convo_text}\n\n" if convo_text else ""
    
    
    model = getattr(settings, "GEMINI_GEN_MODEL", "gemini-1.5-flash")
    url   = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": settings.GOOGLE_API_KEY,
    }

    prompt = f"""You are a clinical tutor helping a medical student at Zagazig University in Egypt.

    You MUST rely ONLY on the following excerpts ("Context"). If a detail is not present in the Context, do NOT add it.
    Do NOT include any citations, bracketed references, source IDs, URLs, or a "References" section in your answer.

    Style rules:
    - Start your first sentence by addressing the student by name: "{student_name}, ..."
    - Use a warm, friendly, encouraging tone, as if you are a kind senior doctor teaching a junior.
    - Prefer concise sentences and bullet points/steps where helpful.
    - Reuse the student's name naturally from time to time in the explanation (not in every line).
    - Focus on: definition, urgent steps, why they matter, and common pitfalls.
    - If the Context is insufficient, reply exactly:
    "I cannot be certain from the available references unliss user not asking for educational."
    - Finish your answer with one short friendly follow-up suggestion on a separate last line,
    starting with:
    "💡 Next:" and suggest what the student could ask you next that is related to this topic
    or to the previous conversation (e.g. comparisons, mnemonics, quick quizzes).

    {convo_block}New question from {student_name}:
    {question}

    Context:
    {context}""".strip()


    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512},
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_CIVIC_INTEGRITY",   "threshold": "BLOCK_NONE"},
        ],
    }
    print(">>> received history:", history)

    print("=== convo_block ===")
    print(convo_block)
    print("====================")

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
    except Exception as e:
        return f"AI call failed: {e}"

    if r.status_code != 200:
        try:
            err = r.json()
        except Exception:
            err = {"raw": r.text}
        return f"AI error {r.status_code}: {err}"

    data = r.json()
    pf = data.get("promptFeedback") or {}
    if pf.get("blockReason"):
        return f"Blocked by safety: {pf.get('blockReason')}"

    text = ""
    cands = data.get("candidates") or []
    if cands:
        parts = (cands[0].get("content") or {}).get("parts") or []
        text = "\n".join(p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")).strip()

    if not text:
        return "I couldn't generate an answer from the provided references."

    text = re.sub(r'(?im)^\s*references\s*:?.*$', "", text)
    text = re.sub(r'\[[^\]\n]{1,120}\]', "", text)
    text = re.sub(r'[ \t]+', " ", text).strip()
    text = re.sub(r'\n{3,}', "\n\n", text)

    return text





def ask(question: str, k: int = 15):
    """
    الواجهة الرئيسية: بتجيب أعلى k مقاطع، تبني سياق، وتستدعي Gemini للإجابة.
    """
    hits = search_top_k(question, k=k)              # [(distance, Chunk), ...]
    ctx  = build_context(hits, max_chars=5000)
    ans  = answer_with_gemini(question, ctx)
    sources = [f"{c.file_name}#{c.chunk_index}" for _, c in hits]
    return {"answer": ans, "sources": sources}






def api_ask(question: str, k: int = 15, probes: int = 10, max_chars: int = 5000 ,student_name: str = "student" , history=None):
    """
    واجهة مرتبة للـ API:
    - answer: نص الإجابة
    - sources: ["file.pdf#chunk", ...]
    - hits: تفاصيل النتائج (للـ UI)
    """
    # لو search_top_k ما بتاخدش probes عندك، سيبها كده والافتراضي داخلها 10
    hits = search_top_k(question, k=k)  # [(distance, Chunk)]
    ctx  = build_context(hits, max_chars=max_chars)
    ans  = answer_with_gemini(question, ctx ,student_name ,history=history)

    sources = [f"{c.file_name}#{c.chunk_index}" for _, c in hits]
    hits_json = [{
        "id": c.id,
        "file_name": c.file_name,
        "chunk_index": c.chunk_index,
        "distance": float(d),
        "score": round(1.0 - float(d), 6),  # (أكبر = أفضل) مع cosine
        "content_preview": (c.content[:300] or "").strip()
    } for d, c in hits]

    return {"answer": ans, "sources": sources, "hits": hits_json}
