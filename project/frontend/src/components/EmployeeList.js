import React from 'react';
import Pagination from './Pagination';

function EmployeeList({ employees, loading, pagination, onEdit, onDelete, onPageChange }) {
  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading employees...</p>
      </div>
    );
  }

  if (employees.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">👥</div>
        <h3>No employees found</h3>
        <p>Try adjusting your search criteria or add a new employee.</p>
      </div>
    );
  }

  const getInitials = (name) => {
    return name
      .split(' ')
      .map(word => word.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getStatusBadge = (isActive) => {
    return (
      <span className={`status-badge ${isActive ? 'active' : 'inactive'}`}>
        {isActive ? 'Active' : 'Inactive'}
      </span>
    );
  };

  return (
    <div className="employee-list-container">
      <div className="list-header">
        <h2>Employees ({pagination.total})</h2>
        <div className="list-info">
          Showing {employees.length} of {pagination.total} employees
        </div>
      </div>

      <div className="employees-grid">
        {employees.map(employee => (
          <div key={employee.id} className="employee-card">
            <div className="employee-header">
              <div className="employee-avatar">
                {getInitials(employee.name)}
              </div>
              <div className="employee-info">
                <h3>{employee.name}</h3>
                <div className="employee-meta">
                  <span className="department">{employee.department}</span>
                  {getStatusBadge(employee.is_active)}
                </div>
              </div>
            </div>
            
            <div className="employee-details">
              <div className="detail-item">
                <span className="detail-label">Email:</span>
                <span className="detail-value">
                  <a href={`mailto:${employee.email}`}>{employee.email}</a>
                </span>
              </div>
              
              {employee.phone && (
                <div className="detail-item">
                  <span className="detail-label">Phone:</span>
                  <span className="detail-value">
                    <a href={`tel:${employee.phone}`}>{employee.phone}</a>
                  </span>
                </div>
              )}
              
              {employee.position && (
                <div className="detail-item">
                  <span className="detail-label">Position:</span>
                  <span className="detail-value">{employee.position}</span>
                </div>
              )}
              
              {employee.location && (
                <div className="detail-item">
                  <span className="detail-label">Location:</span>
                  <span className="detail-value">{employee.location}</span>
                </div>
              )}
            </div>
            
            <div className="employee-actions">
              <button 
                onClick={() => onEdit(employee)}
                className="btn btn-primary btn-sm"
                title="Edit employee"
              >
                Edit
              </button>
              <button 
                onClick={() => onDelete(employee.id)}
                className="btn btn-danger btn-sm"
                title="Delete employee"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {pagination.pages > 1 && (
        <Pagination
          currentPage={pagination.page}
          totalPages={pagination.pages}
          onPageChange={onPageChange}
        />
      )}
    </div>
  );
}

export default EmployeeList;