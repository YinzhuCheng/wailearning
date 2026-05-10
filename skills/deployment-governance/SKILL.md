---
name: deployment-governance
description: Use this when changing CourseEval deployment scripts, setup scripts, nginx/systemd templates, .env.production, production bootstrap docs, Git deploy wrappers, post-deploy checks, or operator-facing upgrade guidance.
---

# Deployment Governance

## Purpose

Keep operator scripts, environment templates, service definitions, and
operations documentation aligned with the deployable implementation.

## Workflow

1. Read `docs/operations/DEPLOYMENT_AND_OPERATIONS.md`,
   `docs/operations/ADMIN_BOOTSTRAP.md`, and
   `docs/architecture/CONFIGURATION_REFERENCE.md`.
2. Compare script behavior with documented commands before trusting prose.
3. Keep `.env.production`, config docs, bootstrap behavior, and deployment
   scripts in the same change set when their contracts move.
4. Prefer scriptable guardrails over prose-only warnings when a deploy rule can
   be checked statically.
5. Run operator-script and repository-normalization checks before handoff.
6. Document environment blockers honestly; Windows cannot prove Linux Bash
   runtime behavior by itself.

## Commands

```powershell
python ops/scripts/dev/check_operator_scripts.py
python ops/scripts/dev/run_validation_target.py static.operator_scripts_governance --timeout-seconds 120
python ops/scripts/dev/check_repository_normalization.py
python ops/scripts/dev/select_validation_targets.py --worktree
git diff --check
```

## Guardrails

- Do not restore old service names, old domains, or retired package paths as
  current deployment truth.
- Frontend deploy scripts must not restart `courseeval-backend.service`.
- Public health checks in `post_deploy_check.sh` must remain opt-in unless docs
  and scripts are changed together.
- `init_db.sql` must fail fast when required `psql -v` variables are missing.
- Treat `bash -n` as blocked on Windows when Bash resolves to the WSL installer;
  validate shell runtime on Linux/CI/deployment hosts.

## Related Files

- `.env.production`
- `ops/scripts/`
- `ops/nginx/`
- `ops/systemd/courseeval-backend.service`
- `docs/operations/DEPLOYMENT_AND_OPERATIONS.md`
- `docs/development/GIT_WORKFLOW.md`
