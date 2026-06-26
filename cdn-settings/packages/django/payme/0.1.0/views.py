import json

from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from paykit.providers.payme.api.merchant import PaymeMerchantAPI


class MerchantAPIViewRaw(PaymeMerchantAPI):
    @classmethod
    def as_view(cls):
        @csrf_exempt
        def view(request):
            api = cls()
            response, status = api.dispatch(
                json.loads(request.body), request.headers.get("Authorization", "")
            )
            return JsonResponse(response, status=status)

        return view
