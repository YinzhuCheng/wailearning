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

## Recommended Production Values

```dotenv
INIT_DEFAULT_DATA=false
INIT_ADMIN_USERNAME=admin
INIT_ADMIN_PASSWORD=<strong-password>
INIT_ADMIN_REAL_NAME=System Administrator
```

## Password Reset Scripts

Useful repository scripts:

- `scripts/reset_user_password.sh`
- `scripts/set-password.sh`

Use these instead of keeping plaintext credentials in repository-side note files.

## Why The Old Plaintext Admin Note Was Removed

The repository should not rely on a stray text file containing credentials. The source of truth is the environment-backed bootstrap configuration plus the database state.

## Related Docs

- [Deployment and Operations](DEPLOYMENT_AND_OPERATIONS.md)
- [Development and Testing](DEVELOPMENT_AND_TESTING.md)
