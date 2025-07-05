"""
Database Models for Employee Directory Application
"""

from datetime import datetime
from typing import Dict, Any, Optional
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.orm import validates
import re

# Import db from app to avoid circular imports
from app import db

class Employee(db.Model):
    """
    Employee model for storing employee information
    
    Attributes:
        id: Primary key
        name: Full name of the employee
        email: Email address (unique)
        phone: Phone number
        department: Department name
        position: Job position/title
        location: Office location
        manager: Manager's name
        is_active: Whether the employee is currently active
        hire_date: Date when employee was hired
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """
    
    __tablename__ = 'employees'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic information
    name = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    
    # Work information
    department = db.Column(db.String(50), nullable=False, index=True)
    position = db.Column(db.String(100))
    location = db.Column(db.String(100))
    manager = db.Column(db.String(100))
    
    # Status and dates
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    hire_date = db.Column(db.Date, default=datetime.utcnow().date)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Validation
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format"""
        if not email:
            raise ValueError("Email is required")
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")
        
        return email.lower().strip()
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate name"""
        if not name or not name.strip():
            raise ValueError("Name is required")
        
        if len(name.strip()) < 2:
            raise ValueError("Name must be at least 2 characters long")
        
        return name.strip()
    
    @validates('department')
    def validate_department(self, key, department):
        """Validate department"""
        if not department or not department.strip():
            raise ValueError("Department is required")
        
        return department.strip()
    
    @validates('phone')
    def validate_phone(self, key, phone):
        """Validate phone number format"""
        if phone:
            # Remove all non-digit characters for validation
            digits_only = re.sub(r'\D', '', phone)
            if len(digits_only) < 10:
                raise ValueError("Phone number must contain at least 10 digits")
        
        return phone.strip() if phone else None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert employee object to dictionary
        
        Returns:
            Dictionary representation of the employee
        """
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'department': self.department,
            'position': self.position,
            'location': self.location,
            'manager': self.manager,
            'is_active': self.is_active,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """
        Convert employee object to summary dictionary (for lists)
        
        Returns:
            Summary dictionary representation of the employee
        """
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'department': self.department,
            'position': self.position,
            'location': self.location,
            'is_active': self.is_active
        }
    
    @classmethod
    def search(cls, query: str, department: Optional[str] = None, is_active: bool = True):
        """
        Search employees by name, email, or position
        
        Args:
            query: Search query string
            department: Optional department filter
            is_active: Filter by active status
            
        Returns:
            SQLAlchemy query object
        """
        search_query = cls.query.filter(cls.is_active == is_active)
        
        if query:
            search_filter = f"%{query.strip()}%"
            search_query = search_query.filter(
                db.or_(
                    cls.name.ilike(search_filter),
                    cls.email.ilike(search_filter),
                    cls.position.ilike(search_filter)
                )
            )
        
        if department:
            search_query = search_query.filter(cls.department == department)
        
        return search_query.order_by(cls.name)
    
    def __repr__(self):
        return f'<Employee {self.name} ({self.email})>'

class Department(db.Model):
    """
    Department model for storing department information
    
    Attributes:
        id: Primary key
        name: Department name (unique)
        description: Department description
        manager_email: Email of department manager
        budget: Department budget
        is_active: Whether the department is currently active
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """
    
    __tablename__ = 'departments'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic information
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    manager_email = db.Column(db.String(120))
    
    # Additional information
    budget = db.Column(db.Numeric(12, 2))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate department name"""
        if not name or not name.strip():
            raise ValueError("Department name is required")
        
        return name.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert department object to dictionary
        
        Returns:
            Dictionary representation of the department
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'manager_email': self.manager_email,
            'budget': float(self.budget) if self.budget else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def employee_count(self) -> int:
        """Get the number of active employees in this department"""
        return Employee.query.filter(
            Employee.department == self.name,
            Employee.is_active == True
        ).count()
    
    def __repr__(self):
        return f'<Department {self.name}>'

class AuditLog(db.Model):
    """
    Audit log model for tracking changes to employee records
    
    Attributes:
        id: Primary key
        employee_id: ID of the affected employee
        action: Type of action (CREATE, UPDATE, DELETE)
        changed_by: User who made the change
        old_values: Previous values (JSON)
        new_values: New values (JSON)
        timestamp: When the change occurred
        ip_address: IP address of the user
        user_agent: User agent string
    """
    
    __tablename__ = 'audit_logs'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Reference information
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # CREATE, UPDATE, DELETE
    changed_by = db.Column(db.String(100), nullable=False)
    
    # Change details
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    
    # Metadata
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.Text)
    
    # Relationship
    employee = db.relationship('Employee', backref=db.backref('audit_logs', lazy=True))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert audit log object to dictionary
        
        Returns:
            Dictionary representation of the audit log
        """
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'action': self.action,
            'changed_by': self.changed_by,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }
    
    @classmethod
    def log_change(cls, employee_id: int, action: str, changed_by: str, 
                   old_values: Optional[Dict] = None, new_values: Optional[Dict] = None,
                   ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """
        Create an audit log entry
        
        Args:
            employee_id: ID of the affected employee
            action: Type of action (CREATE, UPDATE, DELETE)
            changed_by: User who made the change
            old_values: Previous values
            new_values: New values
            ip_address: IP address of the user
            user_agent: User agent string
        """
        audit_log = cls(
            employee_id=employee_id,
            action=action,
            changed_by=changed_by,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(audit_log)
        return audit_log
    
    def __repr__(self):
        return f'<AuditLog {self.action} on Employee {self.employee_id} by {self.changed_by}>'

# Event listeners for automatic audit logging
@event.listens_for(Employee, 'after_insert')
def log_employee_insert(mapper, connection, target):
    """Log employee creation"""
    # Note: This would need to be enhanced to capture user context
    # For now, we'll skip automatic logging and handle it in the routes
    pass

@event.listens_for(Employee, 'after_update')
def log_employee_update(mapper, connection, target):
    """Log employee updates"""
    # Note: This would need to be enhanced to capture user context and old values
    # For now, we'll skip automatic logging and handle it in the routes
    pass

@event.listens_for(Employee, 'after_delete')
def log_employee_delete(mapper, connection, target):
    """Log employee deletion"""
    # Note: This would need to be enhanced to capture user context
    # For now, we'll skip automatic logging and handle it in the routes
    pass