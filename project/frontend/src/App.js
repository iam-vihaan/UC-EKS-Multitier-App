import React, { useState, useEffect } from 'react';
import EmployeeList from './components/EmployeeList';
import EmployeeForm from './components/EmployeeForm';
import SearchFilters from './components/SearchFilters';
import Statistics from './components/Statistics';
import Navigation from './components/Navigation';
import Login from './components/Login';
import { EmployeeService } from './services/EmployeeService';
import { AuthService } from './services/AuthService';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

function App() {
  // State management
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // UI state
  const [currentView, setCurrentView] = useState('employees');
  const [showForm, setShowForm] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState(null);
  
  // Search and filter state
  const [searchFilters, setSearchFilters] = useState({
    search: '',
    department: '',
    location: '',
    isActive: true
  });
  
  // Pagination state
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 20,
    total: 0,
    pages: 0
  });
  
  // Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  // Initialize services
  const employeeService = new EmployeeService(API_BASE_URL);
  const authService = new AuthService(API_BASE_URL);

  // Check authentication on app load
  useEffect(() => {
    const token = authService.getToken();
    if (token) {
      authService.verifyToken()
        .then(response => {
          setIsAuthenticated(true);
          setUser(response.user);
        })
        .catch(() => {
          authService.logout();
          setIsAuthenticated(false);
        });
    }
  }, []);

  // Fetch data when authenticated or filters change
  useEffect(() => {
    if (isAuthenticated) {
      fetchEmployees();
      fetchDepartments();
    }
  }, [isAuthenticated, searchFilters, pagination.page]);

  // Utility functions
  const showMessage = (message, type = 'success') => {
    if (type === 'success') {
      setSuccess(message);
      setError('');
    } else {
      setError(message);
      setSuccess('');
    }
    
    // Clear message after 5 seconds
    setTimeout(() => {
      setSuccess('');
      setError('');
    }, 5000);
  };

  const clearMessages = () => {
    setError('');
    setSuccess('');
  };

  // API functions
  const fetchEmployees = async () => {
    try {
      setLoading(true);
      clearMessages();
      
      const params = {
        ...searchFilters,
        page: pagination.page,
        per_page: pagination.perPage
      };
      
      const response = await employeeService.getEmployees(params);
      
      setEmployees(response.employees);
      setPagination(prev => ({
        ...prev,
        total: response.pagination.total,
        pages: response.pagination.pages
      }));
      
    } catch (err) {
      console.error('Error fetching employees:', err);
      showMessage('Failed to fetch employees. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchDepartments = async () => {
    try {
      const departments = await employeeService.getDepartments();
      setDepartments(departments);
    } catch (err) {
      console.error('Error fetching departments:', err);
    }
  };

  // Authentication handlers
  const handleLogin = async (credentials) => {
    try {
      const response = await authService.login(credentials);
      setIsAuthenticated(true);
      setUser(response.user);
      showMessage('Login successful!');
    } catch (err) {
      throw new Error(err.message || 'Login failed');
    }
  };

  const handleLogout = () => {
    authService.logout();
    setIsAuthenticated(false);
    setUser(null);
    setCurrentView('employees');
    showMessage('Logged out successfully');
  };

  // Employee management handlers
  const handleAddEmployee = () => {
    setEditingEmployee(null);
    setShowForm(true);
    clearMessages();
  };

  const handleEditEmployee = (employee) => {
    setEditingEmployee(employee);
    setShowForm(true);
    clearMessages();
  };

  const handleDeleteEmployee = async (employeeId) => {
    if (!window.confirm('Are you sure you want to delete this employee?')) {
      return;
    }

    try {
      await employeeService.deleteEmployee(employeeId);
      showMessage('Employee deleted successfully');
      await fetchEmployees();
    } catch (err) {
      console.error('Error deleting employee:', err);
      showMessage('Failed to delete employee. Please try again.', 'error');
    }
  };

  const handleFormSubmit = async (employeeData) => {
    try {
      if (editingEmployee) {
        await employeeService.updateEmployee(editingEmployee.id, employeeData);
        showMessage('Employee updated successfully');
      } else {
        await employeeService.createEmployee(employeeData);
        showMessage('Employee created successfully');
      }
      
      setShowForm(false);
      setEditingEmployee(null);
      await fetchEmployees();
    } catch (err) {
      throw new Error(err.message || 'Failed to save employee');
    }
  };

  const handleFormCancel = () => {
    setShowForm(false);
    setEditingEmployee(null);
    clearMessages();
  };

  // Search and filter handlers
  const handleSearchChange = (newFilters) => {
    setSearchFilters(newFilters);
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, page: newPage }));
  };

  // Navigation handlers
  const handleViewChange = (view) => {
    setCurrentView(view);
    setShowForm(false);
    setEditingEmployee(null);
    clearMessages();
  };

  // Render login screen if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="app">
        <Login onLogin={handleLogin} error={error} />
      </div>
    );
  }

  // Main application render
  return (
    <div className="app">
      <Navigation 
        currentView={currentView}
        onViewChange={handleViewChange}
        user={user}
        onLogout={handleLogout}
      />

      <div className="container">
        <div className="header">
          <h1>Employee Directory</h1>
          <p>Internal Support Portal - Find and manage employee information</p>
        </div>

        {/* Success/Error Messages */}
        {success && (
          <div className="message success">
            <span>{success}</span>
            <button onClick={clearMessages} className="close-btn">&times;</button>
          </div>
        )}
        
        {error && (
          <div className="message error">
            <span>{error}</span>
            <button onClick={clearMessages} className="close-btn">&times;</button>
          </div>
        )}

        {/* Main Content */}
        {currentView === 'employees' && (
          <>
            <SearchFilters
              filters={searchFilters}
              departments={departments}
              onFiltersChange={handleSearchChange}
              onAddEmployee={handleAddEmployee}
            />

            <EmployeeList
              employees={employees}
              loading={loading}
              pagination={pagination}
              onEdit={handleEditEmployee}
              onDelete={handleDeleteEmployee}
              onPageChange={handlePageChange}
            />
          </>
        )}

        {currentView === 'statistics' && (
          <Statistics />
        )}

        {/* Employee Form Modal */}
        {showForm && (
          <EmployeeForm
            employee={editingEmployee}
            departments={departments}
            onSubmit={handleFormSubmit}
            onCancel={handleFormCancel}
          />
        )}
      </div>
    </div>
  );
}

export default App;