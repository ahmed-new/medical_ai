# users/urls.py
from django.urls import path
from .views import register, me, login_with_device ,PlanListView, StartFreeTrialView, PurchaseSubscriptionView,CouponValidateView ,CreatePaymentView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView 






urlpatterns = [
    path("auth/register/", register, name="register"),
    path("auth/me/", me, name="me"),
    path("plans/", PlanListView.as_view(), name="plans"),
    path("subscriptions/start-trial/", StartFreeTrialView.as_view(), name="start_trial"),
    path("subscriptions/purchase/", PurchaseSubscriptionView.as_view(), name="purchase_subscription"),
    path("coupons/validate/", CouponValidateView.as_view(), name="coupon_validate"),
    path("payments/create/", CreatePaymentView.as_view(), name="create_payment"),

    # JWT:
    path("auth/login/", login_with_device, name="token_obtain_pair_device"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
