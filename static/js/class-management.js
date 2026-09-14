/**
 * Class Management - Class-centric view for managing students, exams, surveys, and certificates
 * Used by both Institution Admins and Teachers
 */

class ClassManagement {
    constructor() {
        this.currentClass = null;
        this.currentTab = 'students';
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 100000;
            animation: slideIn 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        const colors = {
            success: '#1B5E20',
            error: '#dc2626',
            info: '#1d4ed8',
            warning: '#f59e0b'
        };
        notification.style.background = colors[type] || colors.info;
        notification.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i> ${message}`;
        
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 4000);
    }

    async openClassDetail(courseId, courseTitle) {
        this.currentClass = { id: courseId, title: courseTitle };
        this.currentTab = 'students';
        
        const modal = document.createElement('div');
        modal.id = 'classDetailModal';
        modal.className = 'modal-overlay';
        modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 10000;';
        
        modal.innerHTML = `
            <div class="class-detail-modal" style="background: white; width: 95%; max-width: 700px; height: 85vh; border-radius: 12px; display: flex; flex-direction: column; overflow: hidden;">
                <div class="modal-header" style="padding: 16px 20px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; background: linear-gradient(135deg, #1B5E20, #2E7D32);">
                    <div>
                        <h2 style="margin: 0; color: white; font-size: 18px;">
                            <i class="fas fa-chalkboard-teacher"></i> ${this.escapeHtml(courseTitle)}
                        </h2>
                        <p style="margin: 4px 0 0 0; color: rgba(255,255,255,0.8); font-size: 12px;">Class Management</p>
                    </div>
                    <button onclick="classManagement.closeClassDetail()" style="background: rgba(255,255,255,0.2); border: none; color: white; width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 16px;" data-testid="button-close-class-detail">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="modal-tabs" style="display: flex; gap: 4px; padding: 10px 16px; background: #f9fafb; border-bottom: 1px solid #e5e7eb;">
                    <button onclick="classManagement.switchTab('students')" id="classTab-students" class="tab-btn active" style="padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; display: flex; align-items: center; gap: 6px;" data-testid="tab-students">
                        <i class="fas fa-users"></i> Students
                    </button>
                    <button onclick="classManagement.switchTab('exams')" id="classTab-exams" class="tab-btn" style="padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; display: flex; align-items: center; gap: 6px;" data-testid="tab-exams">
                        <i class="fas fa-file-alt"></i> Exams
                    </button>
                    <button onclick="classManagement.switchTab('surveys')" id="classTab-surveys" class="tab-btn" style="padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; display: flex; align-items: center; gap: 6px;" data-testid="tab-surveys">
                        <i class="fas fa-poll"></i> Surveys
                    </button>
                    <button onclick="classManagement.switchTab('certificates')" id="classTab-certificates" class="tab-btn" style="padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; display: flex; align-items: center; gap: 6px;" data-testid="tab-certificates">
                        <i class="fas fa-certificate"></i> Certificates
                    </button>
                </div>
                
                <div class="modal-content" id="classDetailContent" style="flex: 1; overflow-y: auto; padding: 16px;">
                    <div style="text-align: center; padding: 40px; color: #888;">
                        <i class="fas fa-spinner fa-spin fa-2x"></i>
                        <p>Loading class data...</p>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        this.updateTabStyles();
        await this.loadTabContent('students');
    }

    closeClassDetail() {
        const modal = document.getElementById('classDetailModal');
        if (modal) modal.remove();
        this.currentClass = null;
    }

    switchTab(tab) {
        this.currentTab = tab;
        this.updateTabStyles();
        this.loadTabContent(tab);
    }

    updateTabStyles() {
        const tabs = ['students', 'exams', 'surveys', 'certificates'];
        tabs.forEach(t => {
            const btn = document.getElementById(`classTab-${t}`);
            if (btn) {
                if (t === this.currentTab) {
                    btn.style.background = '#1B5E20';
                    btn.style.color = 'white';
                } else {
                    btn.style.background = 'white';
                    btn.style.color = '#374151';
                }
            }
        });
    }

    async loadTabContent(tab) {
        const container = document.getElementById('classDetailContent');
        if (!container || !this.currentClass) return;
        
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #888;"><i class="fas fa-spinner fa-spin fa-2x"></i><p>Loading...</p></div>';
        
        switch (tab) {
            case 'students':
                await this.loadStudentsTab();
                break;
            case 'exams':
                await this.loadExamsTab();
                break;
            case 'surveys':
                await this.loadSurveysTab();
                break;
            case 'certificates':
                await this.loadCertificatesTab();
                break;
        }
    }

    // ============================================
    // STUDENTS TAB
    // ============================================

    async loadStudentsTab() {
        const container = document.getElementById('classDetailContent');
        if (!container) return;
        
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/students`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                container.innerHTML = '<p style="color: #ef4444; text-align: center; padding: 20px;">Failed to load students</p>';
                return;
            }
            
            const data = await response.json();
            
            if (!data.success || !data.students || data.students.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #888;">
                        <i class="fas fa-user-graduate fa-3x" style="margin-bottom: 16px; opacity: 0.5;"></i>
                        <p>No students enrolled in this class yet</p>
                    </div>
                `;
                return;
            }
            
            let html = `
                <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <h3 style="margin: 0; font-size: 15px;"><i class="fas fa-users"></i> Enrolled Students (${data.students.length})</h3>
                    <input type="text" id="studentSearch" placeholder="Search students..." 
                           style="padding: 6px 10px; border: 1px solid #e5e7eb; border-radius: 6px; width: 180px; font-size: 13px;"
                           onkeyup="classManagement.filterStudents()" data-testid="input-search-students">
                </div>
                <div class="students-list" id="studentsList">
            `;
            
            for (const student of data.students) {
                // Handle both flat and nested data structures
                const enrollmentStatus = student.enrollment?.status || student.enrollment_status || 'pending';
                const paymentStatus = student.enrollment?.payment_status || student.payment_status || 'not_required';
                const progressPercent = student.enrollment?.progress_percent || student.progress_percent || 0;
                const examsPassed = student.progress?.exams?.passed ?? student.exams_passed ?? 0;
                const totalExams = student.progress?.exams?.total ?? student.total_exams ?? 0;
                const avgScore = student.progress?.exams?.average_score ?? student.avg_score ?? 0;
                
                const statusBadge = this.getStatusBadge(enrollmentStatus);
                const paymentBadge = this.getPaymentBadge(paymentStatus);
                const allPassed = examsPassed === totalExams && totalExams > 0;
                
                html += `
                    <div class="student-card" style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin-bottom: 10px;" 
                         data-student-name="${this.escapeHtml(student.full_name).toLowerCase()}" data-testid="student-card-${student.id}">
                        <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px;">
                            <div style="flex: 1;">
                                <h4 style="margin: 0 0 4px 0; color: #1B5E20; font-size: 14px;">
                                    <i class="fas fa-user-graduate"></i> ${this.escapeHtml(student.full_name)}
                                </h4>
                                <p style="margin: 0; color: #666; font-size: 12px;">
                                    @${this.escapeHtml(student.username)} &bull; ${this.escapeHtml(student.email || 'No email')}
                                </p>
                                <div style="margin-top: 6px; display: flex; gap: 6px; flex-wrap: wrap;">
                                    ${statusBadge}
                                    ${paymentBadge}
                                </div>
                            </div>
                            
                            <div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center;">
                                <div style="background: #dbeafe; padding: 4px 10px; border-radius: 6px; text-align: center; min-width: 50px;">
                                    <div style="font-size: 15px; font-weight: bold; color: #1d4ed8;">${progressPercent}%</div>
                                    <div style="font-size: 9px; color: #1d4ed8;">Progress</div>
                                </div>
                                <div style="background: ${allPassed ? '#dcfce7' : '#fef3c7'}; padding: 4px 10px; border-radius: 6px; text-align: center; min-width: 50px;">
                                    <div style="font-size: 15px; font-weight: bold; color: ${allPassed ? '#166534' : '#854d0e'};">${examsPassed}/${totalExams}</div>
                                    <div style="font-size: 9px; color: ${allPassed ? '#166534' : '#854d0e'};">Exams</div>
                                </div>
                                <div style="background: #ede9fe; padding: 4px 10px; border-radius: 6px; text-align: center; min-width: 50px;">
                                    <div style="font-size: 15px; font-weight: bold; color: #5b21b6;">${avgScore}</div>
                                    <div style="font-size: 9px; color: #5b21b6;">Avg Score</div>
                                </div>
                            </div>
                        </div>
                        
                        <div style="margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap;">
                            <button onclick="classManagement.editStudent('${student.id}')" class="btn-secondary" style="padding: 5px 10px; font-size: 12px;" data-testid="button-edit-student-${student.id}">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button onclick="classManagement.viewStudentExams('${student.id}', '${this.escapeHtml(student.full_name)}')" class="btn-secondary" style="padding: 5px 10px; font-size: 12px;" data-testid="button-view-exams-${student.id}">
                                <i class="fas fa-file-alt"></i> View Exams
                            </button>
                        </div>
                    </div>
                `;
            }
            
            html += '</div>';
            container.innerHTML = html;
            
        } catch (error) {
            console.error('Error loading students:', error);
            container.innerHTML = '<p style="color: #ef4444; text-align: center; padding: 20px;">Error loading students</p>';
        }
    }

    filterStudents() {
        const search = document.getElementById('studentSearch')?.value?.toLowerCase() || '';
        const cards = document.querySelectorAll('.student-card');
        cards.forEach(card => {
            const name = card.dataset.studentName || '';
            card.style.display = name.includes(search) ? 'block' : 'none';
        });
    }

    getStatusBadge(status) {
        const colors = {
            'approved': { bg: '#dcfce7', color: '#166534', icon: 'check-circle' },
            'pending': { bg: '#fef3c7', color: '#854d0e', icon: 'clock' },
            'blocked': { bg: '#fef2f2', color: '#991b1b', icon: 'ban' },
            'completed': { bg: '#dbeafe', color: '#1d4ed8', icon: 'graduation-cap' }
        };
        const c = colors[status] || colors.pending;
        return `<span style="background: ${c.bg}; color: ${c.color}; padding: 4px 10px; border-radius: 12px; font-size: 11px;"><i class="fas fa-${c.icon}"></i> ${status}</span>`;
    }

    getPaymentBadge(status) {
        const colors = {
            'paid': { bg: '#dcfce7', color: '#166534', text: 'Paid' },
            'waived': { bg: '#e0f2fe', color: '#0369a1', text: 'Waived' },
            'pending': { bg: '#fef3c7', color: '#854d0e', text: 'Payment Pending' },
            'not_required': { bg: '#f3f4f6', color: '#6b7280', text: 'Free' }
        };
        const c = colors[status] || colors.not_required;
        return `<span style="background: ${c.bg}; color: ${c.color}; padding: 4px 10px; border-radius: 12px; font-size: 11px;">${c.text}</span>`;
    }

    async editStudent(studentId) {
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/students`, {
                credentials: 'include'
            });
            const data = await response.json();
            const student = data.students?.find(s => s.id === studentId);
            
            if (!student) {
                alert('Student not found');
                return;
            }
            
            const modal = document.createElement('div');
            modal.id = 'editStudentModal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 20000;';
            
            modal.innerHTML = `
                <div style="background: white; padding: 24px; border-radius: 12px; max-width: 550px; width: 95%; max-height: 85vh; overflow-y: auto;">
                    <h3 style="margin: 0 0 20px 0;"><i class="fas fa-user-edit"></i> Edit Student Enrollment</h3>
                    <form id="editStudentForm">
                        <div style="display: grid; gap: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 4px; font-weight: 500;">Full Name</label>
                                <input type="text" id="editFullName" value="${this.escapeHtml(student.full_name)}" 
                                       style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="input-edit-fullname">
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Email</label>
                                    <input type="email" id="editEmail" value="${this.escapeHtml(student.email || '')}" 
                                           style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="input-edit-email">
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Phone</label>
                                    <input type="text" id="editPhone" value="${this.escapeHtml(student.phone || '')}" 
                                           style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="input-edit-phone">
                                </div>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Enrollment Status</label>
                                    <select id="editEnrollmentStatus" style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="select-enrollment-status">
                                        <option value="approved" ${student.enrollment_status === 'approved' ? 'selected' : ''}>Approved</option>
                                        <option value="pending" ${student.enrollment_status === 'pending' ? 'selected' : ''}>Pending</option>
                                        <option value="blocked" ${student.enrollment_status === 'blocked' ? 'selected' : ''}>Blocked</option>
                                        <option value="completed" ${student.enrollment_status === 'completed' ? 'selected' : ''}>Completed</option>
                                    </select>
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Payment Status</label>
                                    <select id="editPaymentStatus" style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="select-payment-status">
                                        <option value="paid" ${student.payment_status === 'paid' ? 'selected' : ''}>Paid</option>
                                        <option value="pending" ${student.payment_status === 'pending' ? 'selected' : ''}>Payment Pending</option>
                                        <option value="waived" ${student.payment_status === 'waived' ? 'selected' : ''}>Waived (Free Access)</option>
                                        <option value="not_required" ${student.payment_status === 'not_required' ? 'selected' : ''}>Not Required</option>
                                    </select>
                                </div>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Progress %</label>
                                    <input type="number" id="editProgress" value="${student.progress_percent || 0}" min="0" max="100"
                                           style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="input-edit-progress">
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Final Grade</label>
                                    <input type="number" id="editFinalGrade" value="${student.final_grade || ''}" min="0" max="100" placeholder="Not set"
                                           style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="input-edit-grade">
                                </div>
                            </div>
                            
                            <div style="background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 12px;">
                                <h4 style="margin: 0 0 8px 0; color: #0369a1; font-size: 14px;">
                                    <i class="fas fa-info-circle"></i> Student Stats
                                </h4>
                                <p style="margin: 0; font-size: 13px; color: #0c4a6e;">
                                    Exams: ${student.exams_passed || 0}/${student.total_exams || 0} passed | 
                                    Avg Score: ${student.avg_score || 0}%
                                </p>
                            </div>
                        </div>
                        <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px;">
                            <button type="button" onclick="document.getElementById('editStudentModal').remove()" class="btn-secondary" data-testid="button-cancel-edit">Cancel</button>
                            <button type="submit" class="btn-primary" data-testid="button-save-student">
                                <i class="fas fa-save"></i> Save Changes
                            </button>
                        </div>
                    </form>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            document.getElementById('editStudentForm').onsubmit = async (e) => {
                e.preventDefault();
                await this.saveStudentChanges(studentId);
            };
            
        } catch (error) {
            console.error('Error loading student for edit:', error);
            alert('Error loading student data');
        }
    }

    async saveStudentChanges(studentId) {
        try {
            const finalGradeValue = document.getElementById('editFinalGrade').value;
            const response = await fetch(`/api/classes/${this.currentClass.id}/students/${studentId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    full_name: document.getElementById('editFullName').value,
                    email: document.getElementById('editEmail').value,
                    phone: document.getElementById('editPhone').value,
                    enrollment_status: document.getElementById('editEnrollmentStatus').value,
                    payment_status: document.getElementById('editPaymentStatus').value,
                    progress_percent: parseFloat(document.getElementById('editProgress').value) || 0,
                    final_grade: finalGradeValue ? parseFloat(finalGradeValue) : null
                }),
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                alert(data.error || 'Failed to save changes');
                return;
            }
            
            document.getElementById('editStudentModal').remove();
            this.showNotification('Student updated successfully', 'success');
            await this.loadStudentsTab();
            
        } catch (error) {
            console.error('Error saving student:', error);
            alert('Error saving changes');
        }
    }

    // ============================================
    // EXAMS TAB
    // ============================================

    async loadExamsTab() {
        const container = document.getElementById('classDetailContent');
        if (!container) return;
        
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/exams`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                container.innerHTML = '<p style="color: #ef4444; text-align: center; padding: 20px;">Failed to load exams</p>';
                return;
            }
            
            const data = await response.json();
            
            if (!data.success || !data.exams || data.exams.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #888;">
                        <i class="fas fa-file-alt fa-3x" style="margin-bottom: 16px; opacity: 0.5;"></i>
                        <p>No exams created for this class yet</p>
                    </div>
                `;
                return;
            }
            
            let html = `<h3 style="margin: 0 0 12px 0; font-size: 15px;"><i class="fas fa-file-alt"></i> Exams & Statistics (${data.exams.length})</h3>`;
            
            for (const exam of data.exams) {
                const stats = exam.statistics;
                const passRate = stats.pass_rate || 0;
                const chartId = `chart-${exam.id}`;
                
                html += `
                    <div class="exam-card" style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin-bottom: 10px;" data-testid="exam-card-${exam.id}">
                        <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 10px;">
                            <div style="flex: 1;">
                                <h4 style="margin: 0 0 2px 0; color: #1d4ed8; font-size: 14px;">
                                    <i class="fas fa-file-alt"></i> ${this.escapeHtml(exam.title)}
                                    <span style="font-size: 11px; color: #6b7280; font-weight: normal;">(${exam.exam_type})</span>
                                </h4>
                                <p style="margin: 0; color: #666; font-size: 11px;">
                                    <i class="fas fa-check-circle"></i> ${exam.passing_threshold}% &bull;
                                    <i class="fas fa-redo"></i> ${exam.max_attempts} attempts
                                    ${exam.time_limit_minutes ? ` &bull; <i class="fas fa-clock"></i> ${exam.time_limit_minutes}m` : ''}
                                </p>
                            </div>
                            <span style="background: ${exam.is_published ? '#dcfce7' : '#fef3c7'}; color: ${exam.is_published ? '#166534' : '#854d0e'}; padding: 3px 10px; border-radius: 12px; font-size: 11px; white-space: nowrap;">
                                ${exam.is_published ? 'Published' : 'Draft'}
                            </span>
                        </div>
                        
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 60px; height: 60px; flex-shrink: 0;">
                                <canvas id="${chartId}" width="60" height="60"></canvas>
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 8px; flex: 1;">
                                <div style="background: #dbeafe; padding: 6px 10px; border-radius: 6px; text-align: center; min-width: 55px;">
                                    <div style="font-size: 16px; font-weight: bold; color: #1d4ed8;">${stats.total_submissions}</div>
                                    <div style="font-size: 9px; color: #1d4ed8;">Submitted</div>
                                </div>
                                <div style="background: #dcfce7; padding: 6px 10px; border-radius: 6px; text-align: center; min-width: 55px;">
                                    <div style="font-size: 16px; font-weight: bold; color: #166534;">${stats.passed_count}</div>
                                    <div style="font-size: 9px; color: #166534;">Passed</div>
                                </div>
                                <div style="background: #fef2f2; padding: 6px 10px; border-radius: 6px; text-align: center; min-width: 55px;">
                                    <div style="font-size: 16px; font-weight: bold; color: #991b1b;">${stats.failed_count}</div>
                                    <div style="font-size: 9px; color: #991b1b;">Failed</div>
                                </div>
                                <div style="background: #ede9fe; padding: 6px 10px; border-radius: 6px; text-align: center; min-width: 55px;">
                                    <div style="font-size: 16px; font-weight: bold; color: #5b21b6;">${passRate}%</div>
                                    <div style="font-size: 9px; color: #5b21b6;">Pass Rate</div>
                                </div>
                                <div style="background: #fef3c7; padding: 6px 10px; border-radius: 6px; text-align: center; min-width: 55px;">
                                    <div style="font-size: 16px; font-weight: bold; color: #854d0e;">${stats.avg_score}</div>
                                    <div style="font-size: 9px; color: #854d0e;">Avg Score</div>
                                </div>
                            </div>
                        </div>
                        
                        <div style="margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap;">
                            <button onclick="classManagement.viewExamDetails('${exam.id}', '${this.escapeHtml(exam.title)}')" class="btn-primary" style="padding: 5px 10px; font-size: 12px; background: #1d4ed8; color: white; border: none; border-radius: 4px; cursor: pointer;" data-testid="button-details-exam-${exam.id}">
                                <i class="fas fa-chart-bar"></i> Details
                            </button>
                            <button onclick="classManagement.editExam('${exam.id}')" class="btn-secondary" style="padding: 5px 10px; font-size: 12px;" data-testid="button-edit-exam-${exam.id}">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button onclick="classManagement.viewExamResults('${exam.id}', '${this.escapeHtml(exam.title)}')" class="btn-secondary" style="padding: 5px 10px; font-size: 12px;" data-testid="button-view-results-${exam.id}">
                                <i class="fas fa-list-alt"></i> Results
                            </button>
                        </div>
                    </div>
                `;
            }
            
            container.innerHTML = html;
            
            // Render pie charts for each exam
            for (const exam of data.exams) {
                const stats = exam.statistics;
                const chartId = `chart-${exam.id}`;
                const ctx = document.getElementById(chartId);
                if (ctx && window.Chart) {
                    new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: ['Passed', 'Failed'],
                            datasets: [{
                                data: [stats.passed_count || 0, stats.failed_count || 0],
                                backgroundColor: ['#22c55e', '#ef4444'],
                                borderWidth: 0
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            cutout: '60%',
                            plugins: {
                                legend: { display: false },
                                tooltip: { enabled: true }
                            }
                        }
                    });
                }
            }
            
        } catch (error) {
            console.error('Error loading exams:', error);
            container.innerHTML = '<p style="color: #ef4444; text-align: center; padding: 20px;">Error loading exams</p>';
        }
    }

    async viewExamResults(examId, examTitle) {
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/exams/${examId}/results`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                alert('Failed to load exam results');
                return;
            }
            
            const data = await response.json();
            const courseId = this.currentClass.id;

            const PROCTOR_LABELS = {
                tab_blur: 'Left window',
                paste_detected: 'Paste attempt',
                copy_detected: 'Copy attempt',
                fullscreen_exit: 'Exited fullscreen',
                navigation_attempt: 'Page leave attempt',
            };

            const modal = document.createElement('div');
            modal.id = 'examResultsModal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 20000;';

            const flaggedCount = (data.results || []).filter(r => (r.violation_count || 0) > 0).length;
            const flagBanner = flaggedCount > 0
                ? `<div style="background:#fff3f3;border:1px solid #f5c6c6;border-radius:6px;padding:10px 14px;margin-bottom:14px;color:#c62828;font-size:.9rem;"><i class="fas fa-flag"></i> <strong>${flaggedCount}</strong> submission(s) have suspicious activity. Rows highlighted in red. Review before approving certificates.</div>`
                : '';

            let resultsHtml = (data.results || []).length === 0
                ? '<p style="color: #888; text-align: center; padding: 20px;">No submissions yet</p>'
                : (data.results || []).map(r => {
                    const violations = r.violation_count || 0;
                    const flagged = violations > 0;
                    const forceSubmitted = r.force_submitted || violations >= 3;
                    const eventSummary = Object.entries(r.event_counts || {})
                        .filter(([t]) => t !== 'tab_focus' && t !== 'contextmenu_blocked')
                        .map(([t, n]) => `${PROCTOR_LABELS[t] || t} ×${n}`)
                        .join(', ');
                    const violationBadge = flagged
                        ? `<div style="margin-top:4px;color:#c62828;font-size:11px;font-weight:600;">
                             <i class="fas fa-flag"></i> ${violations} violation${violations > 1 ? 's' : ''}${forceSubmitted ? ' — AUTO-SUBMITTED' : ''}
                             ${eventSummary ? `<br><span style="font-weight:400;color:#a33;">${eventSummary}</span>` : ''}
                           </div>`
                        : '<div style="margin-top:4px;color:#16a34a;font-size:11px;"><i class="fas fa-check"></i> Clean</div>';
                    return `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; padding: 12px; background: ${forceSubmitted ? '#fff0f0' : flagged ? '#fff8f8' : r.passed ? '#f0fdf4' : '#fef2f2'}; border-radius: 6px; margin-bottom: 8px; border-left: 4px solid ${forceSubmitted ? '#c62828' : flagged ? '#f97316' : r.passed ? '#16a34a' : '#dc2626'};" data-testid="result-row-${r.id}">
                        <div>
                            <strong>${this.escapeHtml(r.student_name)}</strong>
                            <span style="color: #6b7280; font-size: 12px; margin-left: 8px;">@${this.escapeHtml(r.student_username)}</span>
                            <div style="font-size: 12px; color: #888; margin-top: 2px;">
                                Attempt #${r.attempt_number} &bull; ${r.submitted_at ? new Date(r.submitted_at).toLocaleString() : 'N/A'}
                            </div>
                            ${violationBadge}
                        </div>
                        <div style="display: flex; align-items: center; gap: 12px; flex-shrink:0;">
                            <div style="text-align:center;">
                                <span style="background: ${r.passed ? '#dcfce7' : '#fef2f2'}; color: ${r.passed ? '#166534' : '#991b1b'}; padding: 6px 14px; border-radius: 20px; font-weight: 600; display:block;">
                                    ${r.percentage ?? r.score}% ${r.passed ? '✓' : '✗'}
                                </span>
                                <small style="color:#888;font-size:11px;">${r.score ?? '?'}/${r.total_points ?? '?'} pts</small>
                            </div>
                            <div style="display: flex; gap: 6px;">
                                ${!r.passed ? `
                                    <button onclick="classManagement.allowRepeat('${examId}', '${r.id}')" class="btn-secondary" style="padding: 4px 10px; font-size: 12px;" title="Allow Repeat" data-testid="button-allow-repeat-${r.id}">
                                        <i class="fas fa-redo"></i>
                                    </button>
                                ` : ''}
                                ${r.passed ? `
                                    <button onclick="classManagement.approveExamCertificate('${examId}', '${r.id}')" class="btn-secondary" style="padding: 4px 10px; font-size: 12px;" title="Approve Certificate" data-testid="button-approve-cert-${r.id}">
                                        <i class="fas fa-certificate"></i>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>`;
                }).join('');

            modal.innerHTML = `
                <div style="background: white; padding: 24px; border-radius: 12px; max-width: 800px; width: 95%; max-height: 85vh; overflow-y: auto;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap:wrap; gap:8px;">
                        <h3 style="margin: 0;"><i class="fas fa-chart-bar"></i> ${this.escapeHtml(examTitle)} — Results</h3>
                        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                            <a href="/api/classes/${encodeURIComponent(courseId)}/exams/${encodeURIComponent(examId)}/results/export-xlsx"
                               download
                               style="background:#217346;color:#fff;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:.85rem;font-weight:600;display:inline-flex;align-items:center;gap:6px;"
                               data-testid="link-export-exam-xlsx">
                               <i class="fas fa-file-excel"></i> Download Excel
                            </a>
                            <button onclick="document.getElementById('examResultsModal').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer; line-height:1;">&times;</button>
                        </div>
                    </div>
                    ${flagBanner}
                    <div style="max-height: 500px; overflow-y: auto;">
                        ${resultsHtml}
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
        } catch (error) {
            console.error('Error loading exam results:', error);
            alert('Error loading exam results');
        }
    }

    async allowRepeat(examId, resultId) {
        if (!confirm('Allow this student to repeat the exam?')) return;
        
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/exams/${examId}/results/${resultId}/allow-repeat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                alert(data.error || 'Failed to allow repeat');
                return;
            }
            
            this.showNotification(`Repeat allowed (max ${data.max_attempts} attempts)`, 'success');
            document.getElementById('examResultsModal')?.remove();
            
        } catch (error) {
            console.error('Error allowing repeat:', error);
            alert('Error allowing repeat');
        }
    }

    async approveExamCertificate(examId, resultId) {
        if (!confirm('Approve certificate for this exam result?')) return;
        
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/exams/${examId}/results/${resultId}/approve-certificate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                alert(data.error || 'Failed to approve certificate');
                return;
            }
            
            this.showNotification('Certificate approved', 'success');
            document.getElementById('examResultsModal')?.remove();
            
        } catch (error) {
            console.error('Error approving certificate:', error);
            alert('Error approving certificate');
        }
    }

    // ============================================
    // SURVEYS TAB
    // ============================================

    async loadSurveysTab() {
        const container = document.getElementById('classDetailContent');
        if (!container) return;
        
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/surveys`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                container.innerHTML = '<p style="color: #ef4444; text-align: center; padding: 20px;">Failed to load surveys</p>';
                return;
            }
            
            const data = await response.json();
            
            if (!data.success || !data.surveys || data.surveys.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #888;">
                        <i class="fas fa-poll fa-3x" style="margin-bottom: 16px; opacity: 0.5;"></i>
                        <p>No surveys created for this class yet</p>
                    </div>
                `;
                return;
            }
            
            let html = `<h3 style="margin: 0 0 12px 0; font-size: 15px;"><i class="fas fa-poll"></i> Surveys & Response Statistics (${data.surveys.length})</h3>`;
            
            for (const survey of data.surveys) {
                const stats = survey.statistics;
                const chartId = `survey-chart-${survey.id}`;
                
                html += `
                    <div class="survey-card" style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; margin-bottom: 10px;" data-testid="survey-card-${survey.id}">
                        <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 10px;">
                            <div style="flex: 1;">
                                <h4 style="margin: 0 0 2px 0; color: #5b21b6; font-size: 14px;">
                                    <i class="fas fa-poll"></i> ${this.escapeHtml(survey.title)}
                                    <span style="font-size: 11px; color: #6b7280; font-weight: normal;">(${survey.survey_type || 'General'})</span>
                                </h4>
                                <p style="margin: 0; color: #666; font-size: 11px;">
                                    ${survey.is_required ? '<i class="fas fa-exclamation-circle"></i> Required' : '<i class="fas fa-minus-circle"></i> Optional'}
                                </p>
                            </div>
                            <span style="background: ${survey.is_published ? '#dcfce7' : '#fef3c7'}; color: ${survey.is_published ? '#166534' : '#854d0e'}; padding: 3px 10px; border-radius: 12px; font-size: 11px; white-space: nowrap;">
                                ${survey.is_published ? 'Published' : 'Draft'}
                            </span>
                        </div>
                        
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 60px; height: 60px; flex-shrink: 0;">
                                <canvas id="${chartId}" width="60" height="60"></canvas>
                            </div>
                            <div style="display: flex; flex-wrap: wrap; gap: 8px; flex: 1;">
                                <div style="background: #dbeafe; padding: 6px 10px; border-radius: 6px; text-align: center; min-width: 55px;">
                                    <div style="font-size: 16px; font-weight: bold; color: #1d4ed8;">${stats.total_students}</div>
                                    <div style="font-size: 9px; color: #1d4ed8;">Students</div>
                                </div>
                                <div style="background: #dcfce7; padding: 6px 10px; border-radius: 6px; text-align: center; min-width: 55px;">
                                    <div style="font-size: 16px; font-weight: bold; color: #166534;">${stats.unique_responders || stats.response_count}</div>
                                    <div style="font-size: 9px; color: #166534;">Responded</div>
                                </div>
                                <div style="background: #ede9fe; padding: 6px 10px; border-radius: 6px; text-align: center; min-width: 55px;">
                                    <div style="font-size: 16px; font-weight: bold; color: #5b21b6;">${stats.response_rate}%</div>
                                    <div style="font-size: 9px; color: #5b21b6;">Rate</div>
                                </div>
                            </div>
                            <button onclick="classManagement.viewSurveyResponses('${survey.id}', '${this.escapeHtml(survey.title)}')" class="btn-primary" style="padding: 5px 10px; font-size: 12px; background: #5b21b6; color: white; border: none; border-radius: 4px; cursor: pointer;" data-testid="button-details-survey-${survey.id}">
                                <i class="fas fa-chart-bar"></i> Details
                            </button>
                        </div>
                    </div>
                `;
            }
            
            container.innerHTML = html;
            
            // Render response rate charts
            for (const survey of data.surveys) {
                const stats = survey.statistics;
                const chartId = `survey-chart-${survey.id}`;
                const ctx = document.getElementById(chartId);
                const responders = stats.unique_responders || stats.response_count;
                const notResponded = Math.max(0, stats.total_students - responders);
                
                if (ctx && window.Chart) {
                    new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: ['Responded', 'Pending'],
                            datasets: [{
                                data: [responders, notResponded],
                                backgroundColor: ['#22c55e', '#e5e7eb'],
                                borderWidth: 0
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            cutout: '60%',
                            plugins: {
                                legend: { display: false },
                                tooltip: { enabled: true }
                            }
                        }
                    });
                }
            }
            
        } catch (error) {
            console.error('Error loading surveys:', error);
            container.innerHTML = '<p style="color: #ef4444; text-align: center; padding: 20px;">Error loading surveys</p>';
        }
    }

    async viewSurveyResponses(surveyId, surveyTitle) {
        try {
            // Use detailed endpoint for full question-level stats
            const response = await fetch(`/api/classes/${this.currentClass.id}/surveys/${surveyId}/details`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                alert('Failed to load survey details');
                return;
            }
            
            const data = await response.json();
            
            const modal = document.createElement('div');
            modal.id = 'surveyResponsesModal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 20000;';
            
            // Build statistics summary
            const stats = data.statistics;
            let statsHtml = `
                <div style="display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap;">
                    <div style="background: #dbeafe; padding: 10px 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: bold; color: #1d4ed8;">${stats.total_students}</div>
                        <div style="font-size: 11px; color: #1d4ed8;">Total Students</div>
                    </div>
                    <div style="background: #dcfce7; padding: 10px 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: bold; color: #166534;">${stats.unique_responders}</div>
                        <div style="font-size: 11px; color: #166534;">Responded</div>
                    </div>
                    <div style="background: #ede9fe; padding: 10px 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: bold; color: #5b21b6;">${stats.response_rate}%</div>
                        <div style="font-size: 11px; color: #5b21b6;">Response Rate</div>
                    </div>
                </div>
            `;
            
            // Build questions with statistics
            let questionsHtml = '<h4 style="margin: 16px 0 12px 0; color: #374151;"><i class="fas fa-list-ol"></i> Questions & Responses</h4>';
            
            data.questions.forEach((q, idx) => {
                questionsHtml += `
                    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                        <div style="font-weight: 600; color: #374151; margin-bottom: 8px;">
                            Q${idx + 1}: ${this.escapeHtml(q.question_text)}
                            <span style="font-size: 11px; color: #6b7280; font-weight: normal;">(${q.question_type})</span>
                        </div>
                `;
                
                if (q.question_type === 'text' || q.question_type === 'long_text') {
                    // Show text responses (comments)
                    if (q.text_responses && q.text_responses.length > 0) {
                        questionsHtml += `<div style="font-size: 12px; color: #666; margin-bottom: 6px;"><i class="fas fa-comments"></i> ${q.text_responses.length} comments:</div>`;
                        q.text_responses.slice(0, 5).forEach(tr => {
                            questionsHtml += `
                                <div style="background: white; padding: 8px; border-radius: 4px; margin-bottom: 4px; font-size: 13px;">
                                    <strong>${this.escapeHtml(tr.student_name)}:</strong> "${this.escapeHtml(tr.response)}"
                                </div>
                            `;
                        });
                        if (q.text_responses.length > 5) {
                            questionsHtml += `<div style="color: #6b7280; font-size: 12px; padding: 4px;">...and ${q.text_responses.length - 5} more</div>`;
                        }
                    } else {
                        questionsHtml += '<div style="color: #888; font-size: 12px;">No comments yet</div>';
                    }
                } else if (q.response_summary && Object.keys(q.response_summary).length > 0) {
                    // Show rating/choice distribution
                    const totalResponses = Object.values(q.response_summary).reduce((a, b) => a + b, 0);
                    questionsHtml += '<div style="display: flex; flex-wrap: wrap; gap: 6px;">';
                    
                    Object.entries(q.response_summary).forEach(([answer, count]) => {
                        const percentage = totalResponses > 0 ? Math.round((count / totalResponses) * 100) : 0;
                        const label = q.options && q.options[parseInt(answer) - 1] ? q.options[parseInt(answer) - 1] : answer;
                        questionsHtml += `
                            <div style="background: #e0e7ff; padding: 4px 10px; border-radius: 12px; font-size: 12px;">
                                ${this.escapeHtml(String(label))}: <strong>${count}</strong> (${percentage}%)
                            </div>
                        `;
                    });
                    questionsHtml += '</div>';
                } else {
                    questionsHtml += '<div style="color: #888; font-size: 12px;">No responses yet</div>';
                }
                
                questionsHtml += '</div>';
            });
            
            // Individual responses section
            let responsesHtml = `<h4 style="margin: 20px 0 12px 0; color: #374151;"><i class="fas fa-users"></i> Individual Responses (${data.responses.length})</h4>`;
            if (data.responses.length === 0) {
                responsesHtml += '<p style="color: #888; text-align: center;">No responses yet</p>';
            } else {
                data.responses.forEach(r => {
                    responsesHtml += `
                        <div style="padding: 10px; background: #f9fafb; border-radius: 6px; margin-bottom: 6px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                <strong>${this.escapeHtml(r.student_name)}</strong>
                                <span style="color: #6b7280; font-size: 11px;">${r.submitted_at ? new Date(r.submitted_at).toLocaleString() : 'N/A'}</span>
                            </div>
                        </div>
                    `;
                });
            }
            
            modal.innerHTML = `
                <div style="background: white; padding: 24px; border-radius: 12px; max-width: 800px; width: 95%; max-height: 85vh; overflow-y: auto;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid #e5e7eb; padding-bottom: 12px;">
                        <h3 style="margin: 0; color: #5b21b6;"><i class="fas fa-poll"></i> ${this.escapeHtml(data.survey.title)}</h3>
                        <button onclick="document.getElementById('surveyResponsesModal').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer;" data-testid="button-close-survey-modal">&times;</button>
                    </div>
                    ${statsHtml}
                    ${questionsHtml}
                    ${responsesHtml}
                </div>
            `;
            
            document.body.appendChild(modal);
            
        } catch (error) {
            console.error('Error loading survey details:', error);
            alert('Error loading survey details');
        }
    }
    
    async viewExamDetails(examId, examTitle) {
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/exams/${examId}/details`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                alert('Failed to load exam details');
                return;
            }
            
            const data = await response.json();
            
            const modal = document.createElement('div');
            modal.id = 'examDetailsModal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 20000;';
            
            // Statistics summary
            const stats = data.statistics;
            let statsHtml = `
                <div style="display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap;">
                    <div style="background: #dbeafe; padding: 10px 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: bold; color: #1d4ed8;">${stats.total_submissions}</div>
                        <div style="font-size: 11px; color: #1d4ed8;">Submissions</div>
                    </div>
                    <div style="background: #dcfce7; padding: 10px 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: bold; color: #166534;">${stats.passed_count}</div>
                        <div style="font-size: 11px; color: #166534;">Passed</div>
                    </div>
                    <div style="background: #fef2f2; padding: 10px 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: bold; color: #991b1b;">${stats.failed_count}</div>
                        <div style="font-size: 11px; color: #991b1b;">Failed</div>
                    </div>
                    <div style="background: #ede9fe; padding: 10px 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: bold; color: #5b21b6;">${stats.pass_rate}%</div>
                        <div style="font-size: 11px; color: #5b21b6;">Pass Rate</div>
                    </div>
                    <div style="background: #fef3c7; padding: 10px 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: bold; color: #854d0e;">${stats.avg_score}%</div>
                        <div style="font-size: 11px; color: #854d0e;">Avg Score</div>
                    </div>
                </div>
            `;
            
            // Questions section
            let questionsHtml = `<h4 style="margin: 16px 0 12px 0; color: #374151;"><i class="fas fa-list-ol"></i> Exam Questions (${data.questions.length})</h4>`;
            data.questions.forEach((q, idx) => {
                questionsHtml += `
                    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                        <div style="font-weight: 600; color: #374151; margin-bottom: 6px;">
                            Q${idx + 1}: ${this.escapeHtml(q.question_text)}
                            <span style="font-size: 11px; color: #6b7280; font-weight: normal;">(${q.question_type}, ${q.points} pts)</span>
                        </div>
                        ${q.options && q.options.length > 0 ? `
                            <div style="font-size: 12px; color: #666;">
                                Options: ${q.options.map((opt, i) => `<span style="background: ${q.correct_answer == (i+1) || q.correct_answer == opt ? '#dcfce7' : '#f3f4f6'}; padding: 2px 6px; border-radius: 4px; margin-right: 4px;">${opt}</span>`).join('')}
                            </div>
                        ` : ''}
                        <div style="font-size: 11px; color: #22c55e; margin-top: 4px;">
                            <i class="fas fa-check"></i> Correct: ${this.escapeHtml(String(q.correct_answer))}
                        </div>
                    </div>
                `;
            });
            
            // Student results
            let resultsHtml = `<h4 style="margin: 20px 0 12px 0; color: #374151;"><i class="fas fa-users"></i> Student Results (${data.results.length})</h4>`;
            if (data.results.length === 0) {
                resultsHtml += '<p style="color: #888; text-align: center;">No submissions yet</p>';
            } else {
                data.results.forEach(r => {
                    resultsHtml += `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: ${r.passed ? '#f0fdf4' : '#fef2f2'}; border-radius: 6px; margin-bottom: 6px;">
                            <div>
                                <strong>${this.escapeHtml(r.student_name)}</strong>
                                <span style="color: #6b7280; font-size: 12px; margin-left: 8px;">@${this.escapeHtml(r.student_username)}</span>
                                <div style="font-size: 11px; color: #888;">Attempt #${r.attempt_number} - ${r.submitted_at ? new Date(r.submitted_at).toLocaleString() : 'N/A'}</div>
                            </div>
                            <span style="background: ${r.passed ? '#dcfce7' : '#fef2f2'}; color: ${r.passed ? '#166534' : '#991b1b'}; padding: 6px 14px; border-radius: 20px; font-weight: 600;">
                                ${r.percentage}% ${r.passed ? '✓' : '✗'}
                            </span>
                        </div>
                    `;
                });
            }
            
            modal.innerHTML = `
                <div style="background: white; padding: 24px; border-radius: 12px; max-width: 800px; width: 95%; max-height: 85vh; overflow-y: auto;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid #e5e7eb; padding-bottom: 12px;">
                        <div>
                            <h3 style="margin: 0; color: #1d4ed8;"><i class="fas fa-file-alt"></i> ${this.escapeHtml(data.exam.title)}</h3>
                            <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">
                                Pass: ${data.exam.passing_threshold}% &bull; Max attempts: ${data.exam.max_attempts}
                                ${data.exam.time_limit_minutes ? ` &bull; Time: ${data.exam.time_limit_minutes}m` : ''}
                            </div>
                        </div>
                        <button onclick="document.getElementById('examDetailsModal').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer;" data-testid="button-close-exam-modal">&times;</button>
                    </div>
                    ${statsHtml}
                    ${questionsHtml}
                    ${resultsHtml}
                </div>
            `;
            
            document.body.appendChild(modal);
            
        } catch (error) {
            console.error('Error loading exam details:', error);
            alert('Error loading exam details');
        }
    }

    // ============================================
    // CERTIFICATES TAB
    // ============================================

    async loadCertificatesTab() {
        const container = document.getElementById('classDetailContent');
        if (!container) return;
        
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/certificates`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                container.innerHTML = '<p style="color: #ef4444; text-align: center; padding: 20px;">Failed to load certificates</p>';
                return;
            }
            
            const data = await response.json();
            
            if (!data.success || !data.certificates || data.certificates.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #888;">
                        <i class="fas fa-certificate fa-3x" style="margin-bottom: 16px; opacity: 0.5;"></i>
                        <p>No students enrolled for certificate tracking</p>
                    </div>
                `;
                return;
            }
            
            // Group by status
            const eligible = data.certificates.filter(c => c.all_exams_passed && !c.certificate_issued);
            const pending = data.certificates.filter(c => c.certificate_status === 'pending');
            const issued = data.certificates.filter(c => c.certificate_issued);
            const failed = data.certificates.filter(c => c.any_failed && !c.all_exams_passed);
            
            let html = `<h3 style="margin: 0 0 16px 0;"><i class="fas fa-certificate"></i> Certificate Management</h3>`;
            
            // Eligible for certificate
            if (eligible.length > 0) {
                html += `<h4 style="color: #166534; margin: 16px 0 12px 0;"><i class="fas fa-check-circle"></i> Eligible for Certificate (${eligible.length})</h4>`;
                html += eligible.map(c => this.renderCertificateCard(c, 'eligible')).join('');
            }
            
            // Pending approval
            if (pending.length > 0) {
                html += `<h4 style="color: #f59e0b; margin: 16px 0 12px 0;"><i class="fas fa-clock"></i> Pending Approval (${pending.length})</h4>`;
                html += pending.map(c => this.renderCertificateCard(c, 'pending')).join('');
            }
            
            // Already issued
            if (issued.length > 0) {
                html += `<h4 style="color: #1d4ed8; margin: 16px 0 12px 0;"><i class="fas fa-certificate"></i> Certificates Issued (${issued.length})</h4>`;
                html += issued.map(c => this.renderCertificateCard(c, 'issued')).join('');
            }
            
            // Failed - can force issue
            if (failed.length > 0) {
                html += `<h4 style="color: #991b1b; margin: 16px 0 12px 0;"><i class="fas fa-exclamation-triangle"></i> Failed Exams - Manual Review Required (${failed.length})</h4>`;
                html += failed.map(c => this.renderCertificateCard(c, 'failed')).join('');
            }
            
            container.innerHTML = html;
            
        } catch (error) {
            console.error('Error loading certificates:', error);
            container.innerHTML = '<p style="color: #ef4444; text-align: center; padding: 20px;">Error loading certificates</p>';
        }
    }

    renderCertificateCard(cert, status) {
        const examsSummary = cert.exam_results?.map(e => 
            `<span style="background: ${e.passed ? '#dcfce7' : '#fef2f2'}; color: ${e.passed ? '#166534' : '#991b1b'}; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 4px;">${this.escapeHtml(e.exam_title)}: ${e.score}%</span>`
        ).join('') || '';
        
        // Status badge based on certificate status
        let statusBadge = '';
        if (status === 'issued') {
            statusBadge = `<span style="background: #166534; color: white; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;">
                <i class="fas fa-check-circle"></i> Approved
            </span>`;
        } else if (status === 'eligible') {
            statusBadge = `<span style="background: #2563eb; color: white; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;">
                <i class="fas fa-star"></i> Eligible
            </span>`;
        } else if (status === 'pending') {
            statusBadge = `<span style="background: #f59e0b; color: white; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;">
                <i class="fas fa-clock"></i> Pending
            </span>`;
        } else if (status === 'failed') {
            statusBadge = `<span style="background: #dc2626; color: white; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;">
                <i class="fas fa-exclamation-triangle"></i> Review Required
            </span>`;
        }
        
        let actions = '';
        if (status === 'eligible' || status === 'pending') {
            actions = `
                <button onclick="classManagement.approveCertificate('${cert.enrollment_id}')" class="btn-primary" style="padding: 8px 16px; font-size: 13px;" data-testid="button-approve-${cert.enrollment_id}">
                    <i class="fas fa-check"></i> Approve and Issue
                </button>
            `;
        } else if (status === 'failed') {
            actions = `
                <button onclick="classManagement.forceIssueCertificate('${cert.enrollment_id}')" class="btn-secondary" style="padding: 8px 16px; font-size: 13px; background: #f59e0b; color: white; border: none;" data-testid="button-force-issue-${cert.enrollment_id}">
                    <i class="fas fa-certificate"></i> Force Issue
                </button>
            `;
        } else if (status === 'issued') {
            actions = `
                <div style="display: flex; flex-direction: column; gap: 8px; align-items: flex-end;">
                    <span style="color: #666; font-size: 12px;"><i class="fas fa-calendar"></i> Issued ${cert.certificate_issued_at ? new Date(cert.certificate_issued_at).toLocaleDateString() : ''}</span>
                    <button onclick="classManagement.viewCertificate('${cert.enrollment_id}')" class="btn-secondary" style="padding: 6px 12px; font-size: 13px;" data-testid="button-view-cert-${cert.enrollment_id}">
                        <i class="fas fa-eye"></i> View Certificate
                    </button>
                </div>
            `;
        }
        
        return `
            <div class="certificate-card" style="background: ${status === 'issued' ? '#f0fdf4' : '#f9fafb'}; border: 1px solid ${status === 'issued' ? '#86efac' : '#e5e7eb'}; border-radius: 8px; padding: 16px; margin-bottom: 12px;" data-testid="certificate-card-${cert.enrollment_id}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                            <h4 style="margin: 0; color: #1B5E20;">
                                <i class="fas fa-user-graduate"></i> ${this.escapeHtml(cert.student_name)}
                            </h4>
                            ${statusBadge}
                        </div>
                        <p style="margin: 0 0 8px 0; color: #666; font-size: 13px;">
                            @${this.escapeHtml(cert.student_username)} &bull; ${this.escapeHtml(cert.student_email || '')}
                        </p>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
                            <span style="background: #dbeafe; color: #1d4ed8; padding: 4px 10px; border-radius: 12px; font-size: 11px;">
                                Progress: ${cert.progress_percent}%
                            </span>
                            <span style="background: ${cert.all_exams_passed ? '#dcfce7' : '#fef2f2'}; color: ${cert.all_exams_passed ? '#166534' : '#991b1b'}; padding: 4px 10px; border-radius: 12px; font-size: 11px;">
                                Exams: ${cert.exams_passed}/${cert.total_exams}
                            </span>
                        </div>
                        <div style="margin-top: 8px;">
                            ${examsSummary}
                        </div>
                    </div>
                    <div>
                        ${actions}
                    </div>
                </div>
            </div>
        `;
    }

    async approveCertificate(enrollmentId) {
        if (!confirm('Approve and issue certificate for this student?')) return;
        
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/certificates/${enrollmentId}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                alert(data.error || 'Failed to approve certificate');
                return;
            }
            
            this.showNotification('Certificate approved!', 'success');
            await this.loadCertificatesTab();
            
        } catch (error) {
            console.error('Error approving certificate:', error);
            alert('Error approving certificate');
        }
    }

    async forceIssueCertificate(enrollmentId) {
        if (!confirm('Force issue certificate even though the student failed some exams? This action will be logged.')) return;
        
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/certificates/${enrollmentId}/force-issue`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                alert(data.error || 'Failed to force issue certificate');
                return;
            }
            
            this.showNotification('Certificate force issued!', 'success');
            await this.loadCertificatesTab();
            
        } catch (error) {
            console.error('Error force issuing certificate:', error);
            alert('Error force issuing certificate');
        }
    }

    async viewStudentExams(studentId, studentName) {
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/students/${studentId}/exams`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                alert('Failed to load student exams');
                return;
            }
            
            const data = await response.json();
            
            const modal = document.createElement('div');
            modal.id = 'studentExamsModal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 20000;';
            
            let examsHtml = '';
            if (!data.exams || data.exams.length === 0) {
                examsHtml = '<p style="color: #888; text-align: center; padding: 20px;">No exams in this class</p>';
            } else {
                for (const exam of data.exams) {
                    const attemptsHtml = exam.attempts.length === 0 
                        ? '<p style="color: #888; font-size: 13px; margin: 8px 0 0 0;">No attempts yet</p>'
                        : exam.attempts.map(a => `
                            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: ${a.passed ? '#f0fdf4' : '#fef2f2'}; border-radius: 4px; margin-top: 6px;">
                                <span>Attempt #${a.attempt_number} - ${a.submitted_at ? new Date(a.submitted_at).toLocaleDateString() : 'In progress'}</span>
                                <span style="font-weight: 600; color: ${a.passed ? '#166534' : '#991b1b'};">${a.score || 0}% ${a.passed ? '✓' : '✗'}</span>
                            </div>
                        `).join('');
                    
                    examsHtml += `
                        <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h4 style="margin: 0; color: #1d4ed8;">
                                    <i class="fas fa-file-alt"></i> ${this.escapeHtml(exam.exam_title)}
                                </h4>
                                <span style="background: ${exam.latest_passed ? '#dcfce7' : exam.attempts_count > 0 ? '#fef2f2' : '#f3f4f6'}; 
                                       color: ${exam.latest_passed ? '#166534' : exam.attempts_count > 0 ? '#991b1b' : '#6b7280'}; 
                                       padding: 4px 12px; border-radius: 20px; font-size: 12px;">
                                    ${exam.latest_passed ? 'Passed' : exam.attempts_count > 0 ? 'Failed' : 'Not Attempted'}
                                </span>
                            </div>
                            <p style="margin: 8px 0 0 0; color: #666; font-size: 13px;">
                                Pass threshold: ${exam.passing_threshold}% | Best score: ${exam.best_score}% | Attempts: ${exam.attempts_count}/${exam.max_attempts}
                            </p>
                            ${attemptsHtml}
                        </div>
                    `;
                }
            }
            
            modal.innerHTML = `
                <div style="background: white; padding: 24px; border-radius: 12px; max-width: 700px; width: 95%; max-height: 80vh; overflow-y: auto;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <div>
                            <h3 style="margin: 0;"><i class="fas fa-user-graduate"></i> ${this.escapeHtml(studentName)}</h3>
                            <p style="margin: 4px 0 0 0; color: #666; font-size: 13px;">Exam History</p>
                        </div>
                        <button onclick="document.getElementById('studentExamsModal').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer;" data-testid="button-close-student-exams">&times;</button>
                    </div>
                    <div style="max-height: 500px; overflow-y: auto;">
                        ${examsHtml}
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
        } catch (error) {
            console.error('Error loading student exams:', error);
            alert('Error loading student exams');
        }
    }

    async editExam(examId) {
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/exams/${examId}`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                alert('Failed to load exam details');
                return;
            }
            
            const data = await response.json();
            const exam = data.exam;
            
            const modal = document.createElement('div');
            modal.id = 'editExamModal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 20000;';
            
            modal.innerHTML = `
                <div style="background: white; padding: 24px; border-radius: 12px; max-width: 600px; width: 95%; max-height: 85vh; overflow-y: auto;">
                    <h3 style="margin: 0 0 20px 0;"><i class="fas fa-edit"></i> Edit Exam</h3>
                    <form id="editExamForm">
                        <div style="display: grid; gap: 16px;">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Title (English)</label>
                                    <input type="text" id="examTitle" value="${this.escapeHtml(exam.title)}" required
                                           style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="input-exam-title">
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Title (Arabic) العنوان</label>
                                    <input type="text" id="examTitleAr" value="${this.escapeHtml(exam.title_ar || '')}"
                                           style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px; direction: rtl; text-align: right;" data-testid="input-exam-title-ar">
                                </div>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Description (English)</label>
                                    <textarea id="examDescription" rows="3" style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="input-exam-description">${this.escapeHtml(exam.description || '')}</textarea>
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Description (Arabic) الوصف</label>
                                    <textarea id="examDescriptionAr" rows="3" style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px; direction: rtl; text-align: right;" data-testid="input-exam-description-ar">${this.escapeHtml(exam.description_ar || '')}</textarea>
                                </div>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Exam Type</label>
                                    <select id="examType" style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="select-exam-type">
                                        <option value="quiz" ${exam.exam_type === 'quiz' ? 'selected' : ''}>Quiz</option>
                                        <option value="midterm" ${exam.exam_type === 'midterm' ? 'selected' : ''}>Midterm</option>
                                        <option value="final" ${exam.exam_type === 'final' ? 'selected' : ''}>Final</option>
                                        <option value="practice" ${exam.exam_type === 'practice' ? 'selected' : ''}>Practice</option>
                                        <option value="exit_exam" ${exam.exam_type === 'exit_exam' ? 'selected' : ''}>Exit Exam</option>
                                    </select>
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Pass Threshold (%)</label>
                                    <input type="number" id="examPassThreshold" value="${exam.passing_threshold || 60}" min="0" max="100"
                                           style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="input-pass-threshold">
                                </div>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Max Attempts</label>
                                    <input type="number" id="examMaxAttempts" value="${exam.max_attempts || 1}" min="1" max="10"
                                           style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="input-max-attempts">
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 4px; font-weight: 500;">Time Limit (minutes)</label>
                                    <input type="number" id="examTimeLimit" value="${exam.time_limit_minutes || ''}" min="0" placeholder="No limit"
                                           style="width: 100%; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" data-testid="input-time-limit">
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <input type="checkbox" id="examPublished" ${exam.is_published ? 'checked' : ''} data-testid="checkbox-published">
                                <label for="examPublished">Published (visible to students)</label>
                            </div>
                        </div>
                        <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 24px;">
                            <button type="button" onclick="document.getElementById('editExamModal').remove()" class="btn-secondary" data-testid="button-cancel-edit-exam">Cancel</button>
                            <button type="submit" class="btn-primary" data-testid="button-save-exam">
                                <i class="fas fa-save"></i> Save Changes
                            </button>
                        </div>
                    </form>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            document.getElementById('editExamForm').onsubmit = async (e) => {
                e.preventDefault();
                await this.saveExamChanges(examId);
            };
            
        } catch (error) {
            console.error('Error loading exam for edit:', error);
            alert('Error loading exam details');
        }
    }

    async saveExamChanges(examId) {
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/exams/${examId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: document.getElementById('examTitle').value,
                    title_ar: document.getElementById('examTitleAr')?.value || '',
                    description: document.getElementById('examDescription').value,
                    description_ar: document.getElementById('examDescriptionAr')?.value || '',
                    exam_type: document.getElementById('examType').value,
                    passing_threshold: parseInt(document.getElementById('examPassThreshold').value) || 60,
                    max_attempts: parseInt(document.getElementById('examMaxAttempts').value) || 1,
                    time_limit_minutes: parseInt(document.getElementById('examTimeLimit').value) || null,
                    is_published: document.getElementById('examPublished').checked
                }),
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                alert(data.error || 'Failed to save exam');
                return;
            }
            
            document.getElementById('editExamModal').remove();
            this.showNotification('Exam updated successfully', 'success');
            await this.loadExamsTab();
            
        } catch (error) {
            console.error('Error saving exam:', error);
            alert('Error saving exam');
        }
    }

    async viewCertificate(enrollmentId) {
        try {
            const response = await fetch(`/api/classes/${this.currentClass.id}/certificates/${enrollmentId}/view`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                const data = await response.json();
                alert(data.error || 'Failed to load certificate');
                return;
            }
            
            const data = await response.json();
            const cert = data.certificate;
            
            const modal = document.createElement('div');
            modal.id = 'viewCertificateModal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 20000;';
            
            modal.innerHTML = `
                <div style="background: white; border-radius: 12px; max-width: 700px; width: 95%; overflow: hidden;">
                    <div style="background: linear-gradient(135deg, #1B5E20, #2E7D32); padding: 20px 24px; text-align: center;">
                        <h2 style="margin: 0; color: white;"><i class="fas fa-certificate"></i> Certificate of Completion</h2>
                        <p style="margin: 4px 0 0 0; color: rgba(255,255,255,0.8); font-size: 13px;">SkillPilot</p>
                    </div>
                    
                    <div style="padding: 32px; text-align: center; background: linear-gradient(180deg, #f9fafb, white);">
                        <p style="color: #666; font-size: 14px; margin: 0 0 8px 0;">This is to certify that</p>
                        <h3 style="margin: 0 0 16px 0; color: #1B5E20; font-size: 28px; font-weight: 600;">${this.escapeHtml(cert.student_name)}</h3>
                        
                        <p style="color: #666; font-size: 14px; margin: 0 0 8px 0;">has successfully completed the course</p>
                        <h4 style="margin: 0 0 24px 0; color: #374151; font-size: 20px;">${this.escapeHtml(cert.course_title)}</h4>
                        
                        <div style="display: flex; justify-content: center; gap: 32px; margin: 24px 0; flex-wrap: wrap;">
                            <div style="text-align: center;">
                                <div style="font-size: 24px; font-weight: bold; color: #1d4ed8;">${cert.final_grade}%</div>
                                <div style="font-size: 12px; color: #6b7280;">Final Grade</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 24px; font-weight: bold; color: #166534;">${cert.exams_completed}/${cert.total_exams}</div>
                                <div style="font-size: 12px; color: #6b7280;">Exams Completed</div>
                            </div>
                        </div>
                        
                        <div style="border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 20px;">
                            <p style="margin: 0; font-size: 13px; color: #6b7280;">
                                Certificate Number: <strong>${this.escapeHtml(cert.certificate_number)}</strong>
                            </p>
                            <p style="margin: 8px 0 0 0; font-size: 13px; color: #6b7280;">
                                Issue Date: <strong>${cert.issue_date ? new Date(cert.issue_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A'}</strong>
                            </p>
                        </div>
                    </div>
                    
                    <div style="padding: 16px 24px; border-top: 1px solid #e5e7eb; display: flex; gap: 12px; justify-content: flex-end;">
                        <button onclick="classManagement.downloadCertificate('${enrollmentId}')" class="btn-secondary" data-testid="button-download-certificate">
                            <i class="fas fa-download"></i> Download PDF
                        </button>
                        <button onclick="document.getElementById('viewCertificateModal').remove()" class="btn-primary" data-testid="button-close-certificate">
                            Close
                        </button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
        } catch (error) {
            console.error('Error loading certificate:', error);
            alert('Error loading certificate');
        }
    }

    async downloadCertificate(enrollmentId) {
        this.showNotification('Preparing certificate download...', 'info');
        
        try {
            // Use server-side PDF generation with logos, stamps, and signatures
            const response = await fetch(`/api/classes/${this.currentClass.id}/certificates/${enrollmentId}/download`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to download certificate');
            }
            
            // Get the PDF blob and download it
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `certificate-${enrollmentId}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showNotification('Certificate downloaded!', 'success');
        } catch (error) {
            console.error('Error downloading PDF:', error);
            this.showNotification('Error downloading certificate: ' + error.message, 'error');
        }
    }
}

const classManagement = new ClassManagement();
