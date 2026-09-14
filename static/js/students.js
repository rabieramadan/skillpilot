// Enhanced Student Management Module
class StudentManager {
    constructor(app) {
        this.app = app;
        this.students = [];
        this.filteredStudents = [];
        this.currentEditStudent = null;
        this.currentStudentDetails = null;
        this.searchQuery = '';
    }

    async loadStudents() {
        try {
            const response = await fetch('/api/students/', {
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('Failed to load students');
            }
            
            const data = await response.json();
            this.students = data.students || [];
            this.filteredStudents = [...this.students];
            this.renderStudentsSection();
        } catch (error) {
            console.error('Error loading students:', error);
            this.showMessage('Failed to load students', 'error');
        }
    }

    renderStudentsSection() {
        const container = document.getElementById('studentsTableContainer');
        if (!container) return;

        const totalStudents = this.students.length;
        const displayStudents = this.filteredStudents;

        container.innerHTML = `
            <div class="students-header">
                <div class="students-stats">
                    <div class="stat-badge">
                        <i class="fas fa-users"></i>
                        <span>${totalStudents} Total Students</span>
                    </div>
                    <div class="stat-badge">
                        <i class="fas fa-filter"></i>
                        <span>${displayStudents.length} Shown</span>
                    </div>
                </div>
                <div class="students-search">
                    <div class="search-input-wrapper">
                        <i class="fas fa-search"></i>
                        <input type="text" 
                               id="studentSearchInput" 
                               placeholder="Search by name, email, username..." 
                               value="${this.searchQuery}"
                               oninput="studentManager.handleSearch(this.value)"
                               data-testid="input-student-search">
                        ${this.searchQuery ? `<button class="search-clear" onclick="studentManager.clearSearch()"><i class="fas fa-times"></i></button>` : ''}
                    </div>
                </div>
            </div>
            
            ${displayStudents.length === 0 ? `
                <div class="empty-state">
                    <i class="fas fa-user-graduate"></i>
                    <p>${this.searchQuery ? 'No students match your search' : 'No students found'}</p>
                    ${this.searchQuery ? `<button class="btn-secondary" onclick="studentManager.clearSearch()">Clear Search</button>` : ''}
                </div>
            ` : `
                <div class="students-grid">
                    ${displayStudents.map(student => this.renderStudentCard(student)).join('')}
                </div>
            `}
        `;
        
        if (window.i18n) {
            window.i18n.translatePage();
        }
    }

    renderStudentCard(student) {
        const initials = this.getInitials(student.full_name);
        const bgColor = this.getAvatarColor(student.user_id);
        
        return `
            <div class="student-card" onclick="studentManager.viewStudentDetails('${student.user_id}')" data-testid="card-student-${student.user_id}">
                <div class="student-avatar" style="background: ${bgColor}">
                    ${initials}
                </div>
                <div class="student-info">
                    <h4 class="student-name">${this.escapeHtml(student.full_name)}</h4>
                    <p class="student-username">@${this.escapeHtml(student.username)}</p>
                    <p class="student-email"><i class="fas fa-envelope"></i> ${this.escapeHtml(student.email)}</p>
                    <p class="student-org"><i class="fas fa-building"></i> ${this.escapeHtml(student.organization || 'No organization')}</p>
                </div>
                <div class="student-actions">
                    <button class="btn-icon" onclick="event.stopPropagation(); studentManager.viewStudentDetails('${student.user_id}')" title="View Details" data-testid="button-view-${student.user_id}">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-icon" onclick="event.stopPropagation(); studentManager.editStudent('${student.user_id}')" title="Edit Student" data-testid="button-edit-${student.user_id}">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon" onclick="event.stopPropagation(); studentManager.resetPassword('${student.user_id}')" title="Reset Password" data-testid="button-reset-password-${student.user_id}">
                        <i class="fas fa-key"></i>
                    </button>
                </div>
            </div>
        `;
    }

    handleSearch(query) {
        this.searchQuery = query.toLowerCase().trim();
        
        if (!this.searchQuery) {
            this.filteredStudents = [...this.students];
        } else {
            this.filteredStudents = this.students.filter(student => 
                student.full_name.toLowerCase().includes(this.searchQuery) ||
                student.username.toLowerCase().includes(this.searchQuery) ||
                student.email.toLowerCase().includes(this.searchQuery) ||
                (student.organization && student.organization.toLowerCase().includes(this.searchQuery)) ||
                (student.phone && student.phone.includes(this.searchQuery))
            );
        }
        
        this.renderStudentsSection();
    }

    clearSearch() {
        this.searchQuery = '';
        this.filteredStudents = [...this.students];
        this.renderStudentsSection();
    }

    async viewStudentDetails(userId) {
        const student = this.students.find(s => s.user_id === userId);
        if (!student) return;

        this.currentStudentDetails = student;

        // Show loading state
        const modal = document.getElementById('studentDetailsModal');
        if (!modal) {
            this.createDetailsModal();
        }
        
        document.getElementById('studentDetailsModal').classList.add('show');
        document.getElementById('studentDetailsContent').innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <i class="fas fa-spinner fa-spin fa-2x"></i>
                <p style="margin-top: 15px;">Loading student details...</p>
            </div>
        `;

        try {
            // Fetch enrollments and certificates in parallel
            const [enrollmentsRes, certificatesRes] = await Promise.all([
                fetch(`/api/students/${userId}/enrollments`, { credentials: 'include' }),
                fetch(`/api/students/${userId}/certificates`, { credentials: 'include' })
            ]);

            const enrollmentsData = enrollmentsRes.ok ? await enrollmentsRes.json() : { enrollments: [] };
            const certificatesData = certificatesRes.ok ? await certificatesRes.json() : { certificates: [] };

            this.renderStudentDetailsModal(student, enrollmentsData.enrollments || [], certificatesData.certificates || []);
        } catch (error) {
            console.error('Error fetching student details:', error);
            this.renderStudentDetailsModal(student, [], []);
        }
    }

    createDetailsModal() {
        const modalHTML = `
            <div id="studentDetailsModal" class="modal">
                <div class="modal-content" style="max-width: 900px; max-height: 90vh;">
                    <div class="modal-header">
                        <h3><i class="fas fa-user-graduate"></i> Student Details</h3>
                        <button class="modal-close" onclick="document.getElementById('studentDetailsModal').classList.remove('show')">&times;</button>
                    </div>
                    <div class="modal-body" id="studentDetailsContent" style="overflow-y: auto; max-height: 70vh;"></div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    renderStudentDetailsModal(student, enrollments, certificates) {
        const content = document.getElementById('studentDetailsContent');
        const initials = this.getInitials(student.full_name);
        const bgColor = this.getAvatarColor(student.user_id);

        content.innerHTML = `
            <div class="student-details-grid">
                <!-- Student Profile Section -->
                <div class="details-section profile-section">
                    <div class="profile-header">
                        <div class="profile-avatar" style="background: ${bgColor}">
                            ${initials}
                        </div>
                        <div class="profile-info">
                            <h2>${this.escapeHtml(student.full_name)}</h2>
                            <p class="username">@${this.escapeHtml(student.username)}</p>
                            <span class="role-badge">Student</span>
                        </div>
                        <button class="btn-primary btn-sm" onclick="studentManager.editStudent('${student.user_id}')">
                            <i class="fas fa-edit"></i> Edit Info
                        </button>
                    </div>
                    
                    <div class="profile-details">
                        <div class="detail-item">
                            <i class="fas fa-envelope"></i>
                            <span>${this.escapeHtml(student.email)}</span>
                        </div>
                        <div class="detail-item">
                            <i class="fas fa-phone"></i>
                            <span>${this.escapeHtml(student.phone || 'Not provided')}</span>
                        </div>
                        <div class="detail-item">
                            <i class="fas fa-building"></i>
                            <span>${this.escapeHtml(student.organization || 'Not provided')}</span>
                        </div>
                        <div class="detail-item">
                            <i class="fas fa-calendar-alt"></i>
                            <span>Joined: ${student.registered_at ? new Date(student.registered_at).toLocaleDateString() : 'Unknown'}</span>
                        </div>
                        <div class="detail-item">
                            <i class="fas fa-clock"></i>
                            <span>Last Login: ${student.last_login ? new Date(student.last_login).toLocaleString() : 'Never'}</span>
                        </div>
                    </div>
                    
                    <div class="profile-actions">
                        <button class="btn-secondary" onclick="studentManager.resetPassword('${student.user_id}')">
                            <i class="fas fa-key"></i> Reset Password
                        </button>
                    </div>
                </div>

                <!-- Enrolled Courses Section -->
                <div class="details-section">
                    <h3><i class="fas fa-book"></i> Enrolled Courses (${enrollments.length})</h3>
                    ${enrollments.length === 0 ? `
                        <div class="empty-section">
                            <i class="fas fa-book-open"></i>
                            <p>Not enrolled in any courses</p>
                        </div>
                    ` : `
                        <div class="enrollments-list">
                            ${enrollments.map(e => `
                                <div class="enrollment-item">
                                    <div class="enrollment-info">
                                        <strong>${this.escapeHtml(e.class_title || e.class_id)}</strong>
                                        <span class="enrollment-status status-${e.status}">${e.status}</span>
                                    </div>
                                    <small>Enrolled: ${e.requested_at ? new Date(e.requested_at).toLocaleDateString() : 'Unknown'}</small>
                                </div>
                            `).join('')}
                        </div>
                    `}
                </div>

                <!-- Certificates Section -->
                <div class="details-section">
                    <h3><i class="fas fa-certificate"></i> Certificates (${certificates.length})</h3>
                    ${certificates.length === 0 ? `
                        <div class="empty-section">
                            <i class="fas fa-award"></i>
                            <p>No certificates earned yet</p>
                        </div>
                    ` : `
                        <div class="certificates-list">
                            ${certificates.map(cert => `
                                <div class="certificate-item">
                                    <div class="cert-icon ${cert.type === 'prompt_engineering' ? 'cert-blue' : 'cert-green'}">
                                        <i class="fas fa-award"></i>
                                    </div>
                                    <div class="cert-info">
                                        <strong>${this.escapeHtml(cert.title || cert.type)}</strong>
                                        <small>Certificate #: ${cert.certificate_number || 'N/A'}</small>
                                        <small>Issued: ${cert.issued_at ? new Date(cert.issued_at).toLocaleDateString() : 'Unknown'}</small>
                                        ${cert.score ? `<small>Score: ${cert.score}%</small>` : ''}
                                    </div>
                                    <div class="cert-actions">
                                        <button class="btn-sm btn-secondary" onclick="studentManager.viewCertificate('${student.user_id}', '${cert.id}', '${cert.type}')" title="View Certificate">
                                            <i class="fas fa-eye"></i>
                                        </button>
                                        <button class="btn-sm btn-primary" onclick="studentManager.regenerateCertificate('${student.user_id}', '${cert.id}', '${cert.type}')" title="Regenerate Certificate">
                                            <i class="fas fa-sync-alt"></i>
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `}
                </div>
            </div>
        `;
    }

    async viewCertificate(userId, certId, certType) {
        try {
            let endpoint;
            if (certType === 'prompt_engineering') {
                endpoint = `/api/survey/exit-exam/certificate/${certId}`;
            } else if (certType === 'ethics') {
                endpoint = `/api/ethics/certificate/${certId}`;
            } else {
                endpoint = `/api/survey/exit-exam/certificate/${certId}`;
            }
            
            const response = await fetch(endpoint, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                window.open(url, '_blank');
            } else {
                this.showMessage('Certificate not available for download', 'error');
            }
        } catch (error) {
            console.error('Error viewing certificate:', error);
            this.showMessage('Error loading certificate', 'error');
        }
    }

    async regenerateCertificate(userId, certId, certType) {
        if (!confirm('Regenerate this certificate with current student information?\n\nThis will update the certificate with the latest name and details.')) {
            return;
        }

        try {
            const response = await fetch(`/api/students/${userId}/certificates/${certId}/regenerate`, {
                method: 'POST',
                credentials: 'include'
            });

            if (response.ok) {
                this.showMessage('Certificate regenerated successfully', 'success');
                this.viewStudentDetails(userId);
            } else {
                const data = await response.json();
                throw new Error(data.error || 'Failed to regenerate certificate');
            }
        } catch (error) {
            console.error('Error regenerating certificate:', error);
            this.showMessage(error.message, 'error');
        }
    }

    editStudent(userId) {
        const student = this.students.find(s => s.user_id === userId);
        if (!student) return;

        this.currentEditStudent = student;

        document.getElementById('editStudentId').value = student.user_id;
        document.getElementById('editStudentUsername').value = student.username;
        document.getElementById('editStudentFullName').value = student.full_name;
        document.getElementById('editStudentEmail').value = student.email;
        document.getElementById('editStudentPhone').value = student.phone || '';
        document.getElementById('editStudentOrganization').value = student.organization || '';

        document.getElementById('editStudentModal').classList.add('show');
    }

    async saveStudentEdit() {
        const userId = document.getElementById('editStudentId').value;
        const updateData = {
            username: document.getElementById('editStudentUsername').value.trim(),
            full_name: document.getElementById('editStudentFullName').value.trim(),
            email: document.getElementById('editStudentEmail').value.trim(),
            phone: document.getElementById('editStudentPhone').value.trim(),
            organization: document.getElementById('editStudentOrganization').value.trim()
        };

        try {
            const response = await fetch(`/api/students/${userId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(updateData)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to update student');
            }

            this.showMessage('Student information updated successfully', 'success');
            document.getElementById('editStudentModal').classList.remove('show');
            await this.loadStudents();
            
            // Refresh details modal if open
            if (this.currentStudentDetails && this.currentStudentDetails.user_id === userId) {
                this.viewStudentDetails(userId);
            }
        } catch (error) {
            console.error('Error updating student:', error);
            this.showMessage(error.message, 'error');
        }
    }

    async resetPassword(userId) {
        const student = this.students.find(s => s.user_id === userId);
        if (!student) return;

        if (!confirm(`Reset password for ${student.full_name}?\n\nA new random password will be generated.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/students/${userId}/reset-password`, {
                method: 'POST',
                credentials: 'include'
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to reset password');
            }

            document.getElementById('resetPasswordUsername').textContent = data.username;
            document.getElementById('resetPasswordNew').textContent = data.new_password;
            document.getElementById('passwordResetModal').classList.add('show');

        } catch (error) {
            console.error('Error resetting password:', error);
            this.showMessage(error.message, 'error');
        }
    }

    copyPassword() {
        const password = document.getElementById('resetPasswordNew').textContent;
        navigator.clipboard.writeText(password).then(() => {
            this.showMessage('Password copied to clipboard', 'success');
        }).catch(err => {
            console.error('Failed to copy password:', err);
        });
    }

    getInitials(name) {
        return name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
    }

    getAvatarColor(id) {
        const colors = [
            'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
            'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
            'linear-gradient(135deg, #1B5E20 0%, #4CAF50 100%)',
            'linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%)',
            'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)'
        ];
        const hash = id.split('').reduce((acc, char) => char.charCodeAt(0) + acc, 0);
        return colors[hash % colors.length];
    }

    showMessage(message, type = 'info') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flash-message flash-${type}`;
        messageDiv.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(messageDiv);

        setTimeout(() => messageDiv.classList.add('show'), 10);
        setTimeout(() => {
            messageDiv.classList.remove('show');
            setTimeout(() => messageDiv.remove(), 300);
        }, 3000);
    }

    escapeHtml(text) {
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return String(text || '').replace(/[&<>"']/g, m => map[m]);
    }
}

// Initialize student manager
let studentManager;
document.addEventListener('DOMContentLoaded', () => {
    studentManager = new StudentManager(window.app);
    window.studentManager = studentManager;
});

// Also initialize if app becomes available later
if (typeof window !== 'undefined') {
    window.StudentManager = StudentManager;
}
