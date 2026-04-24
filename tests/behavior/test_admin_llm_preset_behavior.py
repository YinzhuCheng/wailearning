"""
P1–P3: Admin LLM endpoint preset (optional API key, validation gate, bind to course).

Execution deferred — see tests/behavior/conftest.py.
"""


class AdminLlmPresetDialog:
    """Settings.vue preset dialog placeholder."""

    def create_preset_without_api_key(self, name: str) -> None:
        """Save preset with empty key (allowed)."""

    def click_validate_without_key(self) -> None:
        """Expect validation error guidance."""

    def fill_api_key_and_validate_with_image(self, image_path: str) -> None:
        """Upload test image → run validate → expect passed/failed per mock."""


def test_p1_create_preset_save_without_api_key() -> None:
    """P1: New preset without key appears in table; DB allows empty key string."""
    AdminLlmPresetDialog().create_preset_without_api_key("skeleton-preset")


def test_p2_validate_without_key_shows_error() -> None:
    """P2: Validate without key → user-visible error (no silent pass)."""
    AdminLlmPresetDialog().click_validate_without_key()


def test_p3_validate_then_teacher_binds_to_course() -> None:
    """P3: After validate, teacher course LLM can select preset in endpoints list."""
    dlg = AdminLlmPresetDialog()
    dlg.fill_api_key_and_validate_with_image("/tmp/tiny.png")
