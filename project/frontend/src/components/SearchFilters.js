import React, { useState } from 'react';

function SearchFilters({ filters, departments, onFiltersChange, onAddEmployee }) {
  const [localFilters, setLocalFilters] = useState(filters);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : value;
    
    setLocalFilters(prev => ({
      ...prev,
      [name]: newValue
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onFiltersChange(localFilters);
  };

  const handleReset = () => {
    const resetFilters = {
      search: '',
      department: '',
      location: '',
      isActive: true
    };
    setLocalFilters(resetFilters);
    onFiltersChange(resetFilters);
  };

  return (
    <div className="search-section">
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-row">
          <div className="form-group">
            <label htmlFor="search">Search</label>
            <input
              type="text"
              id="search"
              name="search"
              value={localFilters.search}
              onChange={handleInputChange}
              placeholder="Search by name, email, or position..."
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="department">Department</label>
            <select
              id="department"
              name="department"
              value={localFilters.department}
              onChange={handleInputChange}
            >
              <option value="">All Departments</option>
              {departments.map(dept => (
                <option key={dept.name} value={dept.name}>
                  {dept.name} ({dept.employee_count})
                </option>
              ))}
            </select>
          </div>
          
          <div className="form-group">
            <label htmlFor="location">Location</label>
            <input
              type="text"
              id="location"
              name="location"
              value={localFilters.location}
              onChange={handleInputChange}
              placeholder="Filter by location..."
            />
          </div>
        </div>
        
        <div className="search-row">
          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                name="isActive"
                checked={localFilters.isActive}
                onChange={handleInputChange}
              />
              <span className="checkbox-text">Show active employees only</span>
            </label>
          </div>
          
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              Search
            </button>
            <button type="button" onClick={handleReset} className="btn btn-secondary">
              Reset
            </button>
            <button type="button" onClick={onAddEmployee} className="btn btn-success">
              Add Employee
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

export default SearchFilters;