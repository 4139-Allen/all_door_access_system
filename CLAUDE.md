# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-platform door access management system: FastAPI backend shared by Web (Vue 3), WeChat Mini Program, and future uni-app mobile app. Features JWT auth, device management, access logs, WebSocket real-time updates, and AI-powered natural language door control (DeepSeek integration).

## Project Structure

```
all_door_access_system/
├── backend/        # Python FastAPI backend (shared by all platforms)
├── web/            # Vue 3 + Element Plus web admin dashboard
├── app/            # uni-app cross-platform mobile app (iOS/Android)
├── miniprogram/    # WeChat Mini Program (native)
├── stm32/          # STM32F103 firmware + ESP8266 WiFi module
├── deploy/         # Docker deployment configs (docker-compose, .env, SSL, etc.)
│   ├── docker-compose.yml
│   ├── .env
│   ├── mosquitto.conf
│   └── deploy.sh / deploy.bat
├── SSL/            # SSL certificates for doorlink.top
├── CLAUDE.md
└── README.md
```

## Architecture

### Backend (`backend/`)

Three-layer backend architecture:

```
api/        (FastAPI routers) -> services/     (business logic) -> database/models/  (SQLAlchemy)
utils/      (auth, response, exceptions, logger, rate_limiter)
schemas/    (Pydantic validation)
core/       (config, AI system prompt)
```

- **API layer** (`backend/api/*.py`): FastAPI routers, receives requests, calls service layer, returns unified `{code, msg, data}` responses via `utils/response_schema.py`
- **Service layer** (`backend/services/*.py`): Business logic, throws exceptions (ValueError, PermissionError) that `@handle_api_exception` catches
- **Data layer** (`backend/database/models/*.py`): SQLAlchemy ORM models (User, Device, UserDevice, DoorLog)
- **Auth** (`backend/utils/auth.py`): JWT tokens with Redis-backed token validation + blacklist mechanism
- **Dependency injection**: FastAPI `Depends()` for DB sessions (`get_db`), current user (`get_current_user_obj`), and admin validation (`require_admin`)
- **Web Frontend** (`web/`): Vue 3 + Element Plus, Vite build tool, routes protected by navigation guard checking `localStorage.token`
- **Mini Program** (`miniprogram/`): WeChat native mini program with wx.login() + JWT auth via X-Token header
- **Mobile App** (`app/`): uni-app + Vue 3 Composition API, cross-platform (iOS/Android/H5), uses X-Token auth

## Key Conventions

- All API responses follow `{"code": int, "msg": str, "data": any}` format using `success()` and `error()` from `utils/response.py`
- API route handlers use `@handle_api_exception` decorator for automatic error-to-response conversion
- DB sessions are injected via `db: Session = Depends(get_db)`
- Admin-only endpoints use `current_user: User = Depends(require_admin)`
- Redis caching with `setex()` for device lists (60s), stats (180s), AI context (900s)
- Config from env vars via `core/config.py` loaded from `.env`

## Development Commands

```bash
# Backend - install dependencies
cd backend && pip install -r requirements.txt

# Backend - run dev server (hot reload enabled)
cd backend && python main.py

# Backend - run on custom host/port
cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Web Frontend - install dependencies
cd web && npm install

# Web Frontend - dev server (default http://localhost:5173)
cd web && npm run dev

# Web Frontend - production build (required before Docker)
cd web && npm run build

# Mobile App - install dependencies
cd app && npm install

# Mobile App - dev server (H5 mode, default http://localhost:5174)
cd app && npm run dev:h5

# Mobile App - build for production
cd app && npm run build:h5

# Docker - full deployment (from deploy/ directory)
cd deploy && docker compose up -d

# Docker - rebuild single service after code changes
cd deploy && docker compose up -d --build fastapi
cd deploy && docker compose up -d --build frontend

# Docker - view logs
cd deploy && docker compose logs -f fastapi

# Database Migration (Alembic) - manage database schema changes
cd backend

# Check current database version
python manage_db.py current

# View migration history
python manage_db.py history

# Create new migration after model changes
python manage_db.py create -m "add_user_phone_field"

# Upgrade database to latest version
python manage_db.py upgrade

# Rollback one version
python manage_db.py downgrade -1
```

## Important Notes

- Docker `.env` in `deploy/` must use service names (`MYSQL_HOST=mysql`, `REDIS_HOST=redis`), not `localhost`
- Web frontend must be built (`cd web && npm run build`) before Docker deployment
- Admin account auto-created on first start (configurable via `ADMIN_USERNAME`/`ADMIN_PASSWORD` in `deploy/.env`)
- AI features are optional; missing `DEEPSEEK_API_KEY` logs a warning but doesn't block startup
- Cache invalidation: device list cache keyed by `cache:device:list:user:{user_id}`, invalidate on device CRUD
- Logs go to `backend/logs/app.log.YYYY-MM-DD` with 30-day rotation
- Structured logging: Set `LOG_FORMAT=json` in `.env` for JSON logs (recommended for production)

## Structured Logging

The application supports structured JSON logging for better observability in production.

### Configuration

Set `LOG_FORMAT` environment variable in `.env`:
```bash
# Development (default) - plain text format
LOG_FORMAT=text

# Production - JSON format (recommended)
LOG_FORMAT=json
```

### Usage in Code

```python
from utils.logger import AppLogger
logger = AppLogger.get_logger()

# Basic log
logger.info("User login successful")

# Log with context (automatically added to JSON fields)
logger.info("Door opened", extra={
    "user_id": 1,
    "device_id": "001",
    "action": "door_open"
})
```

### JSON Output Example

```json
{
  "timestamp": "2026-06-11 18:30:15,123",
  "level": "INFO",
  "message": "Door opened",
  "user_id": 1,
  "device_id": "001",
  "logger": "app",
  "module": "door_service",
  "function": "open_door",
  "line": 42,
  "pid": 1234
}
```

### Production Integration

JSON logs can be easily integrated with:
- **ELK Stack** (Elasticsearch + Logstash + Kibana)
- **Loki + Grafana**
- **Alibaba Cloud SLS** (Log Service)
- **AWS CloudWatch**

Just configure your log collector to read `logs/app.log` line by line.

## Database Models

### User Model (`database/models/user.py`)
- `id`: Integer, primary key, indexed
- `username`: String(50), unique, indexed
- `password`: String(100), bcrypt hashed (72-byte limit)
- `role`: String(20), default "user" (options: "admin", "user")
- `created_at`: DateTime, auto-generated with `datetime.now`

### Device Model (`database/models/device.py`)
- `id`: Integer, primary key, indexed
- `name`: String(100), device name/number (e.g., "001", "002")
- `status`: String(20), default "offline" (options: "online", "offline")
- `location`: String(200), device location description
- `created_at`: DateTime, auto-generated
- `updated_at`: DateTime, auto-updated on change

### DoorLog Model (`database/models/door_log.py`)
- `id`: Integer, primary key, indexed
- `user_id`: Integer, foreign key to User.id
- `device_id`: Integer, foreign key to Device.id
- `action`: String(50), action description (e.g., "开门")
- `status`: String(50), result status (e.g., "成功", "失败：无权限")
- `time`: DateTime, auto-generated

### UserDevice Model (`database/models/user_device.py`)
- `id`: Integer, primary key, indexed
- `user_id`: Integer, foreign key to User.id (with CASCADE delete)
- `device_id`: Integer, foreign key to Device.id (with CASCADE delete, indexed)

## API Endpoints

### Authentication
- `POST /auth/login` - User login with username/password
- `POST /auth/register` - User registration (creates regular user)
- `POST /auth/logout` - Logout and invalidate token
- `PUT /auth/password` - Change current user's password
- `POST /auth/wx-login` - WeChat Mini Program login (code → JWT)
- `PUT /auth/wx-bind` - Bind existing account to WeChat

### User Management (Admin Only)
- `GET /users?page=1&size=10&username=&role=` - Get paginated user list with filters
- `POST /users` - Create new user
- `DELETE /users/{user_id}` - Delete user and associated data
- `GET /users/{user_id}/devices` - Get devices bound to a specific user

### Device Management
- `POST /devices` - Create new device (Admin only)
- `GET /devices?name=` - Get device list (filtered by permission)
- `PUT /devices/{device_id}` - Update device info (Admin only)
- `DELETE /devices/{device_id}` - Delete device (Admin only, must unbind users first)
- `POST /devices/{device_id}/bind` - Bind user to device (Admin only)
- `DELETE /devices/{device_id}/unbind?user_id=` - Unbind user from device (Admin only)

### Door Control
- `POST /doors/{device_id}/open` - Open door (permission checked)
- `GET /door-logs?page=1&size=10&user_id=&device_name=&status=&start_time=&end_time=` - Query door logs

### Statistics
- `GET /statistics` - Get dashboard statistics (role-based data)

### AI Assistant
- `POST /ai/chat` - AI-powered natural language door control (Admin only)

### WebSocket
- `ws://host/ws` - Real-time door open notifications for admins

### System
- `GET /health` - Health check endpoint

## Frontend Structure

### Web Dashboard (`web/src/views/`)
- `Login.vue` - Login/Register page with tab switching
- `Layout.vue` - Main layout with sidebar navigation and password change dialog
- `Dashboard.vue` - Dashboard with statistics and AI chat floating button
- `Users.vue` - User management with bind/unbind functionality (Admin only)
- `Device.vue` - Device CRUD operations (Admin only)
- `Door.vue` - Door control and personal access logs
- `Log.vue` - Comprehensive door logs with advanced filtering (Admin only)

### Mini Program (`miniprogram/miniprogram/pages/`)
- `login/` - WeChat one-click login + username/password form
- `doors/` - Device list with open door button, pull-to-refresh
- `logs/` - Personal door access logs with pagination
- `profile/` - User info card, change password, logout

### Key Features
- Role-based menu visibility (admin vs user)
- Real-time WebSocket notifications for door opens (admins only)
- AI assistant floating button on dashboard
- Password change dialog in header
- Responsive design with Element Plus components
- Route guards checking `localStorage.token`

### State Management
- Token stored in `localStorage` as 'token'
- Role stored in `localStorage` as 'role' for UI rendering
- No Pinia/Vuex used, direct localStorage access
- Axios interceptors handle auth headers and error responses

## Configuration Details

### Required Environment Variables
- `SECRET_KEY` - JWT signing key (must be strong random string)
- `MYSQL_HOST` - Database host ("mysql" in Docker, "localhost" locally)
- `MYSQL_PASSWORD` - Database password
- `MYSQL_DB` - Database name

### Optional Environment Variables
- `ALGORITHM` - JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiry (default: 3600)
- `ADMIN_USERNAME` - Default admin username (default: admin)
- `ADMIN_PASSWORD` - Default admin password (default: 123456)
- `AUTO_CREATE_ADMIN` - Auto-create admin on startup (default: true)
- `DEEPSEEK_API_KEY` - DeepSeek API key for AI features
- `AI_API_URL` - AI API endpoint (default: DeepSeek URL)
- `AI_MODEL` - AI model name (default: deepseek-v4-flash)
- `AI_TIMEOUT` - AI request timeout in seconds (default: 15)
- `AI_TEMPERATURE` - AI temperature parameter (default: 0.1)
- `REDIS_HOST` - Redis host (default: 127.0.0.1)
- `REDIS_PORT` - Redis port (default: 6379)
- `REDIS_DB` - Redis database number (default: 0)
- `REDIS_PASSWORD` - Redis password (optional)
- `ALLOWED_ORIGINS` - CORS allowed origins, comma-separated (default: *)
- `WX_APPID` - WeChat Mini Program AppID
- `WX_SECRET` - WeChat Mini Program AppSecret

### Important Configuration Notes
- In Docker environment, use service names: `MYSQL_HOST=mysql`, `REDIS_HOST=redis`
- Locally, use: `MYSQL_HOST=localhost`, `REDIS_HOST=127.0.0.1`
- AI features are optional; system works without `DEEPSEEK_API_KEY`
- Frontend must be built before Docker deployment
- Generate secure SECRET_KEY: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

## Caching Strategy

### Redis Cache Keys
- `token:{token}` - Active session tokens (TTL = token expiry minutes)
- `blacklist:{token}` - Revoked tokens (TTL = 86400s / 24 hours)
- `cache:device:list:user:{user_id}` - Device list per user (TTL = 60s)
- `stat:user:{user_id}` - User statistics (TTL = 180s)
- `ai:context:user:{user_id}` - AI conversation context (TTL = 900s / 15 minutes)

### Cache Invalidation Rules
- Device cache invalidated on: create, update, delete, bind, unbind operations
- All users' device cache cleared when device is created/updated/deleted
- Individual user cache cleared when binding/unbinding devices
- Statistics cache uses TTL-based expiration only
- AI context cleared after successful door open operation

## Security Considerations

### Authentication & Authorization
- JWT tokens with Redis-backed validation
- Token blacklist mechanism for logout functionality
- Password hashing with bcrypt (72-byte limit enforced)
- Role-based access control (admin vs user)
- Admin-only endpoints protected with `require_admin` dependency
- Permission checks for door opening (admin or bound user)

### Input Validation
- Pydantic schemas for all API inputs with field validators
- Username: 1-50 chars, alphanumeric + underscore + Chinese characters
- Password: 6-72 chars minimum/maximum
- Device name/location: required fields with length limits
- SQL injection prevention via SQLAlchemy ORM

### Security Best Practices
- Never commit `.env` file to version control
- Change default admin password after first login
- Use strong SECRET_KEY in production (min 32 characters)
- Restrict `ALLOWED_ORIGINS` in production (avoid using `*`)
- Enable Redis password authentication in production
- Use HTTPS in production with proper SSL certificates
- Regular dependency updates for security patches

## Testing & Debugging

### Backend Testing
- Access Swagger UI: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
- Health check: GET http://localhost:8000/health
- Check logs: `docker compose logs -f fastapi` or view `logs/app.log.YYYY-MM-DD`
- Test API with curl: `curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"123456"}'`

### Frontend Testing
- Dev server: http://localhost:5173
- Production build serves at: http://localhost (port 80 via Nginx)
- Check browser console for WebSocket connection status
- Network tab shows API calls to http://127.0.0.1:8000 (dev) or /api/ (prod)

### Common Issues & Solutions
- **Redis connection failure**: System runs but login/logout won't work properly. Start Redis: `redis-server`
- **Database init failure**: Check MySQL credentials and connectivity. Verify MYSQL_HOST/MYSQL_PASSWORD
- **CORS errors**: Verify ALLOWED_ORIGINS configuration matches frontend URL
- **WebSocket disconnects**: Check network stability and proxy configuration in nginx.conf
- **AI not working**: Verify DEEPSEEK_API_KEY is set and valid, check network access to api.deepseek.com
- **Password too long**: bcrypt has 72-byte limit, enforce in frontend validation
- **Token expired**: Default 3600 minutes, adjust ACCESS_TOKEN_EXPIRE_MINUTES if needed
- **Frontend 404 on refresh**: Nginx config handles Vue Router history mode with try_files

### Docker Troubleshooting
- All docker commands should be run from `deploy/` directory
- Rebuild after code changes: `cd deploy && docker compose up -d --build <service_name>`
- View all logs: `cd deploy && docker compose logs -f`
- Restart single service: `cd deploy && docker compose restart <service_name>`
- Check container status: `cd deploy && docker compose ps`
- Reset database: Stop containers, remove mysql-data volume, restart

## Development Workflow

### Database Migration (Alembic)

The project uses Alembic for database schema versioning and migration management.

**Key Files:**
- `backend/alembic.ini` - Alembic configuration
- `backend/alembic/env.py` - Environment setup (imports project models and config)
- `backend/alembic/versions/` - Migration scripts directory
- `backend/manage_db.py` - Management script for common operations

**Typical Workflow:**
1. Modify SQLAlchemy model (e.g., add field to `database/models/user.py`)
2. Generate migration: `python manage_db.py create -m "add_user_phone_field"`
3. Review generated script in `alembic/versions/`
4. Apply migration: `python manage_db.py upgrade`
5. Rollback if needed: `python manage_db.py downgrade -1`

**Available Commands:**
```bash
cd backend

python manage_db.py current          # Show current database version
python manage_db.py history          # Show migration history
python manage_db.py create -m "msg"  # Create new migration (autogenerate)
python manage_db.py upgrade          # Upgrade to latest version
python manage_db.py downgrade -1     # Rollback one version
```

**Direct Alembic Commands:**
```bash
alembic current                      # Show current version
alembic history                      # Show migration history
alembic revision --autogenerate -m "msg"  # Create migration
alembic upgrade head                 # Upgrade to latest
alembic downgrade -1                 # Rollback one version
```

**Important Notes:**
- Always review autogenerated migrations before applying
- Migrations are stored in `backend/alembic/versions/`
- The `init_database()` in `db.py` still uses `create_all()` as fallback
- For production, prefer Alembic migrations over `create_all()`

### Adding New Feature
1. Define Pydantic schema in `backend/schemas/`
2. Implement business logic in `backend/services/`
3. Create API endpoint in `backend/api/` with `@handle_api_exception`
4. Add route to `backend/api/routers.py`
5. Update web frontend in `web/src/views/`
6. Test with Swagger UI and web frontend

### Code Style Guidelines
- Backend: Follow PEP 8, use type hints, add docstrings
- Frontend: Use Composition API (`<script setup>`), consistent component naming
- Commit messages: Use conventional commits (feat, fix, docs, style, refactor, test, chore)
- Branch strategy: main (production), develop (development), feature/* (features)

### Service Layer Pattern
- All business logic in `services/` directory
- Use `@service_exception_handler` decorator for automatic rollback
- Throw ValueError for business logic errors
- Throw PermissionError for authorization failures
- Return meaningful data or raise exceptions (don't return error dicts)

### API Layer Pattern
- Keep handlers thin, delegate to service layer
- Always use `@handle_api_exception` decorator
- Use FastAPI Depends() for dependency injection
- Return `success()` or `error()` from `utils/response.py`
- Add proper tags and descriptions to routes
