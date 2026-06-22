from django.urls import path

from paykit.providers.payme.views import MerchantAPIView, SubscriptionAPIView

app_name = "payme"

urlpatterns = [
    path("merchant/", MerchantAPIView.as_view(), name="merchant"),
    path("subscription/", SubscriptionAPIView.as_view(), name="subscription"),
]
