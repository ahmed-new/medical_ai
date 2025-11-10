# # edu/policy.py
# from typing import Set
# from users.models import User
# from django.db.models import Q

# PLAN_POLICIES = {
#     "none":     {"ai_daily_limit": 0,   "sources": set()},  # لا أسئلة ولا AI
#     "basic":    {"ai_daily_limit": 10,  "sources": {"qbank"}},
#     "premium":  {"ai_daily_limit": 30,  "sources": {"qbank", "exam_review"}},
#     "advanced": {"ai_daily_limit": 100, "sources": {"qbank", "exam_review", "tbl", "flipped", "old_exam"}},
# }





# def get_policy(user: User):
#     plan = (user.plan or "none").lower()
#     return PLAN_POLICIES.get(plan, PLAN_POLICIES["none"])

# def sources_allowed(user: User) -> Set[str]:
#     return get_policy(user)["sources"]

# def can_view_questions(user: User) -> bool:
#     # يشترط اشتراك فعّال لعرض الأسئلة
#     return bool(user.is_active_subscription) and bool(sources_allowed(user))



# # -------- Flashcards visibility --------
# def flashcard_visibility_q(user: User) -> Q:
#     """
#     يرجّع Q مناسب لتصفية FlashCard حسب خطة المستخدم:
#       - none/basic:   user-owned فقط
#       - premium:      admin + user-owned
#       - advanced:     admin + user-owned (حاليًا كل شيء متاح)
#     """
#     plan = (user.plan or "none").lower()
#     if plan in ("none", "basic"):
#         return Q(owner_type="user", owner=user)
#     elif plan == "premium":
#         return Q(owner_type="admin") | Q(owner_type="user", owner=user)
#     elif plan == "advanced":
#         return Q(owner_type="admin") | Q(owner_type="user", owner=user)
#     # افتراضي أمان
#     return Q(owner_type="user", owner=user)


# def can_view_lesson_content(user: User) -> bool:
#     # لازم اشتراك مفعّل وخطة ليست none
#     return bool(user.is_active_subscription) and (user.plan or "none") != "none"

# edu/policy.py
from typing import Set
from users.models import User
from django.db.models import Q

PLAN_POLICIES = {
    "none": {
        "ai_daily_limit": 0,
        "sources": set(),
        "allow_tbl": False,
        "allow_flipped": False,
    },
    "basic": {
        "ai_daily_limit": 10,
        "sources": {"qbank"},
        "allow_tbl": False,
        "allow_flipped": False,
    },
    "premium": {
        "ai_daily_limit": 30,
        "sources": {"qbank", "exam_review"},
        "allow_tbl": False,   # ما يشوفش TBL
        "allow_flipped": False,  # ما يشوفش Flipped
    },
    "advanced": {
        "ai_daily_limit": 100,
        "sources": {"qbank", "exam_review", "old_exam"},
        "allow_tbl": True,       # يشوف TBL
        "allow_flipped": True,   # يشوف Flipped
    },
}


def _plan(user) -> str:
    p = getattr(user, "plan", None)
    if isinstance(p, str):
        return (p or "none").lower()
    return "none"

def _active(user) -> bool:
    return bool(getattr(user, "is_active_subscription", False))

def get_policy(user: User):
    plan = _plan(user)
    return PLAN_POLICIES.get(plan, PLAN_POLICIES["none"])

def sources_allowed(user: User) -> Set[str]:
    return get_policy(user)["sources"]

def can_view_questions(user: User) -> bool:
    return _active(user) and bool(sources_allowed(user))

def flashcard_visibility_q(user: User) -> Q:
    plan = _plan(user)
    if plan in ("none", "basic"):
        return Q(owner_type="user", owner=user)
    elif plan in ("premium", "advanced"):
        return Q(owner_type="admin") | Q(owner_type="user", owner=user)
    return Q(owner_type="user", owner=user)

def can_view_lesson_content(user: User) -> bool:
    return _active(user) and _plan(user) != "none"

def can_use_flashcards(user: User) -> bool:
    return _active(user) and _plan(user) in ("premium", "advanced")
