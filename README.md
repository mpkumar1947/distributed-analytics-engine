# 📊 Distributed Analytics Engine (Gradiator)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Production_Ready-2496ED.svg?logo=docker&logoColor=white)

> **🚀 Production Status:** Currently powering the Gradiator ecosystem for **2,000+ active students** at IIT Kanpur. Integrated live via Telegram at [@gradiator_iitk_bot](https://www.t.me/gradiator_iitk_bot).

## 💡 Overview

The **Distributed Analytics Engine** is the high-performance backend microservice driving the Gradiator academic platform. Built to handle heavy concurrent traffic during peak university registration periods, it ingests, processes, and serves complex academic data, grading trends, and instructor metrics in real-time.

It acts as the central data nervous system, seamlessly communicating with both a React-based web frontend and a native Telegram Mini-App authentication system.

## 🏗️ Architecture & Tech Stack

This service is designed as an independent, fully containerized API, optimized for sub-millisecond response times.

* **Core API:** FastAPI (Python) for asynchronous, high-throughput REST endpoints.
* **Database:** Managed Cloud PostgreSQL (Flexible Server) for robust, relational data storage.
* **Caching & Queues:** Redis (via Docker) to cache intensive analytical queries and handle rate-limiting.
* **Migrations:** SQLAlchemy + Alembic for version-controlled database schema management.
* **Infrastructure:** Docker & Docker Compose, running behind an Nginx reverse proxy with dynamic cross-network Docker DNS resolution.

## ✨ Key Features

* **Live Telegram Integration:** Powers a custom, cryptographically secure (HMAC-SHA256) WhatsApp-Web style QR login flow using Telegram Mini Apps.
* **Complex Data Aggregation:** Calculates real-time grade distributions (A, B, C ratios) across thousands of historical academic records.
* **Algorithmic Profiling:** Generates dynamic "Instructor Dossiers" and automatically flags course offerings (e.g., "Excellent", "Course Massacre") based on standard deviation and mean grade analysis.
* **Microservice Isolation:** Operates on its own isolated Docker network (`distributed-analytics-engine_app_network`), safely proxying requests from external frontends.

## 🔀 Branching Strategy

We maintain a clean, two-branch workflow to ensure production stability:

* `main`: **Production environment.** Stable, battle-tested code actively deployed on the live VPS and serving the student body.
* `development` / `data-pipeline`: Active workspace for testing new data ingestion scripts, experimenting with caching strategies, and drafting new API endpoints.

## 💻 Local Setup & Deployment

### Prerequisites

* Docker & Docker Compose installed.
* Access to the external PostgreSQL Flexible Server URI.

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/distributed-analytics-engine.git
   cd distributed-analytics-engine
   ```

2. **Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   DATABASE_URL=postgresql://user:password@your-cloud-db-host.com:5432/dbname
   REDIS_URL=redis://redis_broker:6379/0
   # Add Telegram Bot Tokens / Auth secrets here
   ```

3. **Deploy the Engine:**
   Spin up the FastAPI server and Redis broker in detached mode:
   ```bash
   docker compose up -d --build
   ```

4. **Run Database Migrations:**
   Ensure your local schema matches production:
   ```bash
   docker compose exec api alembic upgrade head
   ```

Once running, the interactive Swagger UI API documentation is immediately available at: `http://localhost:8000/docs`

---

*Built to bring data-driven scheduling to the student community. Code with ❤️ and lots of coffee.*