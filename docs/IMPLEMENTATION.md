# alphabench Backend Documentation

## Authentication & Authorization

### Google OAuth Flow (`src/api/routes/auth.py`, `src/core/auth/google.py`)

1. Users can authenticate via Google OAuth
2. Post successful authentication, user details are stored in database (`src/db/queries/auth.py`)
3. JWT token is generated and returned to frontend (`src/core/auth/jwt.py`)

### Anonymous Users

-   Identified by IP address and MAC address
-   Limited to 3 reports per day
-   User details stored in database with anonymous flag (`src/db/queries/users.py`)

## Rate Limiting

### Implementation (`src/api/dependencies.py`)

1. Anonymous Users: 3 reports/day
2. Authenticated Users: 5 reports/day
3. Subscribed Users: Configurable limit (n reports/day)

Rate limits are enforced through database queries checking request counts (`src/db/queries/users.py`)

## Main Application Flow

### 1. Backtest Request Submission

**Route**: `POST /api/backtests` (`src/api/routes/backtests.py`)

```
Request → BacktestRequest Schema → Database → Celery Task Queue
```

**Process**:

1. Validate incoming request (`src/schemas/backtests.py`)
2. Store request in database (`src/db/queries/backtests.py`)
3. Generate strategy title using LLM (`src/infrastructure/llm/openai_client.py`)
4. Return UUID and title to user
5. Queue request for processing (`src/tasks/script_generation.py`)

### 2. Script Generation Pipeline

**Worker**: Script Generator (`src/tasks/script_generation.py`)

```
Task Queue → LLM → Python Script → S3 Storage → Next Task
```

**Process**:

1. Fetch request details from database
2. Use LLM to generate Python backtesting script (`src/core/backtesting/generator.py`)
3. Get required data points list
4. Fetch historical data (`src/db/queries/backtests.py`)
5. Generate two CSV files:
    - Validation dataset (small)
    - Full dataset
6. Store files in S3 (`src/infrastructure/storage/s3_client.py`)
7. Queue for validation (`src/tasks/script_validation.py`)

### 3. Script Validation Pipeline

**Worker**: Script Validator (`src/tasks/script_validation.py`)

```
Task Queue → S3 → Script Execution → Success/Failure → Next Task/Retry
```

**Process**:

1. Fetch script and validation dataset from S3
2. Execute script with validation data (`src/core/backtesting/validator.py`)
3. If successful:
    - Delete validation dataset
    - Queue for full execution
4. If unsuccessful:
    - Send script and error to LLM
    - Generate fixed script
    - Retry validation

### 4. Full Backtest Execution

**Worker**: Backtest Executor (`src/tasks/backtest_execution.py`)

```
Task Queue → S3 → Script Execution → Log Generation → Database Update
```

**Process**:

1. Fetch validated script and full dataset
2. Execute backtest (`src/core/backtesting/executor.py`)
3. Save execution logs to S3
4. Update database `ready_for_report` flag
5. Queue for report generation

### 5. Report Generation

**Worker**: Report Generator (`src/tasks/report_generation.py`)

```
Task Queue → S3 → LLM Analysis → Markdown Report → Database Update
```

**Process**:

1. Monitor for requests with `ready_for_report=true`
2. Fetch execution logs from S3
3. Pass logs to LLM for analysis (`src/core/reports/analyzer.py`)
4. Generate markdown report
5. Store report in S3
6. Update database with report URL and `generated_report=true`

## Additional APIs

All routes defined in `src/api/routes/`

### Subscription Management (`subscriptions.py`)

-   GET `/api/subscriptions` - List all plans
-   GET `/api/subscriptions/active` - Get user's active subscription
-   POST `/api/subscriptions` - Purchase subscription

### User Management (`users.py`)

-   GET `/api/users/profile` - Get user profile
-   PATCH `/api/users/profile` - Update user profile

### Report Management (`reports.py`)

-   GET `/api/reports` - List user's reports
-   GET `/api/reports/{id}` - Get specific report details

## Database Schema

Key tables (SQL in `src/db/queries/`):

-   users
-   backtest_requests
-   subscription_plans
-   user_subscriptions
-   rate_limits

## Infrastructure

-   Database: PostgreSQL
-   Queue: Redis + Celery
-   Storage: AWS S3
-   LLM: OpenAI API
-   Environment: Dockerized

## Monitoring and Logging

-   Structured logging (`src/utils/logger.py`)
-   Prometheus metrics (`src/utils/metrics.py`)
-   Error tracking (`src/api/error_handlers.py`)

## Configuration

All configuration managed through environment variables and `src/config/settings.py`

## Security Considerations

1. JWT-based authentication
2. Rate limiting
3. Input validation
4. Secure script execution environment
5. S3 bucket access control
6. Database connection pooling
7. API key rotation
8. User data encryption
