#users/streak.py 

from datetime import timedelta
from django.utils import timezone
from zoneinfo import ZoneInfo

CAIRO = ZoneInfo("Africa/Cairo")

def record_activity(user):
    s = getattr(user, "streak", None)
    if s is None:
        from users.models import UserStreak
        s = UserStreak.objects.create(user=user, current_streak=0, last_active_date=None)

    today = timezone.now().astimezone(CAIRO).date()
    if s.last_active_date == today:
        return  # نشاط اليوم محسوب بالفعل

    # أول نشاط في يوم جديد:
    if s.last_active_date == today - timedelta(days=1):
        s.current_streak += 1
    else:
        s.current_streak = 1

    s.last_active_date = today
    s.save(update_fields=["current_streak", "last_active_date"])
