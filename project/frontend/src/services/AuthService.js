/**
 * Authentication Service - Handles user authentication and token management
 */

export class AuthService {
  constructor(baseURL) {
    this.baseURL = baseURL;
    this.tokenKey = 'employee_directory_token';
    this.userKey = 'employee_directory_user';
  }

  /**
   * Login user with credentials
   */
  async login(credentials) {
    const response = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(credentials)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.message || 'Login failed';
      throw new Error(message);
    }

    const data = await response.json();
    
    // Store token and user info
    this.setToken(data.access_token);
    this.setUser(data.user);
    
    return data;
  }

  /**
   * Logout user
   */
  logout() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  }

  /**
   * Get stored token
   */
  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  /**
   * Set token in storage
   */
  setToken(token) {
    localStorage.setItem(this.tokenKey, token);
  }

  /**
   * Get stored user info
   */
  getUser() {
    const user = localStorage.getItem(this.userKey);
    return user ? JSON.parse(user) : null;
  }

  /**
   * Set user info in storage
   */
  setUser(user) {
    localStorage.setItem(this.userKey, JSON.stringify(user));
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    return !!this.getToken();
  }

  /**
   * Verify token validity
   */
  async verifyToken() {
    const token = this.getToken();
    if (!token) {
      throw new Error('No token found');
    }

    const response = await fetch(`${this.baseURL}/auth/verify`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      this.logout();
      throw new Error('Token verification failed');
    }

    return response.json();
  }

  /**
   * Get authorization header
   */
  getAuthHeader() {
    const token = this.getToken();
    return token ? `Bearer ${token}` : null;
  }

  /**
   * Handle token expiration
   */
  handleTokenExpiration() {
    this.logout();
    // Redirect to login or show login modal
    window.location.reload();
  }

  /**
   * Refresh token (if refresh token functionality is implemented)
   */
  async refreshToken() {
    // This would be implemented if the backend supports refresh tokens
    throw new Error('Refresh token not implemented');
  }

  /**
   * Check if token is expired (basic check)
   */
  isTokenExpired() {
    const token = this.getToken();
    if (!token) return true;

    try {
      // Decode JWT token (basic implementation)
      const payload = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Date.now() / 1000;
      return payload.exp < currentTime;
    } catch (error) {
      return true;
    }
  }

  /**
   * Auto-refresh token before expiration
   */
  setupTokenRefresh() {
    const token = this.getToken();
    if (!token) return;

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const expirationTime = payload.exp * 1000;
      const currentTime = Date.now();
      const timeUntilExpiration = expirationTime - currentTime;
      
      // Refresh 5 minutes before expiration
      const refreshTime = timeUntilExpiration - (5 * 60 * 1000);
      
      if (refreshTime > 0) {
        setTimeout(() => {
          this.verifyToken().catch(() => {
            this.handleTokenExpiration();
          });
        }, refreshTime);
      }
    } catch (error) {
      console.error('Error setting up token refresh:', error);
    }
  }
}