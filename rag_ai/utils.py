# rag_ai/utils.py
from datetime import date
from django.db import transaction
from .models import DailyAIUsage

def can_consume_ai(user):
    from edu.policy import get_policy
    policy = get_policy(user)
    limit = int(policy.get("ai_daily_limit", 0))
    if limit <= 0:
        return False, limit, 0
    today = date.today()
    obj, _ = DailyAIUsage.objects.get_or_create(user=user, date=today)
    return (obj.count < limit), limit, obj.count

def consume_ai(user, n=1):
    today = date.today()
    with transaction.atomic():
        obj, _ = DailyAIUsage.objects.select_for_update().get_or_create(user=user, date=today)
        obj.count += n
        obj.save()
        return obj.count
