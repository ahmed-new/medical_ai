import uuid, requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.template.loader import render_to_string
from django.http import HttpResponse,JsonResponse
from django.views.decorators.http import require_POST,require_GET,require_http_methods
from django.utils import timezone
from datetime import datetime



API = settings.BASE_API_URL


def _ensure_device_id(request):
    if "device_id" not in request.session:
        request.session["device_id"] = settings.WEB_DEVICE_ID or f"web-{uuid.uuid4()}"
    return request.session["device_id"]


def _headers(request):
    _ensure_device_id(request)
    h = {"X-Device-Id": request.session["device_id"]}
    if (acc := request.session.get("access")):
        h["Authorization"] = f"Bearer {acc}"
    return h




# web/views.py
def register_view(request):
    if request.method == "POST":
        payload = {
            "username": request.POST.get("username","").strip(),
            "email": request.POST.get("email","").strip(),
            "password": request.POST.get("password","").strip(),
            "phone_number": request.POST.get("phone_number","").strip() or None,
            "study_year": request.POST.get("study_year","").strip(),  # required
        }
        r = None
        try:
            r = requests.post(f"{API}/auth/register/", json=payload, timeout=10)
        except Exception:
            messages.error(request, "Could not reach the server.")
            return render(request, "pages/register.html", {"form": payload})

        if r.status_code in (200,201):
            messages.success(request, "Account created. Please sign in.")
            return redirect("web_login")

        # عرض أخطاء واضحة
        try:
            err = r.json()
        except Exception:
            err = {"detail": f"Unexpected error: {r.status_code}"}
        if isinstance(err, dict):
            for k,v in err.items():
                if isinstance(v, list):
                    for m in v: messages.error(request, f"{k}: {m}")
                else:
                    messages.error(request, f"{k}: {v}")
        else:
            messages.error(request, "Registration failed.")
        return render(request, "pages/register.html", {"form": payload})

    return render(request, "pages/register.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        device_id = _ensure_device_id(request)  # ensure same device ID

        try:
            r = requests.post(
                f"{API}/auth/login/",
                json={"username": username, "password": password, "device_id": device_id},
                timeout=8,
            )
        except Exception:
            messages.error(request, "Unable to connect to the server.")
            return render(request, "pages/login.html")

        if r.status_code == 200:
            data = r.json()
            request.session["access"] = data.get("access")
            request.session["refresh"] = data.get("refresh")
            return redirect("web_home")

        elif r.status_code == 409:
            messages.error(
                request,
                "Your account is already logged in on another device. "
                "Please log out from one device or contact support to manage devices.",
            )

        elif r.status_code in (400, 401):
            messages.error(request, "Invalid username or password.")

        else:
            messages.error(request, f"Unexpected error: {r.status_code}")

    return render(request, "pages/login.html")


def logout_view(request):
    request.session.flush()
    return redirect("web_login")


def _require_auth(request):
    return bool(request.session.get("access"))


def home(request):
    if not _require_auth(request):
        return redirect("web_login")

    # /auth/me
    me = {}
    try:
        r = requests.get(f"{API}/auth/me/", headers=_headers(request), timeout=8)
        if r.status_code == 200:
            me = r.json()
        elif r.status_code == 401:
            return redirect("web_login")
    except Exception:
        pass

    # /streak/message
    streak = {"current_streak": 0, "message": "—"}
    try:
        r = requests.get(f"{API}/v1/edu/streak/message/", headers=_headers(request), timeout=8)
        if r.status_code == 200:
            streak = r.json()
    except Exception:
        pass

    # NEW: KPIs from your endpoints
    study_today_min = 0
    study_month_min = 0
    trees_today = 0
    solved_qs = 0
    accuracy = 0.0
    fav_lessons_total = 0
    flashcards_reviewed = 0  # لسه placeholder

    # Study sessions (today)
    try:
        r = requests.get(f"{API}/v1/track/sessions/?period=today", headers=_headers(request), timeout=8)
        if r.status_code == 200:
            js = r.json()
            study_today_min = js.get("total_minutes", 0) or 0
            trees_today = study_today_min // 25  # 25 min = 1 tree
    except Exception:
        pass

    # Study sessions (month)
    try:
        r = requests.get(f"{API}/v1/track/sessions/?period=month", headers=_headers(request), timeout=8)
        if r.status_code == 200:
            js = r.json()
            study_month_min = js.get("total_minutes", 0) or 0
    except Exception:
        pass

    # Question attempts stats (all-time)
    try:
        r = requests.get(f"{API}/v1/edu/questions/attempts/stats/?period=all", headers=_headers(request), timeout=8)
        if r.status_code == 200:
            js = r.json()
            solved_qs = js.get("total", 0) or 0
            accuracy = js.get("accuracy", 0.0) or 0.0
    except Exception:
        pass

    # Favorites lessons total (نستخدم total من اللست)
    try:
        r = requests.get(f"{API}/v1/edu/favorites/lessons/?limit=1&offset=0", headers=_headers(request), timeout=8)
        if r.status_code == 200:
            js = r.json()
            fav_lessons_total = js.get("total", 0) or 0
    except Exception:
        pass

    ctx = {
        "me": me,
        "streak": streak,
        "study_today_min": study_today_min,
        "study_month_min": study_month_min,
        "trees_today": trees_today,
        "solved_qs": solved_qs,
        "accuracy": accuracy,
        "fav_lessons_total": fav_lessons_total,
        "flashcards_reviewed": flashcards_reviewed,
    }
    return render(request, "pages/home.html", ctx)





@require_POST
def favorite_lesson_toggle(request, lesson_id: int):
    if not _require_auth(request):
        return redirect("web_login")

    headers = _headers(request)

    # 1) اعرف هل الدرس مفضّل حاليًا
    is_fav = False
    try:
        rf = requests.get(f"{API}/v1/edu/favorites/lessons/ids/", headers=headers, timeout=6)
        if rf.status_code == 200:
            ids = set(rf.json().get("ids", []))
            is_fav = int(lesson_id) in ids
    except Exception:
        pass

    # 2) بدّل الحالة عبر الـ API
    try:
        if is_fav:
            # إزالة
            requests.delete(
                f"{API}/v1/edu/favorites/lessons/remove/?lesson={int(lesson_id)}",
                headers=headers, timeout=6
            )
            is_fav = False
        else:
            # إضافة
            requests.post(
                f"{API}/v1/edu/favorites/lessons/add/",
                headers=headers, json={"lesson": int(lesson_id)}, timeout=6
            )
            is_fav = True
    except Exception:
        # حتى لو فشل، هنرجّع الزر بالحالة القديمة
        pass

    # 3) رجّع HTML صغير للزر عشان HTMX يستبدله مكان القديم
    html = render_to_string(
        "components/_favorite_button.html",
        {"lesson_id": int(lesson_id), "is_fav": is_fav},
        request=request,
    )
    return HttpResponse(html)







@require_POST
def mark_lesson_done(request, lesson_id: int):
    if not _require_auth(request):
        return HttpResponse('<span class="text-danger small">Auth required</span>', status=401)

    try:
        r = requests.post(
            f"{API}/v1/edu/lessons/{lesson_id}/progress/done/",
            headers=_headers(request),
            timeout=8
        )
    except Exception:
        return HttpResponse('<span class="text-danger small">Network error</span>', status=502)

    if r.status_code in (200, 201):
        html = render_to_string(
            "components/_lesson_done_button.html",
            {"lesson_id": lesson_id, "is_done": True},
            request=request,
        )
        return HttpResponse(html, status=200)  # << HTML خام
    else:
        try:
            detail = r.json().get("detail") or r.text
        except Exception:
            detail = f"Error {r.status_code}"
        return HttpResponse(f'<span class="text-danger small">{detail}</span>', status=r.status_code)




def materials_home(request):
    if not _require_auth(request):
        return redirect("web_login")

    subject_id = request.GET.get("subject")
    chapter_id = request.GET.get("chapter")
    part_type  = request.GET.get("part_type")  # theoretical|practical

    headers = _headers(request)

    year_me = {}
    semesters, modules, subjects = [], [], []
    chapters, lessons = [], []
    mods_by_sem, subs_by_mod = {}, {}
    error = None

    # 0) User year (optional for display)
    try:
        r = requests.get(f"{API}/v1/edu/years/me/", headers=headers, timeout=8)
        if r.status_code == 200:
            year_me = r.json() or {}
        elif r.status_code == 401:
            return redirect("web_login")
    except Exception:
        pass

    # 1) Semesters
    try:
        r = requests.get(f"{API}/v1/edu/semesters/", headers=headers, timeout=8)
        if r.status_code == 200:
            semesters = r.json() or []
        elif r.status_code == 401:
            return redirect("web_login")
        else:
            error = f"Semesters error: {r.status_code}"
    except Exception:
        error = "Cannot reach API for semesters."

    # 2) Modules
    try:
        r = requests.get(f"{API}/v1/edu/modules/", headers=headers, timeout=8)
        if r.status_code == 200:
            modules = r.json() or []
        elif r.status_code == 401:
            return redirect("web_login")
        else:
            error = f"Modules error: {r.status_code}"
    except Exception:
        error = "Cannot reach API for modules."

    # 3) Subjects
    try:
        r = requests.get(f"{API}/v1/edu/subjects/", headers=headers, timeout=8)
        if r.status_code == 200:
            subjects = r.json() or []
        elif r.status_code == 401:
            return redirect("web_login")
        else:
            error = f"Subjects error: {r.status_code}"
    except Exception:
        error = "Cannot reach API for subjects."

    # 4) Build maps for the tree: mods_by_sem / subs_by_mod
    for m in modules:
        sem_id = m.get("semester")
        if sem_id:
            mods_by_sem.setdefault(sem_id, []).append(m)

    for s in subjects:
        mod_id = s.get("module")
        if mod_id:
            subs_by_mod.setdefault(mod_id, []).append(s)

    # Sort by (order, id) when available
    semesters.sort(key=lambda x: (x.get("order", 0), x.get("id", 0)))
    for arr in mods_by_sem.values():
        arr.sort(key=lambda x: (x.get("order", 0), x.get("id", 0)))
    for arr in subs_by_mod.values():
        arr.sort(key=lambda x: (x.get("order", 0), x.get("id", 0)))

    # 5) If a subject is selected: fetch Chapters first.
    #    DO NOT fetch lessons until a chapter is chosen.
    if subject_id:
        # Chapters
        try:
            rc = requests.get(
                f"{API}/v1/edu/chapters/?subject_id={subject_id}",
                headers=headers, timeout=8
            )
            if rc.status_code == 200:
                chapters = rc.json() or []
                chapters.sort(key=lambda x: (x.get("order", 0), x.get("id", 0)))
            elif rc.status_code == 401:
                return redirect("web_login")
        except Exception:
            pass

        # Lessons → only when a chapter is selected
        lessons = []
        if chapter_id:
            try:
                url = f"{API}/v1/edu/lessons/?subject_id={subject_id}&chapter_id={chapter_id}"
                if part_type in ("theoretical", "practical"):
                    url += f"&part_type={part_type}"
                rl = requests.get(url, headers=headers, timeout=8)
                if rl.status_code == 200:
                    lessons = rl.json() or []
                    lessons.sort(key=lambda x: (x.get("order", 0), x.get("id", 0)))
                elif rl.status_code == 401:
                    return redirect("web_login")
            except Exception:
                pass

    # 6) View mode
    mode = "subject_detail" if subject_id else "tree"

    # Selected subject name
    subject_name = None
    if subject_id and subjects:
        try:
            sid = int(subject_id)
            for s in subjects:
                if s.get("id") == sid:
                    subject_name = s.get("name") or f"Subject #{sid}"
                    break
        except ValueError:
            subject_name = "Subject"
    favorite_ids = []
    try:
        rf = requests.get(f"{API}/v1/edu/favorites/lessons/ids/", headers=headers, timeout=8)
        if rf.status_code == 200:
            favorite_ids = (rf.json() or {}).get("ids", []) or []
    except Exception:
        pass
    
    
    done_ids = []
    if subject_id:
        try:
            u = f"{API}/v1/edu/lessons/progress/ids/?subject_id={subject_id}"
            rr = requests.get(u, headers=headers, timeout=8)
            if rr.status_code == 200:
                done_ids = rr.json().get("ids", []) or []
        except Exception:
            pass
        
    ctx = {
        "mode": mode,
        "year_me": year_me,
        "semesters": semesters,
        "modules": modules,
        "subjects": subjects,
        "mods_by_sem": mods_by_sem,   # { semester_id: [modules...] }
        "subs_by_mod": subs_by_mod,   # { module_id: [subjects...] }
        # when a subject is selected:
        "chapters": chapters,
        "lessons": lessons,
        "favorite_ids": set(favorite_ids),
        "done_ids": done_ids,
        "subject_id": subject_id,
        "subject_name": subject_name,
        "active_part_type": part_type or "",
        "active_chapter": chapter_id or "",
        "error": error,
    }
    return render(request, "pages/materials_home.html", ctx)






def materials_lesson(request, lesson_id: int):
    if not _require_auth(request):
        return redirect("web_login")

    headers = _headers(request)

    # 1) تفاصيل الدرس
    lesson = None
    limited = False     # لو 402
    block_msg = None    # رسالة المنع عند 402

    try:
        r = requests.get(f"{API}/v1/edu/lessons/{lesson_id}/", headers=headers, timeout=10)
    except Exception:
        messages.error(request, "Unable to reach server.")
        return redirect("web_materials_home")

    if r.status_code == 200:
        lesson = r.json() or {}
    elif r.status_code == 402:
        # {detail: "...", lesson: <lite>}
        js = r.json()
        block_msg = js.get("detail") or "Subscription required to view lesson content."
        lesson = js.get("lesson") or {}
        limited = True
    elif r.status_code == 404:
        messages.error(request, "Lesson not found.")
        return redirect("web_materials_home")
    elif r.status_code == 401:
        return redirect("web_login")
    else:
        messages.error(request, f"Unexpected error: {r.status_code}")
        return redirect("web_materials_home")

    # 2) حالة المفضلة (IDs)
    favorite_ids = []
    try:
        rf = requests.get(f"{API}/v1/edu/favorites/lessons/ids/", headers=headers, timeout=8)
        if rf.status_code == 200:
            favorite_ids = rf.json().get("ids", []) or []
    except Exception:
        pass
    is_fav = lesson_id in favorite_ids

    # 3) حالة “تم الإنجاز”
    is_done = False
    try:
        rp = requests.get(
            f"{API}/v1/edu/lessons/progress/count/?lesson_id={lesson_id}",
            headers=headers, timeout=8
        )
        if rp.status_code == 200:
            is_done = (rp.json().get("count") or 0) > 0
    except Exception:
        pass

    # 4) معلومات مساعدة للعرض
    subject_id = lesson.get("subject")
    chapter = lesson.get("chapter")  # ممكن يكون رقم أو dict حسب السيريلایزر
    chapter_title = None
    if isinstance(chapter, dict):
        chapter_title = chapter.get("title") or chapter.get("name")
    # لو serializer بيرجع ID فقط، هنعرض رقم أو نتجاهل

    ctx = {
        "lesson": lesson,
        "lesson_id": lesson_id,
        "is_fav": is_fav,
        "is_done": is_done,
        "limited": limited,
        "block_msg": block_msg,
        "subject_id": subject_id,
        "chapter_title": chapter_title,
    }
    return render(request, "pages/materials_lesson.html", ctx)







@require_GET
def lesson_questions_list(request, lesson_id: int):
    if not _require_auth(request):
        return HttpResponse("Auth", status=401)

    def _to_int(v, d, lo, hi):
        try:
            x = int(v); return max(lo, min(hi, x))
        except Exception:
            return d

    limit  = _to_int(request.GET.get("limit"), 15, 1, 100)
    offset = _to_int(request.GET.get("offset"), 0, 0, 1_000_000)
    mode   = request.GET.get("mode", "panel")          # panel | list
    qtype  = request.GET.get("qtype")
    if qtype not in ("mcq", "written"):
        qtype = None

    # لو مفيش qtype -> ارجع Landing خفيفة بدون أي استعلامات API
    if qtype is None:
        html = render_to_string(
            "components/_questions_landing.html",
            {"lesson_id": lesson_id, "limit": limit},  # limit افتراضي نمرره للروابط
            request=request,
        )
        return HttpResponse(html, status=200)

    # من هنا فقط نطلب الـAPI
    api_url = f"{API}/v1/edu/questions/?lesson_id={lesson_id}&limit={limit}&offset={offset}&question_type={qtype}"

    try:
        r = requests.get(api_url, headers=_headers(request), timeout=10)
        if r.status_code != 200:
            html = "<div class='alert alert-secondary'>No questions.</div>" if mode=="panel" else ""
            return HttpResponse(html, status=r.status_code)
        js = r.json() or {}
        if isinstance(js, dict):
            items = js.get("items", []) or []
            total = js.get("total", 0) or 0
        else:
            items = js or []
            total = offset + len(items)
    except Exception:
        err = "<div class='alert alert-secondary'>Network error.</div>" if mode=="panel" else ""
        return HttpResponse(err, status=502)

    next_offset = offset + len(items)
    has_more = next_offset < total

    ctx = {
        "lesson_id": lesson_id,
        "items": items,
        "limit": limit,
        "offset": offset,
        "next_offset": next_offset,
        "has_more": has_more,
        "qtype": qtype,   # ضروري للروابط
    }

    if mode == "list":
        html = render_to_string("components/_questions_list_items.html", ctx, request=request)
        html += render_to_string("components/_questions_load_more.html", ctx, request=request)  # oob
        return HttpResponse(html, status=200)

    html = render_to_string("components/_questions_panel.html", ctx, request=request)
    return HttpResponse(html, status=200)








@require_GET
def question_detail_htmx(request, pk: int):
    """تفاصيل سؤال واحد (HTMX fragment) — نعرض النص + الصورة + خيارات لو MCQ."""
    if not _require_auth(request):
        return HttpResponse("Auth", status=401)
    try:
        r = requests.get(f"{API}/v1/edu/questions/{pk}/", headers=_headers(request), timeout=10)
        if r.status_code != 200:
            return HttpResponse("<div class='text-danger small'>Question not found.</div>", status=r.status_code)
        q = r.json() or {}
    except Exception:
        return HttpResponse("<div class='text-danger small'>Network error.</div>", status=502)

    html = render_to_string("components/_question_detail.html", {"q": q}, request=request)
    return HttpResponse(html, status=200)






def web_question_attempt(request, pk: int):
    if not _require_auth(request): return HttpResponse(status=401)
    if request.method != "POST": return HttpResponse(status=405)

    payload = {}
    if "option_id" in request.POST:
        payload["option_id"] = request.POST.get("option_id")
    if "is_correct" in request.POST:
        payload["is_correct"] = request.POST.get("is_correct") in ("1","true","True")

    try:
        r = requests.post(f"{API}/v1/edu/questions/{pk}/attempt/",
                          json=payload, headers=_headers(request), timeout=8)
    except Exception:
        return HttpResponse('<div class="alert alert-danger">Network error.</div>')

    # هات تفاصيل السؤال علشان الخيارات للناتج
    rd = requests.get(f"{API}/v1/edu/questions/{pk}/",
                      headers=_headers(request), timeout=8)
    q = rd.json() if rd.status_code==200 else {"options":[]}

    if r.status_code not in (200,201):
        return HttpResponse('<div class="alert alert-danger">Submit failed.</div>')

    res = r.json() or {}
    html = render_to_string("components/_question_result.html", {
        "q": q,
        "chosen_id": int(payload.get("option_id") or 0) or None,
        "correct_id": res.get("correct_option_id"),
        "explanation": res.get("explanation") or "",
        "mode": "submit",
    }, request=request)
    return HttpResponse(html)





def web_question_reveal(request, pk: int):
    if not _require_auth(request): return HttpResponse(status=401)

    try:
        r = requests.get(f"{API}/v1/edu/questions/{pk}/reveal/",
                         headers=_headers(request), timeout=8)
    except Exception:
        return HttpResponse('<div class="alert alert-danger">Network error.</div>')

    rd = requests.get(f"{API}/v1/edu/questions/{pk}/",
                      headers=_headers(request), timeout=8)
    q = rd.json() if rd.status_code==200 else {"options":[]}

    if r.status_code != 200:
        return HttpResponse('<div class="alert alert-danger">Reveal failed.</div>')

    res = r.json() or {}
    html = render_to_string("components/_question_result.html", {
        "q": q,
        "chosen_id": None,  # لم يختر
        "correct_id": res.get("correct_option_id"),
        "explanation": res.get("explanation") or res.get("answer_text") or "",
        "mode": "reveal",
    }, request=request)
    return HttpResponse(html)






# تحميل تبويب الفلاش كاردز (يرجع HTML مرندر)
@require_http_methods(["GET"])
def web_flashcards_panel(request, lesson_id: int):
    mine = request.GET.get("mine") in ("1", "true", "True")

    url = f"{API}/v1/edu/flashcards/?lesson_id={lesson_id}"
    if mine:
        url += "&mine=1"

    flashcards = []
    try:
        r = requests.get(url, headers=_headers(request), timeout=8)
        if r.status_code == 200:
            flashcards = r.json() or []
    except Exception:
        flashcards = []

    html = render_to_string(
        "components/_flashcards_panel.html",
        {"lesson_id": lesson_id, "flashcards": flashcards, "mine": mine},
        request=request,
    )
    return HttpResponse(html)  # مهم: HTML مرندر، مش نص خام


# إنشاء فلاش كارد؛ يرجّع HTML للكارت الجديد فقط ويترك القائمة كما هي
@require_POST
def web_flashcards_create(request, lesson_id: int):
    question = (request.POST.get("question") or "").strip()
    answer   = (request.POST.get("answer") or "").strip()
    order    = int(request.POST.get("order") or 1)

    if not question:
        return HttpResponse('<div class="alert alert-danger">Question is required.</div>', status=400)

    payload = {
        "lesson": lesson_id,
        "question": question,
        "answer": answer,
        "order": order,
        "owner_type": "user",
    }
    try:
        r = requests.post(f"{API}/v1/edu/flashcards/", json=payload, headers=_headers(request), timeout=8)
    except Exception:
        return HttpResponse('<div class="alert alert-danger">Network error.</div>', status=502)

    if r.status_code not in (200, 201):
        return HttpResponse('<div class="alert alert-danger">Failed to add.</div>', status=400)

    # لو الـ API بيرجع {id: ...} بس، نبني الدكت يدويًا للعرض
    data = r.json() or {}
    fc = {
        "id": data.get("id"),
        "question": question,
        "answer": answer,
        "owner_type": "user",
        "owner": None,
    }

    # استخدم نفس الـ markup الموجود في البانل (الكارت القلاب)
    card_html = render_to_string("components/_flashcard_item.html", {"fc": fc}, request=request)
    return HttpResponse(card_html, status=201)


# حذف فلاش كارد (زرار Delete داخل الكارت)
@require_http_methods(["DELETE"])
def web_flashcard_delete(request, pk: int):
    try:
        r = requests.delete(f"{API}/v1/edu/flashcards/{pk}/", headers=_headers(request), timeout=8)
        if r.status_code in (200, 204):
            return HttpResponse("")  # htmx hx-swap="outerHTML" هيشيله
    except Exception:
        pass
    return HttpResponse('<div class="alert alert-danger">Delete failed.</div>', status=400)



@require_POST
def pomodoro_log(request):
    if not _require_auth(request):
        return JsonResponse({"ok": False, "detail": "auth"}, status=401)

    try:
        minutes = int(request.POST.get("minutes", "0"))
    except ValueError:
        minutes = 0
    if minutes <= 0 or minutes > 6 * 60:  # sanity
        return JsonResponse({"ok": False, "detail": "invalid minutes"}, status=400)

    started_at = request.POST.get("started_at")
    if not started_at:
        # fallback: الآن - minutes
        started_at = (timezone.now() - timezone.timedelta(minutes=minutes)).isoformat()

    payload = {
        "started_at": started_at,   # ISO 8601
        "minutes": minutes,
        "source": "pomodoro",
    }

    try:
        r = requests.post(
            f"{API}/v1/track/sessions/",
            headers=_headers(request),
            json=payload,
            timeout=8,
        )
        if r.status_code in (200, 201):
            return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "detail": f"api:{r.status_code}"}, status=400)
    except Exception:
        return JsonResponse({"ok": False, "detail": "network"}, status=502)






# ------ صفحة دخول القسم ------
def web_questions_browse(request):
    if not _require_auth(request):
        return redirect("web_login")
    return render(request, "pages/questions_browse.html")


# --------------- helpers ---------------

def _json_list(resp):
    """
    عشان الـ DRF ساعات يرجّع list وساعات dict فيها items
    """
    try:
        data = resp.json()
    except Exception:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "results", "data"):
            v = data.get(key)
            if isinstance(v, list):
                return v
    return []


def _q_int(v, d=0, lo=None, hi=None):
    try:
        x = int(v)
        if lo is not None:
            x = max(lo, x)
        if hi is not None:
            x = min(hi, x)
        return x
    except Exception:
        return d


# --------------- NAV (left) ---------------

def q_nav_semesters(request):
    semesters = []
    try:
        r = requests.get(f"{API}/v1/edu/semesters/", headers=_headers(request), timeout=8)
        semesters = _json_list(r)
    except Exception:
        semesters = []

    html = render_to_string(
        "components/questions/_nav_semesters.html",
        {"semesters": semesters},
        request=request,
    )
    return HttpResponse(html)


def q_nav_modules(request):
    sem_id = request.GET.get("semester_id")
    modules = []
    if sem_id:
        try:
            r = requests.get(
                f"{API}/v1/edu/modules/?semester_id={sem_id}",
                headers=_headers(request),
                timeout=8,
            )
            modules = _json_list(r)
        except Exception:
            modules = []

    html = render_to_string(
        "components/questions/_nav_modules.html",
        {"modules": modules},
        request=request,
    )
    return HttpResponse(html)


# --------------- PANELS (right - main hubs) ---------------

def q_panel_module_hub(request):
    """
    أول ما الطالب يختار Module
    """
    mid = request.GET.get("module_id")
    ctx = {"module_id": mid}
    return HttpResponse(
        render_to_string("components/questions/_panel_module_hub.html", ctx, request=request)
    )


def q_panel_old_hub(request):
    """
    Old Exams → Finals | MidTerm | TPL | Flipped
    (مش زر واحد TPL & Flipped زى الموبايل)
    """
    mid = request.GET.get("module_id")
    ctx = {"module_id": mid}
    return HttpResponse(
        render_to_string("components/questions/_panel_old_hub.html", ctx, request=request)
    )


def q_panel_examreview_hub(request):
    """
    Exam review → Finals | MidTerm | TPL & Flipped
    """
    mid = request.GET.get("module_id")
    ctx = {"module_id": mid}
    return HttpResponse(
        render_to_string("components/questions/_panel_examreview_hub.html", ctx, request=request)
    )


# --------------- shared smaller panels ---------------

def q_panel_years(request):
    """
    بنستخدمها فى:
    - old finals
    - old midterm
    - old tpl
    - old flipped
    - exam_review (كل أنواعه)
    """
    module_id = request.GET.get("module_id")
    source    = request.GET.get("source")  # old | exam_review
    kind      = request.GET.get("kind")    # final | midterm | tpl | flipped

    years = []
    if module_id:
        # نحاول نجيبها من الـ API
        try:
            url = f"{API}/v1/edu/exam-years/?module_id={module_id}"
            if source:
                url += f"&source={source}"
            if kind:
                url += f"&exam_kind={kind}"
            r = requests.get(url, headers=_headers(request), timeout=8)
            data = r.json() if r.status_code == 200 else []
            # نتوقع يرجّع list عادية
            if isinstance(data, list):
                years = data
            elif isinstance(data, dict):
                years = data.get("years") or []
        except Exception:
            years = []

    # fallback لو الـ API مش جاهز
    if not years:
        from datetime import datetime
        cy = datetime.now().year
        years = [cy, cy - 1, cy - 2]

    ctx = {
        "module_id": module_id,
        "source": source,
        "kind": kind,
        "years": years,
    }
    return HttpResponse(
        render_to_string("components/questions/_panel_years.html", ctx, request=request)
    )



def q_panel_subjects(request):
    """
    دى بتتعامل مع 4 سيناريوهات:
    1) Exams           → module_id + source=exams
    2) Old Exams       → module_id + source=old + kind + exam_year
       - لو kind=final → بعد المادة هنروح parts
       - لو kind=midterm/tpl/flipped → بعد المادة نروح questions مباشرة
    3) Exam review     → module_id + source=exam_review + kind + exam_year
       - لو kind=final → بعد المادة parts
       - غير كده → chapters على طول
    4) الحالة العادية لو حصل missing params هنرجّع subjects بس
    """
    mid        = request.GET.get("module_id")
    source     = request.GET.get("source", "exams")
    kind       = request.GET.get("kind")
    exam_year  = request.GET.get("exam_year")
    subjects   = []

    if mid:
        try:
            r = requests.get(
                f"{API}/v1/edu/subjects/?module_id={mid}",
                headers=_headers(request),
                timeout=8,
            )
            subjects = _json_list(r)
        except Exception:
            subjects = []

    ctx = {
        "subjects": subjects,
        "module_id": mid,
        "source": source,
        "kind": kind,
        "exam_year": exam_year,
    }
    return HttpResponse(
        render_to_string("components/questions/_panel_subjects.html", ctx, request=request)
    )


def q_panel_parts(request):
    """
    دى للأماكن اللى فيها الجزء (theoretical / practical):
    - Exams
    - Old Exams → Finals بس
    - Exam review → Finals بس
    """
    ctx = {
        "module_id": request.GET.get("module_id"),
        "subject_id": request.GET.get("subject_id"),
        "source": request.GET.get("source"),
        "kind": request.GET.get("kind"),
        "exam_year": request.GET.get("exam_year"),
    }
    return HttpResponse(
        render_to_string("components/questions/_panel_parts.html", ctx, request=request)
    )


def q_panel_chapters(request):
    """
    دى للحالات اللى فيها chapters → lessons → questions
    - Exams بعد اختيار part
    - Exam review (معظمها)
    """
    subject_id = request.GET.get("subject_id")
    part_type  = request.GET.get("part_type")
    exam_year  = request.GET.get("exam_year")
    source     = request.GET.get("source")
    kind       = request.GET.get("kind")

    chapters = []
    subject_name = "Chapters"

    if subject_id:
        # اسم المادة
        try:
            rs = requests.get(
                f"{API}/v1/edu/subjects/{subject_id}/",
                headers=_headers(request),
                timeout=8,
            )
            if rs.status_code == 200:
                sd = rs.json()
                subject_name = sd.get("name") or subject_name
        except Exception:
            pass

        # chapters
        try:
            rc = requests.get(
                f"{API}/v1/edu/chapters/?subject_id={subject_id}",
                headers=_headers(request),
                timeout=8,
            )
            chapters = _json_list(rc)
        except Exception:
            chapters = []

    ctx = {
        "subject_id": subject_id,
        "subject_name": subject_name,
        "chapters": chapters,
        "part_type": part_type,
        "exam_year": exam_year,
        "source": source,
        "kind": kind,
    }
    return HttpResponse(
        render_to_string("components/questions/_panel_chapters.html", ctx, request=request)
    )


def q_panel_lessons(request):
    chapter_id = request.GET.get("chapter_id")
    part_type  = request.GET.get("part_type")
    lessons    = []
    chapter_name = "Lessons"

    if chapter_id:
        # اسم الشابتر
        try:
            rc = requests.get(
                f"{API}/v1/edu/chapters/{chapter_id}/",
                headers=_headers(request),
                timeout=8,
            )
            if rc.status_code == 200:
                cd = rc.json()
                chapter_name = cd.get("title") or chapter_name
        except Exception:
            pass

        # الدروس
        try:
            url = f"{API}/v1/edu/lessons/?chapter_id={chapter_id}"
            if part_type in ("theoretical", "practical"):
                url += f"&part_type={part_type}"
            rl = requests.get(url, headers=_headers(request), timeout=8)
            lessons = _json_list(rl)
        except Exception:
            lessons = []

    ctx = {
        "chapter_id": chapter_id,
        "chapter_name": chapter_name,
        "lessons": lessons,
        "part_type": part_type,
        # بنعدى باقى البارامز عشان نوصلها لليفل الأسئلة
        "subject_id": request.GET.get("subject_id"),
        "exam_year": request.GET.get("exam_year"),
        "source": request.GET.get("source"),
        "kind": request.GET.get("kind"),
    }
    return HttpResponse(
        render_to_string("components/questions/_panel_lessons.html", ctx, request=request)
    )


def q_panel_questions(request):
    """
    دى اللى بتعرض البوكس اللى جواه list الأسئلة (الـ wrapper)
    """
    ctx = {
        "lesson_id":  request.GET.get("lesson_id"),
        "subject_id": request.GET.get("subject_id"),
        "source":     request.GET.get("source"),
        "kind":       request.GET.get("kind"),
        "exam_year":  request.GET.get("exam_year"),
        "part_type":  request.GET.get("part_type"),
        "limit":      int(request.GET.get("limit", 10)),
        "qtype":      request.GET.get("qtype", "mcq"),
    }
    return HttpResponse(
        render_to_string("components/questions/_panel_questions_wrapper.html", ctx, request=request)
    )


# --------------- DATA (the real questions call) ---------------





@require_GET
def web_questions_list(request):
    if not _require_auth(request):
        return HttpResponse("Auth", status=401)

    subject_id = request.GET.get("subject_id")
    lesson_id  = request.GET.get("lesson_id")
    source     = request.GET.get("source")
    kind       = request.GET.get("kind")
    exam_year  = request.GET.get("exam_year")
    part_type  = request.GET.get("part_type")
    qtype      = request.GET.get("qtype")  # مهم: مش هنفترض mcq
    limit      = _q_int(request.GET.get("limit"), 15, 1, 100)
    offset     = _q_int(request.GET.get("offset"), 0, 0)

    # 1) لو لسه ما اختارش نوع السؤال → رجّع landing الخاصة بقسم الأسئلة
    if qtype not in ("mcq", "written"):
        html = render_to_string(
            "components/questions/_questions_landing.html",   # ← النسخة الجديدة
            {
                "subject_id": subject_id,
                "lesson_id": lesson_id,
                "source": source,
                "kind": kind,
                "exam_year": exam_year,
                "part_type": part_type,
                "limit": limit,
            },
            request=request,
        )
        return HttpResponse(html, status=200)

    # 2) لو اختار نوع السؤال → نطلب الـ API عادي
    base = f"{API}/v1/edu/questions/?limit={limit}&offset={offset}&question_type={qtype}"

    if subject_id:
        base += f"&subject_id={subject_id}"
    if lesson_id:
        base += f"&lesson_id={lesson_id}"
    if part_type in ("theoretical", "practical"):
        base += f"&part_type={part_type}"

    if source in ("old", "exam_review"):
        if kind:
            base += f"&exam_kind={kind}"
        if exam_year:
            base += f"&exam_year={exam_year}"

    try:
        r = requests.get(base, headers=_headers(request), timeout=10)
        if r.status_code != 200:
            return HttpResponse("<div class='alert alert-secondary'>No questions.</div>", status=200)
        data = r.json() or {}
        if isinstance(data, dict):
            items = data.get("items", []) or []
            total = data.get("total", 0) or 0
        else:
            items = data or []
            total = offset + len(items)
    except Exception:
        return HttpResponse("<div class='alert alert-secondary'>Network error.</div>", status=200)

    next_offset = offset + len(items)
    has_more = next_offset < total

    ctx = {
        "items": items,
        "limit": limit,
        "offset": offset,
        "next_offset": next_offset,
        "has_more": has_more,
        "qtype": qtype,
        # نرجّعهم عشان الـ load more والفورم
        "subject_id": subject_id,
        "lesson_id": lesson_id,
        "source": source,
        "kind": kind,
        "exam_year": exam_year,
        "part_type": part_type,
    }

    html = render_to_string("components/questions/_questions_panel.html", ctx, request=request)
    return HttpResponse(html, status=200)








def flashcards_home(request):
    if not _require_auth(request):
        return redirect("web_login")
    return render(request, "pages/flashcards_home.html")


# ---- Planner (web) ----

def web_planner(request):
    if not _require_auth(request):
        return redirect("web_login")

    from datetime import date, timedelta
    days = []
    today = date.today()
    for i in range(0, 7):
        d = today + timedelta(days=i)
        days.append({
            "iso": d.isoformat(),
            "day": d.day,
            "wd": d.strftime("%a"),
        })
    return render(request, "pages/planner.html", {"next_days": days})




def planner_tasks_htmx(request):
    """ترجع ليست التاسكات (كلها أو ليوم معيّن)"""
    if not _require_auth(request):
        return HttpResponse("Auth", status=401)

    date_str = request.GET.get("date")  # بصيغة YYYY-MM-DD
    tasks = []
    try:
        r = requests.get(f"{API}/v1/edu/planner/tasks/", headers=_headers(request), timeout=8)
        if r.status_code == 200:
            tasks = r.json() or []
    except Exception:
        tasks = []

    # فلترة حسب اليوم لو مبعوت
    if date_str:
        try:
            tasks = [t for t in tasks if t.get("due_date") == date_str]
        except Exception:
            pass

    ctx = {
        "tasks": tasks,
        "selected_date": date_str,
    }
    html = render_to_string("components/planner/_tasks_list.html", ctx, request=request)
    return HttpResponse(html, status=200)




@require_POST
def planner_task_create_htmx(request):
    if not _require_auth(request):
        return HttpResponse("Auth", status=401)

    title = request.POST.get("title") or ""
    due_date = request.POST.get("due_date") or ""
    payload = {"title": title}
    if due_date:
        payload["due_date"] = due_date

    try:
        r = requests.post(
            f"{API}/v1/edu/planner/tasks/",
            json=payload,
            headers=_headers(request),
            timeout=8,
        )
    except Exception:
        return HttpResponse("<div class='alert alert-danger'>Network error.</div>", status=502)

    # بعد الإضافة نرجّع الليست كاملة لنفس اليوم لو كان مبعوت
    return planner_tasks_htmx(request)


def planner_task_toggle_htmx(request, pk):
    """لو متعلم يتشال، لو مش متعلم يتعلّم"""
    if not _require_auth(request):
        return HttpResponse("Auth", status=401)

    # هنجيب التاسك علشان نعرف حالته الحالية
    try:
        # مافيش endpoint get للواحد، فهنجيب الكل ونفلتر
        r = requests.get(f"{API}/v1/edu/planner/tasks/", headers=_headers(request), timeout=8)
        tasks = r.json() if r.status_code == 200 else []
        task = next((t for t in tasks if t.get("id") == pk), None)
    except Exception:
        task = None

    if not task:
        return HttpResponse(status=404)

    is_done = task.get("is_done")
    url = (
        f"{API}/v1/edu/planner/tasks/{pk}/undone/"
        if is_done
        else f"{API}/v1/edu/planner/tasks/{pk}/done/"
    )

    try:
        requests.post(url, headers=_headers(request), timeout=8)
    except Exception:
        pass

    # رجّع الليست لليوم المختار لو فيه
    return planner_tasks_htmx(request)





@require_http_methods(["DELETE", "POST"])
def planner_task_delete_htmx(request, pk):
    if not _require_auth(request):
        return HttpResponse("Auth", status=401)
    try:
        requests.delete(
            f"{API}/v1/edu/planner/tasks/{pk}/",
            headers=_headers(request),
            timeout=8,
        )
    except Exception:
        pass
    return planner_tasks_htmx(request)
























def web_profile(request):
    if not _require_auth(request):
        return redirect("web_login")

    me = {}
    try:
        r = requests.get(f"{API}/auth/me/", headers=_headers(request), timeout=8)
        if r.status_code == 200:
            me = r.json() or {}
    except Exception:
        me = {}

    # ديفولتات
    me.setdefault("username", "")
    me.setdefault("email", "")
    me.setdefault("phone_number", "")
    me.setdefault("study_year", "")
    me.setdefault("plan", "")
    me.setdefault("is_active_subscription", False)
    me.setdefault("activated_at", "")
    me.setdefault("expires_at", "")

    def _fmt_iso(s: str):
        if not s:
            return ""
        try:
            # السلاسل جاية بالشكل ده: 2025-10-23T07:41:19.002735Z
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            # نحولها لتوقيت السيرفر/المستخدم
            dt = dt.astimezone(timezone.get_current_timezone())
            # شكل مقروء من غير ثواني
            return dt.strftime("%d %b %Y, %H:%M")
        except Exception:
            return s  # لو فشل خليه زي ما هو

    activated_fmt = _fmt_iso(me.get("activated_at"))
    expires_fmt = _fmt_iso(me.get("expires_at"))

    ctx = {
        "me": me,
        "activated_at_fmt": activated_fmt,
        "expires_at_fmt": expires_fmt,
    }
    return render(request, "pages/profile.html", ctx)






# plans
def web_plans(request):
    """صفحة عرض الباقات"""
    if not _require_auth(request):
        return redirect("web_login")

    # 1) هات بيانات اليوزر عشان نعرف هو على انهى خطة
    me = {}
    try:
        r = requests.get(f"{API}/auth/me/", headers=_headers(request), timeout=8)
        if r.status_code == 200:
            me = r.json() or {}
    except Exception:
        me = {}
    me_plan = (me.get("plan") or "").lower()
    me_active = bool(me.get("is_active_subscription"))

    # 2) هات الباقات
    plans = []
    try:
        r = requests.get(f"{API}/plans/", timeout=8)
        if r.status_code == 200:
            plans = (r.json() or {}).get("plans", []) or []
    except Exception:
        plans = []

    ctx = {
        "me": me,
        "plans": plans,
        "current_plan": me_plan,
        "is_active": me_active,
    }
    return render(request, "pages/plans.html", ctx)


# ---- HTMX: شراء باقة ----
def web_plans_purchase(request):
    if not _require_auth(request):
        return HttpResponse("Auth", status=401)
    if request.method != "POST":
        return HttpResponse(status=405)

    plan_code = (request.POST.get("plan_code") or "").strip()
    coupon = (request.POST.get("coupon") or "").strip()

    if not plan_code:
        return HttpResponse("<div class='alert alert-danger'>Plan code is required.</div>", status=400)

    try:
        r = requests.post(
            f"{API}/subscriptions/purchase/",
            json={"plan_code": plan_code, "coupon_code": coupon},
            headers=_headers(request),
            timeout=10,
        )
    except Exception:
        return HttpResponse("<div class='alert alert-danger'>Network error.</div>", status=502)

    if r.status_code not in (200, 201):
        # رجع المسج من الـ API لو فيه
        try:
            msg = r.json().get("error") or "Purchase failed."
        except Exception:
            msg = "Purchase failed."
        return HttpResponse(f"<div class='alert alert-danger mb-2'>{msg}</div>", status=400)

    # نجحت
    return HttpResponse("<div class='alert alert-success mb-2'>Subscription activated.</div>", status=200)


# ---- HTMX: تفعيل الترايل ----
def web_plans_start_trial(request):
    if not _require_auth(request):
        return HttpResponse("Auth", status=401)
    if request.method != "POST":
        return HttpResponse(status=405)

    plan_code = (request.POST.get("plan_code") or "basic").strip()

    try:
        r = requests.post(
            f"{API}/subscriptions/start-trial/",
            json={"plan_code": plan_code},
            headers=_headers(request),
            timeout=10,
        )
    except Exception:
        return HttpResponse("<div class='alert alert-danger'>Network error.</div>", status=502)

    if r.status_code not in (200, 201):
        try:
            msg = r.json().get("error") or "Trial activation failed."
        except Exception:
            msg = "Trial activation failed."
        return HttpResponse(f"<div class='alert alert-danger mb-2'>{msg}</div>", status=400)

    return HttpResponse("<div class='alert alert-success mb-2'>Free trial activated.</div>", status=200)