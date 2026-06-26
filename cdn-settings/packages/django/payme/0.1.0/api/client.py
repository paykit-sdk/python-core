import logging

import requests

from paykit.providers.payme.config import request_link
from paykit.providers.payme.models import PaymeMerchant

logger = logging.getLogger(__name__)


class PaymeSubscribeClient:
    """
    Thin HTTP wrapper around Payme Subscribe API.
    Each method authenticates with the merchant's own Basic credentials.
    """

    def _rpc(self, merchant: PaymeMerchant, method: str, params: dict) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        try:
            response = requests.post(
                request_link + "/api",
                json=payload,
                headers={
                    "X-Auth": merchant.merchant_key,
                    "Authorization": f"Basic {merchant.base64_key}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            response.raise_for_status()
        except requests.Timeout:
            raise RuntimeError(f"Payme request timed out: {method}")
        except requests.RequestException as exc:
            raise RuntimeError(f"Payme network error [{method}]: {exc}") from exc

        data = response.json()

        if "error" in data:
            err = data["error"]
            raise PaymeAPIError(
                code=err.get("code"),
                message=err.get("message"),
                data=err.get("data"),
            )

        return data.get("result", {})

    # ── cards ─────────────────────────────────────────────────────────────────

    def cards_create(
        self,
        merchant: PaymeMerchant,
        card_number: str,
        card_expire: str,
        save: bool = True,
    ) -> dict:
        return self._rpc(
            merchant,
            "cards.create",
            {
                "card": {"number": card_number, "expire": card_expire},
                "save": save,
            },
        )

    def cards_get_verify_code(self, merchant: PaymeMerchant, token: str) -> dict:
        return self._rpc(merchant, "cards.get_verify_code", {"token": token})

    def cards_verify(self, merchant: PaymeMerchant, token: str, code: str) -> dict:
        return self._rpc(merchant, "cards.verify", {"token": token, "code": code})

    def cards_check(self, merchant: PaymeMerchant, token: str) -> dict:
        return self._rpc(merchant, "cards.check", {"token": token})

    def cards_remove(self, merchant: PaymeMerchant, token: str) -> dict:
        return self._rpc(merchant, "cards.remove", {"token": token})

    # ── receipts ──────────────────────────────────────────────────────────────

    def receipts_create(
        self,
        merchant: PaymeMerchant,
        amount: int,
        account: dict,
        description: str = "",
    ) -> dict:
        return self._rpc(
            merchant,
            "receipts.create",
            {
                "amount": amount,
                "account": account,
                "description": description,
            },
        )

    def receipts_pay(
        self,
        merchant: PaymeMerchant,
        receipt_id: str,
        token: str,
        payer: dict = None,
    ) -> dict:
        params = {"id": receipt_id, "token": token}
        if payer:
            params["payer"] = payer
        return self._rpc(merchant, "receipts.pay", params)

    def receipts_send(
        self, merchant: PaymeMerchant, receipt_id: str, phone: str
    ) -> dict:
        return self._rpc(merchant, "receipts.send", {"id": receipt_id, "phone": phone})

    def receipts_cancel(self, merchant: PaymeMerchant, receipt_id: str) -> dict:
        return self._rpc(merchant, "receipts.cancel", {"id": receipt_id})

    def receipts_check(self, merchant: PaymeMerchant, receipt_id: str) -> dict:
        return self._rpc(merchant, "receipts.check", {"id": receipt_id})

    def receipts_get(self, merchant: PaymeMerchant, receipt_id: str) -> dict:
        return self._rpc(merchant, "receipts.get", {"id": receipt_id})

    def receipts_get_all(
        self,
        merchant: PaymeMerchant,
        count: int = 50,
        from_time: int = None,
        to_time: int = None,
        offset: int = 0,
    ) -> dict:
        params: dict = {"count": count, "offset": offset}
        if from_time is not None:
            params["_from"] = from_time
        if to_time is not None:
            params["_to"] = to_time
        return self._rpc(merchant, "receipts.get_all", params)


class PaymeAPIError(Exception):
    """Raised when Payme returns a JSON-RPC error."""

    def __init__(self, code: int, message, data=None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"Payme error {code}: {message} (data={data})")
