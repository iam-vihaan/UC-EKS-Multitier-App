# Employee Directory Backend

Flask-based REST API for the Employee Directory application, designed to run on AWS EKS with EC2 nodes.

## Features

- RESTful API for employee management
- PostgreSQL/MySQL database support via Amazon RDS
- AWS Secrets Manager integration for secure credential storage
- JWT authentication
- Health check endpoints
- Comprehensive logging
- Docker containerization

## API Endpoints

### Authentication
- `POST /api/auth/login` - User authentication

### Employees
- `GET /api/employees` - List all employees (with search and filtering)
- `GET /api/employees/<id>` - Get specific employee
- `POST /api/employees` - Create new employee
- `PUT /api/employees/<id>` - Update employee
- `DELETE /api/employees/<id>` - Delete employee

### Departments
- `GET /api/departments` - List all departments

### Statistics
- `GET /api/stats` - Get employee statistics

### Health
- `GET /health` - Health check endpoint

## Environment Variables

- `DATABASE_URL`: Database connection string
- `DB_SECRET_NAME`: AWS Secrets Manager secret name for DB credentials
- `AWS_REGION`: AWS region for Secrets Manager
- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `FLASK_ENV`: Environment (development/production)
- `PORT`: Port to run the application (default: 5000)

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py

# Run with gunicorn
gunicorn --bind 0.0.0.0:5000 app:app
```

## Docker

```bash
# Build the Docker image
docker build -t employee-directory-backend .

# Run locally
docker run -p 5000:5000 employee-directory-backend
```

## Database Setup

The application supports both SQLite (for development) and PostgreSQL/MySQL (for production). Database tables are created automatically on first run.

## AWS Integration

- **RDS**: Database hosting
- **Secrets Manager**: Secure credential storage
- **EKS**: Container orchestration
- **EC2**: Compute nodes for backend pods

## Deployment

This backend is configured to run on AWS EKS with EC2 nodes. See the Kubernetes manifests in the `k8s/` directory for deployment configuration.