/**
 * Employee Service - Handles all employee-related API calls
 */

import { AuthService } from './AuthService';

export class EmployeeService {
  constructor(baseURL) {
    this.baseURL = baseURL;
    this.authService = new AuthService(baseURL);
  }

  /**
   * Get authorization headers
   */
  getAuthHeaders() {
    const token = this.authService.getToken();
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` })
    };
  }

  /**
   * Handle API response
   */
  async handleResponse(response) {
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.message || errorData.error || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
    }
    return response.json();
  }

  /**
   * Build URL with query parameters
   */
  buildURL(endpoint, params = {}) {
    const url = new URL(`${this.baseURL}${endpoint}`);
    Object.keys(params).forEach(key => {
      if (params[key] !== undefined && params[key] !== null && params[key] !== '') {
        url.searchParams.append(key, params[key]);
      }
    });
    return url.toString();
  }

  /**
   * Get all employees with optional filters
   */
  async getEmployees(params = {}) {
    const url = this.buildURL('/employees', params);
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get a specific employee by ID
   */
  async getEmployee(id) {
    const response = await fetch(`${this.baseURL}/employees/${id}`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Create a new employee
   */
  async createEmployee(employeeData) {
    const response = await fetch(`${this.baseURL}/employees`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(employeeData)
    });
    return this.handleResponse(response);
  }

  /**
   * Update an existing employee
   */
  async updateEmployee(id, employeeData) {
    const response = await fetch(`${this.baseURL}/employees/${id}`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(employeeData)
    });
    return this.handleResponse(response);
  }

  /**
   * Delete an employee
   */
  async deleteEmployee(id) {
    const response = await fetch(`${this.baseURL}/employees/${id}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get all departments
   */
  async getDepartments() {
    const response = await fetch(`${this.baseURL}/departments`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get employees in a specific department
   */
  async getDepartmentEmployees(departmentName, params = {}) {
    const url = this.buildURL(`/departments/${encodeURIComponent(departmentName)}/employees`, params);
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get employee statistics
   */
  async getStatistics() {
    const response = await fetch(`${this.baseURL}/stats`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Advanced search for employees
   */
  async searchEmployees(searchParams = {}) {
    const url = this.buildURL('/search', searchParams);
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Get audit log for an employee
   */
  async getEmployeeAuditLog(id, params = {}) {
    const url = this.buildURL(`/employees/${id}/audit`, params);
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    return this.handleResponse(response);
  }

  /**
   * Export employees data (if implemented)
   */
  async exportEmployees(format = 'csv', filters = {}) {
    const params = { ...filters, format };
    const url = this.buildURL('/employees/export', params);
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    
    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }
    
    return response.blob();
  }

  /**
   * Bulk update employees (if implemented)
   */
  async bulkUpdateEmployees(updates) {
    const response = await fetch(`${this.baseURL}/employees/bulk`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ updates })
    });
    return this.handleResponse(response);
  }

  /**
   * Get employee suggestions for autocomplete
   */
  async getEmployeeSuggestions(query, limit = 10) {
    const params = { q: query, limit, fields: 'name,email,department' };
    const url = this.buildURL('/employees/suggestions', params);
    const response = await fetch(url, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    return this.handleResponse(response);
  }
}