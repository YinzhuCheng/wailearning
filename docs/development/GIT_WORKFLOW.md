# Git Workflow

## Recommended Remote Layout

- `origin`: your working repository
- `upstream`: the upstream open-source source, if you track one
- optional mirror remotes if your team uses them

## Day-to-Day Flow

```bash
git checkout main
git pull --ff-only origin main
git checkout -b feature/<short-name>
```

After making changes:

```bash
git add <paths>
git commit -m "Describe the change"
git push -u origin feature/<short-name>
```

## Suggested Branch Strategy

- keep `main` or your release branch clean,
- develop features on short-lived branches,
- merge after tests and review,
- deploy from an explicit branch name instead of assuming the server is already on the right ref.

## Server-Side Deploy From Git

```bash
cd /opt/dd-class/source
sudo GIT_BRANCH=<branch> GIT_REMOTE=origin bash ops/scripts/redeploy.sh
```

This is safer than manually mixing `fetch`, `checkout`, and deploy commands on a live server.

## Updating From Upstream

If you track an upstream repository:

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

Resolve conflicts locally before deployment.

## Practical Rules

- Do not deploy from a dirty server worktree if you can avoid it.
- Do not assume a plain `git fetch` gave you the exact remote-tracking ref you want.
- Always verify the commit you deployed, not just the branch name.
- Pair git alignment with deployment checks.

## Related Docs

- [Deployment and Operations](DEPLOYMENT_AND_OPERATIONS.md)
