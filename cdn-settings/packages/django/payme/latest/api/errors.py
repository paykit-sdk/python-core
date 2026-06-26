class PaymeError:
    TRANSPORT_ERROR = {
        "code": -32300,
        "message": {
            "ru": "Ошибка транспорта",
            "uz": "Transport xatosi",
            "en": "Transport error",
        },
    }
    PARSE_ERROR = {
        "code": -32700,
        "message": {"ru": "Ошибка разбора", "uz": "Parse xatosi", "en": "Parse error"},
    }
    INVALID_REQUEST = {
        "code": -32600,
        "message": {
            "ru": "Неверный запрос",
            "uz": "Noto'g'ri so'rov",
            "en": "Invalid request",
        },
    }
    METHOD_NOT_FOUND = {
        "code": -32601,
        "message": {
            "ru": "Метод не найден",
            "uz": "Metod topilmadi",
            "en": "Method not found",
        },
    }
    INVALID_PARAMS = {
        "code": -32602,
        "message": {
            "ru": "Неверные параметры",
            "uz": "Noto'g'ri parametrlar",
            "en": "Invalid params",
        },
    }
    INVALID_TOKEN_FORMAT = {
        "code": -32500,
        "message": {
            "ru": "Неверный формат токена",
            "uz": "Token formati noto'g'ri",
            "en": "Invalid token format",
        },
    }
    ACCESS_DENIED = {
        "code": -32504,
        "message": {
            "ru": "Доступ запрещён",
            "uz": "Ruxsat yo'q",
            "en": "Access denied",
        },
    }
    SYSTEM_ERROR = {
        "code": -32400,
        "message": {
            "ru": "Внутренняя ошибка сервиса",
            "uz": "Tizimda xatolik yuzaga keldi",
            "en": "Internal service error",
        },
    }

    class MerchantError:
        PROCESSING_SERVER_ERROR = {
            "code": -31002,
            "message": {
                "ru": "Сервер процессинга недоступен",
                "uz": "Protsessing serveri mavjud emas",
                "en": "Processing server unavailable",
            },
        }
        INCORRECT_AMOUNT = {
            "code": -31001,
            "message": {
                "ru": "Неверная сумма",
                "uz": "Noto'g'ri summa",
                "en": "Incorrect amount",
            },
        }
        ACCOUNT_NOT_FOUND = {
            "code": -31050,
            "message": {
                "ru": "Счёт не найден",
                "uz": "Hisob topilmadi",
                "en": "Account not found",
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
        TRANSACTION_ALREADY_EXISTS = {
            "code": -31099,
            "message": {
                "ru": "Транзакция уже существует",
                "uz": "Tranzaksiya allaqachon mavjud",
                "en": "Transaction already exists",
            },
        }
        CANNOT_CANCEL_TRANSACTION = {
            "code": -31007,
            "message": {
                "ru": "Невозможно отменить транзакцию",
                "uz": "Tranzaksiyani bekor qilib bo'lmaydi",
                "en": "Cannot cancel transaction",
            },
        }
        CANNOT_PERFORM_OPERATION = {
            "code": -31008,
            "message": {
                "ru": "Невозможно выполнить операцию",
                "uz": "Amalni bajarib bo'lmaydi",
                "en": "Cannot perform operation",
            },
        }
        INVALID_FISCAL_PARAMS = {
            "code": -32602,
            "message": {
                "ru": "Неверные фискальные параметры",
                "uz": "Fiskal parametrlarda xatolik",
                "en": "Invalid fiscal parameters",
            },
        }
        RECEIPTS_NOT_FOUND = {
            "code": -31602,
            "message": {
                "ru": "Чеки не найдены",
                "uz": "Cheklar topilmadi",
                "en": "Receipts not found",
            },
        }
        UNKNOWN_PARTNER = {
            "code": -31601,
            "message": {
                "ru": "Неизвестный партнёр",
                "uz": "Noma'lum hamkor",
                "en": "Unknown partner",
            },
        }

    class SubscribeError:
        CARD_NOT_FOUND = {
            "code": -31400,
            "message": {
                "ru": "Карта не найдена",
                "uz": "Karta topilmadi",
                "en": "Card not found",
            },
        }
        INVALID_CARD_NUMBER = {
            "code": -31300,
            "message": {
                "ru": "Неверный номер карты",
                "uz": "Karta raqami noto'g'ri",
                "en": "Invalid card number",
            },
        }
        INVALID_EXPIRY_DATE = {
            "code": -31300,
            "message": {
                "ru": "Неверная дата истечения",
                "uz": "Amal qilish muddati noto'g'ri",
                "en": "Invalid expiry date",
            },
        }
        CORPORATE_CARD_NOT_ALLOWED = {
            "code": -31300,
            "message": {
                "ru": "Операции с корпоративными картами запрещены",
                "uz": "Korporativ kartalar bilan operatsiya taqiqlangan",
                "en": "Corporate card operations not allowed",
            },
        }
        SMS_NOT_CONNECTED = {
            "code": -31301,
            "message": {
                "ru": "SMS-уведомления не подключены",
                "uz": "SMS xabarnoma ulanmagan",
                "en": "SMS notification not connected",
            },
        }
        CARD_EXPIRED = {
            "code": -31301,
            "message": {
                "ru": "Срок действия карты истёк",
                "uz": "Kartaning amal qilish muddati tugagan",
                "en": "Card has expired",
            },
        }
        CARD_BLOCKED = {
            "code": -31301,
            "message": {
                "ru": "Карта заблокирована",
                "uz": "Karta bloklangan",
                "en": "Card is blocked",
            },
        }
        BALANCE_ERROR = {
            "code": -31302,
            "message": {
                "ru": "Не удалось получить баланс",
                "uz": "Balansni olishda xatolik",
                "en": "Unable to retrieve balance",
            },
        }
        INSUFFICIENT_FUNDS = {
            "code": -31303,
            "message": {
                "ru": "Недостаточно средств",
                "uz": "Mablag' yetarli emas",
                "en": "Insufficient funds",
            },
        }
        INSUFFICIENT_FUNDS_V2 = {
            "code": -31630,
            "message": {
                "ru": "Недостаточно средств",
                "uz": "Mablag' yetarli emas",
                "en": "Insufficient funds",
            },
        }

        class OtpError:
            OTP_SEND_ERROR = {
                "code": -31110,
                "message": {
                    "ru": "Ошибка отправки SMS",
                    "uz": "SMS yuborishda xatolik",
                    "en": "OTP send error",
                },
            }
            OTP_EXPIRED = {
                "code": -31101,
                "message": {
                    "ru": "Код OTP истёк",
                    "uz": "OTP kodi muddati o'tgan",
                    "en": "OTP code expired",
                },
            }
            OTP_ATTEMPTS_EXCEEDED = {
                "code": -31102,
                "message": {
                    "ru": "Превышено количество попыток",
                    "uz": "Urinishlar soni oshib ketdi",
                    "en": "OTP attempts exceeded",
                },
            }
            OTP_INVALID_CODE = {
                "code": -31103,
                "message": {
                    "ru": "Неверный код OTP",
                    "uz": "OTP kodi noto'g'ri",
                    "en": "Invalid OTP code",
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
