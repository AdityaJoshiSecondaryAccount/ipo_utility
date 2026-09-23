11-09-2026 -> startes

19-09-2026 -> 1. Trades page Started
22-09-2026 -> Trades page ended
## WhatsApp Cloud API

Set these environment variables before starting the application:

- `WHATSAPP_API_VERSION` (defaults to `v21.0`)
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_ACCESS_TOKEN` (`WHATSAPP_API_KEY` is also accepted for compatibility)

The approved Meta template must be named `ipo_order_confirmation` and use the
named body parameters defined in `whatsapp/client.py`.
