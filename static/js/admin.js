// Admin User Management
class AdminManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        // Load users when admin tab is clicked
        document.querySelector('[data-tab="admin"]')?.addEventListener('click', () => {
            this.loadUsers();
        });
    }

    setupEventListeners() {
        // Edit user form
        const editForm = document.getElementById('editUserForm');
        if (editForm) {
            editForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveUserChanges();
            });
        }

        // Reset password form
        const resetForm = document.getElementById('resetPasswordAdminForm');
        if (resetForm) {
            resetForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.resetUserPassword();
            });
        }

        // Modal close handlers
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                const modalId = btn.getAttribute('data-modal');
                document.getElementById(modalId).classList.remove('show');
            });
        });
    }

    async loadUsers() {
        try {
            const response = await fetch('/api/auth/users', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.displayUsers(data.users);
            } else {
                console.error('Failed to load users');
            }
        } catch (error) {
            console.error('Error loading users:', error);
        }
    }

    displayUsers(users) {
        const tbody = document.getElementById('usersTableBody');
        
        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No users found</td></tr>';
            return;
        }

        tbody.innerHTML = users.map(user => `
            <tr>
                <td>${this.escapeHtml(user.username)}</td>
                <td>${this.escapeHtml(user.full_name)}</td>
                <td>${this.escapeHtml(user.email)}</td>
                <td>${this.escapeHtml(user.organization || '-')}</td>
                <td><span class="badge badge-${user.role === 'Instructor' ? 'warning' : 'primary'}">${user.role || 'Student'}</span></td>
                <td>
                    <button class="btn-sm btn-primary" onclick="adminManager.editUser('${user.user_id}')" data-testid="button-edit-user-${user.user_id}">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn-sm btn-warning" onclick="adminManager.showResetPassword('${user.user_id}', '${this.escapeHtml(user.username)}')" data-testid="button-reset-password-${user.user_id}">
                        <i class="fas fa-key"></i> Reset Password
                    </button>
                </td>
            </tr>
        `).join('');
    }

    async editUser(userId) {
        try {
            const response = await fetch('/api/auth/users', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                const user = data.users.find(u => u.user_id === userId);
                
                if (user) {
                    document.getElementById('editUserId').value = user.user_id;
                    document.getElementById('editUserFullName').value = user.full_name;
                    document.getElementById('editUserEmail').value = user.email;
                    document.getElementById('editUserPhone').value = user.phone || '';
                    document.getElementById('editUserOrganization').value = user.organization || '';
                    document.getElementById('editUserRole').value = user.role || 'Student';
                    
                    document.getElementById('editUserModal').classList.add('show');
                }
            }
        } catch (error) {
            console.error('Error loading user:', error);
        }
    }

    async saveUserChanges() {
        const userId = document.getElementById('editUserId').value;
        const fullName = document.getElementById('editUserFullName').value.trim();
        const email = document.getElementById('editUserEmail').value.trim();
        const phone = document.getElementById('editUserPhone').value.trim();
        const organization = document.getElementById('editUserOrganization').value.trim();
        const role = document.getElementById('editUserRole').value;

        try {
            const response = await fetch(`/api/auth/admin/users/${userId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    full_name: fullName,
                    email: email,
                    phone: phone,
                    organization: organization,
                    role: role
                })
            });

            const data = await response.json();

            if (response.ok) {
                alert('User updated successfully!');
                document.getElementById('editUserModal').classList.remove('show');
                this.loadUsers();
            } else {
                alert(data.error || 'Failed to update user');
            }
        } catch (error) {
            console.error('Error updating user:', error);
            alert('Failed to update user. Please try again.');
        }
    }

    showResetPassword(userId, username) {
        document.getElementById('resetPasswordUserId').value = userId;
        document.getElementById('resetPasswordUsername').textContent = username;
        document.getElementById('resetPasswordResult').style.display = 'none';
        document.getElementById('adminNewPassword').value = '';
        document.getElementById('resetPasswordModal').classList.add('show');
    }

    async resetUserPassword() {
        const userId = document.getElementById('resetPasswordUserId').value;
        const newPassword = document.getElementById('adminNewPassword').value.trim();

        try {
            const response = await fetch(`/api/auth/admin/users/${userId}/reset-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    new_password: newPassword || undefined
                })
            });

            const data = await response.json();

            if (response.ok) {
                document.getElementById('newPasswordDisplay').textContent = data.new_password;
                document.getElementById('resetPasswordResult').style.display = 'block';
                alert('Password reset successfully! Make sure to copy the new password.');
            } else {
                alert(data.error || 'Failed to reset password');
            }
        } catch (error) {
            console.error('Error resetting password:', error);
            alert('Failed to reset password. Please try again.');
        }
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text ? text.replace(/[&<>"']/g, m => map[m]) : '';
    }
}

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.adminManager = new AdminManager();
    });
} else {
    window.adminManager = new AdminManager();
}
