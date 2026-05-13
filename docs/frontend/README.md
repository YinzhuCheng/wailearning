# Frontend Documentation

This directory documents frontend-specific behavior and UI state contracts.

Use this directory for:

- admin or parent SPA interaction contracts;
- frontend HTTP client behavior;
- notification badge, course switcher, localStorage, and browser-state rules;
- UI behavior that is not primarily a product concept or backend API contract.

Do not put Playwright execution ledgers here; those belong in `docs/testing/`.
Do not put product domain guides here unless the behavior is only about frontend
presentation or browser state.

Primary entry points:

- [HTTP_CLIENT_SLOW_RESPONSE_BUSY_HINT.md](HTTP_CLIENT_SLOW_RESPONSE_BUSY_HINT.md)
- [NOTIFICATION_HEADER_AND_REALTIME_SYNC.md](NOTIFICATION_HEADER_AND_REALTIME_SYNC.md)
