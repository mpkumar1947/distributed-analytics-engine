# Distributed Analytics Engine (Gradiator)

A high-throughput, async-first backend service powering the Gradiator academic intelligence platform. Built to ingest, process, and serve complex academic historical data and grading distributions for 3,000+ Monthly Active Users under heavy concurrent load.

━━━━━━━━━━━━

### ◉ Architecture & Infrastructure

Designed as a stateless, event-driven microservice optimized for fast webhook execution and zero-downtime deployments.

▸ **Core Framework:** FastAPI (Python 3.10+) running in ASGI asynchronous webhook mode.
▸ **Database:** Neon Serverless PostgreSQL. Connected via `asyncpg` utilizing transaction-level connection pooling.
▸ **In-Memory Store:** Upstash Redis (TLS enabled) for strict rate-limiting, session state, and global maintenance toggles.
▸ **Admin Tooling:** Cloudflare Workers acting as a secure edge proxy for a React-based administrative dashboard.
▸ **Deployment:** Fully containerized, CI/CD pipeline integrated directly with Render.

### ◉ Key Technical Capabilities

▸ **Asynchronous Telemetry:** Custom `asyncio` broadcast queue handling mass messaging to thousands of active Telegram users without blocking the main event loop or requiring heavy message brokers like Celery.
▸ **Algorithmic Grading Analysis:** Generates dynamic instructor dossiers and flags grading anomalies by calculating historical standard deviations, mean grade distributions, and outlier metrics in real-time.
▸ **Resilient Event Handling:** Gracefully handles transient database connection failures, network timeouts, and Telegram API limits through exponential backoff and Upstash-backed circuit breakers.
▸ **Zero-Config Maintenance:** Implements a strict, Redis-backed maintenance interceptor at the FastAPI middleware layer, allowing instant traffic halting without requiring database compute or redeployments.

━━━━━━━━━━━━

### ◉ Local Deployment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mpkumar1947/distributed-analytics-engine.git
   cd distributed-analytics-engine
   ```

2. **Environment Configuration:**
   Provide the following secrets via `.env`:
   ```env
   DATABASE_URL="postgresql+asyncpg://user:password@endpoint.aws.neon.tech/dbname?sslmode=require"
   REDIS_URL="rediss://default:TOKEN@endpoint.upstash.io:6379"
   TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
   TELEGRAM_ADMIN_IDS="id1,id2"
   WEBHOOK_URL_PATH_PREFIX="/webhook"
   BOT_STARTUP_MAINTENANCE_MODE="false"
   ```

3. **Database Migrations:**
   Ensure the local schema matches production state via Alembic:
   ```bash
   alembic upgrade head
   ```

4. **Bootstrapping the API:**
   Launch the FastAPI application using Uvicorn (local polling mode available for development):
   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### ◉ Branching Strategy

▸ `main` — Production. Powers the Telegram bot and admin dashboard, strictly monitored and auto-deployed to Render.
▸ `core-api-refactor` — Headless API variant. Strips away the bot and UI components, serving as an isolated grading metrics microservice for external campus projects.

<br>
<p align="center">
  <i>built different. — gradiator</i>
</p>