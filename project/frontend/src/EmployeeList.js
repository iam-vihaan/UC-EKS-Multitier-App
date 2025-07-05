import React from 'react';

function EmployeeList({ employees, loading, onEdit, onDelete }) {
  if (loading) {
    return <div className="loading">Loading employees...</div>;
  }

  if (employees.length === 0) {
    return (
      <div className="empty-state">
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

  return (
    <div className="employees-grid">
      {employees.map(employee => (
        <div key={employee.id} className="employee-card">
          <div className="employee-header">
            <div className="employee-avatar">
              {getInitials(employee.name)}
            </div>
            <div className="employee-info">
              <h3>{employee.name}</h3>
              <div className="department">{employee.department}</div>
            </div>
          </div>
          
          <div className="employee-details">
            <p><strong>Email:</strong> {employee.email}</p>
            <p><strong>Phone:</strong> {employee.phone || 'Not provided'}</p>
            <p><strong>Position:</strong> {employee.position || 'Not specified'}</p>
            <p><strong>Location:</strong> {employee.location || 'Not specified'}</p>
            {employee.manager && (
              <p><strong>Manager:</strong> {employee.manager}</p>
            )}
          </div>
          
          <div className="employee-actions">
            <button 
              onClick={() => onEdit(employee)}
              className="btn btn-primary"
              style={{ fontSize: '14px', padding: '8px 16px' }}
            >
              Edit
            </button>
            <button 
              onClick={() => onDelete(employee.id)}
              className="btn btn-secondary"
              style={{ 
                fontSize: '14px', 
                padding: '8px 16px',
                background: '#fed7d7',
                color: '#c53030',
                border: '2px solid #feb2b2'
              }}
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default EmployeeList;