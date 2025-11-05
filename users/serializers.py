# users/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Payment ,Plan
import uuid


User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["username", "email", "password","phone_number", "study_year"]
        extra_kwargs = {"password": {"write_only": True}, "phone_number": {"required": False, "allow_null": True, "allow_blank": True}}

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email","phone_number", "study_year", "plan",
                  "is_active_subscription", "activated_at", "expires_at"]





class CreatePaymentSerializer(serializers.ModelSerializer):
    plan_code   = serializers.CharField(write_only=True, required=False, allow_blank=True)
    notes_code  = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=100)
    final_price = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "plan",
            "plan_code",
            "discount_code",
            "notes_code",
            "reference_no",
            "user_note",
            "final_price",
        ]
        extra_kwargs = {
            "plan": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        from .models import Plan, Payment
        plan       = attrs.get("plan")
        plan_code  = (attrs.get("plan_code") or "").strip()
        notes_code = (attrs.get("notes_code") or "").strip()

        # لازم plan أو plan_code
        if not plan and not plan_code:
            raise serializers.ValidationError("Either 'plan' or 'plan_code' is required.")

        if not plan:
            try:
                plan = Plan.objects.get(code=plan_code, is_active=True)
            except Plan.DoesNotExist:
                raise serializers.ValidationError("Invalid or inactive plan_code.")
            attrs["plan"] = plan

        # final_price لو مبعتش → خده من plan
        fp = attrs.get("final_price")
        if fp is None:
            attrs["final_price"] = plan.price_egp

        # notes_code من الفرونت أو نولّده
        import uuid
        if not notes_code:
            notes_code = str(uuid.uuid4())[:8]
        else:
            if Payment.objects.filter(notes_code=notes_code).exists():
                raise serializers.ValidationError(
                    {"notes_code": "This notes code is already used. Please refresh and try again."}
                )
        attrs["notes_code"] = notes_code
        return attrs

    def create(self, validated_data):
        user         = self.context["request"].user
        plan         = validated_data["plan"]
        discount_code = (validated_data.get("discount_code") or "").strip() or None
        notes_code    = validated_data["notes_code"]
        reference_no  = (validated_data.get("reference_no") or "").strip() or None
        user_note     = (validated_data.get("user_note") or "").strip() or None
        final_price   = validated_data["final_price"]

        payment = Payment.objects.create(
            user=user,
            plan=plan,
            discount_code=discount_code,
            final_price=final_price,
            notes_code=notes_code,
            reference_no=reference_no,
            user_note=user_note,
        )
        return payment
