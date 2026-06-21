"""Click.uz error codes."""


class ClickException(Exception):
    code: int = -8
    note: str = "Error"

    def __init__(self, note: str = ""):
        self.note = note or self.__class__.note

    def to_response(self, click_trans_id=None, merchant_trans_id=None) -> dict:
        return {
            "click_trans_id":    click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "error":             self.code,
            "error_note":        self.note,
        }


class InvalidSign(ClickException):
    code = -1;  note = "Invalid sign"

class OrderNotFound(ClickException):
    code = -5;  note = "Order not found"

class AlreadyPaid(ClickException):
    code = -4;  note = "Already paid"

class WrongAmount(ClickException):
    code = -2;  note = "Incorrect amount"

class TransactionCancelled(ClickException):
    code = -9;  note = "Transaction cancelled"

class BadRequest(ClickException):
    code = -8;  note = "Bad request"
