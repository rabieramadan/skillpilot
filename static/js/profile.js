// Profile Management
class ProfileManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadProfile();
    }

    setupEventListeners() {
        // Profile form submission
        const profileForm = document.getElementById('profileForm');
        if (profileForm) {
            profileForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.updateProfile();
            });
        }

        // Password change form
        const passwordForm = document.getElementById('changePasswordForm');
        if (passwordForm) {
            passwordForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.changePassword();
            });
        }
    }

    async loadProfile() {
        try {
            const response = await fetch('/api/auth/user/profile', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.displayProfile(data.user);
            } else {
                console.error('Failed to load profile');
            }
        } catch (error) {
            console.error('Error loading profile:', error);
        }
    }

    displayProfile(user) {
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };
        set('profileFullName', user.full_name);
        set('profileEmail', user.email);
        set('profilePhone', user.phone);
        set('profileOrganization', user.organization);
        set('profileJobTitle', user.job_title);
        set('profileProfession', user.profession);
        set('profileCountry', user.country);
        set('profileRegion', user.region);
        set('profileGender', user.gender);
        set('profileEducationLevel', user.education_level);
        set('profileDob', user.date_of_birth);
        set('profileLanguage', user.language || 'en');
    }

    async updateProfile() {
        const val = (id) => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };
        const fullName = val('profileFullName');
        const email = val('profileEmail');

        if (!fullName || !email) {
            alert('Full name and email are required');
            return;
        }

        try {
            const response = await fetch('/api/auth/user/profile', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    full_name: fullName,
                    email: email,
                    phone: val('profilePhone'),
                    organization: val('profileOrganization'),
                    job_title: val('profileJobTitle'),
                    profession: val('profileProfession'),
                    country: val('profileCountry'),
                    region: val('profileRegion'),
                    gender: val('profileGender'),
                    education_level: val('profileEducationLevel'),
                    date_of_birth: val('profileDob'),
                    language: val('profileLanguage') || 'en'
                })
            });

            const data = await response.json();

            if (response.ok) {
                alert('Profile updated successfully!');
                // Update display name if visible
                const displayName = document.getElementById('userDisplayName');
                if (displayName) {
                    displayName.textContent = fullName;
                }
            } else {
                alert(data.error || 'Failed to update profile');
            }
        } catch (error) {
            console.error('Error updating profile:', error);
            alert('Failed to update profile. Please try again.');
        }
    }

    async changePassword() {
        const currentPassword = document.getElementById('currentPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmNewPassword').value;

        if (!currentPassword || !newPassword || !confirmPassword) {
            alert('All password fields are required');
            return;
        }

        if (newPassword !== confirmPassword) {
            alert('New passwords do not match');
            return;
        }

        if (newPassword.length < 6) {
            alert('New password must be at least 6 characters long');
            return;
        }

        try {
            const response = await fetch('/api/auth/user/change-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            const data = await response.json();

            if (response.ok) {
                alert('Password changed successfully!');
                document.getElementById('changePasswordForm').reset();
            } else {
                alert(data.error || 'Failed to change password');
            }
        } catch (error) {
            console.error('Error changing password:', error);
            alert('Failed to change password. Please try again.');
        }
    }
}

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.profileManager = new ProfileManager();
    });
} else {
    window.profileManager = new ProfileManager();
}
