from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import User, Plan, Coupon, Subscription

TRIAL_DAYS = 3


# --------- Helper functions ---------
def _set_user_subscription(user: User, plan_code: str, started_at, ends_at):
    """Update user fields after activating a subscription."""
    user.plan = plan_code
    user.is_active_subscription = True
    if not user.activated_at:
        user.activated_at = started_at
    user.expires_at = ends_at
    user.save(update_fields=["plan", "is_active_subscription", "activated_at", "expires_at"])


def _clear_user_subscription(user: User):
    """Deactivate user subscription if expired."""
    user.is_active_subscription = False
    user.plan = User.Plan.NONE
    user.expires_at = None
    user.save(update_fields=["is_active_subscription", "plan", "expires_at"])


# --------- Free Trial ---------
@transaction.atomic
def start_free_trial(user: User, plan_code: str = "basic") -> Subscription:
    """Grant a 3-day free trial once per user."""
    # Has active subscription
    active = Subscription.objects.filter(
        user=user,
        ends_at__gte=timezone.now(),
        status__in=[Subscription.Status.TRIAL, Subscription.Status.ACTIVE],
    ).first()
    if active:
        raise ValidationError("You already have an active subscription.")

    # Trial already used before
    if Subscription.objects.filter(user=user, is_trial=True).exists():
        raise ValidationError("You have already used your free trial.")

    plan = Plan.objects.get(code=plan_code, is_active=True)
    now = timezone.now()
    ends = now + timezone.timedelta(days=TRIAL_DAYS)

    sub = Subscription.objects.create(
        user=user,
        plan=plan,
        status=Subscription.Status.TRIAL,
        is_trial=True,
        started_at=now,
        ends_at=ends,
        final_price_egp=Decimal("0.00"),
    )

    _set_user_subscription(user, plan.code, now, ends)
    return sub


# --------- Paid Subscription ---------
@transaction.atomic
def purchase_subscription(user: User, plan_code: str, coupon_code: str | None = None) -> Subscription:
    """Activate a paid subscription with optional percentage discount."""
    now = timezone.now()

    # Active paid subscription
    if Subscription.objects.filter(user=user, ends_at__gte=now, status=Subscription.Status.ACTIVE).exists():
        raise ValidationError("You already have an active paid subscription.")

    # If free trial active, mark as expired
    trial = Subscription.objects.filter(user=user, ends_at__gte=now, status=Subscription.Status.TRIAL).first()
    if trial:
        trial.status = Subscription.Status.EXPIRED
        trial.save(update_fields=["status"])

    plan = Plan.objects.get(code=plan_code, is_active=True)
    base_price = Decimal(plan.price_egp)
    final_price = base_price
    coupon_txt = None

    # Handle coupon
    if coupon_code:
        c = Coupon.objects.filter(code=coupon_code.strip().upper()).first()
        if not c or not c.is_valid_now():
            raise ValidationError("Invalid or expired coupon code.")
        # Ensure user hasn't used it before
        if Subscription.objects.filter(user=user, coupon_code=c.code).exists():
            raise ValidationError("You have already used this coupon code.")
        # Check global usage limit
        if c.max_uses_total is not None and c.used_count_total >= c.max_uses_total:
            raise ValidationError("This coupon has reached its usage limit.")

        coupon_txt = c.code
        final_price = base_price * (Decimal("100") - Decimal(c.percent)) / Decimal("100")
        if final_price < 0:
            final_price = Decimal("0.00")

        # Increment global counter
        c.used_count_total += 1
        c.save(update_fields=["used_count_total"])

    ends = now + timezone.timedelta(days=plan.duration_days)

    sub = Subscription.objects.create(
        user=user,
        plan=plan,
        status=Subscription.Status.ACTIVE,
        is_trial=False,
        started_at=now,
        ends_at=ends,
        coupon_code=coupon_txt,
        final_price_egp=final_price.quantize(Decimal("0.01")),
    )

    _set_user_subscription(user, plan.code, now, ends)
    return sub


# --------- Expiration check ---------
def expire_due_subscriptions():
    """Mark expired subscriptions and deactivate users with no active plan."""
    now = timezone.now()
    expired = Subscription.objects.filter(
        ends_at__lt=now,
        status__in=[Subscription.Status.TRIAL, Subscription.Status.ACTIVE],
    )
    expired.update(status=Subscription.Status.EXPIRED)

    from django.db.models import Exists, OuterRef
    active_exists = Subscription.objects.filter(
        user=OuterRef("pk"),
        ends_at__gte=now,
        status__in=[Subscription.Status.TRIAL, Subscription.Status.ACTIVE],
    )
    for u in User.objects.annotate(has_active=Exists(active_exists)).filter(has_active=False, is_active_subscription=True):
        _clear_user_subscription(u)
