# rag_ai/qa.py
import numpy as np
import google.generativeai as genai
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

def answer_with_gemini(question: str, context: str, student_name: str = "Student") -> str:
    """
    English, friendly medical-tutor voice for a Zagazig Univ. student.
    STRICT: rely ONLY on provided context. No citations or References section.
    Starts with student's name.
    """
    import re
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_GEN_MODEL)

    prompt = f"""
You are a clinical tutor helping a medical student at Zagazig University in Egypt.

You MUST rely ONLY on the following excerpts ("Context"). If a detail is not present in the Context, do NOT add it.
Do NOT include any citations, bracketed references, source IDs, URLs, or a "References" section in your answer.

Style rules:
- Start by addressing the student by name: "{student_name}, ..."
- Friendly, supportive, professional English suitable for a medical student.
- Prefer concise sentences and bullet points/steps where helpful.
- Focus on: definition, urgent steps, why they matter, and common pitfalls.
- If the Context is insufficient, reply exactly:
"I cannot be certain from the available references."

Question:
{question}

Context:
{context}
"""
    out = model.generate_content(prompt)
    text = (getattr(out, "text", "") or "").strip()

    if not text:
        return "I cannot be certain from the available references."

    # Hard guard: remove any accidental bracketed refs or a References section
    # Remove lines starting with 'References' (any case)
    text = re.sub(r'(?im)^\s*references\s*:?.*$', "", text)
    # Remove bracketed chunks like [file.pdf#123] or [1], but keep normal brackets in prose
    text = re.sub(r'\[[^\]\n]{1,120}\]', "", text)
    # Collapse extra spaces/newlines after removals
    text = re.sub(r'[ \t]+', ' ', text).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text or "I cannot be certain from the available references."





def ask(question: str, k: int = 15):
    """
    الواجهة الرئيسية: بتجيب أعلى k مقاطع، تبني سياق، وتستدعي Gemini للإجابة.
    """
    hits = search_top_k(question, k=k)              # [(distance, Chunk), ...]
    ctx  = build_context(hits, max_chars=5000)
    ans  = answer_with_gemini(question, ctx)
    sources = [f"{c.file_name}#{c.chunk_index}" for _, c in hits]
    return {"answer": ans, "sources": sources}






def api_ask(question: str, k: int = 15, probes: int = 10, max_chars: int = 5000 ,student_name: str = "student"):
    """
    واجهة مرتبة للـ API:
    - answer: نص الإجابة
    - sources: ["file.pdf#chunk", ...]
    - hits: تفاصيل النتائج (للـ UI)
    """
    # لو search_top_k ما بتاخدش probes عندك، سيبها كده والافتراضي داخلها 10
    hits = search_top_k(question, k=k)  # [(distance, Chunk)]
    ctx  = build_context(hits, max_chars=max_chars)
    ans  = answer_with_gemini(question, ctx ,student_name)

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
