# Behavior / E2E skeleton tests

These tests live under `tests/behavior/` and are **skipped by default** via
`pytest_collection_modifyitems` in `conftest.py` so normal CI runs stay fast.

**Next round:** remove or narrow the skip hook, add Playwright (or similar) +
shared seed helpers, then fill the page objects and assertions.

Run only this package (still skipped until hook removed):

```bash
pytest tests/behavior -v
```
