# Production Readiness Plan

This document outlines the necessary steps to transition the **RNG-THING** application from a development prototype to a production-ready system.

## 1. Security Enhancements

### Critical
- [ ] **Secret Management**: Move `secret_key` and other sensitive values from `config.json` to environment variables or a secrets manager (e.g., Vault, AWS Secrets Manager).
- [ ] **Database Credentials**: Ensure database passwords are strictly managed via environment variables.
- [x] **CORS Configuration**: The current configuration allows all origins (`allow_origins=["*"]`). In production, restrict this to the specific domain(s) of the frontend.
- [ ] **CSRF Protection**: Implement Cross-Site Request Forgery `(CSRF)` protection for all form submissions (Login, Support, Game Actions).
- [x] **Secure Cookies**: Ensure all cookies are set with `Secure`, `HttpOnly`, and `SameSite` flags.
- [ ] **Rate Limiting**: Review and tune `slowapi` limits to prevent abuse on auth and game endpoints.

### Recommended
- [x] **Security Headers**: Implement `HSTS`, `X-Frame-Options`, `X-Content-Type-Options`, and `Content-Security-Policy`.
- [ ] **Dependency Audit**: Run `pip-audit` to identify and update vulnerable dependencies.

## 2. Infrastructure & Deployment

### Containerization
- [ ] **Optimize Dockerfile**: The current multistage build is good, but ensure base images are pinned to specific SHA256 digests for immutability.
- [ ] **Non-Root User**: Verify `appuser` permissions in the `Dockerfile` effectively prevent root access.

### Server Configuration
- [ ] **Reverse Proxy**: Deploy behind Nginx, Traefik, or Caddy to handle SSL termination and serve static files efficiently.
- [ ] **Gunicorn Tuning**: Adjust worker count (`-w`) and threads based on available CPU cores.

### Monitoring
- [ ] **Structured Logging**: Replace standard logging with structured JSON logging (e.g., `structlog`) for better integration with log aggregators (ELK, Datadog).
- [ ] **Metrics**: Expose Prometheus metrics endpoint to track:
    - Active users
    - Game rounds played
    - Error rates
    - API latency

## 3. Database

### Migration
- [ ] **Switch to PostgreSQL/MySQL**: SQLite is not suitable for high-concurrency writing in production. Migrate to a client-server RDBMS.
- [ ] **Connection Pooling**: Implement a connection pool (e.g., via `SQLAlchemy` or `asyncpg`) to manage database connections efficiently.
- [ ] **Migration System**: Replace the custom `_migrate_schema` method with a standard tool like `Alembic` for reliable schema management.

### Data Integrity
- [ ] **Backups**: Implement automated daily/hourly backups.
- [ ] **Transactions**: thorough review of transaction isolation levels to prevent race conditions in balance updates.

## 4. Code Quality & Reliability

### Improvements
- [ ] **Async Database**: The current `sqlite3` driver is synchronous and blocks the asyncio loop. Move to `aiosqlite` or `asyncpg`.
- [ ] **Type Safety**: strict `mypy` check to resolve any remaining type hints.
- [ ] **Error Handling**: Standardize error responses across all API endpoints (remove inline HTML error pages in API routes).
- [ ] **Testing**: Create a comprehensive test suite (Unit + Integration) covering:
    - Auth flows
    - Game logic standard deviation (ensure fairness)
    - Economy transactions

## 5. Performance Optimization

- [ ] **Caching**: Implement Redis for session storage and frequent read-only data (e.g., Leaderboard).
- [ ] **Static Assets**: Offload `app/static` serving to Nginx/CDN.

## 6. Features & Housekeeping

- [ ] **Legal**: Ensure `privacy.html` and `tos.html` strictly adhere to the laws of the target jurisdiction.
- [ ] **User Communication**: Implement transactional emails (Password Reset, Welcome) using a provider like SendGrid/AWS SES.
