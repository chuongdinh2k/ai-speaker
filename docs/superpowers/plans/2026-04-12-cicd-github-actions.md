# CI/CD GitHub Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a GitHub Actions workflow that deploys the backend to EC2 on every push to `main` that changes files under `backend/`.

**Architecture:** A GitHub-hosted runner SSHes into EC2 using `appleboy/ssh-action`, runs `git pull`, then rebuilds and restarts containers with `docker compose -f docker-compose.dev.yml up -d --build`. No image registry — the EC2 server builds images locally from source.

**Tech Stack:** GitHub Actions, appleboy/ssh-action@v1, Docker Compose, EC2 (Amazon Linux / ec2-user)

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Create | `.github/workflows/deploy-backend.yml` | CI/CD workflow definition |
| Create | `docker-compose.dev.yml` | Compose file for EC2 deployment with restart policies |

---

### Task 1: Create `docker-compose.dev.yml`

**Files:**
- Create: `docker-compose.dev.yml`

- [ ] **Step 1: Create the file**

Create `/Users/chuong/Documents/learning/AI-speaker/docker-compose.dev.yml` with this exact content:

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    environment:
      POSTGRES_USER: aispeaker
      POSTGRES_PASSWORD: aispeaker
      POSTGRES_DB: aispeaker
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"

  api:
    build: ./backend
    restart: unless-stopped
    depends_on:
      - postgres
      - redis
    env_file: ./backend/.env
    volumes:
      - audio_data:/app/audio
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    restart: unless-stopped
    depends_on:
      - api
    ports:
      - "80:80"

volumes:
  postgres_data:
  audio_data:
```

- [ ] **Step 2: Verify the file looks correct**

```bash
cat docker-compose.dev.yml
```

Expected: file printed with all 4 services and `restart: unless-stopped` on each.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.dev.yml
git commit -m "feat: add docker-compose.dev.yml with restart policies for EC2"
```

---

### Task 2: Create GitHub Actions workflow

**Files:**
- Create: `.github/workflows/deploy-backend.yml`

- [ ] **Step 1: Create the workflows directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create the workflow file**

Create `.github/workflows/deploy-backend.yml` with this exact content:

```yaml
name: Deploy Backend

on:
  push:
    branches:
      - main
    paths:
      - "backend/**"

jobs:
  deploy:
    name: Deploy to EC2
    runs-on: ubuntu-latest

    steps:
      - name: SSH into EC2 and deploy
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USER }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd /home/ec2-user/ai-speaker
            git pull origin main
            docker compose -f docker-compose.dev.yml up -d --build
```

- [ ] **Step 3: Verify the file looks correct**

```bash
cat .github/workflows/deploy-backend.yml
```

Expected: file printed with trigger on `main` + `backend/**` paths, one job, one step using `appleboy/ssh-action@v1.0.3`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/deploy-backend.yml
git commit -m "feat: add GitHub Actions workflow to deploy backend to EC2"
```

---

### Task 3: Configure GitHub Secrets

This task is done in the GitHub web UI — no code changes.

- [ ] **Step 1: Navigate to your repo secrets**

Go to: `https://github.com/<your-org>/<your-repo>/settings/secrets/actions`

- [ ] **Step 2: Add `EC2_HOST`**

Click **New repository secret**:
- Name: `EC2_HOST`
- Value: your EC2 public IP or hostname (e.g. `54.123.45.67`)

- [ ] **Step 3: Add `EC2_USER`**

Click **New repository secret**:
- Name: `EC2_USER`
- Value: `ec2-user`

- [ ] **Step 4: Add `EC2_SSH_KEY`**

Click **New repository secret**:
- Name: `EC2_SSH_KEY`
- Value: the full contents of your `.pem` private key file, including the `-----BEGIN RSA PRIVATE KEY-----` header and footer lines

To copy your key contents:
```bash
cat ~/.ssh/your-key.pem
```

---

### Task 4: Verify EC2 server is ready

This task runs on the EC2 server — SSH in manually first.

- [ ] **Step 1: SSH into your EC2 server**

```bash
ssh -i ~/.ssh/your-key.pem ec2-user@<EC2_HOST>
```

- [ ] **Step 2: Confirm the repo is cloned at the right path**

```bash
ls /home/ec2-user/ai-speaker
```

Expected: project files visible (`backend/`, `frontend/`, `docker-compose.dev.yml` after push, etc.)

If not cloned yet:
```bash
git clone <your-repo-url> /home/ec2-user/ai-speaker
```

- [ ] **Step 3: Confirm Docker and Docker Compose are installed**

```bash
docker --version
docker compose version
```

Expected: both commands return version strings (Docker 20+, Compose v2+).

If Docker is not installed (Amazon Linux 2):
```bash
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -aG docker ec2-user
# log out and back in for group to take effect
```

If Docker Compose v2 plugin is not installed:
```bash
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
```

- [ ] **Step 4: Confirm `.env` file exists in the backend directory**

```bash
ls /home/ec2-user/ai-speaker/backend/.env
```

Expected: file exists. If not, create it with the required environment variables before deploying.

- [ ] **Step 5: Confirm EC2 security group allows SSH from GitHub Actions**

In AWS Console → EC2 → Security Groups → your instance's group → Inbound rules:

Ensure there is a rule:
- Type: SSH
- Port: 22
- Source: `0.0.0.0/0` (or GitHub's IP ranges for stricter security)

---

### Task 5: Push and verify the workflow runs

- [ ] **Step 1: Push the branch to trigger the workflow**

Make a small change to any file under `backend/` (e.g. add a comment to `backend/app/main.py`), commit, and push to `main`:

```bash
git push origin main
```

- [ ] **Step 2: Watch the workflow run**

Go to: `https://github.com/<your-org>/<your-repo>/actions`

Expected: workflow named "Deploy Backend" appears and runs. Click into it to see the SSH step output.

- [ ] **Step 3: Verify containers are running on EC2**

SSH into EC2:
```bash
ssh -i ~/.ssh/your-key.pem ec2-user@<EC2_HOST>
docker ps
```

Expected: `postgres`, `redis`, `api`, and `frontend` containers all show status `Up`.

- [ ] **Step 4: Verify the API is responding**

```bash
curl http://localhost:8000/health
# or any valid endpoint in your backend
```

Expected: HTTP 200 response.

- [ ] **Step 5: Verify path filter works (frontend change should NOT trigger)**

Make a change to a frontend file, commit, and push to `main`:
```bash
echo "# test" >> frontend/README.md
git add frontend/README.md
git commit -m "test: verify path filter"
git push origin main
```

Go to GitHub Actions. Expected: no new "Deploy Backend" workflow run triggered.
