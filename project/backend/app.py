"""
Employee Directory Backend Application
Flask-based REST API for employee management with AWS integration
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import boto3
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
class Config:
    """Application configuration"""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    
    # JWT configuration
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # AWS configuration
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    DB_SECRET_NAME = os.environ.get('DB_SECRET_NAME', 'employee-directory-production-db-credentials')
    JWT_SECRET_NAME = os.environ.get('JWT_SECRET_NAME', 'employee-directory-production-jwt-secret')
    
    # CORS configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

# Apply configuration
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
cors = CORS(app, origins=Config.CORS_ORIGINS)

def get_secret(secret_name: str) -> Dict[str, Any]:
    """
    Retrieve secret from AWS Secrets Manager
    
    Args:
        secret_name: Name of the secret to retrieve
        
    Returns:
        Dictionary containing secret values
        
    Raises:
        Exception: If secret cannot be retrieved
    """
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=Config.AWS_REGION
        )
        
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        logger.info(f"Successfully retrieved secret: {secret_name}")
        return secret
        
    except Exception as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {e}")
        raise

def configure_database():
    """Configure database connection using Secrets Manager"""
    try:
        # Try to get database credentials from Secrets Manager
        db_secret = get_secret(Config.DB_SECRET_NAME)
        
        # Use the pre-constructed database URL if available
        if 'database_url' in db_secret:
            database_url = db_secret['database_url']
        else:
            # Construct database URL from individual components
            username = db_secret['username']
            password = db_secret['password']
            host = db_secret['host']
            port = db_secret.get('port', 5432)
            dbname = db_secret.get('dbname', 'employee_directory')
            database_url = f"postgresql://{username}:{password}@{host}:{port}/{dbname}"
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        logger.info("Database configuration loaded from Secrets Manager")
        
    except Exception as e:
        logger.warning(f"Could not retrieve database credentials from Secrets Manager: {e}")
        # Fallback to environment variable or SQLite
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///employees.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        logger.info("Using fallback database configuration")

def configure_jwt():
    """Configure JWT using Secrets Manager"""
    try:
        jwt_secret = get_secret(Config.JWT_SECRET_NAME)
        app.config['JWT_SECRET_KEY'] = jwt_secret['jwt_secret_key']
        logger.info("JWT configuration loaded from Secrets Manager")
        
    except Exception as e:
        logger.warning(f"Could not retrieve JWT secret from Secrets Manager: {e}")
        # Fallback to environment variable
        app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'fallback-jwt-secret')
        logger.info("Using fallback JWT configuration")

# Configure application
configure_database()
configure_jwt()

# Initialize extensions with app
db.init_app(app)
jwt.init_app(app)

# Import models after db initialization
from models import Employee, AuditLog

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    """Handle bad request errors"""
    return jsonify({
        'error': 'Bad Request',
        'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
    }), 400

@app.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    db.session.rollback()
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500

# Health check endpoint
@app.route('/health')
def health_check():
    """
    Health check endpoint for load balancer and monitoring
    
    Returns:
        JSON response with health status
    """
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db.session.commit()
        
        # Get basic statistics
        employee_count = Employee.query.count()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'employee_count': employee_count,
            'version': '1.0.0'
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'disconnected',
            'error': str(e)
        }), 503

# Authentication endpoints
@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    User authentication endpoint
    
    Returns:
        JSON response with access token or error
    """
    try:
        data = request.get_json()
        
        if not data:
            raise BadRequest("Request body must be JSON")
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'message': 'Username and password are required'}), 400
        
        # Simple authentication - in production, validate against user database
        # For demo purposes, accept any non-empty credentials
        if len(username) >= 3 and len(password) >= 6:
            access_token = create_access_token(identity=username)
            
            # Log successful login
            logger.info(f"Successful login for user: {username}")
            
            return jsonify({
                'access_token': access_token,
                'user': username,
                'expires_in': int(Config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds())
            }), 200
        
        return jsonify({'message': 'Invalid credentials'}), 401
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'message': 'Authentication failed'}), 500

@app.route('/api/auth/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """
    Verify JWT token validity
    
    Returns:
        JSON response with user information
    """
    current_user = get_jwt_identity()
    return jsonify({
        'valid': True,
        'user': current_user
    }), 200

# Import routes
from routes import *

# Database initialization
def create_tables():
    """Create database tables and add sample data if needed"""
    try:
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Add sample data if no employees exist
            if Employee.query.count() == 0:
                sample_employees = [
                    Employee(
                        name='John Doe',
                        email='john.doe@company.com',
                        phone='+1-555-0101',
                        department='Engineering',
                        position='Senior Software Engineer',
                        location='San Francisco, CA',
                        manager='Jane Smith'
                    ),
                    Employee(
                        name='Jane Smith',
                        email='jane.smith@company.com',
                        phone='+1-555-0102',
                        department='Engineering',
                        position='Engineering Manager',
                        location='San Francisco, CA',
                        manager='Bob Johnson'
                    ),
                    Employee(
                        name='Bob Johnson',
                        email='bob.johnson@company.com',
                        phone='+1-555-0103',
                        department='Engineering',
                        position='VP of Engineering',
                        location='San Francisco, CA'
                    ),
                    Employee(
                        name='Alice Brown',
                        email='alice.brown@company.com',
                        phone='+1-555-0104',
                        department='Marketing',
                        position='Marketing Manager',
                        location='New York, NY',
                        manager='Carol White'
                    ),
                    Employee(
                        name='Carol White',
                        email='carol.white@company.com',
                        phone='+1-555-0105',
                        department='Marketing',
                        position='VP of Marketing',
                        location='New York, NY'
                    ),
                    Employee(
                        name='David Wilson',
                        email='david.wilson@company.com',
                        phone='+1-555-0106',
                        department='Sales',
                        position='Sales Representative',
                        location='Chicago, IL',
                        manager='Eva Davis'
                    ),
                    Employee(
                        name='Eva Davis',
                        email='eva.davis@company.com',
                        phone='+1-555-0107',
                        department='Sales',
                        position='Sales Manager',
                        location='Chicago, IL'
                    ),
                    Employee(
                        name='Frank Miller',
                        email='frank.miller@company.com',
                        phone='+1-555-0108',
                        department='HR',
                        position='HR Specialist',
                        location='Austin, TX',
                        manager='Grace Lee'
                    ),
                    Employee(
                        name='Grace Lee',
                        email='grace.lee@company.com',
                        phone='+1-555-0109',
                        department='HR',
                        position='HR Manager',
                        location='Austin, TX'
                    ),
                    Employee(
                        name='Henry Taylor',
                        email='henry.taylor@company.com',
                        phone='+1-555-0110',
                        department='Finance',
                        position='Financial Analyst',
                        location='Boston, MA',
                        manager='Ivy Chen'
                    ),
                    Employee(
                        name='Ivy Chen',
                        email='ivy.chen@company.com',
                        phone='+1-555-0111',
                        department='Finance',
                        position='Finance Manager',
                        location='Boston, MA'
                    )
                ]
                
                for employee in sample_employees:
                    db.session.add(employee)
                
                db.session.commit()
                logger.info("Sample data added successfully")
                
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        db.session.rollback()
        raise

# Application startup
if __name__ == '__main__':
    # Create tables on startup
    create_tables()
    
    # Get configuration from environment
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting Employee Directory API on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Environment: {os.environ.get('FLASK_ENV', 'production')}")
    
    app.run(host=host, port=port, debug=debug)