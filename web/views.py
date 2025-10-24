import uuid, requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.template.loader import render_to_string
from django.http import HttpResponse,JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone


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
        "subject_id": subject_id,
        "subject_name": subject_name,
        "active_part_type": part_type or "",
        "active_chapter": chapter_id or "",
        "error": error,
    }
    return render(request, "pages/materials_home.html", ctx)






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






def questions_home(request):
    if not _require_auth(request):
        return redirect("web_login")
    return render(request, "pages/questions_home.html")


def flashcards_home(request):
    if not _require_auth(request):
        return redirect("web_login")
    return render(request, "pages/flashcards_home.html")


def planner_home(request):
    if not _require_auth(request):
        return redirect("web_login")
    return render(request, "pages/planner_home.html")


def profile_home(request):
    if not _require_auth(request):
        return redirect("web_login")
    return render(request, "pages/profile_home.html")
