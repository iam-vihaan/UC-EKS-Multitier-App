# Employee Directory Frontend

React-based frontend for the Employee Directory application, designed to run on AWS EKS with Fargate.

## Features

- Employee search and filtering
- CRUD operations for employee management
- Responsive design with modern UI
- Integration with Flask backend API
- Optimized for containerized deployment

## Development

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

## Docker Build

```bash
# Build the Docker image
docker build -t employee-directory-frontend .

# Run locally
docker run -p 3000:80 employee-directory-frontend
```

## Environment Variables

- `REACT_APP_API_URL`: Backend API URL (default: `/api`)

## Deployment

This frontend is configured to run on AWS EKS with Fargate. See the Kubernetes manifests in the `k8s/` directory for deployment configuration.