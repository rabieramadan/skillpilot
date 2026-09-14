// SkillPilot - Class Management Module

class ClassManager {
    constructor() {
        this.currentUserRole = null;
        this.init();
    }

    async init() {
        // Check user auth status to determine role
        await this.checkUserRole();
        this.setupEventListeners();
    }

    async checkUserRole() {
        try {
            const response = await fetch('/api/auth/check');
            const data = await response.json();
            
            if (data.is_logged_in && data.user_id) {
                // Fetch user details to get role
                const usersResponse = await fetch('/api/classes/instructors');
                if (usersResponse.ok) {
                    const usersData = await usersResponse.json();
                    // Check if current user is an instructor
                    const isInstructor = usersData.instructors.some(i => i.user_id === data.user_id);
                    this.currentUserRole = isInstructor ? 'Instructor' : 'Student';
                }
            }
        } catch (error) {
            console.error('Error checking user role:', error);
        }
    }

    setupEventListeners() {
        // Create Instructor Form
        const createInstructorForm = document.getElementById('createInstructorForm');
        if (createInstructorForm) {
            createInstructorForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createInstructor();
            });
        }

        // Create Class Form
        const createClassForm = document.getElementById('createClassForm');
        if (createClassForm) {
            createClassForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createClass();
            });
        }
    }

    // ============================================
    // Instructor Management
    // ============================================

    async showCreateInstructorModal() {
        const modal = document.getElementById('createInstructorModal');
        const userSelect = document.getElementById('instructorUserId');
        
        // Load all users to populate dropdown
        try {
            const response = await fetch('/api/auth/users');
            if (response.ok) {
                const data = await response.json();
                userSelect.innerHTML = '<option value="">-- Select a user to make instructor --</option>';
                
                data.users.forEach(user => {
                    // Only show non-instructor users
                    if (user.role !== 'Instructor') {
                        const option = document.createElement('option');
                        option.value = user.user_id;
                        option.textContent = `${user.full_name} (${user.email})`;
                        userSelect.appendChild(option);
                    }
                });
            }
        } catch (error) {
            console.error('Error loading users:', error);
        }
        
        modal.classList.add('show');
    }

    closeCreateInstructorModal() {
        document.getElementById('createInstructorModal').classList.remove('show');
        document.getElementById('createInstructorForm').reset();
        document.getElementById('instructorError').style.display = 'none';
    }

    async createInstructor() {
        const userId = document.getElementById('instructorUserId').value;
        const bio = document.getElementById('instructorBio').value.trim();
        const expertiseText = document.getElementById('instructorExpertise').value.trim();
        const expertise = expertiseText ? expertiseText.split(',').map(e => e.trim()) : [];
        
        const errorDiv = document.getElementById('instructorError');
        
        if (!userId) {
            errorDiv.textContent = 'Please select a user';
            errorDiv.style.display = 'block';
            return;
        }
        
        try {
            const response = await fetch('/api/classes/instructors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, bio, expertise })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.closeCreateInstructorModal();
                this.showNotification('Instructor created successfully', 'success');
                this.loadInstructors();
            } else {
                errorDiv.textContent = data.error || 'Failed to create instructor';
                errorDiv.style.display = 'block';
            }
        } catch (error) {
            errorDiv.textContent = 'Error creating instructor';
            errorDiv.style.display = 'block';
        }
    }

    async loadInstructors() {
        try {
            const response = await fetch('/api/classes/instructors');
            if (response.ok) {
                const data = await response.json();
                this.displayInstructors(data.instructors);
            }
        } catch (error) {
            console.error('Error loading instructors:', error);
        }
    }

    displayInstructors(instructors) {
        const container = document.getElementById('instructorsList');
        if (!container) return;
        
        if (instructors.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #666;"><i class="fas fa-info-circle"></i> No instructors found. Add an instructor to get started.</p>';
            return;
        }
        
        container.innerHTML = instructors.map(instructor => `
            <div class="instructor-card" data-testid="instructor-${instructor.instructor_id}">
                <div class="instructor-header">
                    <i class="fas fa-user-tie fa-2x"></i>
                    <h4>${instructor.full_name}</h4>
                </div>
                <p><i class="fas fa-envelope"></i> ${instructor.email}</p>
                ${instructor.bio ? `<p><i class="fas fa-info-circle"></i> ${instructor.bio}</p>` : ''}
                ${instructor.expertise && instructor.expertise.length > 0 ? `
                    <div class="expertise-tags">
                        ${instructor.expertise.map(exp => `<span class="tag">${exp}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `).join('');
    }

    // ============================================
    // Class Management
    // ============================================

    async showCreateClassModal() {
        const isAdmin = sessionStorage.getItem('is_admin') === 'true' || window.app?.isAdmin;
        const instructorField = document.querySelector('.admin-only-field');
        
        // Show instructor selection field for both admin and instructors
        if (instructorField) {
            instructorField.style.display = 'block';
        }
        
        // Load and populate instructors
        try {
            const response = await fetch('/api/classes/instructors');
            if (response.ok) {
                const data = await response.json();
                const instructorSelect = document.getElementById('classInstructors');
                
                if (instructorSelect && data.instructors) {
                    instructorSelect.innerHTML = data.instructors.map(inst => 
                        `<option value="${inst.instructor_id}">${inst.full_name}</option>`
                    ).join('');
                    
                    // Auto-select current instructor if they're not admin
                    if (!isAdmin) {
                        const authResponse = await fetch('/api/auth/check');
                        const authData = await authResponse.json();
                        
                        if (authData.is_logged_in && authData.user_id) {
                            // Find the instructor record for current user
                            const currentInstructor = data.instructors.find(inst => inst.user_id === authData.user_id);
                            if (currentInstructor) {
                                // Auto-select current instructor
                                Array.from(instructorSelect.options).forEach(opt => {
                                    if (opt.value === currentInstructor.instructor_id) {
                                        opt.selected = true;
                                    }
                                });
                            }
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error loading instructors:', error);
        }
        
        // Set default year to current year
        const yearInput = document.getElementById('classYear');
        if (yearInput && !yearInput.value) {
            yearInput.value = new Date().getFullYear();
        }
        
        document.getElementById('createClassModal').classList.add('show');
    }

    closeCreateClassModal() {
        document.getElementById('createClassModal').classList.remove('show');
        document.getElementById('createClassForm').reset();
        document.getElementById('classError').style.display = 'none';
    }

    async createClass() {
        const title = document.getElementById('classTitle').value.trim();
        const description = document.getElementById('classDescription').value.trim();
        const courseType = document.getElementById('classCourseType').value;
        const semester = document.getElementById('classSemester').value;
        const year = parseInt(document.getElementById('classYear').value);
        const startDate = document.getElementById('classStartDate').value;
        const endDate = document.getElementById('classEndDate').value;
        const schedule = document.getElementById('classSchedule').value.trim();
        const capacity = parseInt(document.getElementById('classCapacity').value);
        
        // Get pricing type
        const pricingType = document.querySelector('input[name="pricingType"]:checked').value;
        const price = pricingType === 'paid' ? parseFloat(document.getElementById('classPrice').value) : null;
        const paymentUrl = pricingType === 'paid' ? document.getElementById('classPaymentUrl').value.trim() : '';
        
        // Get course content
        const courseContent = document.getElementById('classCourseContent').value.trim();
        
        // Get visibility setting
        const isEnabled = document.getElementById('classIsEnabled').checked;
        
        const errorDiv = document.getElementById('classError');
        
        if (!title) {
            errorDiv.textContent = 'Class title is required';
            errorDiv.style.display = 'block';
            return;
        }
        
        if (!courseType) {
            errorDiv.textContent = 'Course type is required';
            errorDiv.style.display = 'block';
            return;
        }
        
        if (!semester) {
            errorDiv.textContent = 'Semester is required';
            errorDiv.style.display = 'block';
            return;
        }
        
        if (!year || year < 2020 || year > 2030) {
            errorDiv.textContent = 'Valid year is required (2020-2030)';
            errorDiv.style.display = 'block';
            return;
        }
        
        if (pricingType === 'paid' && (!price || price <= 0)) {
            errorDiv.textContent = 'Valid price is required for paid courses';
            errorDiv.style.display = 'block';
            return;
        }
        
        // Get meeting links
        const meetLink = document.getElementById('classMeetLink').value.trim();
        const zoomLink = document.getElementById('classZoomLink').value.trim();
        const youtubeLink = document.getElementById('classYoutubeLink').value.trim();
        
        // Build class data
        const classData = {
            title,
            description,
            course_type: courseType,
            semester: `${semester} ${year}`,
            start_date: startDate || null,
            end_date: endDate || null,
            schedule,
            capacity,
            pricing_type: pricingType,
            price: price,
            payment_url: paymentUrl,
            course_content: courseContent,
            is_enabled: isEnabled,
            meet_link: meetLink || null,
            zoom_link: zoomLink || null,
            youtube_broadcast_link: youtubeLink || null
        };
        
        // If admin and multiple instructors selected
        const instructorSelect = document.getElementById('classInstructors');
        if (instructorSelect && instructorSelect.options) {
            const selectedInstructors = Array.from(instructorSelect.selectedOptions).map(opt => opt.value);
            if (selectedInstructors.length > 0) {
                classData.instructor_ids = selectedInstructors;
            }
        }
        
        try {
            const response = await fetch('/api/classes/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(classData)
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.closeCreateClassModal();
                this.showNotification('Class created successfully', 'success');
                this.loadInstructorClasses();
                this.loadAllClasses();
            } else {
                errorDiv.textContent = data.error || 'Failed to create class';
                errorDiv.style.display = 'block';
            }
        } catch (error) {
            errorDiv.textContent = 'Error creating class';
            errorDiv.style.display = 'block';
        }
    }

    async loadInstructorClasses() {
        try {
            const response = await fetch('/api/classes/list');
            if (response.ok) {
                const data = await response.json();
                this.displayInstructorClasses(data.classes);
            }
        } catch (error) {
            console.error('Error loading instructor classes:', error);
        }
    }

    displayInstructorClasses(classes) {
        const container = document.getElementById('instructorClasses');
        if (!container) return;
        
        if (classes.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #666;"><i class="fas fa-info-circle"></i> No classes found. Create a class to get started.</p>';
            return;
        }
        
        container.innerHTML = classes.map(cls => {
            const regOpen = cls.registration_open !== false;
            const regIcon = regOpen ? 'user-plus' : 'user-slash';
            const regLabel = regOpen ? 'Close Registration' : 'Open Registration';
            const regColor = regOpen ? '#e65100' : '#2e7d32';
            const regBadge = regOpen
                ? '<span style="background:#e8f5e9;color:#2e7d32;border-radius:10px;padding:2px 10px;font-size:.78rem;font-weight:700;"><i class="fas fa-door-open"></i> Registration Open</span>'
                : '<span style="background:#ffebee;color:#c62828;border-radius:10px;padding:2px 10px;font-size:.78rem;font-weight:700;"><i class="fas fa-lock"></i> Registration Closed</span>';
            return `
            <div class="class-card" data-testid="class-${cls.class_id}" style="position:relative;">
                <div class="class-header" style="cursor:pointer;" onclick="app.classManager.viewClassDetails('${cls.class_id}')">
                    <h4><i class="fas fa-chalkboard"></i> ${SKP.escape(cls.title)}</h4>
                    <span class="class-badge"><i class="fas fa-arrow-right"></i> View Details</span>
                </div>
                <div style="margin:8px 0 4px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                    ${regBadge}
                    <button onclick="app.classManager.toggleClassRegistration('${cls.class_id}', ${!regOpen}, this)"
                        style="background:${regColor};color:#fff;border:none;border-radius:8px;padding:5px 14px;font-size:.82rem;cursor:pointer;font-weight:600;"
                        data-testid="button-reg-toggle-${cls.class_id}" title="${regLabel}">
                        <i class="fas fa-${regIcon}"></i> ${regLabel}
                    </button>
                </div>
                ${cls.description ? `<p style="cursor:pointer;" onclick="app.classManager.viewClassDetails('${cls.class_id}')">${SKP.escape(cls.description)}</p>` : ''}
                ${cls.schedule ? `<p><i class="fas fa-clock"></i> ${SKP.escape(cls.schedule)}</p>` : ''}
                <p><i class="fas fa-users"></i> Capacity: ${cls.capacity || 30}</p>
                <p><i class="fas fa-calendar"></i> ${SKP.escape((cls.semester || '') + ' ' + (cls.year || '')).trim()}</p>
            </div>`;
        }).join('');
    }

    async toggleClassRegistration(courseId, openState, btn) {
        const origText = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; }
        try {
            const resp = await fetch(`/api/classes/${encodeURIComponent(courseId)}/registration`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ registration_open: openState })
            });
            const data = await resp.json();
            if (data.success) {
                await this.loadInstructorClasses();
            } else {
                alert(data.error || 'Failed to update registration status');
                if (btn) { btn.disabled = false; btn.innerHTML = origText; }
            }
        } catch (e) {
            alert('Network error: ' + e.message);
            if (btn) { btn.disabled = false; btn.innerHTML = origText; }
        }
    }

    async loadAllClasses(containerId = 'allClassesList') {
        try {
            const response = await fetch('/api/classes/list');
            if (response.ok) {
                const data = await response.json();
                this.displayAllClasses(data.classes, containerId);
            }
        } catch (error) {
            console.error('Error loading all classes:', error);
        }
    }

    displayAllClasses(classes, containerId = 'allClassesList') {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        if (classes.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #666;"><i class="fas fa-info-circle"></i> No classes found.</p>';
            return;
        }
        
        container.innerHTML = classes.map(cls => `
            <div class="class-card clickable" data-testid="class-${cls.class_id}" onclick="app.classManager.viewClassDetails('${cls.class_id}')" style="cursor: pointer;">
                <div class="class-header">
                    <h4><i class="fas fa-chalkboard"></i> ${cls.title}</h4>
                    <span class="class-badge"><i class="fas fa-arrow-right"></i> View Details</span>
                </div>
                ${cls.description ? `<p>${cls.description}</p>` : ''}
                <p><i class="fas fa-user-tie"></i> Instructor: ${cls.instructor_name}</p>
                ${cls.schedule ? `<p><i class="fas fa-clock"></i> ${cls.schedule}</p>` : ''}
                <p><i class="fas fa-users"></i> Capacity: ${cls.capacity || 30}</p>
            </div>
        `).join('');
    }

    async loadCoursesManagementTable() {
        try {
            const response = await fetch('/api/classes/list');
            if (response.ok) {
                const data = await response.json();
                this.displayCoursesManagementTable(data.classes);
            }
        } catch (error) {
            console.error('Error loading courses management table:', error);
        }
    }

    displayCoursesManagementTable(classes) {
        const tbody = document.getElementById('coursesTableBody');
        if (!tbody) return;
        
        if (classes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 40px; color: #666;"><i class="fas fa-info-circle"></i> No courses found. Create a course to get started.</td></tr>';
            return;
        }
        
        tbody.innerHTML = classes.map(cls => {
            const courseType = cls.course_type || 'N/A';
            const pricing = cls.pricing_type === 'paid' ? `Paid (${cls.price || 0} OMR)` : 'Free';
            const instructors = cls.instructor_name || 'Not assigned';
            const studentCount = cls.student_count || 0;
            const isEnabled = cls.is_enabled !== false; // Default to true if not set
            
            return `
                <tr data-testid="course-row-${cls.class_id}">
                    <td><strong>${cls.title}</strong></td>
                    <td>${courseType}</td>
                    <td>${pricing}</td>
                    <td>${instructors}</td>
                    <td>${studentCount}</td>
                    <td>
                        <label class="toggle-switch" data-testid="toggle-visible-${cls.class_id}">
                            <input type="checkbox" ${isEnabled ? 'checked' : ''} onchange="app.classManager.toggleCourseVisibility('${cls.class_id}', this.checked)">
                            <span class="toggle-slider"></span>
                        </label>
                    </td>
                    <td>
                        <button class="btn-sm btn-secondary" onclick="app.classManager.viewClassDetails('${cls.class_id}')" data-testid="button-edit-${cls.class_id}" title="Edit Course">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-sm btn-danger" onclick="app.classManager.deleteCourse('${cls.class_id}')" data-testid="button-delete-${cls.class_id}" title="Delete Course" style="margin-left: 5px;">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    async toggleCourseVisibility(classId, isEnabled) {
        try {
            const response = await fetch(`/api/classes/${classId}/toggle-visibility`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_enabled: isEnabled })
            });
            
            if (response.ok) {
                this.showNotification(
                    `Course ${isEnabled ? 'shown' : 'hidden'} successfully`, 
                    'success'
                );
            } else {
                const data = await response.json();
                this.showNotification(data.error || 'Failed to update course visibility', 'error');
                // Reload to revert the toggle
                this.loadCoursesManagementTable();
            }
        } catch (error) {
            this.showNotification('Error updating course visibility', 'error');
            // Reload to revert the toggle
            this.loadCoursesManagementTable();
        }
    }

    async deleteCourse(classId) {
        if (!confirm('⚠️ Are you sure you want to delete this course?\n\nThis will permanently remove:\n• The course and all its data\n• All student enrollments\n• All course materials\n\nThis action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/classes/${classId}`, { method: 'DELETE' });
            
            if (response.ok) {
                this.showNotification('Course deleted successfully', 'success');
                this.loadCoursesManagementTable();
            } else {
                const data = await response.json();
                this.showNotification(data.error || 'Failed to delete course', 'error');
            }
        } catch (error) {
            this.showNotification('Error deleting course', 'error');
        }
    }

    async deleteClass(classId) {
        if (!confirm('Are you sure you want to delete this class? All enrollments will be removed.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/classes/${classId}`, { method: 'DELETE' });
            
            if (response.ok) {
                this.showNotification('Class deleted successfully', 'success');
                this.loadInstructorClasses();
                this.loadAllClasses();
            } else {
                const data = await response.json();
                this.showNotification(data.error || 'Failed to delete class', 'error');
            }
        } catch (error) {
            this.showNotification('Error deleting class', 'error');
        }
    }

    async showClassDetails(classId) {
        try {
            const response = await fetch(`/api/classes/${classId}/enrollments`);
            if (response.ok) {
                const data = await response.json();
                await this.displayClassDetails(classId, data.enrollments);
            }
        } catch (error) {
            console.error('Error loading class details:', error);
        }
    }

    async displayClassDetails(classId, enrollments) {
        const modal = document.getElementById('classDetailsModal');
        const contentDiv = document.getElementById('classEnrollmentsList');
        
        // Load course files
        const files = await this.loadCourseFiles(classId);
        
        let enrollmentsHtml = '';
        if (enrollments.length === 0) {
            enrollmentsHtml = '<p style="text-align: center; color: #666;"><i class="fas fa-info-circle"></i> No students enrolled yet.</p>';
        } else {
            enrollmentsHtml = `
                <h4><i class="fas fa-users"></i> Enrolled Students (${enrollments.length})</h4>
                <table class="certificate-table">
                    <thead>
                        <tr>
                            <th>Student Name</th>
                            <th>Email</th>
                            <th>Enrolled Date</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${enrollments.map(e => `
                            <tr>
                                <td>${e.student_name}</td>
                                <td>${e.student_email}</td>
                                <td>${new Date(e.enrolled_at).toLocaleDateString()}</td>
                                <td><span class="status-badge status-${e.status}">${e.status}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
        
        // File management section (admin only)
        const filesHtml = `
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                <h4><i class="fas fa-folder-open"></i> Course Files</h4>
                <div style="margin: 15px 0;">
                    <input type="file" id="courseFileInput_${classId}" style="display: inline-block; margin-right: 10px;" data-testid="input-course-file">
                    <button class="btn-primary btn-sm" onclick="app.classManager.uploadCourseFile('${classId}', document.getElementById('courseFileInput_${classId}')).then(success => { if(success) app.classManager.showClassDetails('${classId}'); })" data-testid="button-upload-file">
                        <i class="fas fa-upload"></i> Upload File
                    </button>
                </div>
                ${this.displayCourseFiles(files, classId, true)}
            </div>
        `;
        
        contentDiv.innerHTML = enrollmentsHtml + filesHtml;
        modal.classList.add('show');
    }

    closeClassDetailsModal() {
        document.getElementById('classDetailsModal').classList.remove('show');
    }

    // ============================================
    // Student Enrollment
    // ============================================

    async loadAvailableClasses() {
        try {
            const response = await fetch('/api/classes/available');
            if (response.ok) {
                const data = await response.json();
                this.displayAvailableClasses(data.classes);
            }
        } catch (error) {
            console.error('Error loading available classes:', error);
        }
    }

    displayAvailableClasses(classes) {
        const container = document.getElementById('availableClasses');
        if (!container) return;
        
        if (classes.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #666;"><i class="fas fa-info-circle"></i> No classes available.</p>';
            return;
        }
        
        container.innerHTML = classes.map(cls => `
            <div class="class-card ${cls.is_enrolled ? 'enrolled' : ''} ${cls.is_full ? 'full' : ''}" data-testid="available-class-${cls.class_id}">
                <div class="class-header">
                    <h4><i class="fas fa-chalkboard"></i> ${cls.title}</h4>
                    ${cls.is_enrolled ? '<span class="enrolled-badge"><i class="fas fa-check"></i> Enrolled</span>' : ''}
                </div>
                ${cls.description ? `<p>${cls.description}</p>` : ''}
                <p><i class="fas fa-user-tie"></i> Instructor: ${cls.instructor_name}</p>
                ${cls.schedule ? `<p><i class="fas fa-clock"></i> ${cls.schedule}</p>` : ''}
                <p><i class="fas fa-users"></i> ${cls.current_enrollment}/${cls.capacity || 30} enrolled</p>
                ${!cls.is_enrolled && !cls.is_full ? `
                    <button class="btn-primary" onclick="app.classManager.enrollInClass('${cls.class_id}')" data-testid="button-enroll-${cls.class_id}">
                        <i class="fas fa-user-plus"></i> Enroll
                    </button>
                ` : ''}
                ${cls.is_full && !cls.is_enrolled ? '<p style="color: #dc3545;"><i class="fas fa-exclamation-circle"></i> Class Full</p>' : ''}
            </div>
        `).join('');
    }

    async loadMyEnrollments() {
        try {
            const response = await fetch('/api/classes/enrollments/my');
            if (response.ok) {
                const data = await response.json();
                this.displayMyEnrollments(data.enrollments);
            }
        } catch (error) {
            console.error('Error loading my enrollments:', error);
        }
    }

    displayMyEnrollments(enrollments) {
        const container = document.getElementById('myEnrolledClasses');
        if (!container) return;
        
        console.log(`Total enrollments received: ${enrollments.length}`);
        
        // Filter to only show active (approved) enrollments
        const activeEnrollments = enrollments.filter(e => {
            return e.status === 'approved' || 
                   e.status === 'active' || 
                   e.enrollment_status === 'active';
        });
        
        console.log(`Active enrollments to display: ${activeEnrollments.length}`);
        
        if (activeEnrollments.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #666;"><i class="fas fa-info-circle"></i> You are not enrolled in any classes yet.</p>';
            return;
        }
        
        container.innerHTML = activeEnrollments.map(e => {
            const courseType = e.course_type || 'prompt_engineering';
            const courseTypeLabel = {
                'prompt_engineering': 'Prompt Engineering',
                'ethics_certificate': 'Ethics Certificate',
                'agentic_ai': 'Agentic AI'
            }[courseType] || courseType;
            
            // Build course-specific action buttons
            let actionButtons = `
                <button class="btn-primary btn-sm" onclick="app.classManager.showClassFiles('${e.class_id}', '${e.class_title}')" data-testid="button-view-files-${e.enrollment_id}">
                    <i class="fas fa-folder-open"></i> Course Materials
                </button>
            `;
            
            // Course-type-specific buttons
            if (courseType === 'prompt_engineering') {
                actionButtons += `
                    <button class="btn-secondary btn-sm" onclick="app.showTab('chat')" data-testid="button-start-chat-${e.enrollment_id}">
                        <i class="fas fa-comments"></i> Start Chat
                    </button>
                    <button class="btn-secondary btn-sm" onclick="app.showTab('library')" data-testid="button-library-${e.enrollment_id}">
                        <i class="fas fa-book"></i> Prompt Library
                    </button>
                `;
            } else if (courseType === 'ethics_certificate') {
                actionButtons += `
                    <button class="btn-secondary btn-sm" onclick="app.showTab('survey')" data-testid="button-survey-${e.enrollment_id}">
                        <i class="fas fa-clipboard-list"></i> Entry Survey
                    </button>
                    <button class="btn-secondary btn-sm" onclick="app.showTab('exit-exam')" data-testid="button-exit-exam-${e.enrollment_id}">
                        <i class="fas fa-graduation-cap"></i> Exit Exam
                    </button>
                    <button class="btn-secondary btn-sm" onclick="app.showTab('my-certificates')" data-testid="button-certificates-${e.enrollment_id}">
                        <i class="fas fa-certificate"></i> My Certificate
                    </button>
                `;
            } else if (courseType === 'agentic_ai') {
                actionButtons += `
                    <button class="btn-secondary btn-sm" onclick="app.showTab('agentic-ai-lab')" data-testid="button-ai-lab-${e.enrollment_id}">
                        <i class="fas fa-project-diagram"></i> Artificial Intelligence Laboratory
                    </button>
                `;
            }
            
            return `
                <div class="class-card enrolled" data-testid="enrolled-class-${e.enrollment_id}">
                    <div class="class-header">
                        <h4><i class="fas fa-chalkboard"></i> ${e.class_title}</h4>
                        <span class="status-badge status-approved" data-testid="status-${e.enrollment_id}">Active</span>
                    </div>
                    ${e.class_description ? `<p>${e.class_description}</p>` : ''}
                    <p><i class="fas fa-tag"></i> <strong>${courseTypeLabel}</strong></p>
                    <p><i class="fas fa-user-tie"></i> Instructor: ${e.instructor_name}</p>
                    ${e.class_schedule ? `<p><i class="fas fa-clock"></i> ${e.class_schedule}</p>` : ''}
                    <p><i class="fas fa-calendar"></i> Enrolled: ${new Date(e.enrolled_at).toLocaleDateString()}</p>
                    
                    <!-- Main Go To Course Button -->
                    <div style="margin: 15px 0;">
                        <button class="btn-primary" style="width: 100%; font-size: 16px; padding: 12px;" onclick="app.classManager.goToCourse('${e.class_id}', '${e.class_title}', '${courseType}')" data-testid="button-go-to-course-${e.enrollment_id}">
                            <i class="fas fa-arrow-right"></i> Go To Course
                        </button>
                    </div>
                    
                    <!-- Quick Access Buttons -->
                    <div style="display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap;">
                        ${actionButtons}
                    </div>
                </div>
            `;
        }).join('');
    }

    goToCourse(classId, classTitle, courseType) {
        // Set course context
        if (window.app && window.app.setCourseContext) {
            window.app.setCourseContext(classId, classTitle);
        }
        
        // Store current course info for the course area
        this.currentCourse = {
            id: classId,
            title: classTitle,
            type: courseType
        };
        
        // Navigate to appropriate course area based on type
        if (courseType === 'prompt_engineering') {
            this.showPromptEngineeringCourse(classId, classTitle);
        } else if (courseType === 'ethics_certificate') {
            this.showEthicsCertificateCourse(classId, classTitle);
        } else if (courseType === 'agentic_ai') {
            // Go directly to Agentic AI Lab
            if (window.app) {
                window.app.showTab('agentic-ai-lab');
            }
        }
    }
    
    async showPromptEngineeringCourse(classId, classTitle) {
        // Show the Prompt Engineering course area tab
        if (window.app) {
            window.app.showTab('course-area-prompt-engineering');
        }
        
        // Load course materials for this class
        const files = await this.loadCourseFiles(classId);
        const filesContainer = document.getElementById('peCourseMaterials');
        if (filesContainer) {
            filesContainer.innerHTML = this.displayCourseFiles(files, classId, false);
        }
    }
    
    async showEthicsCertificateCourse(classId, classTitle) {
        // Show the Ethics Certificate course area tab
        if (window.app) {
            window.app.showTab('course-area-ethics-certificate');
        }
    }

    async showClassFiles(classId, classTitle) {
        // Set the course context to show course name at top
        if (window.app && window.app.setCourseContext) {
            window.app.setCourseContext(classId, classTitle);
        }
        
        const files = await this.loadCourseFiles(classId);
        
        // Create or get modal
        let modal = document.getElementById('classFilesModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'classFilesModal';
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3 id="classFilesTitle"></h3>
                        <button class="modal-close" onclick="document.getElementById('classFilesModal').classList.remove('show')">&times;</button>
                    </div>
                    <div class="modal-body" id="classFilesContent"></div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        document.getElementById('classFilesTitle').innerHTML = `<i class="fas fa-folder-open"></i> ${classTitle} - Course Files`;
        document.getElementById('classFilesContent').innerHTML = this.displayCourseFiles(files, classId, false);
        
        modal.classList.add('show');
    }

    async enrollInClass(classId) {
        try {
            const response = await fetch('/api/classes/enroll', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ class_id: classId })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showNotification('Successfully enrolled in class', 'success');
                this.loadAvailableClasses();
                this.loadMyEnrollments();
            } else {
                this.showNotification(data.error || 'Failed to enroll', 'error');
            }
        } catch (error) {
            this.showNotification('Error enrolling in class', 'error');
        }
    }

    async unenroll(enrollmentId) {
        if (!confirm('Are you sure you want to unenroll from this class?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/classes/enrollments/${enrollmentId}`, { method: 'DELETE' });
            
            if (response.ok) {
                this.showNotification('Successfully unenrolled', 'success');
                this.loadAvailableClasses();
                this.loadMyEnrollments();
            } else {
                const data = await response.json();
                this.showNotification(data.error || 'Failed to unenroll', 'error');
            }
        } catch (error) {
            this.showNotification('Error unenrolling from class', 'error');
        }
    }

    showNotification(message, type = 'info') {
        // Use the app's notification system if available
        if (window.app && typeof window.app.showNotification === 'function') {
            window.app.showNotification(message, type);
        } else {
            alert(message);
        }
    }

    // ============================================
    // Enrollment Management (Instructor/Admin)
    // ============================================
    // Note: Enrollments are now auto-approved upon student enrollment request.
    // The pending enrollment workflow has been removed from the UI.

    async viewStudentsData(classId, classTitle) {
        try {
            const response = await fetch(`/api/classes/${classId}/students-data`);
            if (response.ok) {
                const data = await response.json();
                this.displayStudentsDataModal(data, classTitle);
            } else {
                const errorData = await response.json();
                this.showNotification(errorData.error || 'Failed to load student data', 'error');
            }
        } catch (error) {
            console.error('Error loading students data:', error);
            this.showNotification('Error loading student data', 'error');
        }
    }

    displayStudentsDataModal(data, classTitle) {
        const modal = document.getElementById('studentsDataModal');
        if (!modal) return;
        
        document.getElementById('studentsDataClassTitle').textContent = classTitle;
        
        const container = document.getElementById('studentsDataContainer');
        if (!container) return;
        
        if (data.students.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;"><i class="fas fa-info-circle"></i> No enrolled students yet</p>';
        } else {
            container.innerHTML = data.students.map(student => `
                <div class="student-data-card" style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 20px; background: white;">
                    <div class="student-header" style="margin-bottom: 15px; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px;">
                        <h3 style="margin: 0;"><i class="fas fa-user-graduate"></i> ${student.full_name}</h3>
                        <p style="margin: 5px 0; color: #666;">${student.email}</p>
                        <p style="margin: 5px 0; color: #999; font-size: 13px;"><i class="fas fa-calendar"></i> Enrolled: ${new Date(student.enrolled_at).toLocaleString()}</p>
                    </div>
                    
                    <div class="student-metrics" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 15px;">
                        <!-- Attendance Section -->
                        <div class="metric-box" style="background: #e8f5e9; padding: 15px; border-radius: 6px;">
                            <h4 style="margin: 0 0 10px 0; color: #2e7d32;"><i class="fas fa-clipboard-check"></i> Attendance</h4>
                            <p style="margin: 5px 0; font-size: 24px; font-weight: bold; color: #1b5e20;">${student.attendance.total_records}</p>
                            <p style="margin: 5px 0; color: #666; font-size: 13px;">Total Records</p>
                            ${student.attendance.total_records > 0 ? `
                                <details style="margin-top: 10px;">
                                    <summary style="cursor: pointer; color: #2e7d32;">View Records</summary>
                                    <div style="max-height: 200px; overflow-y: auto; margin-top: 10px;">
                                        ${student.attendance.records.map(record => `
                                            <div style="padding: 8px; margin: 5px 0; background: white; border-radius: 4px; font-size: 12px;">
                                                <strong>${new Date(record.timestamp).toLocaleDateString()}</strong>
                                                ${record.notes ? `<br><span style="color: #666;">${record.notes}</span>` : ''}
                                            </div>
                                        `).join('')}
                                    </div>
                                </details>
                            ` : ''}
                        </div>
                        
                        <!-- Survey Section -->
                        <div class="metric-box" style="background: #e3f2fd; padding: 15px; border-radius: 6px;">
                            <h4 style="margin: 0 0 10px 0; color: #1565c0;"><i class="fas fa-clipboard-list"></i> Survey</h4>
                            <p style="margin: 5px 0; font-size: 18px; font-weight: bold; color: ${student.survey.completed ? '#1b5e20' : '#c62828'};">
                                ${student.survey.completed ? '<i class="fas fa-check-circle"></i> Completed' : '<i class="fas fa-times-circle"></i> Not Completed'}
                            </p>
                            ${student.survey.completed ? `
                                <p style="margin: 5px 0; color: #666; font-size: 13px;">
                                    Submitted: ${new Date(student.survey.submitted_at).toLocaleDateString()}
                                </p>
                            ` : ''}
                        </div>
                        
                        <!-- Exit Exam Section -->
                        <div class="metric-box" style="background: #fff3e0; padding: 15px; border-radius: 6px;">
                            <h4 style="margin: 0 0 10px 0; color: #ef6c00;"><i class="fas fa-graduation-cap"></i> Exit Exam</h4>
                            ${student.exit_exam.completed ? `
                                <p style="margin: 5px 0; font-size: 24px; font-weight: bold; color: ${student.exit_exam.score >= 6 ? '#1b5e20' : '#c62828'};">
                                    ${student.exit_exam.score}/${student.exit_exam.total_questions}
                                </p>
                                <p style="margin: 5px 0; color: #666; font-size: 13px;">
                                    Score: ${((student.exit_exam.score / student.exit_exam.total_questions) * 100).toFixed(1)}%
                                </p>
                                <p style="margin: 5px 0; color: #666; font-size: 13px;">
                                    Status: <strong style="color: ${student.exit_exam.certificate_status === 'pass' ? '#1b5e20' : '#c62828'};">
                                        ${student.exit_exam.certificate_status === 'pass' ? 'PASS' : 'FAIL'}
                                    </strong>
                                </p>
                                <p style="margin: 5px 0; color: #999; font-size: 12px;">
                                    ${new Date(student.exit_exam.submitted_at).toLocaleDateString()}
                                </p>
                            ` : `
                                <p style="margin: 5px 0; font-size: 18px; font-weight: bold; color: #c62828;">
                                    <i class="fas fa-times-circle"></i> Not Completed
                                </p>
                            `}
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        modal.classList.add('show');
    }

    closeStudentsDataModal() {
        const modal = document.getElementById('studentsDataModal');
        if (modal) {
            modal.classList.remove('show');
        }
    }

    // ============================================
    // Course File Management
    // ============================================

    async loadCourseFiles(classId) {
        try {
            const response = await fetch(`/api/classes/${classId}/files`);
            const data = await response.json();
            
            if (response.ok) {
                return data.files || [];
            }
            return [];
        } catch (error) {
            console.error('Error loading course files:', error);
            return [];
        }
    }

    async uploadCourseFile(classId, fileInput) {
        try {
            const file = fileInput.files[0];
            if (!file) {
                alert('Please select a file to upload');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`/api/classes/${classId}/files`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification('File uploaded successfully', 'success');
                fileInput.value = ''; // Clear input
                return true;
            } else {
                alert('Failed to upload file: ' + (data.error || 'Unknown error'));
                return false;
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            alert('Error uploading file');
            return false;
        }
    }

    async deleteCourseFile(classId, fileId) {
        if (!confirm('Are you sure you want to delete this file?')) {
            return;
        }

        try {
            const response = await fetch(`/api/classes/${classId}/files/${fileId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification('File deleted successfully', 'success');
                return true;
            } else {
                alert('Failed to delete file: ' + (data.error || 'Unknown error'));
                return false;
            }
        } catch (error) {
            console.error('Error deleting file:', error);
            alert('Error deleting file');
            return false;
        }
    }

    downloadCourseFile(classId, fileId) {
        window.location.href = `/api/classes/${classId}/files/${fileId}/download`;
    }

    displayCourseFiles(files, classId, isAdmin = false) {
        if (files.length === 0) {
            return '<p style="text-align: center; color: #666; margin: 20px 0;"><i class="fas fa-folder-open"></i> No files available</p>';
        }

        return `
            <div class="course-files-list" style="margin-top: 15px;">
                ${files.map(file => {
                    const fileSize = (file.file_size / 1024).toFixed(2); // Convert to KB
                    const uploadDate = new Date(file.uploaded_at).toLocaleDateString();
                    
                    return `
                        <div class="file-item" style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #f8f9fa; border-radius: 6px; margin-bottom: 8px;">
                            <div style="flex: 1;">
                                <i class="fas fa-file"></i>
                                <strong>${file.filename}</strong>
                                <span style="color: #666; font-size: 12px; margin-left: 10px;">
                                    ${fileSize} KB • ${uploadDate}
                                </span>
                            </div>
                            <div>
                                <button class="btn-primary btn-sm" onclick="app.classManager.downloadCourseFile('${classId}', '${file.id}')" data-testid="button-download-file-${file.id}" style="margin-right: 5px;">
                                    <i class="fas fa-download"></i> Download
                                </button>
                                ${isAdmin ? `
                                    <button class="btn-danger btn-sm" onclick="app.classManager.deleteCourseFile('${classId}', '${file.id}').then(success => { if(success) app.classManager.viewClass('${classId}'); })" data-testid="button-delete-file-${file.id}">
                                        <i class="fas fa-trash"></i> Delete
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }

    // ============================================
    // Class Detail View (for Instructors/Admins)
    // ============================================

    async viewClassDetails(classId) {
        try {
            const response = await fetch(`/api/classes/${classId}/details`);
            if (!response.ok) {
                throw new Error('Failed to load class details');
            }

            const data = await response.json();
            this.displayClassDetailView(data);
        } catch (error) {
            console.error('Error loading class details:', error);
            this.showNotification('Error loading class details', 'error');
        }
    }

    displayClassDetailView(data) {
        // Find the appropriate VISIBLE container (instructor or admin view)
        const instructorContainer = document.getElementById('instructorClasses');
        const adminClassesContainer = document.getElementById('adminClassesList');
        const adminInstructorsContainer = document.getElementById('allClassesList');
        
        // Check which container is actually visible (not in a hidden tab)
        const isVisible = (el) => {
            if (!el) return false;
            const style = window.getComputedStyle(el);
            if (style.display === 'none') return false;
            // Check if parent tab is visible
            let parent = el.parentElement;
            while (parent) {
                const parentStyle = window.getComputedStyle(parent);
                if (parentStyle.display === 'none') return false;
                parent = parent.parentElement;
            }
            return true;
        };
        
        // Use the visible container, prioritizing the order based on visibility
        let classListSection = null;
        if (isVisible(instructorContainer)) {
            classListSection = instructorContainer;
        } else if (isVisible(adminClassesContainer)) {
            classListSection = adminClassesContainer;
        } else if (isVisible(adminInstructorsContainer)) {
            classListSection = adminInstructorsContainer;
        } else {
            // Fallback to first available
            classListSection = instructorContainer || adminClassesContainer || adminInstructorsContainer;
        }

        if (!classListSection) {
            console.error('Class list container not found - cannot display details');
            return;
        }

        let classDetailSection = document.getElementById('classDetailSection');

        if (!classDetailSection) {
            // Create class detail section if it doesn't exist
            const section = document.createElement('div');
            section.id = 'classDetailSection';
            section.className = 'class-detail-view';
            section.style.display = 'none';
            classListSection.parentNode.insertBefore(section, classListSection.nextSibling);
            classDetailSection = section;
        }

        const classInfo = data.class;
        const students = data.students;
        
        // IMPORTANT: Set content FIRST, then show the element
        classDetailSection.innerHTML = `
            <div class="class-detail-header">
                <button onclick="app.classManager.backToClassList()" class="btn-back">
                    <i class="fas fa-arrow-left"></i> Back to Classes
                </button>
                <h2><i class="fas fa-chalkboard"></i> ${classInfo.title}</h2>
                <p class="class-meta">
                    <span><i class="fas fa-calendar"></i> ${classInfo.semester} ${classInfo.year}</span>
                    <span><i class="fas fa-code"></i> Code: ${classInfo.class_code}</span>
                    <span><i class="fas fa-users"></i> ${classInfo.total_enrolled}/${classInfo.capacity} Students</span>
                </p>
                <p class="class-description">${classInfo.description || ''}</p>
                
                <div class="instructors-list">
                    <h4><i class="fas fa-user-tie"></i> Instructors</h4>
                    ${classInfo.instructors.map(inst => `
                        <div class="instructor-card">
                            <strong>${inst.name}</strong>
                            <span>${inst.email}</span>
                            ${inst.bio ? `<p>${inst.bio}</p>` : ''}
                        </div>
                    `).join('')}
                </div>
                
                ${(classInfo.meet_link || classInfo.zoom_link || classInfo.youtube_broadcast_link) ? `
                    <div class="meeting-links" style="background: #f0f7ff; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <h4 style="margin-bottom: 12px; color: #1976d2;"><i class="fas fa-video"></i> Meeting & Broadcast Links</h4>
                        <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                            ${classInfo.meet_link ? `
                                <a href="${classInfo.meet_link}" target="_blank" class="btn-primary" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 15px; text-decoration: none;" data-testid="link-meet">
                                    <i class="fab fa-google" style="font-size: 18px;"></i> Join Google Meet
                                </a>
                            ` : ''}
                            ${classInfo.zoom_link ? `
                                <a href="${classInfo.zoom_link}" target="_blank" class="btn-primary" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 15px; text-decoration: none; background: #2d8cff;" data-testid="link-zoom">
                                    <i class="fas fa-video" style="font-size: 18px;"></i> Join Zoom Meeting
                                </a>
                            ` : ''}
                            ${classInfo.youtube_broadcast_link ? `
                                <a href="${classInfo.youtube_broadcast_link}" target="_blank" class="btn-primary" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 15px; text-decoration: none; background: #ff0000;" data-testid="link-youtube">
                                    <i class="fab fa-youtube" style="font-size: 18px;"></i> YouTube Live
                                </a>
                                <a href="https://studio.youtube.com/channel/UC/livestreaming" target="_blank" class="btn-primary" style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 15px; text-decoration: none; background: #cc0000;" data-testid="link-youtube-studio">
                                    <i class="fas fa-broadcast-tower" style="font-size: 18px;"></i> Start Broadcast
                                </a>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}
            </div>

            <div class="class-detail-tabs">
                <button class="tab-btn active" data-tab="students">
                    <i class="fas fa-users"></i> Students (${students.length})
                </button>
                <button class="tab-btn" data-tab="exam">
                    <i class="fas fa-clipboard-check"></i> Exam and Statistics
                </button>
                <button class="tab-btn" data-tab="files">
                    <i class="fas fa-file"></i> Course Files (${classInfo.files.length})
                </button>
            </div>

            <div class="tab-content active" data-tab-content="students">
                <div class="students-table-container">
                    ${students.length > 0 ? `
                        <table class="students-table">
                            <thead>
                                <tr>
                                    <th>Student Name</th>
                                    <th>Email</th>
                                    <th>Organization</th>
                                    <th>Attendance</th>
                                    <th>Entry Survey</th>
                                    <th>Exit Exam</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${students.map(student => `
                                    <tr>
                                        <td><strong>${student.full_name}</strong></td>
                                        <td>${student.email}</td>
                                        <td>${student.organization || '-'}</td>
                                        <td>
                                            <span class="badge badge-info">${student.attendance.total} records</span>
                                        </td>
                                        <td>
                                            ${student.entry_survey.completed ? `
                                                <div class="status-info">
                                                    <span class="badge badge-success">Completed</span>
                                                    <small>Score: ${student.entry_survey.score}</small>
                                                    ${student.entry_survey.certificate_status === 'pass' ? 
                                                        '<span class="badge badge-primary">Certificate Issued</span>' : 
                                                        `<button class="btn-small btn-cert" onclick="app.classManager.issueCertificate('${classInfo.class_id}', '${student.user_id}', 'entry_survey')">
                                                            <i class="fas fa-certificate"></i> Issue Certificate
                                                        </button>`
                                                    }
                                                </div>
                                            ` : '<span class="badge badge-secondary">Not Completed</span>'}
                                        </td>
                                        <td>
                                            ${student.exit_exam.completed ? `
                                                <div class="status-info">
                                                    <span class="badge badge-success">Completed</span>
                                                    <small>${student.exit_exam.percentage}% (${student.exit_exam.score}/${student.exit_exam.score * 2})</small>
                                                    ${student.exit_exam.certificate_status === 'pass' ? 
                                                        '<span class="badge badge-primary">Certificate Issued</span>' : 
                                                        `<button class="btn-small btn-cert" onclick="app.classManager.issueCertificate('${classInfo.class_id}', '${student.user_id}', 'exit_exam')">
                                                            <i class="fas fa-certificate"></i> Issue Certificate
                                                        </button>`
                                                    }
                                                </div>
                                            ` : '<span class="badge badge-secondary">Not Completed</span>'}
                                        </td>
                                        <td>
                                            <button class="btn-danger btn-small" onclick="app.classManager.removeStudent('${classInfo.class_id}', '${student.user_id}', '${student.full_name}')">
                                                <i class="fas fa-user-times"></i> Remove
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    ` : '<p class="no-data">No students enrolled yet.</p>'}
                </div>
            </div>

            <div class="tab-content" data-tab-content="exam">
                <div class="exam-management-section">
                    <h4><i class="fas fa-clipboard-check"></i> Class Exam Management</h4>
                    
                    <!-- Upload Exam Section -->
                    <div class="exam-upload-section" style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <h5><i class="fas fa-upload"></i> Upload Exam Questions (CSV)</h5>
                        <div style="display: flex; gap: 10px; align-items: center; margin-top: 10px;">
                            <input type="file" id="examFileInput_${classInfo.class_id}" accept=".csv" style="flex: 1;" data-testid="input-upload-exam">
                            <button class="btn-primary" onclick="app.classManager.uploadExam('${classInfo.class_id}')" data-testid="button-upload-exam">
                                <i class="fas fa-upload"></i> Upload Exam
                            </button>
                            <button class="btn-secondary" onclick="app.classManager.downloadExamTemplate('${classInfo.class_id}')" data-testid="button-download-template">
                                <i class="fas fa-download"></i> Download Template
                            </button>
                        </div>
                        <p style="color: #666; font-size: 12px; margin-top: 8px;">
                            <i class="fas fa-info-circle"></i> Upload a CSV file containing exam questions. Download the template to see the required format.
                        </p>
                    </div>
                    
                    <!-- Statistics Section -->
                    <div class="statistics-section" style="margin-top: 30px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h5><i class="fas fa-chart-bar"></i> Statistics & Analytics</h5>
                            <div style="display: flex; gap: 10px;">
                                <button class="btn-info" onclick="app.classManager.viewExamStatistics('${classInfo.class_id}')" data-testid="button-exam-stats">
                                    <i class="fas fa-chart-line"></i> Exam Statistics
                                </button>
                                <button class="btn-info" onclick="app.classManager.viewSurveyStatistics('${classInfo.class_id}')" data-testid="button-survey-stats">
                                    <i class="fas fa-poll"></i> Survey Statistics
                                </button>
                            </div>
                        </div>
                        <div id="statisticsDisplay_${classInfo.class_id}" style="margin-top: 20px;">
                            <p class="no-data">Click a button above to view statistics</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="tab-content" data-tab-content="files">
                <div class="file-upload-section" style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h4><i class="fas fa-upload"></i> Upload Course Files</h4>
                    <div style="display: flex; gap: 10px; align-items: center; margin-top: 10px;">
                        <input type="file" id="fileUploadInput_${classInfo.class_id}" style="flex: 1;" data-testid="input-upload-file">
                        <button class="btn-primary" onclick="app.classManager.uploadCourseFile('${classInfo.class_id}', document.getElementById('fileUploadInput_${classInfo.class_id}')).then(success => { if(success) app.classManager.viewClassDetails('${classInfo.class_id}'); })" data-testid="button-upload-file">
                            <i class="fas fa-upload"></i> Upload
                        </button>
                    </div>
                    <p style="color: #666; font-size: 12px; margin-top: 8px;">
                        <i class="fas fa-info-circle"></i> Upload course materials, lecture notes, assignments, or any files students need
                    </p>
                </div>
                
                <div class="files-list">
                    <h4><i class="fas fa-folder"></i> Course Files</h4>
                    ${classInfo.files.length > 0 ? classInfo.files.map(file => `
                        <div class="file-item" style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #f8f9fa; border-radius: 6px; margin-bottom: 8px;">
                            <div style="flex: 1;">
                                <i class="fas fa-file"></i>
                                <strong>${file.filename}</strong>
                                <br>
                                <small style="color: #666;">Uploaded by ${file.uploaded_by_name} on ${new Date(file.uploaded_at).toLocaleDateString()}</small>
                            </div>
                            <div style="display: flex; gap: 5px;">
                                <button class="btn-primary btn-small" onclick="app.classManager.downloadCourseFile('${classInfo.class_id}', '${file.id}')" data-testid="button-download-file-${file.id}">
                                    <i class="fas fa-download"></i> Download
                                </button>
                                <button class="btn-danger btn-small" onclick="app.classManager.deleteCourseFile('${classInfo.class_id}', '${file.id}').then(success => { if(success) app.classManager.viewClassDetails('${classInfo.class_id}'); })" data-testid="button-delete-file-${file.id}">
                                    <i class="fas fa-trash"></i> Delete
                                </button>
                            </div>
                        </div>
                    `).join('') : '<p class="no-data">No files uploaded yet.</p>'}
                </div>
            </div>
        `;

        // Setup tab switching
        const tabButtons = classDetailSection.querySelectorAll('.tab-btn');
        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                
                // Update active tab button
                tabButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Update active tab content
                classDetailSection.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                classDetailSection.querySelector(`[data-tab-content="${tab}"]`).classList.add('active');
            });
        });
        
        // NOW hide class list and show detail view (after content is set)
        classListSection.style.display = 'none';
        classListSection.classList.remove('active');
        
        classDetailSection.style.display = 'block';
        classDetailSection.classList.add('active');
    }

    backToClassList() {
        // Find the appropriate VISIBLE container (instructor or admin view)
        const instructorContainer = document.getElementById('instructorClasses');
        const adminClassesContainer = document.getElementById('adminClassesList');
        const adminInstructorsContainer = document.getElementById('allClassesList');
        
        // Check which container is actually visible (not in a hidden tab)
        const isVisible = (el) => {
            if (!el) return false;
            const style = window.getComputedStyle(el);
            if (style.display === 'none') return false;
            // Check if parent tab is visible
            let parent = el.parentElement;
            while (parent) {
                const parentStyle = window.getComputedStyle(parent);
                if (parentStyle.display === 'none') return false;
                parent = parent.parentElement;
            }
            return true;
        };
        
        // Use the visible container
        let classListSection = null;
        if (isVisible(instructorContainer)) {
            classListSection = instructorContainer;
        } else if (isVisible(adminClassesContainer)) {
            classListSection = adminClassesContainer;
        } else if (isVisible(adminInstructorsContainer)) {
            classListSection = adminInstructorsContainer;
        } else {
            classListSection = instructorContainer || adminClassesContainer || adminInstructorsContainer;
        }
        const classDetailSection = document.getElementById('classDetailSection');
        
        if (classListSection && classDetailSection) {
            // Use 'grid' for classes-grid containers
            classListSection.style.display = 'grid';
            classListSection.classList.add('active');
            
            classDetailSection.style.display = 'none';
            classDetailSection.classList.remove('active');
        }
    }

    async issueCertificate(classId, studentUserId, certType) {
        if (!confirm(`Are you sure you want to issue this certificate? This will mark the ${certType === 'entry_survey' ? 'Entry Survey' : 'Exit Exam'} certificate as approved for this student.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/classes/${classId}/students/${studentUserId}/certificate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: certType })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to issue certificate');
            }

            const data = await response.json();
            this.showNotification(data.message, 'success');
            
            // Reload class details
            await this.viewClassDetails(classId);
        } catch (error) {
            console.error('Error issuing certificate:', error);
            this.showNotification(error.message || 'Error issuing certificate', 'error');
        }
    }

    async removeStudent(classId, studentUserId, studentName) {
        if (!confirm(`Are you sure you want to remove ${studentName} from this class? This action cannot be undone.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/classes/${classId}/students/${studentUserId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to remove student');
            }

            const data = await response.json();
            this.showNotification(data.message, 'success');
            
            // Reload class details
            await this.viewClassDetails(classId);
        } catch (error) {
            console.error('Error removing student:', error);
            this.showNotification(error.message || 'Error removing student', 'error');
        }
    }

    async downloadFile(classId, fileId) {
        try {
            window.open(`/api/classes/${classId}/files/${fileId}/download`, '_blank');
        } catch (error) {
            console.error('Error downloading file:', error);
            this.showNotification('Error downloading file', 'error');
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            ${message}
        `;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
            color: white;
            border-radius: 6px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // ============================================
    // Exam Management Functions
    // ============================================

    downloadExamTemplate(classId) {
        try {
            window.open(`/api/classes/${classId}/exam/template`, '_blank');
            this.showNotification('Downloading exam template...', 'info');
        } catch (error) {
            console.error('Error downloading template:', error);
            this.showNotification('Error downloading template', 'error');
        }
    }

    async uploadExam(classId) {
        const fileInput = document.getElementById(`examFileInput_${classId}`);
        const file = fileInput.files[0];

        if (!file) {
            this.showNotification('Please select a CSV file to upload', 'error');
            return;
        }

        if (!file.name.endsWith('.csv')) {
            this.showNotification('Please upload a CSV file', 'error');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`/api/classes/${classId}/exam/upload`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification(data.message || 'Exam uploaded successfully!', 'success');
                fileInput.value = ''; // Clear the input
            } else {
                this.showNotification(data.error || 'Failed to upload exam', 'error');
            }
        } catch (error) {
            console.error('Error uploading exam:', error);
            this.showNotification('Error uploading exam', 'error');
        }
    }

    async viewExamStatistics(classId) {
        try {
            const response = await fetch(`/api/classes/${classId}/exam/statistics`);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to load exam statistics');
            }

            const data = await response.json();
            this.displayExamStatistics(classId, data.statistics);
        } catch (error) {
            console.error('Error loading exam statistics:', error);
            this.showNotification(error.message || 'Error loading exam statistics', 'error');
        }
    }

    displayExamStatistics(classId, stats) {
        const displayDiv = document.getElementById(`statisticsDisplay_${classId}`);
        
        if (stats.total_submissions === 0) {
            displayDiv.innerHTML = '<p class="no-data">No exam submissions yet.</p>';
            return;
        }

        const html = `
            <div class="statistics-container">
                <h4><i class="fas fa-chart-bar"></i> Exam Statistics</h4>
                
                <!-- Summary Cards -->
                <div class="stats-cards" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                    <div class="stat-card" style="background: #4CAF50; color: white; padding: 20px; border-radius: 8px;">
                        <div style="font-size: 32px; font-weight: bold;">${stats.total_submissions}</div>
                        <div>Total Submissions</div>
                    </div>
                    <div class="stat-card" style="background: #2196F3; color: white; padding: 20px; border-radius: 8px;">
                        <div style="font-size: 32px; font-weight: bold;">${stats.average_score}%</div>
                        <div>Average Score</div>
                    </div>
                    <div class="stat-card" style="background: #FF9800; color: white; padding: 20px; border-radius: 8px;">
                        <div style="font-size: 32px; font-weight: bold;">${stats.pass_rate}%</div>
                        <div>Pass Rate (≥50%)</div>
                    </div>
                    <div class="stat-card" style="background: #9C27B0; color: white; padding: 20px; border-radius: 8px;">
                        <div style="font-size: 32px; font-weight: bold;">${stats.highest_score}%</div>
                        <div>Highest Score</div>
                    </div>
                </div>

                <!-- Score Distribution Chart -->
                <div class="chart-container" style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h5><i class="fas fa-chart-pie"></i> Score Distribution</h5>
                    <div class="bar-chart">
                        ${stats.score_distribution.map(bin => `
                            <div class="bar-item" style="margin: 10px 0;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                    <span>${bin.range}</span>
                                    <strong>${bin.count} students</strong>
                                </div>
                                <div style="background: #e0e0e0; height: 30px; border-radius: 4px; overflow: hidden;">
                                    <div style="background: linear-gradient(90deg, #4CAF50, #2196F3); height: 100%; width: ${(bin.count / stats.total_submissions * 100)}%; transition: width 0.3s;"></div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Question Difficulty Analysis -->
                <div class="chart-container" style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h5><i class="fas fa-brain"></i> Question Difficulty Analysis</h5>
                    <div class="question-stats">
                        ${stats.question_difficulty.map(q => `
                            <div class="question-stat-item" style="margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 6px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                    <div>
                                        <strong>Q${q.question_number}</strong>: ${q.question_text.substring(0, 60)}${q.question_text.length > 60 ? '...' : ''}
                                    </div>
                                    <div style="display: flex; gap: 15px;">
                                        <span style="color: ${q.correct_rate >= 70 ? '#4CAF50' : q.correct_rate >= 40 ? '#FF9800' : '#f44336'};">
                                            <i class="fas fa-check-circle"></i> ${q.correct_rate}% correct
                                        </span>
                                        <span style="color: #666;">
                                            <i class="fas fa-times-circle"></i> ${q.difficulty_percentage}% wrong
                                        </span>
                                    </div>
                                </div>
                                <div style="background: #e0e0e0; height: 8px; border-radius: 4px; overflow: hidden;">
                                    <div style="background: ${q.difficulty_percentage < 30 ? '#4CAF50' : q.difficulty_percentage < 60 ? '#FF9800' : '#f44336'}; height: 100%; width: ${q.difficulty_percentage}%;"></div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Student Results Table -->
                <div class="table-container" style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h5><i class="fas fa-users"></i> Individual Student Results</h5>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                        <thead>
                            <tr style="background: #f8f9fa;">
                                <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ddd;">Rank</th>
                                <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ddd;">Student Name</th>
                                <th style="padding: 12px; text-align: center; border-bottom: 2px solid #ddd;">Score</th>
                                <th style="padding: 12px; text-align: center; border-bottom: 2px solid #ddd;">Points</th>
                                <th style="padding: 12px; text-align: center; border-bottom: 2px solid #ddd;">Submitted</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${stats.student_results.map((student, index) => `
                                <tr style="border-bottom: 1px solid #eee;">
                                    <td style="padding: 12px;">
                                        ${index < 3 ? `<i class="fas fa-trophy" style="color: ${index === 0 ? '#FFD700' : index === 1 ? '#C0C0C0' : '#CD7F32'};"></i>` : ''} 
                                        ${index + 1}
                                    </td>
                                    <td style="padding: 12px;"><strong>${student.student_name}</strong></td>
                                    <td style="padding: 12px; text-align: center;">
                                        <span style="background: ${student.score_percentage >= 70 ? '#4CAF50' : student.score_percentage >= 50 ? '#FF9800' : '#f44336'}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold;">
                                            ${student.score_percentage}%
                                        </span>
                                    </td>
                                    <td style="padding: 12px; text-align: center;">${student.earned_points}/${student.total_points}</td>
                                    <td style="padding: 12px; text-align: center; color: #666; font-size: 12px;">
                                        ${new Date(student.submitted_at).toLocaleDateString()}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        displayDiv.innerHTML = html;
    }

    async viewSurveyStatistics(classId) {
        try {
            const response = await fetch(`/api/classes/${classId}/survey/statistics`);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to load survey statistics');
            }

            const data = await response.json();
            this.displaySurveyStatistics(classId, data.statistics);
        } catch (error) {
            console.error('Error loading survey statistics:', error);
            this.showNotification(error.message || 'Error loading survey statistics', 'error');
        }
    }

    displaySurveyStatistics(classId, stats) {
        const displayDiv = document.getElementById(`statisticsDisplay_${classId}`);
        
        if (stats.total_responses === 0) {
            displayDiv.innerHTML = '<p class="no-data">No survey responses yet.</p>';
            return;
        }

        const html = `
            <div class="statistics-container">
                <h4><i class="fas fa-poll"></i> Entry Survey Statistics</h4>
                
                <!-- Summary Cards -->
                <div class="stats-cards" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                    <div class="stat-card" style="background: #4CAF50; color: white; padding: 20px; border-radius: 8px;">
                        <div style="font-size: 32px; font-weight: bold;">${stats.total_responses}</div>
                        <div>Total Responses</div>
                    </div>
                    <div class="stat-card" style="background: #2196F3; color: white; padding: 20px; border-radius: 8px;">
                        <div style="font-size: 32px; font-weight: bold;">${stats.total_students}</div>
                        <div>Enrolled Students</div>
                    </div>
                    <div class="stat-card" style="background: #FF9800; color: white; padding: 20px; border-radius: 8px;">
                        <div style="font-size: 32px; font-weight: bold;">${stats.response_rate}%</div>
                        <div>Response Rate</div>
                    </div>
                </div>

                <!-- Question Response Distribution -->
                <div class="chart-container" style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h5><i class="fas fa-chart-bar"></i> Question Response Distribution</h5>
                    ${stats.question_responses.map(q => `
                        <div class="question-response" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 6px;">
                            <h6 style="margin-bottom: 15px;">Question ${q.question_id} (${q.total_responses} responses)</h6>
                            ${q.distribution.map(d => `
                                <div class="response-bar" style="margin: 10px 0;">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                        <span>${d.answer}</span>
                                        <strong>${d.count} (${Math.round(d.count / q.total_responses * 100)}%)</strong>
                                    </div>
                                    <div style="background: #e0e0e0; height: 25px; border-radius: 4px; overflow: hidden;">
                                        <div style="background: linear-gradient(90deg, #4CAF50, #2196F3); height: 100%; width: ${(d.count / q.total_responses * 100)}%; transition: width 0.3s;"></div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        displayDiv.innerHTML = html;
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.classManager = new ClassManager();
    });
} else {
    window.classManager = new ClassManager();
}

/**
 * Admin Class Cards - Load and Display All Classes as Cards
 */
async function loadAdminClassCards() {
    try {
        const response = await fetch('/api/classes/list', {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to load classes');
        }
        
        const data = await response.json();
        const classes = data.classes || [];
        
        renderAdminClassCards(classes);
    } catch (error) {
        console.error('Error loading admin class cards:', error);
        document.getElementById('adminClassCardsContainer').innerHTML = `
            <div style="text-align: center; padding: 40px; color: #e74c3c;">
                <i class="fas fa-exclamation-triangle fa-2x"></i>
                <p style="margin-top: 15px;">Failed to load classes</p>
            </div>
        `;
    }
}

/**
 * Render Admin Class Cards
 */
function renderAdminClassCards(classes) {
    const container = document.getElementById('adminClassCardsContainer');
    
    if (!classes || classes.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #999;">
                <i class="fas fa-inbox fa-3x" style="opacity: 0.3;"></i>
                <p style="margin-top: 15px;">No classes found</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = classes.map(cls => {
        const courseTypes = {
            'prompt_engineering': { label: 'Prompt Engineering', color: '#3b82f6' },
            'ethics_certificate': { label: 'Ethics Certificate', color: '#ef4444' },
            'agentic_ai': { label: 'Agentic AI', color: '#8b5cf6' }
        };
        
        const type = courseTypes[cls.course_type] || { label: cls.course_type, color: '#64748b' };
        
        return `
            <div class="admin-class-card" onclick="showClassStudentsModal('${cls.class_id}', '${cls.title}')" data-testid="admin-card-${cls.class_id}">
                <div class="admin-class-card-header">
                    <div>
                        <div class="admin-class-card-title">${cls.title}</div>
                        <div class="admin-class-card-code">${cls.class_code}</div>
                    </div>
                    <span class="admin-class-card-badge" style="background: ${type.color}20; color: ${type.color};">
                        ${type.label}
                    </span>
                </div>
                
                <div class="admin-class-card-info">
                    ${cls.instructor_name ? `
                        <div class="admin-class-card-info-item">
                            <i class="fas fa-chalkboard-teacher"></i>
                            <span>${cls.instructor_name}</span>
                        </div>
                    ` : ''}
                    ${cls.semester ? `
                        <div class="admin-class-card-info-item">
                            <i class="fas fa-calendar-alt"></i>
                            <span>${cls.semester}</span>
                        </div>
                    ` : ''}
                    ${cls.schedule ? `
                        <div class="admin-class-card-info-item">
                            <i class="fas fa-clock"></i>
                            <span>${cls.schedule}</span>
                        </div>
                    ` : ''}
                </div>
                
                <div class="admin-class-card-footer">
                    <div class="admin-class-card-students">
                        <i class="fas fa-users"></i>
                        <span>View Students</span>
                    </div>
                    <span style="font-size: 12px; color: #94a3b8;">
                        <i class="fas fa-arrow-right"></i>
                    </span>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Show Class Details Modal with Tabs (Admin Comprehensive View)
 */
async function showClassStudentsModal(classId, className) {
    const modal = document.getElementById('classStudentsModal');
    const titleElement = document.getElementById('classStudentsModalTitle');
    const bodyElement = document.getElementById('classStudentsModalBody');
    
    // Show modal with loading state
    titleElement.textContent = className;
    bodyElement.innerHTML = `
        <div style="text-align: center; padding: 40px;">
            <i class="fas fa-spinner fa-spin fa-2x" style="color: #ccc;"></i>
            <p style="margin-top: 15px; color: #666;">Loading class details...</p>
        </div>
    `;
    modal.classList.add('show');
    
    try {
        // Fetch all data in parallel including all statistics types
        const [classResponse, enrollmentsResponse, examStatsResponse, surveyStatsResponse, exitExamStatsResponse, exitSurveyStatsResponse] = await Promise.all([
            fetch(`/api/classes/${classId}`, { credentials: 'include' }),
            fetch(`/api/classes/${classId}/enrollments`, { credentials: 'include' }),
            fetch(`/api/classes/${classId}/exam/statistics`, { credentials: 'include' }).catch(() => ({ ok: false })),
            fetch(`/api/classes/${classId}/survey/statistics`, { credentials: 'include' }).catch(() => ({ ok: false })),
            fetch(`/api/classes/${classId}/exit-exam/statistics`, { credentials: 'include' }).catch(() => ({ ok: false })),
            fetch(`/api/classes/${classId}/exit-survey/statistics`, { credentials: 'include' }).catch(() => ({ ok: false }))
        ]);
        
        const classData = classResponse.ok ? await classResponse.json() : null;
        const enrollmentsData = enrollmentsResponse.ok ? await enrollmentsResponse.json() : { enrollments: [] };
        const examStats = examStatsResponse.ok ? await examStatsResponse.json() : null;
        const surveyStats = surveyStatsResponse.ok ? await surveyStatsResponse.json() : null;
        const exitExamStats = exitExamStatsResponse.ok ? await exitExamStatsResponse.json() : null;
        const exitSurveyStats = exitSurveyStatsResponse.ok ? await exitSurveyStatsResponse.json() : null;
        
        renderClassDetailsTabs(classId, classData, enrollmentsData.enrollments, examStats, surveyStats, exitExamStats, exitSurveyStats, bodyElement);
    } catch (error) {
        console.error('Error loading class details:', error);
        bodyElement.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #e74c3c;">
                <i class="fas fa-exclamation-triangle fa-2x"></i>
                <p style="margin-top: 15px;">Failed to load class details</p>
            </div>
        `;
    }
}

/**
 * Render Class Details with Tabbed Interface
 */
function renderClassDetailsTabs(classId, classData, enrollments, examStats, surveyStats, exitExamStats, exitSurveyStats, container) {
    const cls = classData?.class || classData || {};
    
    // Create tab interface with all statistics types
    const tabsHtml = `
        <div class="class-details-tabs">
            <div class="tabs-nav" style="flex-wrap: wrap; gap: 5px;">
                <button class="tab-btn active" onclick="switchClassTab(event, 'overview')" data-testid="tab-overview">
                    <i class="fas fa-info-circle"></i> Overview
                </button>
                <button class="tab-btn" onclick="switchClassTab(event, 'students')" data-testid="tab-students">
                    <i class="fas fa-users"></i> Students (${enrollments.length})
                </button>
                <button class="tab-btn" onclick="switchClassTab(event, 'entry-survey')" data-testid="tab-entry-survey">
                    <i class="fas fa-clipboard-list"></i> Entry Survey
                </button>
                <button class="tab-btn" onclick="switchClassTab(event, 'class-exams')" data-testid="tab-class-exams">
                    <i class="fas fa-file-alt"></i> Class Exams
                </button>
                <button class="tab-btn" onclick="switchClassTab(event, 'exit-exam')" data-testid="tab-exit-exam">
                    <i class="fas fa-graduation-cap"></i> Exit Exam
                </button>
                <button class="tab-btn" onclick="switchClassTab(event, 'training-feedback')" data-testid="tab-training-feedback">
                    <i class="fas fa-comment-dots"></i> Training Feedback
                </button>
            </div>
            
            <div class="tabs-content">
                <!-- Overview Tab -->
                <div class="tab-pane active" id="overview-pane">
                    ${renderOverviewTab(cls, enrollments)}
                </div>
                
                <!-- Students Tab -->
                <div class="tab-pane" id="students-pane">
                    ${renderStudentsTabContent(classId, enrollments)}
                </div>
                
                <!-- Entry Survey Statistics Tab -->
                <div class="tab-pane" id="entry-survey-pane">
                    ${renderEntrySurveyStatsTab(classId, surveyStats)}
                </div>
                
                <!-- Class Exams & Statistics Tab -->
                <div class="tab-pane" id="class-exams-pane">
                    ${renderExamStatsTab(classId, examStats)}
                </div>
                
                <!-- Exit Exam Statistics Tab -->
                <div class="tab-pane" id="exit-exam-pane">
                    ${renderExitExamStatsTab(classId, exitExamStats)}
                </div>
                
                <!-- Training Feedback (Exit Survey) Statistics Tab -->
                <div class="tab-pane" id="training-feedback-pane">
                    ${renderTrainingFeedbackStatsTab(classId, exitSurveyStats)}
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = tabsHtml;
    
    // Render charts if exam stats exist
    if (examStats && examStats.statistics) {
        setTimeout(() => renderExamCharts(examStats.statistics), 100);
    }
    
    // Render exit exam charts if stats exist
    if (exitExamStats && exitExamStats.statistics) {
        setTimeout(() => renderExitExamCharts(exitExamStats.statistics), 100);
    }
}

/**
 * Switch Between Class Detail Tabs
 */
function switchClassTab(event, tabName) {
    // Update tab buttons
    document.querySelectorAll('.class-details-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.closest('.tab-btn').classList.add('active');
    
    // Update tab panes
    document.querySelectorAll('.class-details-tabs .tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    document.getElementById(`${tabName}-pane`).classList.add('active');
}

/**
 * Render Overview Tab
 */
function renderOverviewTab(cls, enrollments) {
    const approvedCount = enrollments.filter(e => e.status === 'approved').length;
    const requestedCount = enrollments.filter(e => e.status === 'requested').length;
    const blockedCount = enrollments.filter(e => e.status === 'blocked').length;
    
    const courseTypes = {
        'prompt_engineering': 'Prompt Engineering',
        'ethics_certificate': 'Ethics Certificate',
        'agentic_ai': 'Agentic AI'
    };
    
    return `
        <div class="overview-grid">
            <div class="overview-section">
                <h3><i class="fas fa-book"></i> Course Information</h3>
                <div class="info-row">
                    <span class="label">Title:</span>
                    <span class="value">${cls.title || 'N/A'}</span>
                </div>
                <div class="info-row">
                    <span class="label">Course Code:</span>
                    <span class="value">${cls.class_code || 'N/A'}</span>
                </div>
                <div class="info-row">
                    <span class="label">Type:</span>
                    <span class="value">${courseTypes[cls.course_type] || cls.course_type || 'N/A'}</span>
                </div>
                <div class="info-row">
                    <span class="label">Semester:</span>
                    <span class="value">${cls.semester || 'N/A'}</span>
                </div>
                <div class="info-row">
                    <span class="label">Schedule:</span>
                    <span class="value">${cls.schedule || 'N/A'}</span>
                </div>
                <div class="info-row">
                    <span class="label">Capacity:</span>
                    <span class="value">${cls.capacity || 'N/A'} students</span>
                </div>
            </div>
            
            <div class="overview-section">
                <h3><i class="fas fa-users"></i> Enrollment Summary</h3>
                <div class="enrollment-stats">
                    <div class="stat-box stat-success">
                        <div class="stat-value">${approvedCount}</div>
                        <div class="stat-label">Approved</div>
                    </div>
                    <div class="stat-box stat-warning">
                        <div class="stat-value">${requestedCount}</div>
                        <div class="stat-label">Pending</div>
                    </div>
                    <div class="stat-box stat-danger">
                        <div class="stat-value">${blockedCount}</div>
                        <div class="stat-label">Blocked</div>
                    </div>
                    <div class="stat-box stat-info">
                        <div class="stat-value">${enrollments.length}</div>
                        <div class="stat-label">Total</div>
                    </div>
                </div>
            </div>
            
            <div class="overview-section">
                <h3><i class="fas fa-chalkboard-teacher"></i> Instructor Information</h3>
                <div class="info-row">
                    <span class="label">Instructor(s):</span>
                    <span class="value">${cls.instructor_name || 'Multiple instructors'}</span>
                </div>
                ${cls.description ? `
                    <div class="info-row" style="margin-top: 15px;">
                        <span class="label">Description:</span>
                        <p class="value" style="margin-top: 5px; color: #666;">${cls.description}</p>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

/**
 * Render Students Tab Content
 */
function renderStudentsTabContent(classId, enrollments) {
    if (!enrollments || enrollments.length === 0) {
        return `
            <div style="text-align: center; padding: 40px; color: #999;">
                <i class="fas fa-user-slash fa-3x" style="opacity: 0.3;"></i>
                <p style="margin-top: 15px;">No students enrolled yet</p>
            </div>
        `;
    }
    
    return `
        <div class="table-responsive">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>Student Name</th>
                        <th>Email</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${enrollments.map(enrollment => {
                        const statusClass = `student-status-${enrollment.status}`;
                        return `
                            <tr>
                                <td><i class="fas fa-user-graduate"></i> ${enrollment.student_name}</td>
                                <td>${enrollment.student_email}</td>
                                <td>
                                    <span class="student-status-badge ${statusClass}">
                                        ${enrollment.status}
                                    </span>
                                </td>
                                <td>
                                    <div style="display: flex; gap: 6px;">
                                        ${enrollment.status !== 'approved' ? `
                                            <button class="btn-success" style="font-size: 11px; padding: 6px 12px;" 
                                                onclick="updateStudentStatus('${classId}', '${enrollment.student_user_id}', 'approved')" 
                                                data-testid="button-approve-${enrollment.student_user_id}">
                                                <i class="fas fa-check"></i> Approve
                                            </button>
                                        ` : ''}
                                        ${enrollment.status !== 'blocked' ? `
                                            <button class="btn-warning" style="font-size: 11px; padding: 6px 12px;" 
                                                onclick="updateStudentStatus('${classId}', '${enrollment.student_user_id}', 'blocked')" 
                                                data-testid="button-block-${enrollment.student_user_id}">
                                                <i class="fas fa-ban"></i> Block
                                            </button>
                                        ` : ''}
                                        <button class="btn-danger" style="font-size: 11px; padding: 6px 12px;" 
                                            onclick="removeStudentFromClass('${classId}', '${enrollment.student_user_id}')" 
                                            data-testid="button-remove-${enrollment.student_user_id}">
                                            <i class="fas fa-trash"></i> Remove
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

/**
 * Render Exam Statistics Tab
 */
function renderExamStatsTab(classId, examStats) {
    if (!examStats || !examStats.statistics) {
        return `
            <div style="text-align: center; padding: 40px; color: #999;">
                <i class="fas fa-chart-bar fa-3x" style="opacity: 0.3;"></i>
                <p style="margin-top: 15px;">No exam statistics available yet</p>
                <p style="margin-top: 10px; font-size: 14px;">Students need to submit exams to generate statistics</p>
            </div>
        `;
    }
    
    const stats = examStats.statistics;
    
    return `
        <div class="stats-overview">
            <div class="stat-card">
                <div class="stat-icon" style="background: #3b82f6;"><i class="fas fa-users"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.total_submissions || 0}</div>
                    <div class="stat-label">Total Submissions</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #10b981;"><i class="fas fa-chart-line"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.average_score || 0}%</div>
                    <div class="stat-label">Average Score</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #f59e0b;"><i class="fas fa-trophy"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.highest_score || 0}%</div>
                    <div class="stat-label">Highest Score</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #ef4444;"><i class="fas fa-chart-area"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.lowest_score || 0}%</div>
                    <div class="stat-label">Lowest Score</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #8b5cf6;"><i class="fas fa-percentage"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.pass_rate || 0}%</div>
                    <div class="stat-label">Pass Rate</div>
                </div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <h3><i class="fas fa-chart-bar"></i> Score Distribution</h3>
                <canvas id="scoreDistributionChart"></canvas>
            </div>
            <div class="chart-container">
                <h3><i class="fas fa-tasks"></i> Question Difficulty</h3>
                <canvas id="questionDifficultyChart"></canvas>
            </div>
        </div>
        
        ${stats.student_results && stats.student_results.length > 0 ? `
            <div class="student-results-section">
                <h3><i class="fas fa-list-ol"></i> Student Performance Rankings</h3>
                <div class="table-responsive">
                    <table class="admin-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Student Name</th>
                                <th>Score</th>
                                <th>Percentage</th>
                                <th>Status</th>
                                <th>Submitted</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${stats.student_results.map((result, index) => {
                                const isPassing = result.percentage >= 50;
                                return `
                                    <tr>
                                        <td><strong>${index + 1}</strong></td>
                                        <td>${result.student_name}</td>
                                        <td>${result.score}/${result.total_points}</td>
                                        <td><strong>${result.percentage}%</strong></td>
                                        <td>
                                            <span class="status-badge ${isPassing ? 'status-approved' : 'status-blocked'}">
                                                ${isPassing ? 'Pass' : 'Fail'}
                                            </span>
                                        </td>
                                        <td>${new Date(result.submitted_at).toLocaleString()}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        ` : ''}
    `;
}

/**
 * Render Entry Survey Statistics Tab
 */
function renderEntrySurveyStatsTab(classId, surveyStats) {
    if (!surveyStats || !surveyStats.statistics) {
        return `
            <div style="text-align: center; padding: 40px; color: #999;">
                <i class="fas fa-clipboard-list fa-3x" style="opacity: 0.3;"></i>
                <p style="margin-top: 15px;">No entry survey responses yet</p>
                <p style="margin-top: 10px; font-size: 14px;">Students need to complete the entry survey</p>
            </div>
        `;
    }
    
    const stats = surveyStats.statistics;
    
    return `
        <div class="stats-header" style="margin-bottom: 20px;">
            <h3><i class="fas fa-clipboard-list"></i> Entry Survey Statistics</h3>
            <p style="color: #666;">Survey responses from enrolled students</p>
        </div>
        <div class="stats-overview">
            <div class="stat-card">
                <div class="stat-icon" style="background: #3b82f6;"><i class="fas fa-users"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.total_responses || 0}</div>
                    <div class="stat-label">Responses</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #8b5cf6;"><i class="fas fa-user-graduate"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.total_students || 0}</div>
                    <div class="stat-label">Total Students</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #10b981;"><i class="fas fa-percentage"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.response_rate || 0}%</div>
                    <div class="stat-label">Response Rate</div>
                </div>
            </div>
        </div>
        
        ${stats.question_responses && stats.question_responses.length > 0 ? `
            <div class="survey-questions" style="margin-top: 20px;">
                <h3><i class="fas fa-question-circle"></i> Question Breakdown</h3>
                ${stats.question_responses.map((q, index) => `
                    <div class="survey-question-card" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                        <h4 style="margin-bottom: 10px;">Question ${index + 1}</h4>
                        ${q.distribution ? `
                            <div class="survey-responses">
                                ${q.distribution.map(d => `
                                    <div class="response-bar" style="display: flex; align-items: center; margin-bottom: 8px;">
                                        <span class="response-label" style="min-width: 150px; font-size: 13px;">${d.answer}</span>
                                        <div class="response-bar-track" style="flex: 1; height: 20px; background: #e5e7eb; border-radius: 4px; margin: 0 10px;">
                                            <div class="response-bar-fill" style="height: 100%; background: #1B5E20; border-radius: 4px; width: ${(d.count / stats.total_responses * 100)}%;"></div>
                                        </div>
                                        <span class="response-count" style="min-width: 40px; text-align: right; font-weight: bold;">${d.count}</span>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        ` : ''}
    `;
}

/**
 * Render Exit Exam Statistics Tab
 */
function renderExitExamStatsTab(classId, exitExamStats) {
    if (!exitExamStats || !exitExamStats.statistics) {
        return `
            <div style="text-align: center; padding: 40px; color: #999;">
                <i class="fas fa-graduation-cap fa-3x" style="opacity: 0.3;"></i>
                <p style="margin-top: 15px;">No exit exam submissions yet</p>
                <p style="margin-top: 10px; font-size: 14px;">Students need to complete the Exit Exam to generate statistics</p>
            </div>
        `;
    }
    
    const stats = exitExamStats.statistics;
    
    return `
        <div class="stats-header" style="margin-bottom: 20px;">
            <h3><i class="fas fa-graduation-cap"></i> Exit Exam Statistics</h3>
            <p style="color: #666;">Prompt Engineering certification exam results</p>
        </div>
        <div class="stats-overview">
            <div class="stat-card">
                <div class="stat-icon" style="background: #3b82f6;"><i class="fas fa-file-alt"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.total_submissions || 0}</div>
                    <div class="stat-label">Submissions</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #8b5cf6;"><i class="fas fa-users"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.total_students || 0}</div>
                    <div class="stat-label">Total Students</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #f59e0b;"><i class="fas fa-check-circle"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.completion_rate || 0}%</div>
                    <div class="stat-label">Completion Rate</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #10b981;"><i class="fas fa-chart-line"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.average_score || 0}/10</div>
                    <div class="stat-label">Average Score</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #22c55e;"><i class="fas fa-trophy"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.highest_score || 0}/10</div>
                    <div class="stat-label">Highest Score</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #6366f1;"><i class="fas fa-percentage"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.pass_rate || 0}%</div>
                    <div class="stat-label">Pass Rate (60%)</div>
                </div>
            </div>
        </div>
        
        <div class="charts-grid" style="margin-top: 20px;">
            <div class="chart-container" style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h3><i class="fas fa-chart-bar"></i> Score Distribution</h3>
                <canvas id="exitExamScoreChart" style="height: 200px;"></canvas>
            </div>
        </div>
        
        ${stats.student_results && stats.student_results.length > 0 ? `
            <div class="student-results-section" style="margin-top: 20px;">
                <h3><i class="fas fa-list-ol"></i> Student Rankings</h3>
                <div class="table-responsive">
                    <table class="admin-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Student Name</th>
                                <th>Score</th>
                                <th>Status</th>
                                <th>Certificate</th>
                                <th>Completed</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${stats.student_results.map((result, index) => `
                                <tr>
                                    <td><strong>${index + 1}</strong></td>
                                    <td>${result.student_name}</td>
                                    <td><strong>${result.score}/10</strong> (${result.percentage}%)</td>
                                    <td>
                                        <span class="status-badge ${result.passed ? 'status-approved' : 'status-blocked'}">
                                            ${result.passed ? 'Pass' : 'Fail'}
                                        </span>
                                    </td>
                                    <td>
                                        ${result.has_certificate ? 
                                            '<span style="color: #22c55e;"><i class="fas fa-certificate"></i> Generated</span>' : 
                                            '<span style="color: #94a3b8;">-</span>'}
                                    </td>
                                    <td>${result.submitted_at ? new Date(result.submitted_at).toLocaleDateString() : '-'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        ` : ''}
    `;
}

/**
 * Render Training Feedback (Exit Survey) Statistics Tab
 */
function renderTrainingFeedbackStatsTab(classId, exitSurveyStats) {
    if (!exitSurveyStats || !exitSurveyStats.statistics) {
        return `
            <div style="text-align: center; padding: 40px; color: #999;">
                <i class="fas fa-comment-dots fa-3x" style="opacity: 0.3;"></i>
                <p style="margin-top: 15px;">No training feedback responses yet</p>
                <p style="margin-top: 10px; font-size: 14px;">Students need to complete the Training Feedback survey</p>
            </div>
        `;
    }
    
    const stats = exitSurveyStats.statistics;
    
    return `
        <div class="stats-header" style="margin-bottom: 20px;">
            <h3><i class="fas fa-comment-dots"></i> Training Feedback Statistics</h3>
            <p style="color: #666;">Post-training satisfaction survey results</p>
        </div>
        <div class="stats-overview">
            <div class="stat-card">
                <div class="stat-icon" style="background: #3b82f6;"><i class="fas fa-comments"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.total_responses || 0}</div>
                    <div class="stat-label">Responses</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #8b5cf6;"><i class="fas fa-users"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.total_students || 0}</div>
                    <div class="stat-label">Total Students</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="background: #10b981;"><i class="fas fa-percentage"></i></div>
                <div class="stat-info">
                    <div class="stat-value">${stats.response_rate || 0}%</div>
                    <div class="stat-label">Response Rate</div>
                </div>
            </div>
            ${stats.average_rating ? `
                <div class="stat-card">
                    <div class="stat-icon" style="background: #f59e0b;"><i class="fas fa-star"></i></div>
                    <div class="stat-info">
                        <div class="stat-value">${stats.average_rating}/5</div>
                        <div class="stat-label">Average Rating</div>
                    </div>
                </div>
            ` : ''}
        </div>
        
        ${stats.question_responses && stats.question_responses.length > 0 ? `
            <div class="survey-questions" style="margin-top: 20px;">
                <h3><i class="fas fa-question-circle"></i> Feedback Breakdown</h3>
                ${stats.question_responses.map((q, index) => `
                    <div class="survey-question-card" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                        <h4 style="margin-bottom: 10px;">Question ${index + 1}</h4>
                        ${q.distribution ? `
                            <div class="survey-responses">
                                ${q.distribution.map(d => `
                                    <div class="response-bar" style="display: flex; align-items: center; margin-bottom: 8px;">
                                        <span class="response-label" style="min-width: 150px; font-size: 13px;">${d.answer}</span>
                                        <div class="response-bar-track" style="flex: 1; height: 20px; background: #e5e7eb; border-radius: 4px; margin: 0 10px;">
                                            <div class="response-bar-fill" style="height: 100%; background: #1B5E20; border-radius: 4px; width: ${(d.count / stats.total_responses * 100)}%;"></div>
                                        </div>
                                        <span class="response-count" style="min-width: 40px; text-align: right; font-weight: bold;">${d.count}</span>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        ` : ''}
    `;
}

// Store chart instances for cleanup
const chartInstances = {};

/**
 * Destroy existing chart instance if it exists
 */
function destroyChart(chartId) {
    if (chartInstances[chartId]) {
        chartInstances[chartId].destroy();
        delete chartInstances[chartId];
    }
}

/**
 * Render Exit Exam Charts using Chart.js
 */
function renderExitExamCharts(stats) {
    const ctx = document.getElementById('exitExamScoreChart');
    if (ctx && stats.score_distribution) {
        // Destroy existing chart if any
        destroyChart('exitExamScoreChart');
        
        const labels = stats.score_distribution.map(d => d.range);
        const data = stats.score_distribution.map(d => d.count);
        
        chartInstances['exitExamScoreChart'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Number of Students',
                    data: data,
                    backgroundColor: ['#ef4444', '#f59e0b', '#eab308', '#22c55e', '#10b981']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }
}

/**
 * Render Survey Statistics Tab (legacy - keeping for compatibility)
 */
function renderSurveyStatsTab(classId, surveyStats) {
    return renderEntrySurveyStatsTab(classId, surveyStats);
}

/**
 * Render Exam Charts using Chart.js
 */
function renderExamCharts(stats) {
    // Score Distribution Chart
    const scoreDistCtx = document.getElementById('scoreDistributionChart');
    if (scoreDistCtx && stats.score_distribution) {
        // Destroy existing chart if any
        destroyChart('scoreDistributionChart');
        
        const labels = stats.score_distribution.map(d => d.range);
        const data = stats.score_distribution.map(d => d.count);
        
        chartInstances['scoreDistributionChart'] = new Chart(scoreDistCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Number of Students',
                    data: data,
                    backgroundColor: ['#ef4444', '#f59e0b', '#eab308', '#22c55e', '#10b981']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }
    
    // Question Difficulty Chart
    const difficultyCtx = document.getElementById('questionDifficultyChart');
    if (difficultyCtx && stats.question_difficulty) {
        // Destroy existing chart if any
        destroyChart('questionDifficultyChart');
        
        const questions = stats.question_difficulty.map(q => `Q${q.question_number}`);
        const difficulties = stats.question_difficulty.map(q => q.difficulty_percentage);
        
        chartInstances['questionDifficultyChart'] = new Chart(difficultyCtx, {
            type: 'bar',
            data: {
                labels: questions,
                datasets: [{
                    label: 'Error Rate (%)',
                    data: difficulties,
                    backgroundColor: difficulties.map(d => 
                        d > 70 ? '#ef4444' : d > 40 ? '#f59e0b' : '#22c55e'
                    )
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Render Students List in Modal
 */
function renderStudentsList(classId, enrollments, container) {
    if (!enrollments || enrollments.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #999;">
                <i class="fas fa-user-slash fa-3x" style="opacity: 0.3;"></i>
                <p style="margin-top: 15px;">No students enrolled yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <div class="table-responsive">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>Student Name</th>
                        <th>Email</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${enrollments.map(enrollment => {
                        const statusClass = `student-status-${enrollment.status}`;
                        return `
                            <tr>
                                <td><i class="fas fa-user-graduate"></i> ${enrollment.student_name}</td>
                                <td>${enrollment.student_email}</td>
                                <td>
                                    <span class="student-status-badge ${statusClass}">
                                        ${enrollment.status}
                                    </span>
                                </td>
                                <td>
                                    <div style="display: flex; gap: 6px;">
                                        ${enrollment.status !== 'approved' ? `
                                            <button class="btn-success" style="font-size: 11px; padding: 6px 12px;" 
                                                onclick="updateStudentStatus('${classId}', '${enrollment.student_user_id}', 'approved')" 
                                                data-testid="button-approve-${enrollment.student_user_id}">
                                                <i class="fas fa-check"></i> Approve
                                            </button>
                                        ` : ''}
                                        ${enrollment.status !== 'blocked' ? `
                                            <button class="btn-warning" style="font-size: 11px; padding: 6px 12px;" 
                                                onclick="updateStudentStatus('${classId}', '${enrollment.student_user_id}', 'blocked')" 
                                                data-testid="button-block-${enrollment.student_user_id}">
                                                <i class="fas fa-ban"></i> Block
                                            </button>
                                        ` : ''}
                                        <button class="btn-danger" style="font-size: 11px; padding: 6px 12px;" 
                                            onclick="removeStudentFromClass('${classId}', '${enrollment.student_user_id}')" 
                                            data-testid="button-remove-${enrollment.student_user_id}">
                                            <i class="fas fa-trash"></i> Remove
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

/**
 * Update Student Enrollment Status
 */
async function updateStudentStatus(classId, studentUserId, newStatus) {
    const confirmMsg = newStatus === 'approved' 
        ? 'Approve this student enrollment?' 
        : newStatus === 'blocked' 
        ? 'Block this student from accessing the class?' 
        : 'Reject this student enrollment?';
    
    if (!confirm(confirmMsg)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/classes/${classId}/students/${studentUserId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ status: newStatus })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to update status');
        }
        
        const data = await response.json();
        alert(data.message || 'Student status updated successfully!');
        
        // Reload the student list
        const titleElement = document.getElementById('classStudentsModalTitle');
        const className = titleElement.textContent.split(' - ')[0];
        showClassStudentsModal(classId, className);
    } catch (error) {
        console.error('Error updating student status:', error);
        alert('Error: ' + error.message);
    }
}

/**
 * Remove Student from Class
 */
async function removeStudentFromClass(classId, studentUserId) {
    if (!confirm('Are you sure you want to completely remove this student from the class? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/classes/${classId}/students/${studentUserId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to remove student');
        }
        
        const data = await response.json();
        alert(data.message || 'Student removed successfully!');
        
        // Reload the student list
        const titleElement = document.getElementById('classStudentsModalTitle');
        const className = titleElement.textContent.split(' - ')[0];
        showClassStudentsModal(classId, className);
    } catch (error) {
        console.error('Error removing student:', error);
        alert('Error: ' + error.message);
    }
}

// Make functions globally available
window.loadAdminClassCards = loadAdminClassCards;
window.showClassStudentsModal = showClassStudentsModal;
window.updateStudentStatus = updateStudentStatus;
window.removeStudentFromClass = removeStudentFromClass;
window.switchClassTab = switchClassTab;
