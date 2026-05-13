---
name: utf8-safe-editing
description: Use this before editing CourseEval multilingual, Chinese, Markdown, Vue, JSON, env, shell, or documentation files from Windows PowerShell, especially when output shows mojibake, suspicious glyphs, or encoding-sensitive text.
---

# UTF-8 Safe Editing

## Purpose

Prevent PowerShell display artifacts from becoming committed text corruption.
Treat terminal mojibake as untrusted until verified by UTF-8-aware tooling.

## Workflow

1. Read `docs/contributing/ENCODING_AND_MOJIBAKE_SAFETY.md`.
2. Inspect suspicious files with UTF-8-safe helpers instead of trusting the
   PowerShell console rendering.
3. Prefer `apply_patch` around stable ASCII anchors for manual edits.
4. After editing, run the changed-file encoding check.
5. If text still looks suspicious, verify by bytes, escaped output, or the
   repository helper scripts before making further edits.

## Commands

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ops\scripts\windows\safe-text-workflow.ps1 -Path <repo-relative-path>
python ops/scripts/dev/check_text_encoding.py --fail-on-suspicious <changed-file>
python ops/scripts/dev/run_validation_target.py static.encoding_text_tools --timeout-seconds 120
git diff --check
```

## Guardrails

- Do not run destructive grep-replace over Chinese or mixed-language text.
- Do not "fix" mojibake seen only in PowerShell until UTF-8 checks confirm the
  file bytes are wrong.
- Keep private local paths out of committed diagnostics.
- For docs/governance work, also run
  `python ops/scripts/dev/check_repository_normalization.py`.

## Related Files

- `docs/contributing/ENCODING_AND_MOJIBAKE_SAFETY.md`
- `ops/scripts/windows/safe-text-workflow.ps1`
- `ops/scripts/dev/check_text_encoding.py`
- `ops/scripts/dev/safe_show_text.py`
- `ops/scripts/dev/safe_write_text.py`
