# PayKit

Payment provider integration toolkit for Django and other web frameworks.

## Installation

```bash
pip install paykit-sdk
```

## Quick Start

Initialize PayKit in your project directory. If `paykit.json` already exists, it will sync automatically.

```bash
paykit init
```

## CLI Reference

### Set Framework

PayKit auto-detects your framework. Only run this if detection fails or you want to override it.

```bash
paykit set django
paykit set flask
```

### Add a Provider

```bash
paykit add payme              # latest version
paykit add payme@latest       # explicitly latest
paykit add payme@1            # major version
paykit add payme@1.0.0        # exact version
```

### Re-sync Config

After editing `paykit.json`, re-run init to apply changes:

```bash
paykit init
```

## Configuration

`paykit.json` is auto-generated on `paykit init`. Edit it as needed, then re-run `paykit init`.

```json
{
  "framework": "django",
  "providers": {
    "payme": "latest"
  },
  "defaults": {
    "payme": {
      "language": "uz",
      "request_link": "https://test.paycom.uz",
      "callback_link": "https://your-domain.com/payme_endpoint/"
    }
  }
}
```

| Field | Description | Options |
|---|---|---|
| `language` | Payment page language shown to user | `uz`, `ru`, `en` |
| `request_link` | Payme checkout URL | Use test URL during development, production URL when live |
| `callback_link` | Redirect URL after payment completes | Must be a publicly accessible URL |

## Supported

| Category | Supported |
|---|---|
| Languages | Python |
| Frameworks | Django |
| Providers | Payme |

---

For Django-specific integration (views, webhook handlers, payment link generation), see [Usage](/paykit/usage).


# Inpired from [Paytechuz](https://paytechuz/paytechuz)

Support [Muhammadali - Support group](https://t.me/paytechuz)
