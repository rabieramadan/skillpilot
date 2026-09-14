// SkillPilot - Authentication and Attendance Module

class AuthManager {
    constructor() {
        this.currentUser = null;
        this.isLoggedIn = false;
        this.init();
    }

    async init() {
        await this.checkAuthStatus();
        this.setupAuthEventListeners();
        
        // Don't auto-show login modal - we now use a landing page
        // The server will redirect to landing page if not authenticated
    }

    async checkAuthStatus() {
        try {
            const response = await fetch('/api/auth/check');
            const data = await response.json();
            
            this.isLoggedIn = data.is_logged_in || false;
            if (this.isLoggedIn) {
                this.currentUser = {
                    userId: data.user_id,
                    username: data.username,
                    fullName: data.full_name
                };
                this.updateUIForLoggedInUser();
            }
        } catch (error) {
            console.error('Error checking auth status:', error);
        }
    }

    setupAuthEventListeners() {
        // Auth tab switching
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
                e.target.classList.add('active');
                
                const authType = e.target.dataset.auth;
                document.getElementById('loginForm').style.display = authType === 'login' ? 'block' : 'none';
                document.getElementById('registerForm').style.display = authType === 'register' ? 'block' : 'none';
            });
        });

        // Login
        document.getElementById('loginSubmitBtn').addEventListener('click', () => this.handleLogin());
        document.getElementById('loginPassword').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleLogin();
        });

        // Registration
        document.getElementById('registerSubmitBtn').addEventListener('click', () => this.handleRegister());

        // Continue to login after registration
        document.getElementById('continueLoginBtn').addEventListener('click', () => {
            document.getElementById('regSuccessModal').classList.remove('show');
            document.getElementById('loginModal').classList.add('show');
        });

        // User logout
        const userLogoutBtn = document.getElementById('userLogoutBtn');
        if (userLogoutBtn) {
            userLogoutBtn.addEventListener('click', () => this.handleLogout());
        }

        // User info button - opens profile tab for password change
        const userInfoBtn = document.getElementById('userInfoBtn');
        if (userInfoBtn) {
            userInfoBtn.addEventListener('click', () => this.showProfileTab());
        }

        // Admin logout (top bar)
        const adminLogoutBtn = document.getElementById('adminLogoutBtn');
        if (adminLogoutBtn) {
            adminLogoutBtn.addEventListener('click', () => this.handleAdminLogout());
        }

        // Universal logout (menu) - handles all user types
        const menuUniversalLogoutBtn = document.getElementById('menuUniversalLogoutBtn');
        if (menuUniversalLogoutBtn) {
            menuUniversalLogoutBtn.addEventListener('click', () => this.handleUniversalLogout());
        }

        // Attendance
        const attendanceBtn = document.getElementById('recordAttendanceBtn');
        if (attendanceBtn) {
            attendanceBtn.addEventListener('click', () => this.showAttendanceModal());
        }

        const submitAttendanceBtn = document.getElementById('submitAttendanceBtn');
        if (submitAttendanceBtn) {
            submitAttendanceBtn.addEventListener('click', () => this.recordAttendance());
        }

        // Forgot Password
        const forgotPasswordLink = document.getElementById('forgotPasswordLink');
        if (forgotPasswordLink) {
            forgotPasswordLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.showForgotPasswordForm();
            });
        }

        const backToLoginLink = document.getElementById('backToLoginLink');
        if (backToLoginLink) {
            backToLoginLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.showLoginForm();
            });
        }

        const forgotPasswordCheckBtn = document.getElementById('forgotPasswordCheckBtn');
        if (forgotPasswordCheckBtn) {
            forgotPasswordCheckBtn.addEventListener('click', () => this.handleForgotPasswordCheck());
        }

        const forgotPasswordResetBtn = document.getElementById('forgotPasswordResetBtn');
        if (forgotPasswordResetBtn) {
            forgotPasswordResetBtn.addEventListener('click', () => this.handleForgotPasswordReset());
        }
    }

    async handleLogin() {
        const username = document.getElementById('loginUsername').value.trim();
        const password = document.getElementById('loginPassword').value;

        if (!username || !password) {
            alert('Please enter username and password');
            return;
        }

        try {
            const response = await fetch('/api/auth/user/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                this.isLoggedIn = true;
                this.currentUser = {
                    userId: data.user.user_id,
                    username: data.user.username,
                    fullName: data.user.full_name
                };
                
                document.getElementById('loginModal').classList.remove('show');
                this.updateUIForLoggedInUser();
                this.showNotification('Login successful! Welcome back.', 'success');
                
                // Update admin UI state after user login (ensure admin tabs stay hidden for non-admin users)
                if (window.app && typeof window.app.checkAdminStatus === 'function') {
                    await window.app.checkAdminStatus();
                    window.app.updateAdminUI();
                }
                
                // Clear password
                document.getElementById('loginPassword').value = '';
            } else {
                alert(data.error || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('Login failed. Please try again.');
        }
    }

    async handleRegister() {
        const fullName = document.getElementById('regFullName').value.trim();
        const email = document.getElementById('regEmail').value.trim();
        const username = document.getElementById('regUsername').value.trim();
        const password = document.getElementById('regPassword').value;
        const phone = document.getElementById('regPhone').value.trim();
        const organization = document.getElementById('regOrganization').value.trim();
        const securityQ1 = document.getElementById('regSecurityQ1').value.trim();
        const securityQ2 = document.getElementById('regSecurityQ2').value.trim();
        const securityQ3 = document.getElementById('regSecurityQ3').value.trim();

        // Validation
        if (!fullName || !email || !username || !password) {
            alert('Full name, email, username, and password are required');
            return;
        }

        if (password.length < 6) {
            alert('Password must be at least 6 characters long');
            return;
        }

        if (!securityQ1 || !securityQ2 || !securityQ3) {
            alert('All three security questions are required');
            return;
        }

        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    full_name: fullName, 
                    email, 
                    username,
                    password,
                    phone, 
                    organization,
                    security_q1: securityQ1,
                    security_q2: securityQ2,
                    security_q3: securityQ3
                })
            });

            const data = await response.json();

            if (response.ok) {
                // Show username confirmation
                document.getElementById('confirmedUsername').textContent = data.username || username;
                
                // Clear form
                document.getElementById('regFullName').value = '';
                document.getElementById('regEmail').value = '';
                document.getElementById('regUsername').value = '';
                document.getElementById('regPassword').value = '';
                document.getElementById('regPhone').value = '';
                document.getElementById('regOrganization').value = '';
                document.getElementById('regSecurityQ1').value = '';
                document.getElementById('regSecurityQ2').value = '';
                document.getElementById('regSecurityQ3').value = '';
                
                // Show success modal
                document.getElementById('loginModal').classList.remove('show');
                document.getElementById('regSuccessModal').classList.add('show');
            } else {
                alert(data.error || 'Registration failed');
            }
        } catch (error) {
            console.error('Registration error:', error);
            alert('Registration failed. Please try again.');
        }
    }

    async handleLogout() {
        try {
            // Use APP_BASE_URL for proper reverse proxy support (set by index.html)
            const baseUrl = window.APP_BASE_URL || window.BASE_URL || '';
            await fetch('/api/auth/user/logout', { method: 'POST' });
            this.isLoggedIn = false;
            this.currentUser = null;
            this.updateUIForLoggedOutUser();
            
            // Redirect to SkillPilot landing page
            window.location.href = baseUrl + '/skillpilot-landing';
        } catch (error) {
            console.error('Logout error:', error);
            // Still redirect on error
            const baseUrl = window.APP_BASE_URL || window.BASE_URL || '';
            window.location.href = baseUrl + '/skillpilot-landing';
        }
    }

    async handleAdminLogout() {
        try {
            // Use APP_BASE_URL for proper reverse proxy support (set by index.html)
            const baseUrl = window.APP_BASE_URL || window.BASE_URL || '';
            await fetch('/api/auth/logout', { method: 'POST' });
            this.showNotification('Admin logged out successfully', 'success');
            
            // Redirect to admin login page
            window.location.href = baseUrl + '/admin/login';
        } catch (error) {
            console.error('Admin logout error:', error);
            const baseUrl = window.APP_BASE_URL || window.BASE_URL || '';
            window.location.href = baseUrl + '/admin/login';
        }
    }

    async handleUniversalLogout() {
        // Universal logout that works for all user types
        const baseUrl = window.APP_BASE_URL || window.BASE_URL || '';
        try {
            // Try both logout endpoints to ensure complete logout
            await fetch('/api/auth/logout', { method: 'POST' });
            await fetch('/api/auth/user/logout', { method: 'POST' });
            
            this.isLoggedIn = false;
            this.currentUser = null;
            
            // Redirect to SkillPilot landing page
            window.location.href = baseUrl + '/skillpilot-landing';
        } catch (error) {
            console.error('Logout error:', error);
            // Still redirect even if error
            window.location.href = baseUrl + '/skillpilot-landing';
        }
    }

    updateUIForLoggedInUser() {
        // Show user info
        document.getElementById('userDisplayName').textContent = this.currentUser.fullName;
        document.getElementById('userInfoBtn').style.display = '';
        document.getElementById('recordAttendanceBtn').style.display = '';
        document.getElementById('userLogoutBtn').style.display = '';
    }

    updateUIForLoggedOutUser() {
        document.getElementById('userInfoBtn').style.display = 'none';
        document.getElementById('recordAttendanceBtn').style.display = 'none';
        document.getElementById('userLogoutBtn').style.display = 'none';
    }

    async showAttendanceModal() {
        document.getElementById('attendanceModal').classList.add('show');
        await this.loadAttendanceHistory();
    }

    async recordAttendance() {
        const notes = document.getElementById('attendanceNotes').value.trim();

        try {
            const response = await fetch('/api/auth/attendance/record', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notes })
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification('Attendance recorded successfully!', 'success');
                document.getElementById('attendanceNotes').value = '';
                await this.loadAttendanceHistory();
            } else {
                alert(data.error || 'Failed to record attendance');
            }
        } catch (error) {
            console.error('Attendance error:', error);
            alert('Failed to record attendance');
        }
    }

    async loadAttendanceHistory() {
        try {
            const response = await fetch('/api/auth/attendance/user');
            const data = await response.json();

            const list = document.getElementById('attendanceList');
            if (data.records && data.records.length > 0) {
                list.innerHTML = data.records.map(r => `
                    <div class="attendance-record">
                        <div class="record-date">
                            <i class="fas fa-calendar"></i> ${new Date(r.timestamp).toLocaleString()}
                        </div>
                        ${r.notes ? `<div class="record-notes">${r.notes}</div>` : ''}
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<p>No attendance records yet.</p>';
            }
        } catch (error) {
            console.error('Error loading attendance:', error);
        }
    }

    showNotification(message, type) {
        // Use existing notification system if available
        if (window.app && typeof window.app.showNotification === 'function') {
            window.app.showNotification(message, type);
        } else {
            alert(message);
        }
    }

    showProfileTab() {
        // Navigate to profile tab where user can change password
        if (window.app && typeof window.app.showTab === 'function') {
            window.app.showTab('profile');
            // Load profile data
            if (window.profileManager && typeof window.profileManager.loadProfile === 'function') {
                window.profileManager.loadProfile();
            }
        } else {
            // Fallback: directly show profile tab
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            const profileTab = document.getElementById('profile-tab');
            if (profileTab) {
                profileTab.classList.add('active');
                // Load profile data
                if (window.profileManager && typeof window.profileManager.loadProfile === 'function') {
                    window.profileManager.loadProfile();
                }
            }
        }
    }

    showForgotPasswordForm() {
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const forgotPasswordForm = document.getElementById('forgotPasswordForm');
        
        if (loginForm) loginForm.style.display = 'none';
        if (registerForm) registerForm.style.display = 'none';
        if (forgotPasswordForm) forgotPasswordForm.style.display = 'block';
        
        // Reset the form
        const usernameInput = document.getElementById('forgotUsername');
        if (usernameInput) usernameInput.value = '';
        
        const securitySection = document.getElementById('securityQuestionsSection');
        if (securitySection) securitySection.style.display = 'none';
        
        const checkBtn = document.getElementById('forgotPasswordCheckBtn');
        const resetBtn = document.getElementById('forgotPasswordResetBtn');
        if (checkBtn) checkBtn.style.display = 'block';
        if (resetBtn) resetBtn.style.display = 'none';
    }

    showLoginForm() {
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const forgotPasswordForm = document.getElementById('forgotPasswordForm');
        
        if (loginForm) loginForm.style.display = 'block';
        if (registerForm) registerForm.style.display = 'none';
        if (forgotPasswordForm) forgotPasswordForm.style.display = 'none';
        
        // Reset auth tabs
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.classList.remove('active');
            if (tab.dataset.auth === 'login') {
                tab.classList.add('active');
            }
        });
    }

    async handleForgotPasswordCheck() {
        const username = document.getElementById('forgotUsername').value.trim();
        
        if (!username) {
            alert('Please enter your username');
            return;
        }

        try {
            const response = await fetch('/api/auth/forgot-password/check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username })
            });

            const data = await response.json();

            if (response.ok && data.user_found) {
                if (data.source === 'json' && data.has_security_questions) {
                    // User has security questions - show the form
                    const securitySection = document.getElementById('securityQuestionsSection');
                    if (securitySection) securitySection.style.display = 'block';
                    
                    const checkBtn = document.getElementById('forgotPasswordCheckBtn');
                    const resetBtn = document.getElementById('forgotPasswordResetBtn');
                    if (checkBtn) checkBtn.style.display = 'none';
                    if (resetBtn) resetBtn.style.display = 'block';
                    
                    this.showNotification('Please answer your security questions to reset your password.', 'info');
                } else if (data.source === 'database') {
                    // Database user - needs admin reset
                    alert('Your account requires an administrator to reset your password. Please contact support.');
                } else {
                    alert('Password reset not available for this account. Please contact support.');
                }
            } else {
                alert(data.error || 'User not found. Please check your username.');
            }
        } catch (error) {
            console.error('Forgot password check error:', error);
            alert('Failed to check account. Please try again.');
        }
    }

    async handleForgotPasswordReset() {
        const username = document.getElementById('forgotUsername').value.trim();
        const securityQ1 = document.getElementById('forgotSecurityQ1').value.trim();
        const securityQ2 = document.getElementById('forgotSecurityQ2').value.trim();
        const securityQ3 = document.getElementById('forgotSecurityQ3').value.trim();
        const newPassword = document.getElementById('forgotNewPassword').value;

        if (!username) {
            alert('Username is required');
            return;
        }

        if (!securityQ1 || !securityQ2 || !securityQ3) {
            alert('Please answer all security questions');
            return;
        }

        if (!newPassword || newPassword.length < 6) {
            alert('New password must be at least 6 characters');
            return;
        }

        try {
            const response = await fetch('/api/auth/forgot-password/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username,
                    security_q1: securityQ1,
                    security_q2: securityQ2,
                    security_q3: securityQ3,
                    new_password: newPassword
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification('Password reset successful! You can now login with your new password.', 'success');
                
                // Clear the form
                document.getElementById('forgotUsername').value = '';
                document.getElementById('forgotSecurityQ1').value = '';
                document.getElementById('forgotSecurityQ2').value = '';
                document.getElementById('forgotSecurityQ3').value = '';
                document.getElementById('forgotNewPassword').value = '';
                
                // Go back to login form
                this.showLoginForm();
            } else {
                alert(data.error || 'Password reset failed. Please check your answers.');
            }
        } catch (error) {
            console.error('Password reset error:', error);
            alert('Failed to reset password. Please try again.');
        }
    }
}

// Global function to fill demo credentials
function fillDemoCredentials(username, password) {
    const usernameField = document.getElementById('loginUsername');
    const passwordField = document.getElementById('loginPassword');
    
    if (usernameField && passwordField) {
        usernameField.value = username;
        passwordField.value = password;
        
        // Add a visual feedback
        usernameField.style.backgroundColor = '#f0fdf4';
        passwordField.style.backgroundColor = '#f0fdf4';
        
        setTimeout(() => {
            usernameField.style.backgroundColor = '';
            passwordField.style.backgroundColor = '';
        }, 500);
    }
}

// Make it globally available
window.fillDemoCredentials = fillDemoCredentials;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.authManager = new AuthManager();
});
