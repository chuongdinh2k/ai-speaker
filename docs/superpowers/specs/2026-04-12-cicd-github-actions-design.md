# CI/CD GitHub Actions Design

**Date:** 2026-04-12  
**Status:** Approved

## Overview

A GitHub Actions workflow that automatically deploys the backend to an EC2 server whenever backend source files change and are merged to `main`. No Docker registry is used — the EC2 server builds images locally from source.

## Trigger Conditions

The workflow triggers on `push` to `main` only when files under `backend/` change:

```yaml
on:
  push:
    branches: [main]
    paths:
      - "backend/**"
```

Frontend-only or doc-only changes do not trigger a deploy.

## GitHub Secrets

Configure these in repo **Settings → Secrets and variables → Actions**:

| Secret name | Value |
|---|---|
| `EC2_HOST` | EC2 public IP or hostname |
| `EC2_USER` | `ec2-user` |
| `EC2_SSH_KEY` | PEM private key content for SSH access |

The EC2 security group must allow inbound SSH (port 22) from GitHub Actions runners.

## Workflow: `.github/workflows/deploy-backend.yml`

- Runs on `ubuntu-latest` (GitHub-hosted runner)
- Uses `appleboy/ssh-action` to SSH into EC2
- Executes on EC2:
  1. `cd /home/ec2-user/ai-speaker`
  2. `git pull origin main`
  3. `docker compose -f docker-compose.dev.yml up -d --build`

## `docker-compose.dev.yml`

Mirrors `docker-compose.yml` with one addition: `restart: unless-stopped` on all services so containers survive EC2 reboots.

Services:
- `postgres` — pgvector/pgvector:pg16, persistent volume
- `redis` — redis:7-alpine
- `api` — built from `./backend`, port 8000, reads `./backend/.env`
- `frontend` — built from `./frontend`, port 80

The `.env` file lives on the server only, never committed to git.

## Deployment Flow

```
Push to main (backend/** changed)
  → GitHub Actions triggers
    → SSH into EC2 (appleboy/ssh-action)
      → git pull origin main
        → docker compose -f docker-compose.dev.yml up -d --build
          → containers restart with new code
```

## Future Improvements

- Add a Docker registry (ECR or Docker Hub) to separate build from deploy
- Consider self-hosted GitHub runner on EC2 to eliminate SSH key management
- Add health check step after deploy to verify the API is responding
