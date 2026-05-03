# Admin Bootstrap and Demo Seed

## Bootstrap Admin Account

The backend can create an initial admin account during startup when `INIT_DEFAULT_DATA=true`.

Environment variables:

- `INIT_ADMIN_USERNAME`
- `INIT_ADMIN_PASSWORD`
- `INIT_ADMIN_REAL_NAME`

Defaults in code currently are:

- username: `admin`
- password: `ChangeMe123!`
- real name: `System Administrator`

These defaults are suitable only for local development. Production deployments must override them.

## Important Behavior

- The bootstrap logic creates the admin account only if that username does not already exist.
- Startup does not overwrite an existing admin password just because environment variables changed later.
- The bootstrap flow is part of application startup and uses the main backend settings.
- The admin bootstrap and the demo seed are both controlled during application startup, but they are not the same concern:
  the admin account uses `INIT_ADMIN_*` values, while the larger demo bundle is controlled by `INIT_DEFAULT_DATA`.
- In the current implementation, startup also runs schema repair, normalization, roster reconciliation, and optional demo seeding inside the FastAPI lifespan path. Treat bootstrap-related failures as startup-path issues, not only as authentication issues.

## Demo Seed Bundle

When `INIT_DEFAULT_DATA=true`, startup can also seed a demo teaching bundle.

That bundle includes:

- a demo teacher account,
- several demo student accounts,
- a demo class,
- required and elective courses,
- demo materials and homework,
- related roster synchronization behavior.

This is useful for local development and E2E testing, but should usually be disabled in production.

Current implementation context:

- `main.py` creates tables, runs schema-update helpers, normalizes teacher/class and semester links, backfills homework grading data, reconciles student users and roster rows, and only then applies optional demo seeding
- if `INIT_DEFAULT_DATA=true`, the demo seed is followed by another roster reconciliation before startup completes
- if `ENABLE_LLM_GRADING_WORKER=true` and `LLM_GRADING_WORKER_LEADER=true`, the in-process grading worker is started after startup initialization

## Recommended Production Values

```dotenv
INIT_DEFAULT_DATA=false
INIT_ADMIN_USERNAME=admin
INIT_ADMIN_PASSWORD=<strong-password>
INIT_ADMIN_REAL_NAME=System Administrator
```

## Password Reset Scripts

Useful repository scripts:

- `ops/scripts/reset_user_password.sh`
- `ops/scripts/set-password.sh`

Use these instead of keeping plaintext credentials in repository-side note files.

## Why The Old Plaintext Admin Note Was Removed

The repository should not rely on a stray text file containing credentials. The source of truth is the environment-backed bootstrap configuration plus the database state.

## Related Docs

- [Deployment and Operations](DEPLOYMENT_AND_OPERATIONS.md)
- [Development and Testing](../development/DEVELOPMENT_AND_TESTING.md)
