import React, { useState, useEffect } from 'react';
import { EmployeeService } from '../services/EmployeeService';

function Statistics() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const employeeService = new EmployeeService(process.env.REACT_APP_API_URL || '/api');

  useEffect(() => {
    fetchStatistics();
  }, []);

  const fetchStatistics = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await employeeService.getStatistics();
      setStats(data);
    } catch (err) {
      console.error('Error fetching statistics:', err);
      setError('Failed to load statistics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading statistics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <p>{error}</p>
        <button onClick={fetchStatistics} className="btn btn-primary">
          Retry
        </button>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const departmentEntries = Object.entries(stats.departments || {});
  const locationEntries = Object.entries(stats.locations || {});

  return (
    <div className="statistics-container">
      <div className="stats-header">
        <h2>Employee Statistics</h2>
        <p>Overview of employee data and trends</p>
      </div>

      {/* Summary Cards */}
      <div className="stats-grid">
        <div className="stat-card primary">
          <div className="stat-icon">👥</div>
          <div className="stat-content">
            <h3>{stats.total_employees}</h3>
            <p>Total Active Employees</p>
          </div>
        </div>

        <div className="stat-card secondary">
          <div className="stat-icon">🏢</div>
          <div className="stat-content">
            <h3>{departmentEntries.length}</h3>
            <p>Departments</p>
          </div>
        </div>

        <div className="stat-card success">
          <div className="stat-icon">📈</div>
          <div className="stat-content">
            <h3>{stats.recent_hires}</h3>
            <p>Recent Hires (30 days)</p>
          </div>
        </div>

        <div className="stat-card warning">
          <div className="stat-icon">📍</div>
          <div className="stat-content">
            <h3>{locationEntries.length}</h3>
            <p>Office Locations</p>
          </div>
        </div>
      </div>

      {/* Department Breakdown */}
      <div className="stats-section">
        <h3>Employees by Department</h3>
        <div className="chart-container">
          {departmentEntries.length > 0 ? (
            <div className="bar-chart">
              {departmentEntries
                .sort((a, b) => b[1] - a[1])
                .map(([department, count]) => {
                  const percentage = (count / stats.total_employees) * 100;
                  return (
                    <div key={department} className="bar-item">
                      <div className="bar-label">
                        <span className="department-name">{department}</span>
                        <span className="department-count">{count}</span>
                      </div>
                      <div className="bar-container">
                        <div 
                          className="bar-fill" 
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                      <div className="bar-percentage">{percentage.toFixed(1)}%</div>
                    </div>
                  );
                })}
            </div>
          ) : (
            <p className="no-data">No department data available</p>
          )}
        </div>
      </div>

      {/* Location Breakdown */}
      {locationEntries.length > 0 && (
        <div className="stats-section">
          <h3>Employees by Location</h3>
          <div className="chart-container">
            <div className="location-grid">
              {locationEntries
                .sort((a, b) => b[1] - a[1])
                .map(([location, count]) => (
                  <div key={location} className="location-card">
                    <div className="location-icon">📍</div>
                    <div className="location-info">
                      <h4>{location}</h4>
                      <p>{count} employee{count !== 1 ? 's' : ''}</p>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Growth Trend */}
      {stats.growth && stats.growth.length > 0 && (
        <div className="stats-section">
          <h3>Employee Growth Trend</h3>
          <div className="chart-container">
            <div className="line-chart">
              {stats.growth.map((item, index) => (
                <div key={item.month} className="growth-item">
                  <div className="growth-bar">
                    <div 
                      className="growth-fill" 
                      style={{ 
                        height: `${Math.max(10, (item.new_employees / Math.max(...stats.growth.map(g => g.new_employees))) * 100)}%` 
                      }}
                    ></div>
                  </div>
                  <div className="growth-label">
                    <div className="growth-month">{item.month}</div>
                    <div className="growth-count">{item.new_employees}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Refresh Info */}
      <div className="stats-footer">
        <p>
          Last updated: {new Date(stats.generated_at).toLocaleString()}
        </p>
        <button onClick={fetchStatistics} className="btn btn-secondary">
          Refresh Data
        </button>
      </div>
    </div>
  );
}

export default Statistics;