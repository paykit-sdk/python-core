"""
URL configuration for django_test project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

from paykit.providers.payme import generate_paylink
from paykit.providers.payme.models import PaymeMerchant, PaymeTransaction
from paykit.providers.payme.views import MerchantAPIViewRaw

template = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    body {{
        margin: 0;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #0a0a0a;
        font-family: sans-serif;
    }}
    a {{
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 14px 28px;
        background: #111;
        color: #e0e0e0;
        text-decoration: none;
        border: 1px solid #2a2a2a;
        border-radius: 10px;
        font-size: 15px;
        transition: background 0.2s, border-color 0.2s, color 0.2s;
    }}
    a:hover {{
        background: #1a1a1a;
        border-color: #555;
        color: #fff;
    }}
    a svg {{opacity: 0.5; transition: opacity 0.2s; }}
    a:hover svg {{opacity: 1; }}
    </style>
    </head>
    <body>
    <a href="{}" target="_blank">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
        <polyline points="15 3 21 3 21 9"/>
        <line x1="10" y1="14" x2="21" y2="3"/>
        </svg>
        {}
    </a>
    </body>
    </html>
"""


def pay_link(request):

    payment_link = generate_paylink(id=2, amount=200)
    html_page = template.format(payment_link, payment_link)

    return HttpResponse(
        html_page.encode("utf-8"),
        content_type="text/html",
    )


class MerchantAPIView(MerchantAPIViewRaw):
    # check order
    # bu order aynan qachon to'g'ri bo'lishini aytish
    # nega inherit sabab: akkauntli shotga pul solish uchun bu yerni nastroyka qilsa ok
    # sotib olishga oddi django filter qo'ysa yetadi
    def check_order(self, merchant, order_id, amount):
        # akkaunt uchun
        # return Account.objects.filter(user_id=order_id)
        # yana boshqa maxsus filterlar qo'yish mumkin ya'ni aynan shu summani so'raganmi

        # buyurtma
        # return Order.objects.filter(merchant=merchant, id=order_id, amount=amount)
        return True

    def on_payment(self, merchant: PaymeMerchant, tx: PaymeTransaction) -> None:
        # pul tushganda yangilashlar, sms yo boshqa
        # django signalsdan tozaroq yechim

        # akkaunt uchun shunchangki balance += tx.amount
        # order = Order.objects.get(id=tx.order_id)
        # order.success = True
        # order.save()

        # myapi.send_sms(order.user_phone, f"Hi we got {tx.amount} from you")
        return super().on_payment(merchant, tx)

    def on_cancelled(self, merchant: PaymeMerchant, tx: PaymeTransaction) -> None:
        # bu sodda sistemaga kerakmas, lekin ayrim hollar uchun mavjud
        return super().on_cancelled(merchant, tx)

    def on_cancelled_after_perform(
        self, merchant: PaymeMerchant, tx: PaymeTransaction
    ) -> None:
        # pul tushgandan so'ng qaytarib olsa,
        # money back
        return super().on_cancelled_after_perform(merchant, tx)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("generate_url/", pay_link),
    path("payme_endpoint/", MerchantAPIView.as_view(), name="payme_merchant"),
]
