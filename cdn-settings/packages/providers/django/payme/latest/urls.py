from django.urls import path

from paykit.providers.payme.views import MerchantAPIView

urlpatterns = [
    path("merchant/", MerchantAPIView.as_view(), name="payme_merchant"),
]
