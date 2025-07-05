import React from 'react';

function Navigation({ currentView, onViewChange, user, onLogout }) {
  const navItems = [
    { id: 'employees', label: 'Employees', icon: '👥' },
    { id: 'statistics', label: 'Statistics', icon: '📊' }
  ];

  return (
    <nav className="navigation">
      <div className="nav-brand">
        <h2>Employee Directory</h2>
      </div>
      
      <div className="nav-items">
        {navItems.map(item => (
          <button
            key={item.id}
            className={`nav-item ${currentView === item.id ? 'active' : ''}`}
            onClick={() => onViewChange(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        ))}
      </div>
      
      <div className="nav-user">
        <span className="user-info">
          <span className="user-icon">👤</span>
          <span className="user-name">{user}</span>
        </span>
        <button className="logout-btn" onClick={onLogout}>
          Logout
        </button>
      </div>
    </nav>
  );
}

export default Navigation;