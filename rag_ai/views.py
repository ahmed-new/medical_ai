# rag_ai/views.py
import json, time, uuid, traceback
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from users.permissions import SingleDeviceOnly
from rag_ai.qa import ask, api_ask
from rag_ai.utils import can_consume_ai, consume_ai
from users.streak import record_activity
# ===== الواجهة القديمة (تفضل كما هي) =========================================
def chat_ui(request):
    return render(request, "rag/chat.html")

@csrf_exempt
@require_POST
def ask_api(request):
    q = (request.POST.get("q") or "").strip()
    if not q:
        return HttpResponseBadRequest("Missing q")
    if not settings.GOOGLE_API_KEY:
        return HttpResponseBadRequest("Missing GOOGLE_API_KEY")
    try:
        result = ask(q, k=6)
        return JsonResponse(result, json_dumps_params={"ensure_ascii": False})
    except Exception as e:
        traceback.print_exc()
        return HttpResponseBadRequest(str(e))


# ===== API v1 “محمي بـ Bearer” (DRF) =========================================
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication

def _err(code, message, http_status):
    return Response({"error": {"code": code, "message": message}}, status=http_status)

class AskApiV1(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, SingleDeviceOnly]  # لازم توكن

    def post(self, request):
        if not settings.GOOGLE_API_KEY:
            return _err("missing_api_key", "Missing GOOGLE_API_KEY", status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            body = request.data if isinstance(request.data, dict) else {}
            q = (body.get("q") or "").strip()
            if not q:
                return _err("bad_request", "Missing field 'q'", status.HTTP_400_BAD_REQUEST)

            k = int(body.get("k", 15))
            probes = int(body.get("probes", 10))
            max_chars = int(body.get("max_chars", 5000))
        except Exception as e:
            return _err("bad_request", str(e), status.HTTP_400_BAD_REQUEST)

        t0 = time.perf_counter()
        try:
            data = api_ask(q, k=k, probes=probes, max_chars=max_chars)
        except Exception as e:
            traceback.print_exc()
            return _err("server_error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        resp = {
            **data,
            "usage": {
                "embedding_model": getattr(settings, "GEMINI_EMBED_MODEL", ""),
                "generation_model": getattr(settings, "GEMINI_GEN_MODEL", ""),
                "k": k,
                "probes": probes,
                "max_chars": max_chars,
                "vector_metric": "cosine",
                "elapsed_ms": elapsed_ms,
            },
            "trace_id": str(uuid.uuid4()),
        }
        return Response(resp, status=status.HTTP_200_OK)





import json

class AskApiV1Simple(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, SingleDeviceOnly]

    def post(self, request):
        if not settings.GOOGLE_API_KEY:
            return Response({"error": {"code": "missing_api_key", "message": "Missing GOOGLE_API_KEY"}}, status=500)

        body = request.data if isinstance(request.data, dict) else {}
        q = (body.get("q") or "").strip()
        if not q:
            return Response({"error": {"code": "bad_request", "message": "Missing field 'q'"}}, status=400)

        # ✅ history (اختياري)
        raw_history = body.get("history")

        if isinstance(raw_history, str):
            # جاية كسلسلة JSON
            try:
                history = json.loads(raw_history)
            except Exception:
                history = []
        elif isinstance(raw_history, list):
            # جاية list جاهزة من web_ai_ask
            history = raw_history
        else:
            history = []

        history = history[-10:]  # آخر 10 رسائل بس
        print(">>> received history:", history)

        # باقى الكود كما هو...
        if not request.user.is_active_subscription:
            return Response({"error": {"code": "inactive", "message": "Subscription inactive"}}, status=402)

        ok, limit, used = can_consume_ai(request.user)
        if not ok:
            return Response({"error": {"code": "ai_limit", "message": "Daily AI limit reached", "limit": limit, "used": used}}, status=429)

        try:
            display_name = getattr(request.user, "first_name", "") or getattr(request.user, "username", "") or "Student"
            data = api_ask(q, k=10, probes=10, max_chars=4000, student_name=display_name, history=history)
            consume_ai(request.user)
            record_activity(request.user)
            return Response({"answer": data.get("answer", "")}, status=200)
        except Exception as e:
            return Response({"error": {"code": "server_error", "message": str(e)}}, status=500)