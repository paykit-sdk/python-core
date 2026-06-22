class PaymeError:
    PARSE_ERROR = {
        "code": -32700,
        "message": {"ru": "Ошибка разбора", "uz": "Parse xatosi", "en": "Parse error"},
    }
    METHOD_NOT_FOUND = {
        "code": -32601,
        "message": {
            "ru": "Метод не найден",
            "uz": "Metod topilmadi",
            "en": "Method not found",
        },
    }
    INTERNAL_ERROR = {
        "code": -32603,
        "message": {
            "ru": "Внутренняя ошибка",
            "uz": "Ichki xato",
            "en": "Internal error",
        },
    }
    INSUFFICIENT_PRIVILEGE = {
        "code": -32504,
        "message": {
            "ru": "Недостаточно прав",
            "uz": "Ruxsat yo'q",
            "en": "Insufficient privilege",
        },
    }
    INVALID_AMOUNT = {
        "code": -31001,
        "message": {
            "ru": "Неверная сумма",
            "uz": "Noto'g'ri miqdor",
            "en": "Invalid amount",
        },
    }
    TRANSACTION_NOT_FOUND = {
        "code": -31003,
        "message": {
            "ru": "Транзакция не найдена",
            "uz": "Tranzaksiya topilmadi",
            "en": "Transaction not found",
        },
    }
    TRANSACTION_CANNOT_PERFORM = {
        "code": -31008,
        "message": {
            "ru": "Невозможно выполнить операцию",
            "uz": "Amalni bajarib bo'lmaydi",
            "en": "Cannot perform operation",
        },
    }
    ORDER_NOT_FOUND = {
        "code": -31050,
        "message": {
            "ru": "Заказ не найден",
            "uz": "Buyurtma topilmadi",
            "en": "Order not found",
        },
    }
    ORDER_ALREADY_PAID = {
        "code": -31051,
        "message": {
            "ru": "Заказ уже оплачен",
            "uz": "Buyurtma allaqachon to'langan",
            "en": "Order already paid",
        },
    }
    UNABLE_TO_CANCEL = {
        "code": -31007,
        "message": {
            "ru": "Невозможно отменить",
            "uz": "Bekor qilib bo'lmaydi",
            "en": "Unable to cancel",
        },
    }
    INVALID_ACCOUNT = {
        "code": -31050,
        "message": {
            "ru": "Неверный аккаунт",
            "uz": "Noto'g'ri hisob",
            "en": "Invalid account",
        },
    }


def error_response(request_id, error):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": error,
    }


def success_response(request_id, result):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }
