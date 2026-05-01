# Parent Portal

## Overview

The parent portal is a separate Vue 3 application under `parent-portal/`. In production it is served from `/parent/` and gives parent-code users read-only access to student information relevant to guardians.

## What Parents Can Do

- bind access through a parent code,
- view score summaries and detailed scores,
- read class and school notifications available to the student context,
- view homework lists and due dates,
- read high-level statistics for the linked student.

## Local Development

```bash
cd parent-portal
npm install
npm run dev
```

The dev server uses Vite and should proxy API requests to the backend.

## Current Shape

The portal is intentionally thinner than the admin frontend.

- It is read-oriented.
- It relies on parent-code verification rather than full JWT user login.
- It stores parent-side context in the browser after verification.

## Backend API Family

The portal is backed by `/api/parent`.

Typical endpoints include:

- verification,
- student info,
- scores,
- notifications,
- homework,
- summary statistics.

## Operational Notes

- Parent codes are generated and managed from the main system.
- The portal should be deployed together with the admin frontend during production rollouts.
- Because this is a separate SPA, a backend-only deploy does not update parent-facing static assets.

## Related Docs

- [System Overview](SYSTEM_OVERVIEW.md)
- [Deployment and Operations](DEPLOYMENT_AND_OPERATIONS.md)
