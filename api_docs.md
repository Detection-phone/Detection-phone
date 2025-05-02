# Phone Detection System API Documentation

## Authentication

All API endpoints (except login) require authentication. Include the session cookie in your requests.

### Login
```http
POST /api/login
Content-Type: application/json

{
    "username": "string",
    "password": "string"
}
```

Response:
```json
{
    "message": "Login successful"
}
```

### Logout
```http
GET /api/logout
```

Response:
```json
{
    "message": "Logout successful"
}
```

## Detections

### Get Detections
```http
GET /api/detections?page=1&per_page=10&status=pending&start_date=2024-01-01&end_date=2024-01-31
```

Query Parameters:
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)
- `status`: Filter by status (optional)
- `start_date`: Filter by start date (optional)
- `end_date`: Filter by end date (optional)

Response:
```json
{
    "detections": [
        {
            "id": 1,
            "timestamp": "2024-01-01T12:00:00",
            "location": "Room 101",
            "confidence": 0.95,
            "image_path": "detections/20240101_120000.jpg",
            "status": "Pending"
        }
    ],
    "total": 100,
    "pages": 10,
    "current_page": 1
}
```

### Delete Detection
```http
DELETE /api/detections/{detection_id}
```

Response:
```json
{
    "message": "Detection deleted successfully"
}
```

## Settings

### Get Settings
```http
GET /api/settings
```

Response:
```json
{
    "camera": {
        "start_time": "08:00",
        "end_time": "17:00",
        "blur_faces": true,
        "confidence_threshold": 0.4
    },
    "notifications": {
        "email": true,
        "sms": false,
        "telegram": true
    }
}
```

### Update Settings
```http
POST /api/settings
Content-Type: application/json

{
    "camera_start_time": "08:00",
    "camera_end_time": "17:00",
    "blur_faces": true,
    "confidence_threshold": 0.4,
    "email_enabled": true,
    "sms_enabled": false,
    "telegram_enabled": true
}
```

Response:
```json
{
    "message": "Settings updated successfully"
}
```

## User Management

### Create User
```http
POST /api/users
Content-Type: application/json

{
    "username": "newuser",
    "password": "password123",
    "role": "user"
}
```

Response:
```json
{
    "message": "User created successfully"
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
    "error": "Invalid request data"
}
```

### 401 Unauthorized
```json
{
    "error": "Authentication required"
}
```

### 403 Forbidden
```json
{
    "error": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
    "error": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
    "error": "Internal server error"
}
```

## Rate Limiting

API requests are limited to:
- 100 requests per minute for authenticated users
- 10 requests per minute for unauthenticated users

## Security

- All API endpoints use HTTPS
- Passwords are hashed using bcrypt
- Session cookies are HTTP-only and secure
- CSRF protection is enabled
- Input validation is performed on all requests

## Best Practices

1. Always check the response status code
2. Handle errors gracefully
3. Implement retry logic for failed requests
4. Cache responses when appropriate
5. Use pagination for large datasets
6. Validate all input data
7. Use proper error handling
8. Implement proper logging 