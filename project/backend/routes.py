"""
API Routes for Employee Directory Application
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, desc
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest, NotFound

from app import app, db
from models import Employee, Department, AuditLog

logger = logging.getLogger(__name__)

# Helper functions
def get_client_ip() -> str:
    """Get client IP address from request"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif request.environ.get('HTTP_X_REAL_IP'):
        return request.environ['HTTP_X_REAL_IP']
    else:
        return request.environ.get('REMOTE_ADDR', 'unknown')

def get_user_agent() -> str:
    """Get user agent from request"""
    return request.headers.get('User-Agent', 'unknown')

def validate_employee_data(data: Dict[str, Any], required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Validate employee data
    
    Args:
        data: Employee data dictionary
        required_fields: List of required field names
        
    Returns:
        Validated and cleaned data dictionary
        
    Raises:
        BadRequest: If validation fails
    """
    if not data:
        raise BadRequest("Request body must contain JSON data")
    
    # Default required fields for creation
    if required_fields is None:
        required_fields = ['name', 'email', 'department']
    
    # Check required fields
    for field in required_fields:
        if field not in data or not str(data[field]).strip():
            raise BadRequest(f"'{field}' is required and cannot be empty")
    
    # Clean and validate data
    cleaned_data = {}
    
    # String fields that should be stripped
    string_fields = ['name', 'email', 'phone', 'department', 'position', 'location', 'manager']
    for field in string_fields:
        if field in data and data[field] is not None:
            cleaned_data[field] = str(data[field]).strip()
    
    # Boolean fields
    if 'is_active' in data:
        cleaned_data['is_active'] = bool(data['is_active'])
    
    # Date fields
    if 'hire_date' in data and data['hire_date']:
        try:
            if isinstance(data['hire_date'], str):
                cleaned_data['hire_date'] = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
            else:
                cleaned_data['hire_date'] = data['hire_date']
        except ValueError:
            raise BadRequest("hire_date must be in YYYY-MM-DD format")
    
    return cleaned_data

# Employee endpoints
@app.route('/api/employees', methods=['GET'])
def get_employees():
    """
    Get all employees with optional search and filtering
    
    Query Parameters:
        search: Search term for name, email, or position
        department: Filter by department
        is_active: Filter by active status (default: true)
        page: Page number for pagination (default: 1)
        per_page: Items per page (default: 50, max: 100)
        sort_by: Sort field (name, email, department, created_at)
        sort_order: Sort order (asc, desc)
        
    Returns:
        JSON response with employee list and pagination info
    """
    try:
        # Get query parameters
        search = request.args.get('search', '').strip()
        department = request.args.get('department', '').strip()
        is_active = request.args.get('is_active', 'true').lower() == 'true'
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('per_page', 50))))
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Build query using the search method
        query = Employee.search(search, department, is_active)
        
        # Apply sorting
        sort_column = getattr(Employee, sort_by, Employee.name)
        if sort_order.lower() == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Apply pagination
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Format response
        employees = [emp.to_summary_dict() for emp in pagination.items]
        
        response_data = {
            'employees': employees,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'filters': {
                'search': search,
                'department': department,
                'is_active': is_active
            }
        }
        
        logger.info(f"Retrieved {len(employees)} employees (page {page}/{pagination.pages})")
        return jsonify(response_data), 200
        
    except ValueError as e:
        logger.error(f"Invalid parameter in get_employees: {e}")
        return jsonify({'error': 'Invalid parameter value'}), 400
    except Exception as e:
        logger.error(f"Error fetching employees: {e}")
        return jsonify({'error': 'Failed to fetch employees'}), 500

@app.route('/api/employees/<int:employee_id>', methods=['GET'])
def get_employee(employee_id: int):
    """
    Get a specific employee by ID
    
    Args:
        employee_id: Employee ID
        
    Returns:
        JSON response with employee details
    """
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            raise NotFound(f"Employee with ID {employee_id} not found")
        
        logger.info(f"Retrieved employee: {employee.name} (ID: {employee_id})")
        return jsonify(employee.to_dict()), 200
        
    except NotFound:
        return jsonify({'error': f'Employee with ID {employee_id} not found'}), 404
    except Exception as e:
        logger.error(f"Error fetching employee {employee_id}: {e}")
        return jsonify({'error': 'Failed to fetch employee'}), 500

@app.route('/api/employees', methods=['POST'])
@jwt_required()
def create_employee():
    """
    Create a new employee
    
    Returns:
        JSON response with created employee data
    """
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        
        # Validate input data
        validated_data = validate_employee_data(data)
        
        # Check if email already exists
        existing_employee = Employee.query.filter_by(email=validated_data['email']).first()
        if existing_employee:
            return jsonify({'error': 'Email address already exists'}), 409
        
        # Create new employee
        employee = Employee(**validated_data)
        db.session.add(employee)
        db.session.flush()  # Get the ID without committing
        
        # Log the creation
        AuditLog.log_change(
            employee_id=employee.id,
            action='CREATE',
            changed_by=current_user,
            new_values=validated_data,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        db.session.commit()
        
        logger.info(f"Created employee: {employee.name} (ID: {employee.id}) by {current_user}")
        return jsonify(employee.to_dict()), 201
        
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Integrity error creating employee: {e}")
        return jsonify({'error': 'Email address already exists'}), 409
    except BadRequest as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating employee: {e}")
        return jsonify({'error': 'Failed to create employee'}), 500

@app.route('/api/employees/<int:employee_id>', methods=['PUT'])
@jwt_required()
def update_employee(employee_id: int):
    """
    Update an existing employee
    
    Args:
        employee_id: Employee ID
        
    Returns:
        JSON response with updated employee data
    """
    try:
        current_user = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        
        if not employee:
            raise NotFound(f"Employee with ID {employee_id} not found")
        
        data = request.get_json()
        
        # Validate input data (no required fields for updates)
        validated_data = validate_employee_data(data, required_fields=[])
        
        # Check if email is being changed and if it already exists
        if 'email' in validated_data and validated_data['email'] != employee.email:
            existing_employee = Employee.query.filter_by(email=validated_data['email']).first()
            if existing_employee:
                return jsonify({'error': 'Email address already exists'}), 409
        
        # Store old values for audit log
        old_values = employee.to_dict()
        
        # Update employee fields
        for field, value in validated_data.items():
            if hasattr(employee, field):
                setattr(employee, field, value)
        
        # Update timestamp
        employee.updated_at = datetime.utcnow()
        
        # Log the update
        AuditLog.log_change(
            employee_id=employee.id,
            action='UPDATE',
            changed_by=current_user,
            old_values=old_values,
            new_values=validated_data,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        db.session.commit()
        
        logger.info(f"Updated employee: {employee.name} (ID: {employee_id}) by {current_user}")
        return jsonify(employee.to_dict()), 200
        
    except NotFound:
        return jsonify({'error': f'Employee with ID {employee_id} not found'}), 404
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Integrity error updating employee: {e}")
        return jsonify({'error': 'Email address already exists'}), 409
    except BadRequest as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating employee {employee_id}: {e}")
        return jsonify({'error': 'Failed to update employee'}), 500

@app.route('/api/employees/<int:employee_id>', methods=['DELETE'])
@jwt_required()
def delete_employee(employee_id: int):
    """
    Delete an employee (soft delete by setting is_active to False)
    
    Args:
        employee_id: Employee ID
        
    Returns:
        JSON response confirming deletion
    """
    try:
        current_user = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        
        if not employee:
            raise NotFound(f"Employee with ID {employee_id} not found")
        
        # Store old values for audit log
        old_values = employee.to_dict()
        employee_name = employee.name
        
        # Soft delete by setting is_active to False
        employee.is_active = False
        employee.updated_at = datetime.utcnow()
        
        # Log the deletion
        AuditLog.log_change(
            employee_id=employee.id,
            action='DELETE',
            changed_by=current_user,
            old_values=old_values,
            new_values={'is_active': False},
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        db.session.commit()
        
        logger.info(f"Deleted employee: {employee_name} (ID: {employee_id}) by {current_user}")
        return jsonify({'message': 'Employee deleted successfully'}), 200
        
    except NotFound:
        return jsonify({'error': f'Employee with ID {employee_id} not found'}), 404
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting employee {employee_id}: {e}")
        return jsonify({'error': 'Failed to delete employee'}), 500

# Department endpoints
@app.route('/api/departments', methods=['GET'])
def get_departments():
    """
    Get all departments with employee counts
    
    Returns:
        JSON response with department list
    """
    try:
        # Get unique departments from employees table
        department_query = db.session.query(
            Employee.department,
            func.count(Employee.id).label('employee_count')
        ).filter(
            Employee.is_active == True
        ).group_by(Employee.department).order_by(Employee.department)
        
        departments = []
        for dept_name, count in department_query.all():
            if dept_name:  # Skip null departments
                departments.append({
                    'name': dept_name,
                    'employee_count': count
                })
        
        # Add some default departments if none exist
        if not departments:
            default_departments = [
                'Engineering', 'Marketing', 'Sales', 'HR', 'Finance',
                'Operations', 'Customer Support', 'Product', 'Design'
            ]
            departments = [{'name': dept, 'employee_count': 0} for dept in default_departments]
        
        logger.info(f"Retrieved {len(departments)} departments")
        return jsonify(departments), 200
        
    except Exception as e:
        logger.error(f"Error fetching departments: {e}")
        return jsonify({'error': 'Failed to fetch departments'}), 500

@app.route('/api/departments/<string:department_name>/employees', methods=['GET'])
def get_department_employees(department_name: str):
    """
    Get all employees in a specific department
    
    Args:
        department_name: Name of the department
        
    Returns:
        JSON response with employee list for the department
    """
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('per_page', 50))))
        is_active = request.args.get('is_active', 'true').lower() == 'true'
        
        # Query employees in the department
        query = Employee.query.filter(
            Employee.department == department_name,
            Employee.is_active == is_active
        ).order_by(Employee.name)
        
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        employees = [emp.to_summary_dict() for emp in pagination.items]
        
        response_data = {
            'department': department_name,
            'employees': employees,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }
        
        logger.info(f"Retrieved {len(employees)} employees for department: {department_name}")
        return jsonify(response_data), 200
        
    except ValueError as e:
        logger.error(f"Invalid parameter in get_department_employees: {e}")
        return jsonify({'error': 'Invalid parameter value'}), 400
    except Exception as e:
        logger.error(f"Error fetching employees for department {department_name}: {e}")
        return jsonify({'error': 'Failed to fetch department employees'}), 500

# Statistics endpoints
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    Get employee statistics and analytics
    
    Returns:
        JSON response with various statistics
    """
    try:
        # Basic counts
        total_employees = Employee.query.filter(Employee.is_active == True).count()
        total_inactive = Employee.query.filter(Employee.is_active == False).count()
        
        # Department statistics
        dept_stats = db.session.query(
            Employee.department,
            func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True
        ).group_by(Employee.department).all()
        
        department_stats = {dept: count for dept, count in dept_stats if dept}
        
        # Location statistics
        location_stats = db.session.query(
            Employee.location,
            func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True,
            Employee.location.isnot(None)
        ).group_by(Employee.location).all()
        
        location_counts = {loc: count for loc, count in location_stats if loc}
        
        # Recent hires (last 30 days)
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
        recent_hires = Employee.query.filter(
            Employee.hire_date >= thirty_days_ago,
            Employee.is_active == True
        ).count()
        
        # Growth statistics
        growth_stats = []
        for i in range(6):  # Last 6 months
            month_start = datetime.utcnow().replace(day=1) - timedelta(days=30 * i)
            month_end = month_start.replace(day=28) + timedelta(days=4)  # End of month
            
            count = Employee.query.filter(
                Employee.created_at >= month_start,
                Employee.created_at < month_end
            ).count()
            
            growth_stats.append({
                'month': month_start.strftime('%Y-%m'),
                'new_employees': count
            })
        
        growth_stats.reverse()  # Chronological order
        
        response_data = {
            'total_employees': total_employees,
            'total_inactive': total_inactive,
            'recent_hires': recent_hires,
            'departments': department_stats,
            'locations': location_counts,
            'growth': growth_stats,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info("Generated employee statistics")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

# Audit log endpoints
@app.route('/api/employees/<int:employee_id>/audit', methods=['GET'])
@jwt_required()
def get_employee_audit_log(employee_id: int):
    """
    Get audit log for a specific employee
    
    Args:
        employee_id: Employee ID
        
    Returns:
        JSON response with audit log entries
    """
    try:
        # Check if employee exists
        employee = Employee.query.get(employee_id)
        if not employee:
            raise NotFound(f"Employee with ID {employee_id} not found")
        
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('per_page', 20))))
        
        # Query audit logs
        query = AuditLog.query.filter(
            AuditLog.employee_id == employee_id
        ).order_by(desc(AuditLog.timestamp))
        
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        audit_logs = [log.to_dict() for log in pagination.items]
        
        response_data = {
            'employee_id': employee_id,
            'employee_name': employee.name,
            'audit_logs': audit_logs,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }
        
        logger.info(f"Retrieved audit log for employee {employee_id}")
        return jsonify(response_data), 200
        
    except NotFound:
        return jsonify({'error': f'Employee with ID {employee_id} not found'}), 404
    except ValueError as e:
        logger.error(f"Invalid parameter in get_employee_audit_log: {e}")
        return jsonify({'error': 'Invalid parameter value'}), 400
    except Exception as e:
        logger.error(f"Error fetching audit log for employee {employee_id}: {e}")
        return jsonify({'error': 'Failed to fetch audit log'}), 500

# Search endpoint
@app.route('/api/search', methods=['GET'])
def search_employees():
    """
    Advanced search endpoint with multiple filters
    
    Query Parameters:
        q: Search query
        department: Department filter
        location: Location filter
        position: Position filter
        manager: Manager filter
        is_active: Active status filter
        hire_date_from: Hire date range start
        hire_date_to: Hire date range end
        
    Returns:
        JSON response with search results
    """
    try:
        # Get search parameters
        query_text = request.args.get('q', '').strip()
        department = request.args.get('department', '').strip()
        location = request.args.get('location', '').strip()
        position = request.args.get('position', '').strip()
        manager = request.args.get('manager', '').strip()
        is_active = request.args.get('is_active', 'true').lower() == 'true'
        hire_date_from = request.args.get('hire_date_from')
        hire_date_to = request.args.get('hire_date_to')
        
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('per_page', 50))))
        
        # Build query
        query = Employee.query.filter(Employee.is_active == is_active)
        
        # Apply text search
        if query_text:
            search_filter = f"%{query_text}%"
            query = query.filter(
                db.or_(
                    Employee.name.ilike(search_filter),
                    Employee.email.ilike(search_filter),
                    Employee.position.ilike(search_filter)
                )
            )
        
        # Apply filters
        if department:
            query = query.filter(Employee.department == department)
        
        if location:
            query = query.filter(Employee.location.ilike(f"%{location}%"))
        
        if position:
            query = query.filter(Employee.position.ilike(f"%{position}%"))
        
        if manager:
            query = query.filter(Employee.manager.ilike(f"%{manager}%"))
        
        # Apply date range filters
        if hire_date_from:
            try:
                date_from = datetime.strptime(hire_date_from, '%Y-%m-%d').date()
                query = query.filter(Employee.hire_date >= date_from)
            except ValueError:
                return jsonify({'error': 'hire_date_from must be in YYYY-MM-DD format'}), 400
        
        if hire_date_to:
            try:
                date_to = datetime.strptime(hire_date_to, '%Y-%m-%d').date()
                query = query.filter(Employee.hire_date <= date_to)
            except ValueError:
                return jsonify({'error': 'hire_date_to must be in YYYY-MM-DD format'}), 400
        
        # Apply pagination
        pagination = query.order_by(Employee.name).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        employees = [emp.to_summary_dict() for emp in pagination.items]
        
        response_data = {
            'employees': employees,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'search_params': {
                'query': query_text,
                'department': department,
                'location': location,
                'position': position,
                'manager': manager,
                'is_active': is_active,
                'hire_date_from': hire_date_from,
                'hire_date_to': hire_date_to
            }
        }
        
        logger.info(f"Search returned {len(employees)} results")
        return jsonify(response_data), 200
        
    except ValueError as e:
        logger.error(f"Invalid parameter in search_employees: {e}")
        return jsonify({'error': 'Invalid parameter value'}), 400
    except Exception as e:
        logger.error(f"Error in employee search: {e}")
        return jsonify({'error': 'Search failed'}), 500