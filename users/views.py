# users/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, MeSerializer ,CreatePaymentSerializer
from .models import Subscription



User = get_user_model()

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """
    Body: { "username": "", "email": "", "password": "", "study_year": "y1|y2|..." }
    Note: subscription is NOT active; admin must activate later.
    """
    ser = RegisterSerializer(data=request.data)
    if ser.is_valid():
        ser.save()
        return Response({"detail": "registered"}, status=status.HTTP_201_CREATED)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Returns the current user's profile and subscription status.
    """
    return Response(MeSerializer(request.user).data, status=status.HTTP_200_OK)







# users/views.py (بديل لـ TokenObtainPairView)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.utils import timezone

# users/views.py
@api_view(["POST"])
@permission_classes([AllowAny])
def login_with_device(request):
    """
    Body: { "username": "", "password": "", "device_id": "<UUID or any string>" }
    سياسة:
    - يُسمح بتسجيل جهازين (device_id_1, device_id_2).
    - active_device_id يُحدَّث عند كل تسجيل دخول إلى الجهاز الحالي.
    - أي طلبات من جهاز غير نشِط تُرفض بواسطة SingleDeviceOnly.
    """
    username = (request.data.get("username") or "").strip()
    password = (request.data.get("password") or "").strip()
    device_id = (request.data.get("device_id") or "").strip()

    if not username or not password:
        return Response({"detail": "username and password are required"}, status=400)

    user = authenticate(username=username, password=password)
    if not user:
        return Response({"detail": "Invalid credentials"}, status=401)

    # superuser مستثنى من القيد
    if user.is_superuser:
        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)}, status=200)

    if not device_id:
        return Response({"detail": "device_id is required"}, status=400)

    # حالياً مسجلين؟
    slot1 = (user.device_id_1 or "").strip()
    slot2 = (user.device_id_2 or "").strip()

    if device_id == slot1 or device_id == slot2:
        # الجهاز معروف — فعّله
        user.active_device_id = device_id
        user.save(update_fields=["active_device_id"])
    else:
        # جهاز جديد
        if not slot1:
            user.device_id_1 = device_id
            user.active_device_id = device_id
            user.save(update_fields=["device_id_1", "active_device_id"])
        elif not slot2:
            user.device_id_2 = device_id
            user.active_device_id = device_id
            user.save(update_fields=["device_id_2", "active_device_id"])
        else:
            # الاتنين مليانين: ارفض أو اعمل سياسة استبدال لاحقاً
            return Response({"detail": "Two devices already registered"}, status=409)

    # اصدار التوكنات
    refresh = RefreshToken.for_user(user)
    return Response({"refresh": str(refresh), "access": str(refresh.access_token)}, status=200)








# users/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.core.exceptions import ValidationError
from .models import Plan
from .services import start_free_trial, purchase_subscription

# ---------- GET /api/plans/ ----------
class PlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = Plan.objects.filter(is_active=True).values(
            "code", "name", "price_egp", "duration_days"
        )
        return Response({"plans": list(plans)}, status=200)


# ---------- POST /api/subscriptions/start-trial/ ----------
class StartFreeTrialView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # اختياري: plan_code من الـ body، وإلا "basic"
            plan_code = (request.data.get("plan_code") or "basic").strip()

            # تأكيد أن البلان موجودة وفعالة
            from .models import Plan
            try:
                Plan.objects.get(code=plan_code, is_active=True)
            except Plan.DoesNotExist:
                return Response({"error": "Invalid or inactive plan_code."}, status=400)

            sub = start_free_trial(request.user, plan_code=plan_code)
            return Response({
                "message": "Free trial activated successfully.",
                "plan": sub.plan.code,
                "ends_at": sub.ends_at.isoformat(),
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            msg = e.messages[0] if getattr(e, "messages", None) else str(e)
            return Response({"error": msg}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)



# ---------- POST /api/subscriptions/purchase/ ----------
class PurchaseSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_code = (request.data.get("plan_code") or "").strip()
        coupon_code = (request.data.get("coupon_code") or "").strip().upper() or None


        if not plan_code:
            return Response({"error": "plan_code is required."}, status=400)

        # تحقُّق صريح إن الخطة موجودة وفعّالة قبل نداء الخدمة
        try:
            Plan.objects.get(code=plan_code, is_active=True)
        except Plan.DoesNotExist:
            return Response({"error": "Invalid plan_code."}, status=400)

        try:
            sub = purchase_subscription(request.user, plan_code, coupon_code)
            return Response({
                "message": "Subscription activated successfully.",
                "plan": sub.plan.code,
                "price_paid": str(sub.final_price_egp),
                "ends_at": sub.ends_at.isoformat(),
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            msg = e.messages[0] if getattr(e, "messages", None) else str(e)
            return Response({"error": msg}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        
        
        
        

# ---------- GET /api/coupons/validate/ ----------
class CouponValidateView(APIView):
    """
    Validate a coupon code (optionally against a specific plan) without consuming it.
    - Auth: IsAuthenticated (to check per-user usage rule: once per user)
    - Query params:
        code       (required)  -> coupon code string
        plan_code  (optional)  -> to compute discounted price for that plan
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = (request.query_params.get("code") or "").strip().upper()
        plan_code = (request.query_params.get("plan_code") or "").strip()

        if not code:
            return Response({"error": "code is required."}, status=400)

        # 1) fetch coupon
        from .models import Coupon, Plan, Subscription
        c = Coupon.objects.filter(code=code).first()
        if not c:
            return Response({"valid": False, "message": "Coupon not found."}, status=200)

        # 2) basic validity (active + date + global usage)
        if not c.is_valid_now():
            return Response({"valid": False, "message": "Invalid or expired coupon."}, status=200)

        # 3) per-user rule: once per user (if used before => invalid)
        if Subscription.objects.filter(user=request.user, coupon_code=c.code).exists():
            return Response({"valid": False, "message": "You have already used this coupon."}, status=200)

        # 4) optionally compute discounted price for a given plan
        data = {
            "valid": True,
            "code": c.code,
            "percent": str(c.percent),
            "message": "Coupon is valid.",
        }

        if plan_code:
            try:
                plan = Plan.objects.get(code=plan_code, is_active=True)
                base = plan.price_egp
                discounted = (base * (100 - c.percent) / 100).quantize(base.as_tuple().exponent and base or base)  # keep 2dp
                # ضمان رقمين عشريين
                from decimal import Decimal, ROUND_HALF_UP
                discounted = (Decimal(base) * (Decimal("100") - c.percent) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                data.update({
                    "plan_code": plan.code,
                    "base_price": str(plan.price_egp),
                    "discounted_price": str(discounted),
                })
            except Plan.DoesNotExist:
                data.update({
                    "plan_code": plan_code,
                    "base_price": None,
                    "discounted_price": None,
                    "note": "Plan not found or inactive; price not computed."
                })

        return Response(data, status=200)








INSTAPAY_LINK = "https://ipn.eg/S/mohammadalqady/instapay/8fREG1"

class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CreatePaymentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()

        # أنشئ اشتراك Pending مربوط بالدفع
        sub, created = Subscription.objects.get_or_create(
            payment=payment,
            defaults={
                "user": request.user,
                "plan": payment.plan,
                "status": Subscription.Status.PENDING,
                "is_trial": False,
                "coupon_code": payment.discount_code,
                "final_price_egp": payment.final_price,
            },
        )

        return Response({
            "payment_id": str(payment.id),
            "plan": payment.plan.name,
            "plan_code": payment.plan.code,
            "final_price": str(payment.final_price),
            "notes_code": payment.notes_code,
            "status": payment.status,
            "instapay_link": INSTAPAY_LINK,
        }, status=201)
