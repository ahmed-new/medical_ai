from datetime import timedelta
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Payment, Subscription, User

@receiver(post_save, sender=Payment)
def activate_sub_when_paid(sender, instance: Payment, created, **kwargs):
    # مش مهم created هنا، الأهم إن الحالة دلوقت PAID
    if instance.status != Payment.Status.PAID:
        return

    sub = getattr(instance, "subscription", None)
    if not sub or sub.status != Subscription.Status.PENDING:
        return

    with transaction.atomic():
        # انهي أي اشتراك Active حالي لنفس اليوزر
        Subscription.objects.filter(
            user=sub.user, status=Subscription.Status.ACTIVE
        ).update(status=Subscription.Status.EXPIRED)

        # فعّل الـ subscription
        now = timezone.now()
        sub.status = Subscription.Status.ACTIVE
        sub.started_at = now
        if not sub.ends_at:
            sub.ends_at = now + timedelta(days=int(sub.plan.duration_days or 0))
        sub.save(update_fields=["status", "started_at", "ends_at"])

        # حدّث بيانات اليوزر
        user = sub.user
        user.plan = sub.plan.code   # assuming Plan.code = 'basic'/'premium'/...
        user.is_active_subscription = True
        user.activated_at = sub.started_at
        user.expires_at = sub.ends_at
        user.save(update_fields=["plan", "is_active_subscription", "activated_at", "expires_at"])
