# edu/policy.py
from typing import Set
from users.models import User
from django.db.models import Q

PLAN_POLICIES = {
    "none":     {"ai_daily_limit": 0,   "sources": set()},  # لا أسئلة ولا AI
    "basic":    {"ai_daily_limit": 10,  "sources": {"qbank"}},
    "premium":  {"ai_daily_limit": 30,  "sources": {"qbank", "exam_review"}},
    "advanced": {"ai_daily_limit": 100, "sources": {"qbank", "exam_review", "tbl", "flipped", "old_exam"}},
}

def get_policy(user: User):
    plan = (user.plan or "none").lower()
    return PLAN_POLICIES.get(plan, PLAN_POLICIES["none"])

def sources_allowed(user: User) -> Set[str]:
    return get_policy(user)["sources"]

def can_view_questions(user: User) -> bool:
    # يشترط اشتراك فعّال لعرض الأسئلة
    return bool(user.is_active_subscription) and bool(sources_allowed(user))



# -------- Flashcards visibility --------
def flashcard_visibility_q(user: User) -> Q:
    """
    يرجّع Q مناسب لتصفية FlashCard حسب خطة المستخدم:
      - none/basic:   user-owned فقط
      - premium:      admin + user-owned
      - advanced:     admin + user-owned (حاليًا كل شيء متاح)
    """
    plan = (user.plan or "none").lower()
    if plan in ("none", "basic"):
        return Q(owner_type="user", owner=user)
    elif plan == "premium":
        return Q(owner_type="admin") | Q(owner_type="user", owner=user)
    elif plan == "advanced":
        return Q(owner_type="admin") | Q(owner_type="user", owner=user)
    # افتراضي أمان
    return Q(owner_type="user", owner=user)


def can_view_lesson_content(user: User) -> bool:
    # لازم اشتراك مفعّل وخطة ليست none
    return bool(user.is_active_subscription) and (user.plan or "none") != "none"
