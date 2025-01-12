# AlphaBench API Documentation

## Base URL

```
https://api.alphabench.in/api/v1
```

## Authentication

The API uses JWT tokens for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <token>
```

Anonymous users are automatically assigned a token based on IP and device information.

## Rate Limits

-   Anonymous users: 3 reports/day
-   Authenticated users: 5 reports/day
-   Subscribed users: Configurable limit (n reports/day)

## Endpoints

### Authentication

#### Google OAuth Login

**Request:**

```http
POST /auth/google
Content-Type: application/json

{
    "code": "4/0AfJohXnLW7...",
    "redirect_uri": "https://app.alphabench.in/auth/callback"
}
```

**Response:** (200 OK)

```json
{
	"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
	"token_type": "bearer"
}
```

#### Get Current User

**Request:**

```http
GET /auth/me
Authorization: Bearer <token>
```

**Response:** (200 OK)

```json
{
	"id": "123e4567-e89b-12d3-a456-426614174000",
	"email": "user@example.com",
	"google_id": "109876543210987654321",
	"is_anonymous": false,
	"created_at": "2024-01-01T00:00:00Z",
	"updated_at": "2024-01-01T00:00:00Z"
}
```

### Backtests

#### Create Backtest Request

**Request:**

```http
POST /backtests
Authorization: Bearer <token>
Content-Type: application/json

{
    "instrument_symbol": "AAPL",
    "from_date": "2023-01-01",
    "to_date": "2023-12-31",
    "strategy_description": "Buy when the 50-day moving average crosses above the 200-day moving average. Sell when it crosses below. Use 1% of portfolio per trade."
}
```

**Response:** (201 Created)

```json
{
	"id": "123e4567-e89b-12d3-a456-426614174000",
	"status": "pending",
	"strategy_title": "Golden Cross Strategy"
}
```

#### List User's Backtests

**Request:**

```http
GET /backtests
Authorization: Bearer <token>
```

**Response:** (200 OK)

```json
[
	{
		"id": "123e4567-e89b-12d3-a456-426614174000",
		"status": "completed",
		"strategy_title": "Golden Cross Strategy",
		"created_at": "2024-01-01T00:00:00Z",
		"updated_at": "2024-01-01T00:10:00Z"
	}
]
```

#### Get Specific Backtest

**Request:**

```http
GET /backtests/{backtest_id}
Authorization: Bearer <token>
```

**Response:** (200 OK)

```json
{
	"id": "123e4567-e89b-12d3-a456-426614174000",
	"status": "completed",
	"strategy_title": "Golden Cross Strategy",
	"python_script_url": "https://s3.amazonaws.com/scripts/123...",
	"report_url": "https://s3.amazonaws.com/reports/123...",
	"created_at": "2024-01-01T00:00:00Z",
	"updated_at": "2024-01-01T00:10:00Z"
}
```

### Reports

#### List Generated Reports

**Request:**

```http
GET /reports
Authorization: Bearer <token>
```

**Response:** (200 OK)

```json
[
	{
		"id": "123e4567-e89b-12d3-a456-426614174000",
		"strategy_title": "Golden Cross Strategy",
		"report_url": "https://s3.amazonaws.com/reports/123...",
		"created_at": "2024-01-01T00:00:00Z"
	}
]
```

#### Get Specific Report

**Request:**

```http
GET /reports/{backtest_id}
Authorization: Bearer <token>
```

**Response:** (200 OK)

```json
{
	"id": "123e4567-e89b-12d3-a456-426614174000",
	"strategy_title": "Golden Cross Strategy",
	"report_url": "https://s3.amazonaws.com/reports/123...",
	"created_at": "2024-01-01T00:00:00Z"
}
```

### Subscriptions

#### List Available Plans

**Request:**

```http
GET /subscriptions
Authorization: Bearer <token>
```

**Response:** (200 OK)

```json
[
	{
		"id": "123e4567-e89b-12d3-a456-426614174000",
		"name": "Professional",
		"description": "Advanced backtesting with unlimited reports",
		"price_usd": 49.99,
		"reports_per_day": 100,
		"created_at": "2024-01-01T00:00:00Z"
	}
]
```

#### Get Active Subscription

**Request:**

```http
GET /subscriptions/active
Authorization: Bearer <token>
```

**Response:** (200 OK)

```json
{
	"id": "123e4567-e89b-12d3-a456-426614174000",
	"plan": {
		"name": "Professional",
		"reports_per_day": 100
	},
	"start_date": "2024-01-01T00:00:00Z",
	"end_date": "2024-12-31T23:59:59Z"
}
```

#### Create Subscription

**Request:**

```http
POST /subscriptions
Authorization: Bearer <token>
Content-Type: application/json

{
    "plan_id": "123e4567-e89b-12d3-a456-426614174000",
    "payment_token": "tok_visa_123"
}
```

**Response:** (201 Created)

```json
{
	"id": "123e4567-e89b-12d3-a456-426614174000",
	"plan": {
		"name": "Professional",
		"reports_per_day": 100
	},
	"start_date": "2024-01-01T00:00:00Z",
	"end_date": "2024-12-31T23:59:59Z"
}
```

### Health Checks

#### Basic Health Check

**Request:**

```http
GET /health
```

**Response:** (200 OK)

```json
{
	"status": "healthy"
}
```

#### Detailed Health Check

**Request:**

```http
GET /health/detailed
Authorization: Bearer <token>
```

**Response:** (200 OK)

```json
{
	"status": "healthy",
	"database": {
		"status": "healthy",
		"latency_ms": 5
	},
	"redis": {
		"status": "healthy",
		"latency_ms": 2
	},
	"s3": {
		"status": "healthy"
	},
	"openai": {
		"status": "healthy"
	},
	"celery": {
		"status": "healthy",
		"active_workers": 4
	}
}
```

## Error Responses

### 401 Unauthorized

```json
{
	"detail": "Could not validate credentials"
}
```

### 403 Forbidden

```json
{
	"detail": "Anonymous users cannot subscribe"
}
```

### 404 Not Found

```json
{
	"detail": "Report not found"
}
```

### 429 Too Many Requests

```json
{
	"detail": "Daily report limit exceeded"
}
```

### 500 Internal Server Error

```json
{
	"detail": "Internal server error"
}
```
