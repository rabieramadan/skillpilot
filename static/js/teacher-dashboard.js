class TeacherDashboard {
    constructor() {
        this.courses = [];
        this.currentCourse = null;
        this.currentStudent = null;
    }

    async init() {
        await this.loadCourses();
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showCreateClassModal() {
        const existingModal = document.getElementById('teacherCreateClassModal');
        if (existingModal) existingModal.remove();

        const modal = document.createElement('div');
        modal.id = 'teacherCreateClassModal';
        modal.className = 'modal-overlay';
        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
        modal.innerHTML = `
            <div style="background: white; border-radius: 12px; width: 90%; max-width: 500px; max-height: 90vh; overflow-y: auto;">
                <div style="padding: 20px; border-bottom: 1px solid #e5e7eb;">
                    <h2 style="margin: 0; color: #1B5E20;"><i class="fas fa-plus-circle"></i> Create New Class</h2>
                </div>
                <div style="padding: 20px;">
                    <form id="teacherCreateClassForm">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Class Title *</label>
                            <input type="text" id="newClassTitle" required style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box;" placeholder="e.g., Introduction to AI" data-testid="input-class-title">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Description</label>
                            <textarea id="newClassDescription" rows="3" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box;" placeholder="Brief description of the course" data-testid="input-class-description"></textarea>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Start Date</label>
                                <input type="date" id="newClassStartDate" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box;" data-testid="input-class-start-date">
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">End Date</label>
                                <input type="date" id="newClassEndDate" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box;" data-testid="input-class-end-date">
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Number of Weeks</label>
                                <input type="number" id="newClassWeeks" value="8" min="1" max="52" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box;" data-testid="input-class-weeks">
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Capacity</label>
                                <input type="number" id="newClassCapacity" value="30" min="1" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box;" data-testid="input-class-capacity">
                            </div>
                        </div>
                        <div id="createClassError" style="display: none; color: #ef4444; margin-bottom: 16px; padding: 10px; background: #fef2f2; border-radius: 6px;"></div>
                        <div style="display: flex; gap: 12px; justify-content: flex-end;">
                            <button type="button" onclick="teacherDashboard.closeCreateClassModal()" style="padding: 10px 20px; border: 1px solid #d1d5db; background: white; border-radius: 6px; cursor: pointer;" data-testid="btn-cancel-create-class">Cancel</button>
                            <button type="submit" style="padding: 10px 20px; background: #1B5E20; color: white; border: none; border-radius: 6px; cursor: pointer;" data-testid="btn-submit-create-class"><i class="fas fa-plus"></i> Create Class</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        document.getElementById('teacherCreateClassForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createClass();
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.closeCreateClassModal();
        });
    }

    closeCreateClassModal() {
        const modal = document.getElementById('teacherCreateClassModal');
        if (modal) modal.remove();
    }

    async createClass() {
        const title = document.getElementById('newClassTitle').value.trim();
        const description = document.getElementById('newClassDescription').value.trim();
        const startDate = document.getElementById('newClassStartDate').value;
        const endDate = document.getElementById('newClassEndDate').value;
        const numWeeks = parseInt(document.getElementById('newClassWeeks').value) || 8;
        const capacity = parseInt(document.getElementById('newClassCapacity').value) || 30;
        const errorDiv = document.getElementById('createClassError');

        if (!title) {
            errorDiv.textContent = 'Class title is required';
            errorDiv.style.display = 'block';
            return;
        }

        try {
            const response = await fetch('/api/teacher/courses', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    title,
                    description,
                    start_date: startDate,
                    end_date: endDate,
                    num_weeks: numWeeks,
                    capacity
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to create class');
            }

            this.closeCreateClassModal();
            alert('Class created successfully! Note: The class is saved as a draft. An admin will publish it when ready.');
            await this.loadCourses();

        } catch (error) {
            console.error('Error creating class:', error);
            errorDiv.textContent = error.message;
            errorDiv.style.display = 'block';
        }
    }

    async loadCourses() {
        const container = document.getElementById('teacherCoursesList');
        if (!container) return;

        try {
            const response = await fetch('/api/teacher/courses', {
                credentials: 'include'
            });

            if (!response.ok) {
                if (response.status === 401) {
                    container.innerHTML = '<div style="text-align: center; padding: 40px; color: #ef4444;">Please log in to view your courses</div>';
                    return;
                }
                throw new Error('Failed to load courses');
            }

            const data = await response.json();
            const classes = data.classes || data.courses;
            
            if (!data.success || !classes || classes.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <i class="fas fa-book-open" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                        <p>No courses found. Create a class to get started.</p>
                        <button onclick="teacherDashboard.showCreateClassModal()" class="btn-primary" style="margin-top: 16px; padding: 12px 24px; background: #1B5E20; color: white; border: none; border-radius: 8px; cursor: pointer;" data-testid="btn-create-class">
                            <i class="fas fa-plus"></i> Create New Class
                        </button>
                    </div>
                `;
                return;
            }

            this.courses = classes;
            this.renderCoursesList();
        } catch (error) {
            console.error('Error loading courses:', error);
            container.innerHTML = `<div style="text-align: center; padding: 40px; color: #ef4444;">Error loading courses: ${error.message}</div>`;
        }
    }

    renderCoursesList() {
        const container = document.getElementById('teacherCoursesList');
        if (!container) return;

        container.innerHTML = `
            <div style="display: flex; justify-content: flex-end; margin-bottom: 16px;">
                <button onclick="teacherDashboard.showCreateClassModal()" class="btn-primary" style="padding: 10px 20px; background: #1B5E20; color: white; border: none; border-radius: 8px; cursor: pointer;" data-testid="btn-create-class-header">
                    <i class="fas fa-plus"></i> Create New Class
                </button>
            </div>
        ` + this.courses.map(course => `
            <div class="class-card" style="cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;" 
                 onclick="teacherDashboard.openCourse('${course.id}')" 
                 data-testid="course-card-${course.id}">
                <div class="class-card-header" style="background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%); color: white; padding: 16px; border-radius: 8px 8px 0 0;">
                    <h3 style="margin: 0; font-size: 18px;">${this.escapeHtml(course.title)}</h3>
                    <span style="font-size: 12px; opacity: 0.9;">${this.escapeHtml(course.code || 'No Code')}</span>
                </div>
                <div class="class-card-body" style="padding: 16px;">
                    <p style="color: #666; font-size: 14px; margin-bottom: 12px;">${this.escapeHtml(course.description || 'No description')}</p>
                    <div style="display: flex; gap: 16px; font-size: 14px;">
                        <span style="color: #16a34a;"><i class="fas fa-users"></i> ${course.enrolled_count || 0} enrolled</span>
                        <span style="color: #f59e0b;"><i class="fas fa-clock"></i> ${course.pending_count || 0} pending</span>
                    </div>
                    <div style="margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;">
                        ${course.is_published ? '<span style="background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-size: 12px;"><i class="fas fa-check"></i> Published</span>' : '<span style="background: #fef9c3; color: #854d0e; padding: 4px 8px; border-radius: 4px; font-size: 12px;"><i class="fas fa-eye-slash"></i> Draft</span>'}
                        ${course.meet_link ? '<span style="background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 4px; font-size: 12px;"><i class="fab fa-google"></i> Meet</span>' : ''}
                        ${course.zoom_link ? '<span style="background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 4px; font-size: 12px;"><i class="fas fa-video"></i> Zoom</span>' : ''}
                    </div>
                </div>
            </div>
        `).join('');
    }

    async openCourse(courseId) {
        try {
            const response = await fetch(`/api/teacher/courses/${courseId}`, {
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to load course details');

            const data = await response.json();
            
            if (!data.success) throw new Error(data.error || 'Failed to load course');

            this.currentCourse = {
                ...(data.class || data.course),
                weeks: data.weeks,
                exams: data.exams,
                enrollment_stats: data.enrollment_stats
            };

            this.showCourseDetail();
        } catch (error) {
            console.error('Error loading course:', error);
            alert('Error loading course: ' + error.message);
        }
    }

    showCourseDetail() {
        document.getElementById('teacherDashboardMain').style.display = 'none';
        document.getElementById('teacherCourseDetail').style.display = 'block';
        document.getElementById('teacherStudentDetail').style.display = 'none';

        this.renderCourseHeader();
        this.renderMaterials();
        this.renderAssignments();
        this.renderExams();
        this.loadStudents();
        this.loadSubmissions();
        this.loadSessionLinks();
        this.loadSurveys();
        this.showTab('materials');
    }

    showCoursesList() {
        document.getElementById('teacherDashboardMain').style.display = 'block';
        document.getElementById('teacherCourseDetail').style.display = 'none';
        document.getElementById('teacherStudentDetail').style.display = 'none';
        this.loadCourses();
    }

    renderCourseHeader() {
        const container = document.getElementById('courseDetailHeader');
        if (!container || !this.currentCourse) return;

        container.innerHTML = `
            <div class="admin-card" style="margin-bottom: 16px;">
                <div class="admin-card-body">
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <div style="flex: 1;">
                            <h2 style="margin: 0 0 8px 0;">${this.escapeHtml(this.currentCourse.title)}</h2>
                            <p style="color: #666; margin: 0;">${this.escapeHtml(this.currentCourse.description || 'No description')}</p>
                            <div style="margin-top: 12px; display: flex; gap: 16px; font-size: 14px;">
                                <span style="color: #16a34a;"><i class="fas fa-users"></i> ${this.currentCourse.enrollment_stats?.active || 0} Active Students</span>
                                <span style="color: #3b82f6;"><i class="fas fa-book"></i> ${this.currentCourse.weeks?.length || 0} Weeks</span>
                                <span style="color: #8b5cf6;"><i class="fas fa-file-alt"></i> ${this.currentCourse.exams?.length || 0} Exams</span>
                            </div>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 8px; align-items: flex-end;">
                            ${this.currentCourse.is_published ? 
                                '<span style="background: #dcfce7; color: #166534; padding: 8px 16px; border-radius: 20px;"><i class="fas fa-check-circle"></i> Published</span>' : 
                                '<span style="background: #fef9c3; color: #854d0e; padding: 8px 16px; border-radius: 20px;"><i class="fas fa-eye-slash"></i> Draft</span>'}
                            <button onclick="classManagement.openClassDetail('${this.currentCourse.id}', '${this.escapeHtml(this.currentCourse.title).replace(/'/g, "\\'")}')" 
                                    class="btn-primary" style="padding: 8px 16px;" data-testid="button-manage-class">
                                <i class="fas fa-cogs"></i> Manage Class
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    showTab(tabName) {
        document.querySelectorAll('.teacher-tab-content').forEach(tab => {
            tab.style.display = 'none';
        });
        document.querySelectorAll('.teacher-tab-btn').forEach(btn => {
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-secondary');
        });

        const activeTab = document.getElementById(`teacher-tab-${tabName}`);
        const activeBtn = document.querySelector(`.teacher-tab-btn[data-tab="${tabName}"]`);
        
        if (activeTab) activeTab.style.display = 'block';
        if (activeBtn) {
            activeBtn.classList.remove('btn-secondary');
            activeBtn.classList.add('btn-primary');
        }
        
        // Auto-load attendance when tab is shown
        if (tabName === 'attendance') {
            const dateInput = document.getElementById('teacherAttendanceDate');
            if (dateInput && !dateInput.value) {
                dateInput.value = new Date().toISOString().split('T')[0];
            }
            this.loadAttendance();
        }
        // Lazy-render the AI Analysis tab when opened.
        if (tabName === 'ai-analysis') {
            this.renderCourseAITools();
        }
    }

    // ------------------------------------------------------------------
    // Per-course AI Analysis
    // ------------------------------------------------------------------
    async runClassAIAnalysis() {
        if (!this.currentCourse) return;
        const model = document.getElementById('classAnalysisModel')?.value || '';
        const language = document.getElementById('classAnalysisLanguage')?.value || 'English';
        const status = document.getElementById('classAnalysisStatus');
        const out = document.getElementById('classAnalysisResult');
        if (status) status.textContent = 'Analysing the class roster — this can take 30–60 seconds...';
        if (out) out.textContent = '';
        try {
            const res = await fetch(`/api/teacher/courses/${this.currentCourse.id}/class-ai-analysis`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model, language })
            });
            const data = await res.json();
            if (data.success) {
                this._lastClassAnalysis = data.report;
                if (out) out.textContent = data.report;
                if (status) status.textContent = `Analysed ${data.students_analyzed} students using ${data.model_used}.`;
            } else {
                if (out) out.textContent = '';
                if (status) status.textContent = `Failed: ${data.error || 'unknown error'}`;
            }
        } catch (e) {
            if (status) status.textContent = `Network error: ${e.message}`;
        }
    }

    copyClassAnalysis() {
        if (!this._lastClassAnalysis) return;
        navigator.clipboard.writeText(this._lastClassAnalysis);
    }

    downloadClassAnalysis() {
        if (!this._lastClassAnalysis || !this.currentCourse) return;
        const blob = new Blob([this._lastClassAnalysis], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `class_analysis_${this.currentCourse.id}_${new Date().toISOString().slice(0,10)}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    async renderCourseAITools() {
        if (!this.currentCourse) return;
        const titleEl = document.getElementById('courseAIToolsCourseTitle');
        if (titleEl) titleEl.textContent = this.currentCourse.title || 'this course';
        const grid = document.getElementById('courseAIToolsGrid');
        if (!grid) return;
        if (this._courseAIToolsRendered === this.currentCourse.id) return;
        grid.innerHTML = '<div style="grid-column:1/-1; color:#9ca3af; font-size:13px;">Loading AI tools...</div>';
        try {
            const res = await fetch(`/api/teacher/courses/${this.currentCourse.id}/ai-tools/list`);
            const data = await res.json();
            if (!data.success || !Array.isArray(data.tools)) {
                grid.innerHTML = `<div style="grid-column:1/-1; color:#dc2626;">Failed to load tools: ${data.error || 'unknown'}</div>`;
                return;
            }
            const isArabic = (window.i18n?.currentLang === 'ar');
            grid.innerHTML = '';
            data.tools.forEach(t => {
                const card = document.createElement('div');
                card.className = 'admin-card';
                card.style.cssText = 'cursor:pointer; padding:14px; border:1px solid #e5e7eb; border-radius:10px; transition:all 0.15s; background:white;';
                card.onmouseover = () => { card.style.borderColor = '#6366f1'; card.style.boxShadow = '0 2px 8px rgba(99,102,241,0.15)'; };
                card.onmouseout  = () => { card.style.borderColor = '#e5e7eb'; card.style.boxShadow = 'none'; };
                card.setAttribute('data-testid', `card-course-ai-tool-${t.id}`);
                const title = (isArabic && t.name_ar) ? t.name_ar : t.name;
                const desc  = (isArabic && t.description_ar) ? t.description_ar : t.description;
                card.innerHTML = `
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                        <i class="fas ${t.icon || 'fa-magic'}" style="color:#6366f1; font-size:18px;"></i>
                        <strong style="font-size:14px; color:#111827;">${title}</strong>
                    </div>
                    <div style="font-size:12px; color:#6b7280; line-height:1.4;">${desc || ''}</div>`;
                card.onclick = () => this.openCourseAITool(t.id);
                grid.appendChild(card);
            });
            this._courseAIToolsRendered = this.currentCourse.id;
        } catch (e) {
            grid.innerHTML = `<div style="grid-column:1/-1; color:#dc2626;">Network error: ${e.message}</div>`;
        }
    }

    openCourseAITool(toolId) {
        if (!window.aiTools || !this.currentCourse) return;
        // Open the standard AI tool modal then re-route its submit to the
        // course-scoped endpoint so the prompt is auto-prefixed with course context.
        window.aiTools.openTool(toolId);
        window.aiTools._courseScope = this.currentCourse.id;
    }

    renderMaterials() {
        const container = document.getElementById('courseMaterialsList');
        if (!container || !this.currentCourse) return;

        const weeks = this.currentCourse.weeks || [];

        if (weeks.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-folder-open" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                    <p>No weeks created yet. Add your first week to start adding materials.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = weeks.map(week => `
            <div class="week-section" style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; margin-bottom: 16px; overflow: hidden;">
                <div style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 16px; display: flex; align-items: center; justify-content: between;">
                    <div style="flex: 1;">
                        <h4 style="margin: 0;">Week ${week.week_number}: ${this.escapeHtml(week.title)}</h4>
                        <p style="margin: 4px 0 0 0; opacity: 0.9; font-size: 14px;">${this.escapeHtml(week.description || '')}</p>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn-secondary" style="padding: 6px 12px;" onclick="teacherDashboard.showAddMaterialModal('${week.id}')" data-testid="button-add-material-${week.id}">
                            <i class="fas fa-plus"></i> Add Material
                        </button>
                        <button class="btn-secondary" style="padding: 6px 12px;" onclick="teacherDashboard.showAddAssignmentModal('${week.id}')" data-testid="button-add-assignment-${week.id}">
                            <i class="fas fa-tasks"></i> Add Assignment
                        </button>
                    </div>
                </div>
                <div style="padding: 16px;">
                    ${week.materials && week.materials.length > 0 ? `
                        <div style="margin-bottom: 12px;">
                            <h5 style="margin: 0 0 8px 0; color: #374151;"><i class="fas fa-book"></i> Materials</h5>
                            ${week.materials.map(mat => `
                                <div style="display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: white; border-radius: 6px; margin-bottom: 4px; border: 1px solid #e5e7eb;">
                                    <i class="fas ${this.getMaterialIcon(mat.material_type)}" style="color: #3b82f6;"></i>
                                    <span style="flex: 1;">
                                        ${this.escapeHtml(mat.title)}
                                        ${mat.file_name ? `<span style="color: #666; font-size: 11px; margin-left: 8px;">(${mat.file_name})</span>` : ''}
                                    </span>
                                    ${this.getVisibilityBadge(mat.visibility_state || 'approved', mat.available_at)}
                                    <span style="color: #888; font-size: 12px;">${mat.duration_minutes ? mat.duration_minutes + ' min' : ''}</span>
                                    ${mat.file_url ? `<a href="${mat.file_url}" target="_blank" class="btn-icon" style="padding: 4px 8px; color: #3b82f6;" title="Download"><i class="fas fa-download"></i></a>` : ''}
                                    <button class="btn-icon" onclick="teacherDashboard.editMaterial('${mat.id}')" style="padding: 4px 8px;" data-testid="button-edit-material-${mat.id}">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn-icon" onclick="teacherDashboard.deleteMaterial('${mat.id}')" style="padding: 4px 8px; color: #ef4444;" data-testid="button-delete-material-${mat.id}">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p style="color: #888; font-size: 14px;">No materials added yet</p>'}
                    
                    ${week.assignments && week.assignments.length > 0 ? `
                        <div>
                            <h5 style="margin: 0 0 8px 0; color: #374151;"><i class="fas fa-tasks"></i> Assignments</h5>
                            ${week.assignments.map(assign => `
                                <div style="display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: white; border-radius: 6px; margin-bottom: 4px; border: 1px solid #e5e7eb;">
                                    <i class="fas fa-clipboard-check" style="color: #16a34a;"></i>
                                    <span style="flex: 1;">${this.escapeHtml(assign.title)}</span>
                                    <span style="color: #888; font-size: 12px;">${assign.due_date ? 'Due: ' + new Date(assign.due_date).toLocaleDateString() : ''}</span>
                                    <span style="background: ${assign.is_published ? '#dcfce7' : '#fef9c3'}; color: ${assign.is_published ? '#166534' : '#854d0e'}; padding: 2px 8px; border-radius: 4px; font-size: 11px;">${assign.is_published ? 'Published' : 'Draft'}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    getMaterialIcon(type) {
        const icons = {
            'video': 'fa-video',
            'document': 'fa-file-alt',
            'pdf': 'fa-file-pdf',
            'link': 'fa-link',
            'audio': 'fa-headphones',
            'image': 'fa-image',
            'spreadsheet': 'fa-file-excel',
            'presentation': 'fa-file-powerpoint'
        };
        return icons[type] || 'fa-file';
    }
    
    getVisibilityBadge(state, availableAt) {
        const badges = {
            'draft': '<span style="background: #fef3c7; color: #854d0e; padding: 2px 8px; border-radius: 4px; font-size: 11px;"><i class="fas fa-eye-slash"></i> Draft</span>',
            'approved': '<span style="background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-size: 11px;"><i class="fas fa-check"></i> Published</span>',
            'scheduled': `<span style="background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-size: 11px;"><i class="fas fa-clock"></i> ${availableAt ? new Date(availableAt).toLocaleDateString() : 'Scheduled'}</span>`
        };
        return badges[state] || badges['draft'];
    }

    renderAssignments() {
        const container = document.getElementById('courseAssignmentsList');
        if (!container || !this.currentCourse) return;

        const weeks = this.currentCourse.weeks || [];
        let allAssignments = [];
        
        weeks.forEach(week => {
            if (week.assignments) {
                week.assignments.forEach(a => {
                    allAssignments.push({...a, week_number: week.week_number, week_title: week.title});
                });
            }
        });

        if (allAssignments.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-tasks" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                    <p>No assignments created yet. Go to the Materials tab to add assignments to weeks.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <table class="admin-table" style="width: 100%;">
                <thead>
                    <tr>
                        <th>Assignment</th>
                        <th>Week</th>
                        <th>Type</th>
                        <th>Due Date</th>
                        <th>Max Points</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${allAssignments.map(assign => `
                        <tr>
                            <td>${this.escapeHtml(assign.title)}</td>
                            <td>Week ${assign.week_number}</td>
                            <td>${assign.assignment_type}</td>
                            <td>${assign.due_date ? new Date(assign.due_date).toLocaleDateString() : '-'}</td>
                            <td>${assign.max_points}</td>
                            <td>
                                <span style="background: ${assign.is_published ? '#dcfce7' : '#fef9c3'}; color: ${assign.is_published ? '#166534' : '#854d0e'}; padding: 4px 12px; border-radius: 20px; font-size: 12px;">
                                    ${assign.is_published ? 'Published' : 'Draft'}
                                </span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    renderExams() {
        const container = document.getElementById('courseExamsList');
        if (!container || !this.currentCourse) return;

        const exams = this.currentCourse.exams || [];

        if (exams.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-file-alt" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                    <p>No exams created yet. Click "Create Exam" to add a new exam or quiz.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;">
                ${exams.map(exam => `
                    <div style="background: white; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">
                        <div style="background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%); color: white; padding: 16px;">
                            <h4 style="margin: 0;">${this.escapeHtml(exam.title)}</h4>
                            <span style="font-size: 12px; opacity: 0.9; text-transform: capitalize;">${exam.exam_type}</span>
                        </div>
                        <div style="padding: 16px;">
                            <p style="color: #666; font-size: 14px;">${this.escapeHtml(exam.description || 'No description')}</p>
                            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px;">
                                ${exam.time_limit_minutes ? `<span style="background: #f3f4f6; padding: 4px 8px; border-radius: 4px; font-size: 12px;"><i class="fas fa-clock"></i> ${exam.time_limit_minutes} min</span>` : ''}
                                <span style="background: ${exam.is_published ? '#dcfce7' : '#fef9c3'}; color: ${exam.is_published ? '#166534' : '#854d0e'}; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                                    ${exam.is_published ? 'Published' : 'Draft'}
                                </span>
                            </div>
                            <div style="margin-top: 12px;">
                                <button class="btn-secondary" style="padding: 6px 12px; font-size: 12px;" onclick="teacherDashboard.manageExamQuestions('${exam.id}')" data-testid="button-manage-questions-${exam.id}">
                                    <i class="fas fa-list"></i> Manage Questions
                                </button>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    async loadStudents() {
        const container = document.getElementById('courseStudentsList');
        if (!container || !this.currentCourse) return;

        container.innerHTML = '<div style="text-align: center; padding: 20px;"><i class="fas fa-spinner fa-spin"></i> Loading students...</div>';

        try {
            const response = await fetch(`/api/teacher/courses/${this.currentCourse.id}/students`, {
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to load students');

            const data = await response.json();
            
            if (!data.success || !data.students || data.students.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <i class="fas fa-users" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                        <p>No students enrolled yet.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <table class="admin-table" style="width: 100%;">
                    <thead>
                        <tr>
                            <th>Student</th>
                            <th>Progress</th>
                            <th>Materials</th>
                            <th>Assignments</th>
                            <th>Avg Score</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.students.map(student => `
                            <tr>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <div style="width: 36px; height: 36px; background: #e5e7eb; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                            <i class="fas fa-user" style="color: #6b7280;"></i>
                                        </div>
                                        <div>
                                            <div style="font-weight: 500;">${this.escapeHtml(student.full_name)}</div>
                                            <div style="font-size: 12px; color: #888;">@${this.escapeHtml(student.username)}</div>
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <div style="flex: 1; background: #e5e7eb; height: 8px; border-radius: 4px; overflow: hidden;">
                                            <div style="width: ${student.progress?.overall_percent || 0}%; background: #16a34a; height: 100%;"></div>
                                        </div>
                                        <span style="font-size: 12px; color: #666;">${student.progress?.overall_percent || 0}%</span>
                                    </div>
                                </td>
                                <td>${student.progress?.materials_completed || 0}/${student.progress?.materials_total || 0}</td>
                                <td>${student.progress?.assignments_submitted || 0}/${student.progress?.assignments_total || 0}</td>
                                <td>${student.progress?.average_score != null ? student.progress.average_score + '%' : '-'}</td>
                                <td>
                                    <button class="btn-secondary" style="padding: 4px 8px; font-size: 12px;" onclick="teacherDashboard.viewStudent('${student.id}')" data-testid="button-view-student-${student.id}">
                                        <i class="fas fa-eye"></i> View
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (error) {
            console.error('Error loading students:', error);
            container.innerHTML = `<div style="text-align: center; padding: 40px; color: #ef4444;">Error loading students: ${error.message}</div>`;
        }
    }

    async loadSubmissions() {
        const container = document.getElementById('courseSubmissionsList');
        if (!container || !this.currentCourse) return;

        container.innerHTML = '<div style="text-align: center; padding: 20px;"><i class="fas fa-spinner fa-spin"></i> Loading submissions...</div>';

        try {
            const response = await fetch(`/api/teacher/courses/${this.currentCourse.id}/submissions`, {
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to load submissions');

            const data = await response.json();
            
            if (!data.success || !data.submissions || data.submissions.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <i class="fas fa-inbox" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                        <p>No submissions to grade yet.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <div style="margin-bottom: 16px; padding: 12px; background: #f0fdf4; border-radius: 8px; display: flex; gap: 24px;">
                    <span><strong>${data.stats?.pending || 0}</strong> pending review</span>
                    <span><strong>${data.stats?.graded || 0}</strong> graded</span>
                </div>
                <table class="admin-table" style="width: 100%;">
                    <thead>
                        <tr>
                            <th>Student</th>
                            <th>Assignment</th>
                            <th>Submitted</th>
                            <th>Status</th>
                            <th>Score</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.submissions.map(sub => `
                            <tr>
                                <td>${this.escapeHtml(sub.student?.full_name || 'Unknown')}</td>
                                <td>${this.escapeHtml(sub.assignment?.title || 'Unknown')}</td>
                                <td>${sub.submitted_at ? new Date(sub.submitted_at).toLocaleDateString() : '-'}</td>
                                <td>
                                    <span style="background: ${sub.status === 'graded' ? '#dcfce7' : '#fef9c3'}; color: ${sub.status === 'graded' ? '#166534' : '#854d0e'}; padding: 4px 12px; border-radius: 20px; font-size: 12px;">
                                        ${sub.status === 'graded' ? 'Graded' : 'Pending'}
                                    </span>
                                </td>
                                <td>${sub.score != null ? sub.score + '/' + (sub.assignment?.max_points || 100) : '-'}</td>
                                <td>
                                    <button class="btn-primary" style="padding: 4px 8px; font-size: 12px;" onclick="teacherDashboard.showGradeModal('${sub.id}', '${this.escapeHtml(sub.student?.full_name || '')}', '${this.escapeHtml(sub.assignment?.title || '')}', ${sub.assignment?.max_points || 100}, ${sub.score || ''}, '${this.escapeHtml(sub.feedback || '')}')" data-testid="button-grade-${sub.id}">
                                        <i class="fas fa-check"></i> ${sub.status === 'graded' ? 'Edit Grade' : 'Grade'}
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (error) {
            console.error('Error loading submissions:', error);
            container.innerHTML = `<div style="text-align: center; padding: 40px; color: #ef4444;">Error loading submissions: ${error.message}</div>`;
        }
    }

    loadSessionLinks() {
        if (!this.currentCourse) return;
        
        const meetInput = document.getElementById('courseMeetLink');
        const zoomInput = document.getElementById('courseZoomLink');
        const youtubeInput = document.getElementById('courseYoutubeLink');
        
        if (meetInput) meetInput.value = this.currentCourse.meet_link || '';
        if (zoomInput) zoomInput.value = this.currentCourse.zoom_link || '';
        if (youtubeInput) youtubeInput.value = this.currentCourse.youtube_broadcast_link || '';
    }

    async saveSessionLinks() {
        if (!this.currentCourse) return;

        const data = {
            meet_link: document.getElementById('courseMeetLink')?.value || '',
            zoom_link: document.getElementById('courseZoomLink')?.value || '',
            youtube_broadcast_link: document.getElementById('courseYoutubeLink')?.value || ''
        };

        try {
            const response = await fetch(`/api/teacher/courses/${this.currentCourse.id}/sessions`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data)
            });

            if (!response.ok) throw new Error('Failed to save session links');

            const result = await response.json();
            
            if (result.success) {
                alert('Session links saved successfully!');
                this.currentCourse.meet_link = data.meet_link;
                this.currentCourse.zoom_link = data.zoom_link;
                this.currentCourse.youtube_broadcast_link = data.youtube_broadcast_link;
            } else {
                throw new Error(result.error || 'Failed to save');
            }
        } catch (error) {
            console.error('Error saving session links:', error);
            alert('Error saving session links: ' + error.message);
        }
    }

    async viewStudent(studentId) {
        if (!this.currentCourse) return;
        
        this.currentStudent = { id: studentId };

        try {
            const response = await fetch(`/api/teacher/courses/${this.currentCourse.id}/students/${studentId}/details`, {
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to load student details');

            const data = await response.json();
            
            if (!data.success) throw new Error(data.error || 'Failed to load student');

            this.currentStudent = {
                ...data.student,
                weeks_progress: data.weeks_progress,
                exam_results: data.exam_results,
                summary: data.summary
            };

            this.showStudentDetail();
        } catch (error) {
            console.error('Error loading student:', error);
            alert('Error loading student details: ' + error.message);
        }
    }

    showStudentDetail() {
        document.getElementById('teacherCourseDetail').style.display = 'none';
        document.getElementById('teacherStudentDetail').style.display = 'block';

        this.renderStudentHeader();
        this.renderStudentProgress();
        this.loadChatMessages();
        this.showStudentTab('progress');
    }

    backToStudentsList() {
        document.getElementById('teacherStudentDetail').style.display = 'none';
        document.getElementById('teacherCourseDetail').style.display = 'block';
        this.showTab('students');
    }

    showStudentTab(tabName) {
        document.querySelectorAll('.student-tab-content').forEach(tab => {
            tab.style.display = 'none';
        });
        document.querySelectorAll('.student-tab-btn').forEach(btn => {
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-secondary');
        });

        const activeTab = document.getElementById(`student-tab-${tabName}`);
        const activeBtn = document.querySelector(`.student-tab-btn[data-tab="${tabName}"]`);
        
        if (activeTab) activeTab.style.display = 'block';
        if (activeBtn) {
            activeBtn.classList.remove('btn-secondary');
            activeBtn.classList.add('btn-primary');
        }
    }

    renderStudentHeader() {
        const container = document.getElementById('studentDetailHeader');
        if (!container || !this.currentStudent) return;

        container.innerHTML = `
            <div class="admin-card-body">
                <div style="display: flex; align-items: center; gap: 16px;">
                    <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px;">
                        ${this.currentStudent.full_name?.charAt(0)?.toUpperCase() || 'S'}
                    </div>
                    <div style="flex: 1;">
                        <h3 style="margin: 0;">${this.escapeHtml(this.currentStudent.full_name)}</h3>
                        <p style="margin: 4px 0; color: #666;">@${this.escapeHtml(this.currentStudent.username)} | ${this.escapeHtml(this.currentStudent.email || 'No email')}</p>
                        <p style="margin: 0; font-size: 14px; color: #888;">Enrolled: ${this.currentStudent.enrolled_at ? new Date(this.currentStudent.enrolled_at).toLocaleDateString() : 'N/A'}</p>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 36px; font-weight: bold; color: #16a34a;">${this.currentStudent.summary?.overall_progress || 0}%</div>
                        <div style="color: #666; font-size: 14px;">Overall Progress</div>
                    </div>
                </div>
            </div>
        `;
    }

    renderStudentProgress() {
        const container = document.getElementById('studentProgressDetail');
        if (!container || !this.currentStudent) return;

        const weeks = this.currentStudent.weeks_progress || [];
        const exams = this.currentStudent.exam_results || [];

        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; margin-bottom: 24px;">
                <div style="background: #dbeafe; padding: 20px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #1e40af;">${this.currentStudent.summary?.overall_progress || 0}%</div>
                    <div style="color: #1e40af;">Overall Progress</div>
                </div>
                <div style="background: #dcfce7; padding: 20px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #166534;">Week ${this.currentStudent.summary?.current_week || 1}</div>
                    <div style="color: #166534;">Current Week</div>
                </div>
                <div style="background: #fef9c3; padding: 20px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #854d0e;">${this.currentStudent.summary?.final_grade != null ? this.currentStudent.summary.final_grade + '%' : '-'}</div>
                    <div style="color: #854d0e;">Final Grade</div>
                </div>
            </div>

            <h4><i class="fas fa-calendar-week"></i> Weekly Progress</h4>
            ${weeks.map(week => `
                <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                    <h5 style="margin: 0 0 12px 0;">Week ${week.week_number}: ${this.escapeHtml(week.title)}</h5>
                    
                    ${week.materials && week.materials.length > 0 ? `
                        <div style="margin-bottom: 12px;">
                            <strong style="font-size: 14px; color: #666;">Materials:</strong>
                            ${week.materials.map(mat => `
                                <div style="display: flex; align-items: center; gap: 8px; padding: 8px; background: white; border-radius: 4px; margin-top: 4px;">
                                    <i class="fas ${mat.status === 'completed' ? 'fa-check-circle' : mat.status === 'in_progress' ? 'fa-spinner' : 'fa-circle'}" style="color: ${mat.status === 'completed' ? '#16a34a' : mat.status === 'in_progress' ? '#f59e0b' : '#d1d5db'};"></i>
                                    <span style="flex: 1;">${this.escapeHtml(mat.title)}</span>
                                    <span style="color: #888; font-size: 12px;">${mat.progress_percent}%</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                    
                    ${week.assignments && week.assignments.length > 0 ? `
                        <div>
                            <strong style="font-size: 14px; color: #666;">Assignments:</strong>
                            ${week.assignments.map(assign => `
                                <div style="display: flex; align-items: center; gap: 8px; padding: 8px; background: white; border-radius: 4px; margin-top: 4px;">
                                    <i class="fas ${assign.status === 'graded' ? 'fa-check-circle' : assign.submitted ? 'fa-clock' : 'fa-times-circle'}" style="color: ${assign.status === 'graded' ? '#16a34a' : assign.submitted ? '#f59e0b' : '#ef4444'};"></i>
                                    <span style="flex: 1;">${this.escapeHtml(assign.title)}</span>
                                    <span style="color: #888; font-size: 12px;">${assign.score != null ? assign.score + '/' + assign.max_points : assign.submitted ? 'Pending' : 'Not submitted'}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `).join('')}

            ${exams.length > 0 ? `
                <h4 style="margin-top: 24px;"><i class="fas fa-file-alt"></i> Exam Results</h4>
                ${exams.map(exam => `
                    <div style="display: flex; align-items: center; gap: 12px; padding: 12px; background: ${exam.taken ? (exam.passed ? '#dcfce7' : '#fee2e2') : '#f3f4f6'}; border-radius: 8px; margin-bottom: 8px;">
                        <i class="fas ${exam.taken ? (exam.passed ? 'fa-check-circle' : 'fa-times-circle') : 'fa-minus-circle'}" style="font-size: 20px; color: ${exam.taken ? (exam.passed ? '#16a34a' : '#ef4444') : '#9ca3af'};"></i>
                        <div style="flex: 1;">
                            <div style="font-weight: 500;">${this.escapeHtml(exam.title)}</div>
                            <div style="font-size: 12px; color: #666; text-transform: capitalize;">${exam.type}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-weight: bold; color: ${exam.taken ? (exam.passed ? '#16a34a' : '#ef4444') : '#9ca3af'};">
                                ${exam.taken ? exam.percentage + '%' : 'Not taken'}
                            </div>
                        </div>
                    </div>
                `).join('')}
            ` : ''}
        `;
    }

    async loadChatMessages() {
        const container = document.getElementById('studentChatMessages');
        if (!container || !this.currentCourse || !this.currentStudent) return;

        container.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;"><i class="fas fa-spinner fa-spin"></i> Loading messages...</div>';

        try {
            const response = await fetch(`/api/teacher/courses/${this.currentCourse.id}/chat/${this.currentStudent.id}/messages`, {
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to load messages');

            const data = await response.json();
            
            if (!data.success) throw new Error(data.error || 'Failed to load messages');

            if (!data.messages || data.messages.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <i class="fas fa-comments" style="font-size: 32px; color: #ccc; margin-bottom: 12px;"></i>
                        <p>No messages yet. Start a conversation with this student.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = data.messages.map(msg => `
                <div style="display: flex; ${msg.is_teacher ? 'justify-content: flex-end' : 'justify-content: flex-start'}; margin-bottom: 12px;">
                    <div style="max-width: 70%; padding: 12px 16px; border-radius: 16px; ${msg.is_teacher ? 'background: #3b82f6; color: white; border-bottom-right-radius: 4px;' : 'background: white; border: 1px solid #e5e7eb; border-bottom-left-radius: 4px;'}">
                        <div style="word-wrap: break-word;">${this.escapeHtml(msg.message)}</div>
                        <div style="font-size: 10px; ${msg.is_teacher ? 'color: rgba(255,255,255,0.7);' : 'color: #888;'} margin-top: 4px; text-align: right;">
                            ${new Date(msg.created_at).toLocaleString()}
                        </div>
                    </div>
                </div>
            `).join('');

            container.scrollTop = container.scrollHeight;
        } catch (error) {
            console.error('Error loading messages:', error);
            container.innerHTML = `<div style="text-align: center; padding: 20px; color: #ef4444;">Error loading messages</div>`;
        }
    }

    async sendMessage() {
        if (!this.currentCourse || !this.currentStudent) return;

        const input = document.getElementById('studentChatInput');
        const message = input?.value?.trim();
        
        if (!message) return;

        try {
            const response = await fetch(`/api/teacher/courses/${this.currentCourse.id}/chat/${this.currentStudent.id}/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ message })
            });

            if (!response.ok) throw new Error('Failed to send message');

            const result = await response.json();
            
            if (result.success) {
                input.value = '';
                await this.loadChatMessages();
            } else {
                throw new Error(result.error || 'Failed to send');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            alert('Error sending message: ' + error.message);
        }
    }

    async generateAIReport() {
        if (!this.currentCourse || !this.currentStudent) return;

        const container = document.getElementById('studentAIReport');
        container.innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <i class="fas fa-robot fa-3x" style="color: #3b82f6; margin-bottom: 16px;"></i>
                <p style="color: #666;">Generating AI performance report...</p>
                <p style="font-size: 12px; color: #888;">This may take a few seconds.</p>
            </div>
        `;

        try {
            const response = await fetch(`/api/teacher/courses/${this.currentCourse.id}/students/${this.currentStudent.id}/ai-report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to generate report');

            const data = await response.json();
            
            if (!data.success) throw new Error(data.error || 'Failed to generate report');

            const report = data.report;

            container.innerHTML = `
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 16px;">
                    <h4 style="margin: 0 0 8px 0;"><i class="fas fa-robot"></i> AI Performance Report</h4>
                    <p style="margin: 0; opacity: 0.9; font-size: 14px;">Generated on ${new Date(report.generated_at).toLocaleString()}</p>
                </div>

                <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 16px;">
                    <h5 style="margin: 0 0 8px 0; color: #166534;"><i class="fas fa-chart-line"></i> Performance Summary</h5>
                    <p style="margin: 0; color: #166534;">${this.escapeHtml(report.performance_summary)}</p>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-bottom: 16px;">
                    <div style="background: #dbeafe; padding: 16px; border-radius: 12px;">
                        <h5 style="margin: 0 0 12px 0; color: #1e40af;"><i class="fas fa-star"></i> Strengths</h5>
                        <ul style="margin: 0; padding-left: 20px; color: #1e40af;">
                            ${(report.strengths || []).map(s => `<li>${this.escapeHtml(s)}</li>`).join('')}
                        </ul>
                    </div>
                    <div style="background: #fef9c3; padding: 16px; border-radius: 12px;">
                        <h5 style="margin: 0 0 12px 0; color: #854d0e;"><i class="fas fa-exclamation-triangle"></i> Areas for Improvement</h5>
                        <ul style="margin: 0; padding-left: 20px; color: #854d0e;">
                            ${(report.areas_for_improvement || []).map(a => `<li>${this.escapeHtml(a)}</li>`).join('')}
                        </ul>
                    </div>
                </div>

                <div style="background: #f3f4f6; padding: 16px; border-radius: 12px; margin-bottom: 16px;">
                    <h5 style="margin: 0 0 12px 0; color: #374151;"><i class="fas fa-tasks"></i> Recommended Actions</h5>
                    <ol style="margin: 0; padding-left: 20px; color: #374151;">
                        ${(report.recommended_actions || []).map(a => `<li style="margin-bottom: 8px;">${this.escapeHtml(a)}</li>`).join('')}
                    </ol>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px;">
                    <div style="background: #f0f9ff; padding: 16px; border-radius: 12px;">
                        <h5 style="margin: 0 0 12px 0; color: #0369a1;"><i class="fas fa-lightbulb"></i> Suggested Learning Methods</h5>
                        <ul style="margin: 0; padding-left: 20px; color: #0369a1;">
                            ${(report.suggested_learning_methods || []).map(m => `<li>${this.escapeHtml(m)}</li>`).join('')}
                        </ul>
                    </div>
                    <div style="background: #fdf2f8; padding: 16px; border-radius: 12px;">
                        <h5 style="margin: 0 0 12px 0; color: #9d174d;"><i class="fas fa-plus-circle"></i> Extra Assignments Suggested</h5>
                        <ul style="margin: 0; padding-left: 20px; color: #9d174d;">
                            ${(report.extra_assignments_suggested || []).map(e => `<li>${this.escapeHtml(e)}</li>`).join('')}
                        </ul>
                    </div>
                </div>

                <div style="margin-top: 16px; padding: 12px; background: #f9fafb; border-radius: 8px; display: flex; gap: 24px; font-size: 14px; color: #666;">
                    <span><strong>Progress:</strong> ${report.metrics?.progress || 0}%</span>
                    <span><strong>Avg Score:</strong> ${report.metrics?.average_score?.toFixed(1) || 0}%</span>
                    <span><strong>Assignments:</strong> ${report.metrics?.assignments_completed || 0}</span>
                    <span><strong>Materials:</strong> ${report.metrics?.materials_completed || 0}</span>
                </div>
            `;
        } catch (error) {
            console.error('Error generating report:', error);
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #ef4444;">
                    <i class="fas fa-exclamation-circle fa-2x" style="margin-bottom: 12px;"></i>
                    <p>Error generating AI report: ${error.message}</p>
                    <button class="btn-primary" onclick="teacherDashboard.generateAIReport()" style="margin-top: 12px;">
                        <i class="fas fa-redo"></i> Try Again
                    </button>
                </div>
            `;
        }
    }

    showAddWeekModal() {
        const title = prompt('Enter week title:');
        if (title) {
            this.createWeek(title);
        }
    }

    async createWeek(title) {
        if (!this.currentCourse) return;

        try {
            const response = await fetch(`/api/teacher/courses/${this.currentCourse.id}/weeks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ title, is_published: false })
            });

            if (!response.ok) throw new Error('Failed to create week');

            const result = await response.json();
            
            if (result.success) {
                alert('Week created successfully!');
                await this.openCourse(this.currentCourse.id);
            } else {
                throw new Error(result.error || 'Failed to create');
            }
        } catch (error) {
            console.error('Error creating week:', error);
            alert('Error creating week: ' + error.message);
        }
    }

    showAddMaterialModal(weekId) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'addMaterialModal';
        modal.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
        modal.innerHTML = `
            <div style="background: white; border-radius: 12px; width: 90%; max-width: 600px; max-height: 90vh; overflow-y: auto;">
                <div style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0;"><i class="fas fa-plus-circle"></i> Add Material</h3>
                    <button onclick="document.getElementById('addMaterialModal').remove()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div style="padding: 20px;">
                    <form id="addMaterialForm">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Material Title *</label>
                            <input type="text" id="materialTitle" required style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="e.g., Chapter 1 Notes" data-testid="input-material-title">
                        </div>
                        
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Description</label>
                            <textarea id="materialDescription" rows="2" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="Brief description..." data-testid="input-material-description"></textarea>
                        </div>
                        
                        <div style="margin-bottom: 16px; padding: 16px; background: #f3f4f6; border-radius: 8px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 500;"><i class="fas fa-upload"></i> Upload File</label>
                            <input type="file" id="materialFile" style="width: 100%;" accept=".doc,.docx,.txt,.pdf,.mp4,.mov,.webm,.mp3,.wav,.ogg,.png,.jpg,.jpeg,.gif,.ppt,.pptx,.xls,.xlsx" data-testid="input-material-file">
                            <p style="font-size: 12px; color: #666; margin-top: 8px;">Supported: Documents, PDFs, Videos, Audio, Images, Presentations (max 100MB)</p>
                        </div>
                        
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Or External URL</label>
                            <input type="url" id="materialUrl" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="https://example.com/resource" data-testid="input-material-url">
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Visibility Status</label>
                                <select id="materialVisibility" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" onchange="teacherDashboard.toggleScheduleField('material')" data-testid="select-material-visibility">
                                    <option value="draft">Draft (not visible to students)</option>
                                    <option value="approved">Approved (visible now)</option>
                                    <option value="scheduled">Scheduled (visible at date)</option>
                                </select>
                            </div>
                            <div id="materialScheduleContainer" style="display: none;">
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Available At</label>
                                <input type="datetime-local" id="materialAvailableAt" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-material-available-at">
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 12px; margin-top: 20px;">
                            <button type="button" onclick="document.getElementById('addMaterialModal').remove()" class="btn-secondary" style="flex: 1; padding: 12px;">Cancel</button>
                            <button type="submit" class="btn-primary" style="flex: 1; padding: 12px;" data-testid="button-submit-material">
                                <i class="fas fa-save"></i> Add Material
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        document.getElementById('addMaterialForm').onsubmit = async (e) => {
            e.preventDefault();
            await this.submitMaterial(weekId);
        };
    }
    
    toggleScheduleField(type) {
        const visibility = document.getElementById(`${type}Visibility`).value;
        const scheduleContainer = document.getElementById(`${type}ScheduleContainer`);
        if (scheduleContainer) {
            scheduleContainer.style.display = visibility === 'scheduled' ? 'block' : 'none';
        }
    }

    async submitMaterial(weekId) {
        const title = document.getElementById('materialTitle').value;
        const description = document.getElementById('materialDescription').value;
        const file = document.getElementById('materialFile').files[0];
        const externalUrl = document.getElementById('materialUrl').value;
        const visibility = document.getElementById('materialVisibility').value;
        const availableAt = document.getElementById('materialAvailableAt').value;
        
        if (!title) {
            alert('Please enter a title');
            return;
        }
        
        try {
            let result;
            
            if (file) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('title', title);
                formData.append('description', description);
                formData.append('visibility_state', visibility);
                if (availableAt) formData.append('available_at', availableAt);
                
                const response = await fetch(`/api/teacher/weeks/${weekId}/materials/upload`, {
                    method: 'POST',
                    credentials: 'include',
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Upload failed');
                }
                result = await response.json();
            } else {
                const response = await fetch(`/api/teacher/weeks/${weekId}/materials`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        title,
                        description,
                        external_url: externalUrl,
                        material_type: 'link',
                        visibility_state: visibility,
                        available_at: availableAt || null
                    })
                });
                
                if (!response.ok) throw new Error('Failed to add material');
                result = await response.json();
            }
            
            if (result.success) {
                document.getElementById('addMaterialModal').remove();
                alert('Material added successfully!');
                await this.openCourse(this.currentCourse.id);
            } else {
                throw new Error(result.error || 'Failed to add');
            }
        } catch (error) {
            console.error('Error adding material:', error);
            alert('Error adding material: ' + error.message);
        }
    }

    showAddAssignmentModal(weekId) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'addAssignmentModal';
        modal.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
        modal.innerHTML = `
            <div style="background: white; border-radius: 12px; width: 90%; max-width: 600px; max-height: 90vh; overflow-y: auto;">
                <div style="background: linear-gradient(135deg, #16a34a 0%, #22c55e 100%); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0;"><i class="fas fa-tasks"></i> Add Assignment</h3>
                    <button onclick="document.getElementById('addAssignmentModal').remove()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div style="padding: 20px;">
                    <form id="addAssignmentForm">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Assignment Title *</label>
                            <input type="text" id="assignmentTitle" required style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="e.g., Week 1 Practice" data-testid="input-assignment-title">
                        </div>
                        
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Description</label>
                            <textarea id="assignmentDescription" rows="2" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="Brief description..." data-testid="input-assignment-description"></textarea>
                        </div>
                        
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Instructions</label>
                            <textarea id="assignmentInstructions" rows="3" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="Detailed instructions for students..." data-testid="input-assignment-instructions"></textarea>
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Max Points</label>
                                <input type="number" id="assignmentMaxPoints" value="100" min="0" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-assignment-points">
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Due Date</label>
                                <input type="datetime-local" id="assignmentDueDate" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-assignment-due-date">
                            </div>
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Visibility Status</label>
                                <select id="assignmentVisibility" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" onchange="teacherDashboard.toggleScheduleField('assignment')" data-testid="select-assignment-visibility">
                                    <option value="draft">Draft (not visible to students)</option>
                                    <option value="approved">Approved (visible now)</option>
                                    <option value="scheduled">Scheduled (visible at date)</option>
                                </select>
                            </div>
                            <div id="assignmentScheduleContainer" style="display: none;">
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Available At</label>
                                <input type="datetime-local" id="assignmentAvailableAt" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-assignment-available-at">
                            </div>
                        </div>
                        
                        <div style="margin-bottom: 16px;">
                            <label style="display: flex; align-items: center; gap: 8px;">
                                <input type="checkbox" id="assignmentAllowLate" data-testid="checkbox-allow-late">
                                <span>Allow late submissions</span>
                            </label>
                        </div>
                        
                        <div style="display: flex; gap: 12px; margin-top: 20px;">
                            <button type="button" onclick="document.getElementById('addAssignmentModal').remove()" class="btn-secondary" style="flex: 1; padding: 12px;">Cancel</button>
                            <button type="submit" class="btn-primary" style="flex: 1; padding: 12px;" data-testid="button-submit-assignment">
                                <i class="fas fa-save"></i> Add Assignment
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        document.getElementById('addAssignmentForm').onsubmit = async (e) => {
            e.preventDefault();
            await this.submitAssignment(weekId);
        };
    }

    async submitAssignment(weekId) {
        const title = document.getElementById('assignmentTitle').value;
        const description = document.getElementById('assignmentDescription').value;
        const instructions = document.getElementById('assignmentInstructions').value;
        const maxPoints = parseInt(document.getElementById('assignmentMaxPoints').value) || 100;
        const dueDate = document.getElementById('assignmentDueDate').value;
        const visibility = document.getElementById('assignmentVisibility').value;
        const availableAt = document.getElementById('assignmentAvailableAt').value;
        const allowLate = document.getElementById('assignmentAllowLate').checked;
        
        if (!title) {
            alert('Please enter a title');
            return;
        }
        
        try {
            const response = await fetch(`/api/teacher/weeks/${weekId}/assignments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    title,
                    description,
                    instructions,
                    max_points: maxPoints,
                    due_date: dueDate || null,
                    visibility_state: visibility,
                    available_at: availableAt || null,
                    allow_late: allowLate
                })
            });

            if (!response.ok) throw new Error('Failed to create assignment');

            const result = await response.json();
            
            if (result.success) {
                document.getElementById('addAssignmentModal').remove();
                alert('Assignment created successfully!');
                await this.openCourse(this.currentCourse.id);
            } else {
                throw new Error(result.error || 'Failed to create');
            }
        } catch (error) {
            console.error('Error creating assignment:', error);
            alert('Error creating assignment: ' + error.message);
        }
    }

    showCreateExamModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'createExamModal';
        modal.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
        modal.innerHTML = `
            <div style="background: white; border-radius: 12px; width: 90%; max-width: 600px; max-height: 90vh; overflow-y: auto;">
                <div style="background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0;"><i class="fas fa-plus-circle"></i> Create New Exam</h3>
                    <button onclick="document.getElementById('createExamModal').remove()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div style="padding: 20px;">
                    <form id="createExamForm">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Exam Title *</label>
                            <input type="text" id="newExamTitle" required style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="e.g., Midterm Exam, Quiz 1" data-testid="input-new-exam-title">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Description</label>
                            <textarea id="newExamDescription" rows="3" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="Describe the exam..." data-testid="input-new-exam-description"></textarea>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Exam Type</label>
                                <select id="newExamType" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="select-new-exam-type">
                                    <option value="quiz">Quiz</option>
                                    <option value="midterm">Midterm</option>
                                    <option value="final">Final Exam</option>
                                    <option value="practice">Practice</option>
                                </select>
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Pass Threshold (%)</label>
                                <input type="number" id="newExamPassThreshold" min="0" max="100" value="60" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-new-exam-threshold">
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Time Limit (minutes)</label>
                                <input type="number" id="newExamTimeLimit" min="0" placeholder="No limit" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-new-exam-time">
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Max Attempts</label>
                                <input type="number" id="newExamMaxAttempts" min="1" value="1" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-new-exam-attempts">
                            </div>
                        </div>
                        <div style="display: flex; gap: 16px; margin-bottom: 16px;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" id="newExamShuffle" data-testid="checkbox-new-exam-shuffle">
                                <span>Shuffle Questions</span>
                            </label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" id="newExamShowResults" checked data-testid="checkbox-new-exam-results">
                                <span>Show Results After</span>
                            </label>
                        </div>
                        <div style="display: flex; gap: 12px; justify-content: flex-end; padding-top: 16px; border-top: 1px solid #e5e7eb;">
                            <button type="button" onclick="document.getElementById('createExamModal').remove()" class="btn-secondary" style="padding: 10px 20px;">Cancel</button>
                            <button type="submit" class="btn-primary" style="padding: 10px 20px;" data-testid="button-create-exam-submit">
                                <i class="fas fa-plus"></i> Create Exam
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        document.getElementById('createExamForm').onsubmit = (e) => {
            e.preventDefault();
            this.createExam({
                title: document.getElementById('newExamTitle').value,
                description: document.getElementById('newExamDescription').value,
                exam_type: document.getElementById('newExamType').value,
                passing_threshold: parseInt(document.getElementById('newExamPassThreshold').value) || 60,
                time_limit_minutes: document.getElementById('newExamTimeLimit').value ? parseInt(document.getElementById('newExamTimeLimit').value) : null,
                max_attempts: parseInt(document.getElementById('newExamMaxAttempts').value) || 1,
                shuffle_questions: document.getElementById('newExamShuffle').checked,
                show_results: document.getElementById('newExamShowResults').checked,
                is_published: false
            });
            modal.remove();
        };
    }

    async createExam(data) {
        if (!this.currentCourse) return;

        try {
            const response = await fetch(`/api/teacher/courses/${this.currentCourse.id}/exams`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data)
            });

            if (!response.ok) throw new Error('Failed to create exam');

            const result = await response.json();
            
            if (result.success) {
                alert('Exam created successfully!');
                await this.openCourse(this.currentCourse.id);
            } else {
                throw new Error(result.error || 'Failed to create');
            }
        } catch (error) {
            console.error('Error creating exam:', error);
            alert('Error creating exam: ' + error.message);
        }
    }

    showGradeModal(submissionId, studentName, assignmentTitle, maxPoints, currentScore, currentFeedback) {
        const score = prompt(`Grade for ${studentName} - ${assignmentTitle}\nMax: ${maxPoints} points\n\nEnter score:`, currentScore || '');
        if (score === null) return;
        
        const feedback = prompt('Enter feedback (optional):', currentFeedback || '');
        
        this.gradeSubmission(submissionId, parseFloat(score), feedback);
    }

    async gradeSubmission(submissionId, score, feedback) {
        try {
            const response = await fetch(`/api/teacher/submissions/${submissionId}/grade`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ score, feedback })
            });

            if (!response.ok) throw new Error('Failed to grade submission');

            const result = await response.json();
            
            if (result.success) {
                alert('Submission graded successfully!');
                await this.loadSubmissions();
            } else {
                throw new Error(result.error || 'Failed to grade');
            }
        } catch (error) {
            console.error('Error grading submission:', error);
            alert('Error grading submission: ' + error.message);
        }
    }

    async manageExamQuestions(examId) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'examQuestionsModal';
        modal.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
        modal.innerHTML = `
            <div style="background: white; border-radius: 12px; width: 95%; max-width: 900px; max-height: 90vh; overflow-y: auto;">
                <div style="background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 10;">
                    <h3 style="margin: 0;"><i class="fas fa-list"></i> Manage Exam Questions</h3>
                    <button onclick="document.getElementById('examQuestionsModal').remove()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div style="padding: 20px;">
                    <div id="examQuestionsLoading" style="text-align: center; padding: 40px;">
                        <i class="fas fa-spinner fa-spin fa-2x"></i>
                        <p>Loading questions...</p>
                    </div>
                    <div id="examQuestionsContent" style="display: none;"></div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        await this.loadExamQuestions(examId);
    }
    
    async loadExamQuestions(examId) {
        try {
            const response = await fetch(`/api/teacher/exams/${examId}/questions`, {
                credentials: 'include'
            });
            
            if (!response.ok) throw new Error('Failed to load questions');
            
            const data = await response.json();
            
            document.getElementById('examQuestionsLoading').style.display = 'none';
            document.getElementById('examQuestionsContent').style.display = 'block';
            
            const questions = data.questions || [];
            const examTitle = data.exam?.title || 'Exam';
            
            document.getElementById('examQuestionsContent').innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h4 style="margin: 0;">${this.escapeHtml(examTitle)} - Questions (${questions.length})</h4>
                    <div style="display: flex; gap: 12px;">
                        <button onclick="teacherDashboard.showAIQuestionGenerator('${examId}')" class="btn-secondary" style="padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none;" data-testid="button-ai-generate">
                            <i class="fas fa-robot"></i> Generate with Artificial Intelligence
                        </button>
                        <button onclick="teacherDashboard.showMoodleImportForm('${examId}')" class="btn-secondary" style="padding: 10px 20px; background: #ea580c; color: white; border: none;" data-testid="button-import-moodle">
                            <i class="fas fa-file-import"></i> Import Moodle XML
                        </button>
                        <button onclick="teacherDashboard.translateExamQuestions('${examId}')" class="btn-secondary" style="padding: 10px 20px; background: #0d9488; color: white; border: none;" data-testid="button-translate-questions">
                            <i class="fas fa-language"></i> Auto-translate AR/EN
                        </button>
                        <button onclick="teacherDashboard.showAddQuestionForm('${examId}')" class="btn-primary" style="padding: 10px 20px;" data-testid="button-add-question">
                            <i class="fas fa-plus"></i> Add Question
                        </button>
                    </div>
                </div>
                
                <div id="aiQuestionGeneratorContainer"></div>
                <div id="addQuestionFormContainer"></div>
                
                <div id="questionsListContainer">
                    ${questions.length === 0 ? `
                        <div style="text-align: center; padding: 40px; color: #666; background: #f9fafb; border-radius: 12px;">
                            <i class="fas fa-question-circle" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                            <p>No questions added yet. Click "Add Question" to create your first question.</p>
                        </div>
                    ` : questions.map((q, idx) => `
                        <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 12px;" data-testid="question-card-${q.id}">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div style="flex: 1;">
                                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                        <span style="background: #7c3aed; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">Q${idx + 1}</span>
                                        <span style="background: #e5e7eb; padding: 2px 8px; border-radius: 4px; font-size: 12px; text-transform: capitalize;">${q.question_type}</span>
                                        <span style="color: #666; font-size: 12px;">${q.points} points</span>
                                    </div>
                                    <p style="margin: 0; font-weight: 500;">${this.escapeHtml(q.question_text)}</p>
                                    ${(() => {
                                        const flatOpts = this.flattenOptions(q.options);
                                        if (!flatOpts.length) return '';
                                        const isCorrect = (i) => this.isCorrectAnswer(q.correct_answer, i);
                                        return `
                                        <div style="margin-top: 12px;">
                                            ${flatOpts.map((opt, i) => `
                                                <div style="display: flex; align-items: center; gap: 8px; padding: 6px 12px; background: ${isCorrect(i) ? '#dcfce7' : 'white'}; border: 1px solid ${isCorrect(i) ? '#16a34a' : '#e5e7eb'}; border-radius: 6px; margin-top: 4px;">
                                                    <i class="fas ${isCorrect(i) ? 'fa-check-circle' : 'fa-circle'}" style="color: ${isCorrect(i) ? '#16a34a' : '#d1d5db'};"></i>
                                                    <span>${this.escapeHtml(opt)}</span>
                                                </div>
                                            `).join('')}
                                        </div>`;
                                    })()}
                                </div>
                                <div style="display: flex; gap: 8px;">
                                    <button type="button" onclick="teacherDashboard.showEditExamQuestionForm('${examId}', '${q.id}', ${JSON.stringify(q).replace(/"/g, '&quot;')})" class="btn-secondary" style="padding: 6px 10px; color: #0ea5e9;" data-testid="button-edit-question-${q.id}">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button type="button" onclick="teacherDashboard.deleteQuestion('${examId}', '${q.id}')" class="btn-secondary" style="padding: 6px 10px; color: #ef4444;" data-testid="button-delete-question-${q.id}">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            console.error('Error loading questions:', error);
            document.getElementById('examQuestionsLoading').innerHTML = `
                <div style="color: #ef4444;">
                    <i class="fas fa-exclamation-circle"></i> Error loading questions: ${error.message}
                </div>
            `;
        }
    }
    
    showAddQuestionForm(examId) {
        const container = document.getElementById('addQuestionFormContainer');
        container.innerHTML = `
            <div style="background: #f0f9ff; border: 2px solid #3b82f6; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h5 style="margin: 0 0 16px 0; color: #1e40af;"><i class="fas fa-plus-circle"></i> Add New Question</h5>
                <form id="addQuestionForm">
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 6px; font-weight: 500;">Question Text *</label>
                        <textarea id="newQuestionText" required rows="2" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="Enter your question..." data-testid="input-question-text"></textarea>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Question Type</label>
                            <select id="newQuestionType" onchange="teacherDashboard.toggleOptionsField()" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="select-question-type">
                                <option value="multiple_choice">Multiple Choice</option>
                                <option value="true_false">True/False</option>
                                <option value="short_answer">Short Answer</option>
                                <option value="essay">Essay</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Points</label>
                            <input type="number" id="newQuestionPoints" min="1" value="1" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-question-points">
                        </div>
                    </div>
                    <div id="optionsContainer" style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 6px; font-weight: 500;">Options (one per line)</label>
                        <textarea id="newQuestionOptions" rows="4" oninput="teacherDashboard.updateExamCorrectAnswerDropdown()" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="Option A&#10;Option B&#10;Option C&#10;Option D" data-testid="input-question-options"></textarea>
                    </div>
                    <div id="examCorrectAnswerContainer" style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 6px; font-weight: 500;">Correct Answer</label>
                        <select id="newQuestionAnswer" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-question-answer">
                            <option value="">-- Select correct answer --</option>
                            <option value="True">True</option>
                            <option value="False">False</option>
                        </select>
                    </div>
                    <div id="newRubricContainer" style="display: none; margin-bottom: 16px; background: #fff7ed; border: 1px dashed #fdba74; border-radius: 8px; padding: 12px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                            <label style="font-weight: 500; margin: 0;"><i class="fas fa-list-check"></i> Rubric Criteria</label>
                            <button type="button" class="btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="teacherDashboard.addRubricRow('newRubricRows')" data-testid="button-rubric-add">
                                <i class="fas fa-plus"></i> Add Criterion
                            </button>
                        </div>
                        <p style="margin: 0 0 8px 0; font-size: 12px; color: #92400e;">Define how this answer should be scored. Leave empty to use the default rubric (Accuracy / Reasoning / Clarity).</p>
                        <div id="newRubricRows"></div>
                    </div>
                    <div style="display: flex; gap: 12px; justify-content: flex-end;">
                        <button type="button" onclick="document.getElementById('addQuestionFormContainer').innerHTML=''" class="btn-secondary" style="padding: 10px 20px;">Cancel</button>
                        <button type="submit" class="btn-primary" style="padding: 10px 20px;" data-testid="button-save-question">
                            <i class="fas fa-save"></i> Save Question
                        </button>
                    </div>
                </form>
            </div>
        `;
        
        document.getElementById('addQuestionForm').onsubmit = async (e) => {
            e.preventDefault();
            await this.addQuestion(examId);
        };
    }
    
    toggleOptionsField() {
        const type = document.getElementById('newQuestionType').value;
        const container = document.getElementById('optionsContainer');
        const answerContainer = document.getElementById('examCorrectAnswerContainer');
        const select = document.getElementById('newQuestionAnswer');
        const rubricContainer = document.getElementById('newRubricContainer');

        const isFreeText = (type === 'short_answer' || type === 'essay');
        if (isFreeText) {
            container.style.display = 'none';
            answerContainer.style.display = 'none';
        } else if (type === 'true_false') {
            container.style.display = 'none';
            answerContainer.style.display = 'block';
            // Store as numeric index (0=True, 1=False) so the question-list,
            // edit form, and grader all line up with the same convention.
            select.innerHTML = '<option value="">-- Select correct answer --</option><option value="0">True</option><option value="1">False</option>';
        } else {
            container.style.display = 'block';
            answerContainer.style.display = 'block';
            this.updateExamCorrectAnswerDropdown();
        }
        if (rubricContainer) {
            rubricContainer.style.display = isFreeText ? 'block' : 'none';
        }
    }

    // Rubric editor helpers (shared by add and edit forms).
    rubricRowHtml(criterion) {
        const c = criterion || {};
        const esc = (v) => this.escapeHtml(v == null ? '' : String(v));
        return `
            <div class="rubric-row" style="display: grid; grid-template-columns: 1.2fr 1.2fr 0.6fr 1.5fr auto; gap: 8px; align-items: start; margin-bottom: 8px;">
                <input type="text" class="rubric-name" placeholder="Criterion (e.g. Accuracy)" value="${esc(c.name)}" style="padding: 8px; border: 1px solid #d1d5db; border-radius: 6px;" data-testid="input-rubric-name">
                <input type="text" class="rubric-name-ar" placeholder="بالعربية" value="${esc(c.name_ar)}" dir="rtl" style="padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; text-align:right;" data-testid="input-rubric-name-ar">
                <input type="number" class="rubric-max" min="1" step="1" placeholder="Max" value="${esc(c.max != null ? c.max : 5)}" style="padding: 8px; border: 1px solid #d1d5db; border-radius: 6px;" data-testid="input-rubric-max">
                <input type="text" class="rubric-desc" placeholder="What does a full-credit answer look like?" value="${esc(c.description)}" style="padding: 8px; border: 1px solid #d1d5db; border-radius: 6px;" data-testid="input-rubric-desc">
                <button type="button" onclick="this.closest('.rubric-row').remove()" class="btn-secondary" style="padding: 6px 10px;" title="Remove" data-testid="button-rubric-remove">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
    }

    addRubricRow(rowsContainerId, criterion) {
        const rows = document.getElementById(rowsContainerId);
        if (!rows) return;
        const tmp = document.createElement('div');
        tmp.innerHTML = this.rubricRowHtml(criterion);
        rows.appendChild(tmp.firstElementChild);
    }

    populateRubricRows(rowsContainerId, rubric) {
        const rows = document.getElementById(rowsContainerId);
        if (!rows) return;
        rows.innerHTML = '';
        (rubric || []).forEach(c => this.addRubricRow(rowsContainerId, c));
    }

    collectRubric(rowsContainerId) {
        const rows = document.getElementById(rowsContainerId);
        if (!rows) return null;
        const out = [];
        rows.querySelectorAll('.rubric-row').forEach(row => {
            const name = (row.querySelector('.rubric-name')?.value || '').trim();
            if (!name) return;
            const maxRaw = row.querySelector('.rubric-max')?.value;
            const max = parseFloat(maxRaw);
            out.push({
                name,
                name_ar: (row.querySelector('.rubric-name-ar')?.value || '').trim(),
                max: isNaN(max) || max <= 0 ? 5 : max,
                description: (row.querySelector('.rubric-desc')?.value || '').trim(),
            });
        });
        return out.length ? out : null;
    }
    
    updateExamCorrectAnswerDropdown() {
        const optionsText = document.getElementById('newQuestionOptions')?.value || '';
        const options = optionsText.split('\n').filter(o => o.trim());
        const select = document.getElementById('newQuestionAnswer');
        if (!select) return;
        
        if (options.length === 0) {
            select.innerHTML = '<option value="">-- Enter options first --</option>';
        } else {
            // Use the option index as the value (matches the edit form, the
            // survey form, and the grader). Storing the option *text* here
            // was the bug behind "selecting the correct answer is not fixed
            // and the question is not graded".
            select.innerHTML = '<option value="">-- Select correct answer --</option>' +
                options.map((opt, idx) => `<option value="${idx}">${this.escapeHtml(opt.trim())}</option>`).join('');
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    /**
     * Flatten an options value into an array of plain-string options.
     * Handles: real arrays, a single string with newlines, an array
     * containing one big newline-joined string, dict items, etc.
     */
    flattenOptions(opts) {
        if (opts == null) return [];
        const splitOne = (v) => {
            if (v == null) return [];
            if (typeof v === 'object' && !Array.isArray(v)) {
                if ('text' in v) return [String(v.text).trim()];
                if ('value' in v) return [String(v.value).trim()];
                const vals = Object.values(v);
                return vals.length === 1 ? [String(vals[0]).trim()] : [JSON.stringify(v)];
            }
            const s = String(v);
            return s.split(/\r?\n|\\n/).map(p => p.trim()).filter(Boolean);
        };
        if (typeof opts === 'string') return splitOne(opts);
        if (Array.isArray(opts)) {
            const out = [];
            opts.forEach(o => out.push(...splitOne(o)));
            return out;
        }
        return splitOne(opts);
    }

    /**
     * Compare a stored correct_answer (which may be a number, string,
     * or array of either) against a numeric option index.
     */
    isCorrectAnswer(correct, idx) {
        if (correct == null || correct === '') return false;
        const matches = (c) => c === idx || String(c) === String(idx);
        if (Array.isArray(correct)) return correct.some(matches);
        return matches(correct);
    }
    
    async addQuestion(examId) {
        const questionType = document.getElementById('newQuestionType').value;
        let options = [];
        const rawAnswer = document.getElementById('newQuestionAnswer').value;
        const isFreeText = (questionType === 'short_answer' || questionType === 'essay');

        if (questionType === 'multiple_choice') {
            options = document.getElementById('newQuestionOptions').value.split('\n').filter(o => o.trim());
        } else if (questionType === 'true_false') {
            options = ['True', 'False'];
        }

        if (!isFreeText && (rawAnswer === '' || rawAnswer == null)) {
            alert('Please select the correct answer');
            return;
        }

        // The dropdown now uses option indices ("0", "1", …) for both
        // multiple_choice and true_false, matching the edit form, the
        // survey form, and the grader convention.
        let correctAnswer = null;
        if (!isFreeText) {
            const parsed = parseInt(rawAnswer, 10);
            correctAnswer = isNaN(parsed) ? rawAnswer : parsed;
        }

        const data = {
            question_text: document.getElementById('newQuestionText').value,
            question_type: questionType,
            points: parseInt(document.getElementById('newQuestionPoints').value) || 1,
            options: options,
            correct_answer: correctAnswer
        };
        if (isFreeText) {
            data.rubric = this.collectRubric('newRubricRows');
        }
        
        try {
            const response = await fetch(`/api/teacher/exams/${examId}/questions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data)
            });
            
            if (!response.ok) throw new Error('Failed to add question');
            
            const result = await response.json();
            if (result.success) {
                await this.loadExamQuestions(examId);
            } else {
                throw new Error(result.error || 'Failed to add question');
            }
        } catch (error) {
            console.error('Error adding question:', error);
            alert('Error adding question: ' + error.message);
        }
    }
    
    async deleteQuestion(examId, questionId) {
        if (!confirm('Are you sure you want to delete this question?')) return;
        
        try {
            const response = await fetch(`/api/teacher/exams/${examId}/questions/${questionId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            if (!response.ok) throw new Error('Failed to delete question');
            
            await this.loadExamQuestions(examId);
        } catch (error) {
            console.error('Error deleting question:', error);
            alert('Error deleting question: ' + error.message);
        }
    }
    
    showEditExamQuestionForm(examId, questionId, question) {
        const container = document.getElementById('addQuestionFormContainer');
        const isTrueFalse = question.question_type === 'true_false';
        const options = this.flattenOptions(question.options);
        const optionsAr = this.flattenOptions(question.options_ar);
        
        container.innerHTML = `
            <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h5 style="margin: 0 0 16px 0; color: #b45309;"><i class="fas fa-edit"></i> Edit Question</h5>
                <form id="editExamQuestionForm">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Question Text (English) *</label>
                            <textarea id="editExamQuestionText" required rows="2" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;">${this.escapeHtml(question.question_text || '')}</textarea>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Question Text (Arabic) نص السؤال</label>
                            <textarea id="editExamQuestionTextAr" rows="2" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; direction: rtl; text-align: right;">${this.escapeHtml(question.question_text_ar || '')}</textarea>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Question Type</label>
                            <select id="editExamQuestionType" onchange="teacherDashboard.toggleEditExamOptionsField()" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;">
                                <option value="multiple_choice" ${question.question_type === 'multiple_choice' ? 'selected' : ''}>Multiple Choice</option>
                                <option value="true_false" ${question.question_type === 'true_false' ? 'selected' : ''}>True/False</option>
                                <option value="short_answer" ${question.question_type === 'short_answer' ? 'selected' : ''}>Short Answer</option>
                                <option value="essay" ${question.question_type === 'essay' ? 'selected' : ''}>Essay</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Points</label>
                            <input type="number" id="editExamQuestionPoints" min="1" value="${question.points || 1}" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;">
                        </div>
                    </div>
                    <div id="editExamOptionsContainer" style="display: ${isTrueFalse ? 'none' : 'grid'}; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Options (English, one per line)</label>
                            <textarea id="editExamQuestionOptions" rows="4" oninput="teacherDashboard.updateEditExamCorrectAnswerDropdown()" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;">${options.join('\n')}</textarea>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Options (Arabic) الخيارات</label>
                            <textarea id="editExamQuestionOptionsAr" rows="4" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; direction: rtl; text-align: right;">${optionsAr.join('\n')}</textarea>
                        </div>
                    </div>
                    <div id="editExamCorrectAnswerWrap" style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 6px; font-weight: 500;">Correct Answer</label>
                        <select id="editExamQuestionCorrectAnswer" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;">
                            ${isTrueFalse ? `
                                <option value="">-- Select correct answer --</option>
                                <option value="0" ${question.correct_answer === 0 || question.correct_answer === '0' || question.correct_answer === 'True' ? 'selected' : ''}>True</option>
                                <option value="1" ${question.correct_answer === 1 || question.correct_answer === '1' || question.correct_answer === 'False' ? 'selected' : ''}>False</option>
                            ` : `
                                <option value="">-- Select correct answer --</option>
                                ${options.map((opt, i) => `<option value="${i}" ${question.correct_answer === i || question.correct_answer === String(i) ? 'selected' : ''}>${this.escapeHtml(opt)}</option>`).join('')}
                            `}
                        </select>
                    </div>
                    <div id="editRubricContainer" style="display: none; margin-bottom: 16px; background: #fff7ed; border: 1px dashed #fdba74; border-radius: 8px; padding: 12px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                            <label style="font-weight: 500; margin: 0;"><i class="fas fa-list-check"></i> Rubric Criteria</label>
                            <button type="button" class="btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="teacherDashboard.addRubricRow('editRubricRows')" data-testid="button-rubric-add-edit">
                                <i class="fas fa-plus"></i> Add Criterion
                            </button>
                        </div>
                        <p style="margin: 0 0 8px 0; font-size: 12px; color: #92400e;">Define how this answer should be scored. Leave empty to use the default rubric (Accuracy / Reasoning / Clarity).</p>
                        <div id="editRubricRows"></div>
                    </div>
                    <div style="display: flex; gap: 12px; justify-content: flex-end;">
                        <button type="button" onclick="document.getElementById('addQuestionFormContainer').innerHTML=''" class="btn-secondary" style="padding: 10px 20px;">Cancel</button>
                        <button type="submit" class="btn-primary" style="padding: 10px 20px; background: #f59e0b;" data-testid="button-update-question">
                            <i class="fas fa-save"></i> Update Question
                        </button>
                    </div>
                </form>
            </div>
        `;
        
        document.getElementById('editExamQuestionForm').onsubmit = async (e) => {
            e.preventDefault();
            await this.updateExamQuestion(examId, questionId);
        };

        // Pre-populate rubric rows and reflect initial visibility based on type.
        this.populateRubricRows('editRubricRows', question.rubric || []);
        this.toggleEditExamOptionsField();

        // Bring the edit form into the user's view. The edit form is rendered
        // at the top of the questions modal, above the question list, so when
        // a teacher clicks edit on a question further down the list it can
        // appear off-screen and feel like the page jumped to the top.
        try {
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });
            const focusEl = document.getElementById('editExamQuestionText');
            if (focusEl) setTimeout(() => focusEl.focus({ preventScroll: true }), 250);
        } catch (_) { /* no-op */ }
    }

    toggleEditExamOptionsField() {
        const type = document.getElementById('editExamQuestionType').value;
        const container = document.getElementById('editExamOptionsContainer');
        const select = document.getElementById('editExamQuestionCorrectAnswer');
        const answerWrap = document.getElementById('editExamCorrectAnswerWrap');
        const rubricContainer = document.getElementById('editRubricContainer');

        const isFreeText = (type === 'short_answer' || type === 'essay');
        if (isFreeText) {
            if (container) container.style.display = 'none';
            if (answerWrap) answerWrap.style.display = 'none';
        } else if (type === 'true_false') {
            container.style.display = 'none';
            if (answerWrap) answerWrap.style.display = 'block';
            select.innerHTML = '<option value="">-- Select correct answer --</option><option value="0">True</option><option value="1">False</option>';
        } else {
            container.style.display = 'grid';
            if (answerWrap) answerWrap.style.display = 'block';
            this.updateEditExamCorrectAnswerDropdown();
        }
        if (rubricContainer) {
            rubricContainer.style.display = isFreeText ? 'block' : 'none';
        }
    }
    
    updateEditExamCorrectAnswerDropdown() {
        const optionsText = document.getElementById('editExamQuestionOptions')?.value || '';
        const options = optionsText.split('\n').filter(o => o.trim());
        const select = document.getElementById('editExamQuestionCorrectAnswer');
        if (!select) return;
        
        const currentValue = select.value;
        if (options.length === 0) {
            select.innerHTML = '<option value="">-- Enter options first --</option>';
        } else {
            select.innerHTML = '<option value="">-- Select correct answer --</option>' + 
                options.map((opt, i) => `<option value="${i}" ${currentValue === String(i) ? 'selected' : ''}>${this.escapeHtml(opt.trim())}</option>`).join('');
        }
    }
    
    async updateExamQuestion(examId, questionId) {
        const questionType = document.getElementById('editExamQuestionType').value;
        let options = [];
        let optionsAr = [];
        
        const isFreeText = (questionType === 'short_answer' || questionType === 'essay');
        if (questionType === 'multiple_choice') {
            options = document.getElementById('editExamQuestionOptions').value.split('\n').filter(o => o.trim());
            optionsAr = document.getElementById('editExamQuestionOptionsAr')?.value.split('\n').filter(o => o.trim()) || [];
        } else if (questionType === 'true_false') {
            options = ['True', 'False'];
            optionsAr = ['صحيح', 'خطأ'];
        }

        const correctAnswerSelect = document.getElementById('editExamQuestionCorrectAnswer');
        const correctAnswerIndex = (!isFreeText && correctAnswerSelect && correctAnswerSelect.value !== '')
            ? parseInt(correctAnswerSelect.value)
            : null;

        const data = {
            question_text: document.getElementById('editExamQuestionText').value,
            question_text_ar: document.getElementById('editExamQuestionTextAr')?.value || '',
            question_type: questionType,
            options: options,
            options_ar: optionsAr,
            correct_answer: correctAnswerIndex,
            points: parseInt(document.getElementById('editExamQuestionPoints').value) || 1,
            rubric: isFreeText ? this.collectRubric('editRubricRows') : null,
        };
        
        try {
            const response = await fetch(`/api/teacher/exams/${examId}/questions/${questionId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to update question');
            }
            
            document.getElementById('addQuestionFormContainer').innerHTML = '';
            await this.loadExamQuestions(examId);
        } catch (error) {
            console.error('Error updating question:', error);
            alert('Error updating question: ' + error.message);
        }
    }
    
    showAIQuestionGenerator(examId) {
        const container = document.getElementById('aiQuestionGeneratorContainer');
        container.innerHTML = `
            <div style="background: linear-gradient(135deg, #f0f4ff 0%, #f5f0ff 100%); border: 2px solid #667eea; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h5 style="margin: 0 0 16px 0; color: #4c1d95;"><i class="fas fa-robot"></i> AI Question Generator</h5>
                <p style="color: #666; margin-bottom: 16px; font-size: 14px;">Upload a document and let AI generate bilingual (English/Arabic) questions automatically.</p>
                
                <form id="aiGenerateForm" enctype="multipart/form-data">
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 6px; font-weight: 500;">Upload Document *</label>
                        <input type="file" id="aiDocumentFile" accept=".pdf,.doc,.docx,.txt,.ppt,.pptx" required 
                               style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; background: white;" 
                               data-testid="input-ai-document">
                        <small style="color: #666;">Supported: PDF, DOC, DOCX, TXT, PPT, PPTX</small>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">True/False Questions</label>
                            <input type="number" id="aiTrueFalseCount" min="0" max="50" value="5" 
                                   style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" 
                                   data-testid="input-true-false-count">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">MCQ Questions</label>
                            <input type="number" id="aiMCQCount" min="0" max="50" value="5" 
                                   style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" 
                                   data-testid="input-mcq-count">
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Difficulty</label>
                            <select id="aiDifficulty" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="select-difficulty">
                                <option value="easy">Easy</option>
                                <option value="medium" selected>Medium</option>
                                <option value="hard">Hard</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Topic (Optional)</label>
                            <input type="text" id="aiTopic" placeholder="e.g., Machine Learning" 
                                   style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" 
                                   data-testid="input-topic">
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 12px; justify-content: flex-end;">
                        <button type="button" onclick="document.getElementById('aiQuestionGeneratorContainer').innerHTML=''" class="btn-secondary" style="padding: 10px 20px;">Cancel</button>
                        <button type="submit" class="btn-primary" style="padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none;" data-testid="button-generate-ai-questions">
                            <i class="fas fa-magic"></i> Generate Questions
                        </button>
                    </div>
                </form>
                
                <div id="aiGenerationProgress" style="display: none; margin-top: 16px; text-align: center; padding: 20px;">
                    <i class="fas fa-spinner fa-spin fa-2x" style="color: #667eea;"></i>
                    <p style="margin-top: 12px; color: #666;">AI is generating bilingual questions... This may take a moment.</p>
                </div>
                
                <div id="aiGenerationResult" style="display: none; margin-top: 16px;"></div>
            </div>
        `;
        
        document.getElementById('aiGenerateForm').onsubmit = async (e) => {
            e.preventDefault();
            await this.generateAIQuestions(examId);
        };
    }
    
    async generateAIQuestions(examId) {
        const fileInput = document.getElementById('aiDocumentFile');
        const trueFalseCount = document.getElementById('aiTrueFalseCount').value;
        const mcqCount = document.getElementById('aiMCQCount').value;
        const difficulty = document.getElementById('aiDifficulty').value;
        const topic = document.getElementById('aiTopic').value;
        
        if (!fileInput.files.length) {
            alert('Please select a document file');
            return;
        }
        
        if (!this.currentCourse?.id) {
            alert('Course ID not found. Please refresh and try again.');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('num_true_false', trueFalseCount);
        formData.append('num_mcq', mcqCount);
        formData.append('difficulty', difficulty);
        formData.append('topic', topic);
        formData.append('target_type', 'exam');
        formData.append('target_id', examId);
        
        document.getElementById('aiGenerateForm').style.display = 'none';
        document.getElementById('aiGenerationProgress').style.display = 'block';
        
        const courseId = this.currentCourse.id;
        
        try {
            const response = await fetch(`/api/teacher/courses/${courseId}/generate-questions`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });
            
            const text = await response.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch (parseError) {
                console.error('Response was not JSON:', text.substring(0, 200));
                // The server very likely DID save the questions (commit happens
                // before the response is built), but the response itself was an
                // HTML error page (proxy timeout, worker recycle, session
                // redirect, etc.). Tell the teacher to refresh and check
                // instead of claiming the generation failed.
                document.getElementById('aiGenerationProgress').style.display = 'none';
                document.getElementById('aiGenerateForm').style.display = 'block';
                const warnDiv = document.getElementById('aiGenerationResult');
                warnDiv.style.display = 'block';
                warnDiv.innerHTML = `
                    <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px;">
                        <h5 style="color: #b45309; margin: 0 0 8px 0;"><i class="fas fa-info-circle"></i> Generation may have completed</h5>
                        <p style="margin: 0; color: #92400e;">The server did not return a clear response (possibly a timeout). The questions may already be saved.</p>
                        <button type="button" onclick="teacherDashboard.loadExamQuestions('${examId}'); document.getElementById('aiQuestionGeneratorContainer').innerHTML='';" class="btn-primary" style="margin-top: 12px; padding: 8px 16px;">
                            <i class="fas fa-sync"></i> Refresh Questions
                        </button>
                    </div>
                `;
                return;
            }

            document.getElementById('aiGenerationProgress').style.display = 'none';

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to generate questions');
            }
            
            const resultDiv = document.getElementById('aiGenerationResult');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <div style="background: #dcfce7; border: 1px solid #16a34a; border-radius: 8px; padding: 16px;">
                    <h5 style="color: #16a34a; margin: 0 0 8px 0;"><i class="fas fa-check-circle"></i> Success!</h5>
                    <p style="margin: 0; color: #166534;">${data.message}</p>
                    <p style="margin: 8px 0 0 0; font-size: 14px; color: #666;">Questions have been added to the exam in both English and Arabic.</p>
                    <button onclick="teacherDashboard.loadExamQuestions('${examId}'); document.getElementById('aiQuestionGeneratorContainer').innerHTML='';" class="btn-primary" style="margin-top: 12px; padding: 8px 16px;">
                        <i class="fas fa-sync"></i> Refresh Questions
                    </button>
                </div>
            `;
            
        } catch (error) {
            console.error('Error generating questions:', error);
            document.getElementById('aiGenerationProgress').style.display = 'none';
            document.getElementById('aiGenerateForm').style.display = 'block';
            
            const resultDiv = document.getElementById('aiGenerationResult');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <div style="background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; padding: 16px;">
                    <h5 style="color: #ef4444; margin: 0 0 8px 0;"><i class="fas fa-exclamation-circle"></i> Error</h5>
                    <p style="margin: 0; color: #dc2626;">${error.message}</p>
                </div>
            `;
        }
    }

    showMoodleImportForm(examId) {
        const container = document.getElementById('aiQuestionGeneratorContainer');
        container.innerHTML = `
            <div style="background: #fff7ed; border: 1px solid #fdba74; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 12px 0; color: #ea580c;"><i class="fas fa-file-import"></i> Import Questions from Moodle XML</h4>
                <p style="margin: 0 0 12px 0; color: #666; font-size: 14px;">Upload a Moodle XML export file. Supported question types: Multiple Choice and True/False. Other types are skipped and reported.</p>
                <form id="moodleImportForm">
                    <input type="file" id="moodleXmlFile" accept=".xml" required
                           style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; background: white; margin-bottom: 16px;"
                           data-testid="input-moodle-xml">
                    <div style="display: flex; gap: 12px; justify-content: flex-end;">
                        <button type="button" onclick="document.getElementById('aiQuestionGeneratorContainer').innerHTML=''" class="btn-secondary" style="padding: 10px 20px;">Cancel</button>
                        <button type="submit" class="btn-primary" style="padding: 10px 20px; background: #ea580c; border: none;" data-testid="button-submit-moodle-import">
                            <i class="fas fa-file-import"></i> Import
                        </button>
                    </div>
                </form>
                <div id="moodleImportResult" style="display: none; margin-top: 16px;"></div>
            </div>
        `;
        document.getElementById('moodleImportForm').onsubmit = async (e) => {
            e.preventDefault();
            await this.importMoodleXML(examId);
        };
        try { container.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (_) {}
    }

    async importMoodleXML(examId) {
        const fileInput = document.getElementById('moodleXmlFile');
        if (!fileInput.files.length) { alert('Please select a Moodle XML file'); return; }
        const resultDiv = document.getElementById('moodleImportResult');
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importing...';
        try {
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            const response = await fetch(`/api/teacher/exams/${examId}/questions/import-moodle-xml`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });
            const ct = response.headers.get('content-type') || '';
            if (!ct.includes('application/json')) {
                // Server returned HTML — session expired or redirect to login
                throw new Error('Session expired. Please refresh the page and log in again, then try importing.');
            }
            const data = await response.json();
            if (!response.ok || !data.success) throw new Error(data.error || 'Import failed');
            const skippedHtml = (data.skipped && data.skipped.length)
                ? `<p style="margin: 8px 0 0 0; color: #b45309; font-size: 13px;"><strong>Skipped ${data.skipped.length}:</strong> ${this.escapeHtml(data.skipped.slice(0, 5).join('; '))}${data.skipped.length > 5 ? '…' : ''}</p>`
                : '';
            resultDiv.innerHTML = `
                <div style="background: #dcfce7; border: 1px solid #16a34a; border-radius: 8px; padding: 16px;">
                    <h5 style="color: #16a34a; margin: 0 0 8px 0;"><i class="fas fa-check-circle"></i> Imported ${data.imported} question(s)</h5>
                    ${skippedHtml}
                    <button onclick="teacherDashboard.loadExamQuestions('${examId}'); document.getElementById('aiQuestionGeneratorContainer').innerHTML='';" class="btn-primary" style="margin-top: 12px; padding: 8px 16px;">
                        <i class="fas fa-sync"></i> Refresh Questions
                    </button>
                </div>
            `;
        } catch (error) {
            resultDiv.innerHTML = `
                <div style="background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; padding: 16px;">
                    <h5 style="color: #ef4444; margin: 0 0 8px 0;"><i class="fas fa-exclamation-circle"></i> Import failed</h5>
                    <p style="margin: 0; color: #dc2626;">${this.escapeHtml(error.message)}</p>
                </div>
            `;
        }
    }

    async translateExamQuestions(examId) {
        if (!confirm('Auto-translate all questions so each one has both English and Arabic? Existing text is never changed — only missing translations are filled in.')) return;
        const container = document.getElementById('aiQuestionGeneratorContainer');
        container.innerHTML = `
            <div id="translateStatus" style="background: #f0fdfa; border: 1px solid #14b8a6; border-radius: 12px; padding: 20px; margin-bottom: 20px; text-align: center;">
                <i class="fas fa-spinner fa-spin fa-2x" style="color: #0d9488;"></i>
                <p style="margin-top: 12px; color: #0f766e;">Translating questions with Artificial Intelligence... This may take a minute.</p>
            </div>
        `;
        try {
            const response = await fetch(`/api/teacher/exams/${examId}/questions/translate`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' }
            });
            const ct2 = response.headers.get('content-type') || '';
            if (!ct2.includes('application/json')) {
                throw new Error('Session expired. Please refresh the page and log in again, then try translating.');
            }
            const data = await response.json();
            if (!response.ok || !data.success) throw new Error(data.error || 'Translation failed');
            container.innerHTML = `
                <div style="background: #dcfce7; border: 1px solid #16a34a; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                    <h5 style="color: #16a34a; margin: 0 0 8px 0;"><i class="fas fa-check-circle"></i> ${data.message ? this.escapeHtml(data.message) : `Translated ${data.translated} question(s)`}</h5>
                    <button onclick="teacherDashboard.loadExamQuestions('${examId}'); document.getElementById('aiQuestionGeneratorContainer').innerHTML='';" class="btn-primary" style="margin-top: 12px; padding: 8px 16px;">
                        <i class="fas fa-sync"></i> Refresh Questions
                    </button>
                </div>
            `;
        } catch (error) {
            container.innerHTML = `
                <div style="background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                    <h5 style="color: #ef4444; margin: 0 0 8px 0;"><i class="fas fa-exclamation-circle"></i> Translation failed</h5>
                    <p style="margin: 0; color: #dc2626;">${this.escapeHtml(error.message)}</p>
                </div>
            `;
        }
    }

    async editMaterial(materialId) {
        try {
            const response = await fetch(`/api/teacher/materials/${materialId}`, {
                credentials: 'include'
            });
            
            if (!response.ok) throw new Error('Failed to load material');
            
            const data = await response.json();
            if (!data.success) throw new Error(data.error || 'Failed to load material');
            
            const material = data.material;
            this.showEditMaterialModal(material);
        } catch (error) {
            console.error('Error loading material:', error);
            alert('Error loading material: ' + error.message);
        }
    }
    
    showEditMaterialModal(material) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'editMaterialModal';
        modal.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
        modal.innerHTML = `
            <div style="background: white; border-radius: 12px; width: 90%; max-width: 600px; max-height: 90vh; overflow-y: auto;">
                <div style="background: linear-gradient(135deg, #f97316 0%, #fb923c 100%); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0;"><i class="fas fa-edit"></i> Edit Material</h3>
                    <button onclick="document.getElementById('editMaterialModal').remove()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div style="padding: 20px;">
                    <form id="editMaterialForm">
                        <input type="hidden" id="editMaterialId" value="${material.id}">
                        
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Material Title *</label>
                            <input type="text" id="editMaterialTitle" required value="${this.escapeHtml(material.title)}" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-edit-material-title">
                        </div>
                        
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Description</label>
                            <textarea id="editMaterialDescription" rows="3" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-edit-material-description">${this.escapeHtml(material.description || '')}</textarea>
                        </div>
                        
                        ${material.file_url ? `
                            <div style="margin-bottom: 16px; padding: 12px; background: #f3f4f6; border-radius: 8px;">
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;"><i class="fas fa-file"></i> Current File</label>
                                <span style="color: #666;">${this.escapeHtml(material.file_name || 'Uploaded file')}</span>
                                <a href="${material.file_url}" target="_blank" style="margin-left: 8px; color: #3b82f6;"><i class="fas fa-external-link-alt"></i></a>
                            </div>
                        ` : ''}
                        
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">External URL</label>
                            <input type="url" id="editMaterialUrl" value="${this.escapeHtml(material.external_url || '')}" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="https://example.com/resource" data-testid="input-edit-material-url">
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Visibility Status</label>
                                <select id="editMaterialVisibility" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" onchange="teacherDashboard.toggleEditScheduleField()" data-testid="select-edit-material-visibility">
                                    <option value="draft" ${material.visibility_state === 'draft' ? 'selected' : ''}>Draft (not visible)</option>
                                    <option value="approved" ${material.visibility_state === 'approved' ? 'selected' : ''}>Approved (visible now)</option>
                                    <option value="scheduled" ${material.visibility_state === 'scheduled' ? 'selected' : ''}>Scheduled</option>
                                </select>
                            </div>
                            <div id="editMaterialScheduleContainer" style="display: ${material.visibility_state === 'scheduled' ? 'block' : 'none'};">
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Available At</label>
                                <input type="datetime-local" id="editMaterialAvailableAt" value="${material.available_at ? material.available_at.slice(0, 16) : ''}" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-edit-material-available-at">
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 12px; margin-top: 20px;">
                            <button type="button" onclick="document.getElementById('editMaterialModal').remove()" class="btn-secondary" style="flex: 1; padding: 12px;">Cancel</button>
                            <button type="submit" class="btn-primary" style="flex: 1; padding: 12px;" data-testid="button-save-material">
                                <i class="fas fa-save"></i> Save Changes
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        document.getElementById('editMaterialForm').onsubmit = async (e) => {
            e.preventDefault();
            await this.updateMaterial(material.id);
        };
    }
    
    toggleEditScheduleField() {
        const visibility = document.getElementById('editMaterialVisibility').value;
        const scheduleContainer = document.getElementById('editMaterialScheduleContainer');
        if (scheduleContainer) {
            scheduleContainer.style.display = visibility === 'scheduled' ? 'block' : 'none';
        }
    }
    
    async updateMaterial(materialId) {
        const data = {
            title: document.getElementById('editMaterialTitle').value,
            description: document.getElementById('editMaterialDescription').value,
            external_url: document.getElementById('editMaterialUrl').value || null,
            visibility_state: document.getElementById('editMaterialVisibility').value,
            available_at: document.getElementById('editMaterialAvailableAt').value || null
        };
        
        if (!data.title) {
            alert('Please enter a title');
            return;
        }
        
        try {
            const response = await fetch(`/api/teacher/materials/${materialId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data)
            });
            
            if (!response.ok) throw new Error('Failed to update material');
            
            const result = await response.json();
            
            if (result.success) {
                document.getElementById('editMaterialModal').remove();
                alert('Material updated successfully!');
                await this.openCourse(this.currentCourse.id);
            } else {
                throw new Error(result.error || 'Failed to update');
            }
        } catch (error) {
            console.error('Error updating material:', error);
            alert('Error updating material: ' + error.message);
        }
    }

    async deleteMaterial(materialId) {
        if (!confirm('Are you sure you want to delete this material?')) return;

        try {
            const response = await fetch(`/api/teacher/materials/${materialId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to delete material');

            const result = await response.json();
            
            if (result.success) {
                alert('Material deleted!');
                await this.openCourse(this.currentCourse.id);
            } else {
                throw new Error(result.error || 'Failed to delete');
            }
        } catch (error) {
            console.error('Error deleting material:', error);
            alert('Error deleting material: ' + error.message);
        }
    }
    
    // ============================================
    // SURVEY MANAGEMENT
    // ============================================
    
    async loadSurveys() {
        const container = document.getElementById('courseSurveysList');
        if (!container || !this.currentCourse) return;
        
        container.innerHTML = '<div style="text-align: center; padding: 20px;"><i class="fas fa-spinner fa-spin"></i> Loading surveys...</div>';
        
        try {
            const response = await fetch(`/api/teacher/courses/${this.currentCourse.id}/surveys`, {
                credentials: 'include'
            });
            
            if (!response.ok) throw new Error('Failed to load surveys');
            
            const data = await response.json();
            
            if (!data.success || !data.surveys || data.surveys.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <i class="fas fa-poll" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                        <p>No surveys created yet. Click "Create Survey" to add a new survey.</p>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;">
                    ${data.surveys.map(survey => `
                        <div style="background: white; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;" data-testid="survey-card-${survey.id}">
                            <div style="background: linear-gradient(135deg, #0ea5e9 0%, #38bdf8 100%); color: white; padding: 16px;">
                                <h4 style="margin: 0;">${this.escapeHtml(survey.title)}</h4>
                                <span style="font-size: 12px; opacity: 0.9; text-transform: capitalize;">${survey.survey_type || 'Feedback'}</span>
                            </div>
                            <div style="padding: 16px;">
                                <p style="color: #666; font-size: 14px; margin-bottom: 12px;">${this.escapeHtml(survey.description || 'No description')}</p>
                                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;">
                                    <span style="background: #f3f4f6; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                                        <i class="fas fa-question-circle"></i> ${survey.questions_count || 0} questions
                                    </span>
                                    <span style="background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                                        <i class="fas fa-chart-bar"></i> ${survey.statistics?.response_rate || 0}% response rate
                                    </span>
                                    <span style="background: ${survey.is_published ? '#dcfce7' : '#fef9c3'}; color: ${survey.is_published ? '#166534' : '#854d0e'}; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                                        ${survey.is_published ? 'Published' : 'Draft'}
                                    </span>
                                </div>
                                <div style="display: flex; gap: 8px;">
                                    <button class="btn-secondary" style="padding: 6px 12px; font-size: 12px;" onclick="teacherDashboard.manageSurveyQuestions('${survey.id}')" data-testid="button-manage-survey-questions-${survey.id}">
                                        <i class="fas fa-list"></i> Questions
                                    </button>
                                    <button class="btn-secondary" style="padding: 6px 12px; font-size: 12px;" onclick="teacherDashboard.editSurvey('${survey.id}')" data-testid="button-edit-survey-${survey.id}">
                                        <i class="fas fa-edit"></i> Edit
                                    </button>
                                    <button class="btn-secondary" style="padding: 6px 12px; font-size: 12px; color: #ef4444;" onclick="teacherDashboard.deleteSurvey('${survey.id}')" data-testid="button-delete-survey-${survey.id}">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            console.error('Error loading surveys:', error);
            container.innerHTML = `<div style="text-align: center; padding: 40px; color: #ef4444;">Error loading surveys: ${error.message}</div>`;
        }
    }
    
    showCreateSurveyModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'createSurveyModal';
        modal.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
        modal.innerHTML = `
            <div style="background: white; border-radius: 12px; width: 90%; max-width: 600px; max-height: 90vh; overflow-y: auto;">
                <div style="background: linear-gradient(135deg, #0ea5e9 0%, #38bdf8 100%); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0;"><i class="fas fa-plus-circle"></i> Create New Survey</h3>
                    <button onclick="document.getElementById('createSurveyModal').remove()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div style="padding: 20px;">
                    <form id="createSurveyForm">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Survey Title *</label>
                            <input type="text" id="newSurveyTitle" required style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="e.g., Course Feedback Survey" data-testid="input-new-survey-title">
                        </div>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Description</label>
                            <textarea id="newSurveyDescription" rows="3" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="Describe the survey..." data-testid="input-new-survey-description"></textarea>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Survey Type</label>
                                <select id="newSurveyType" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="select-new-survey-type">
                                    <option value="training_feedback">Training Feedback</option>
                                    <option value="entry_survey">Entry Survey</option>
                                    <option value="exit_survey">Exit Survey</option>
                                    <option value="course_evaluation">Course Evaluation</option>
                                </select>
                            </div>
                            <div style="display: flex; flex-direction: column; justify-content: flex-end;">
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" id="newSurveyRequired" data-testid="checkbox-new-survey-required">
                                    <span>Required for students</span>
                                </label>
                            </div>
                        </div>
                        <div style="display: flex; gap: 12px; justify-content: flex-end; padding-top: 16px; border-top: 1px solid #e5e7eb;">
                            <button type="button" onclick="document.getElementById('createSurveyModal').remove()" class="btn-secondary" style="padding: 10px 20px;">Cancel</button>
                            <button type="submit" class="btn-primary" style="padding: 10px 20px;" data-testid="button-create-survey-submit">
                                <i class="fas fa-plus"></i> Create Survey
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        document.getElementById('createSurveyForm').onsubmit = async (e) => {
            e.preventDefault();
            await this.createSurvey();
            modal.remove();
        };
    }
    
    async createSurvey() {
        if (!this.currentCourse) return;
        
        const data = {
            title: document.getElementById('newSurveyTitle').value,
            description: document.getElementById('newSurveyDescription').value,
            survey_type: document.getElementById('newSurveyType').value,
            is_required: document.getElementById('newSurveyRequired').checked,
            is_published: false
        };
        
        try {
            const response = await fetch(`/api/teacher/courses/${this.currentCourse.id}/surveys`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data)
            });
            
            if (!response.ok) throw new Error('Failed to create survey');
            
            const result = await response.json();
            if (result.success) {
                alert('Survey created successfully!');
                await this.loadSurveys();
            } else {
                throw new Error(result.error || 'Failed to create survey');
            }
        } catch (error) {
            console.error('Error creating survey:', error);
            alert('Error creating survey: ' + error.message);
        }
    }
    
    async editSurvey(surveyId) {
        try {
            const response = await fetch(`/api/teacher/surveys/${surveyId}`, {
                credentials: 'include'
            });
            
            if (!response.ok) throw new Error('Failed to load survey');
            
            const data = await response.json();
            const survey = data.survey;
            
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'editSurveyModal';
            modal.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
            modal.innerHTML = `
                <div style="background: white; border-radius: 12px; width: 90%; max-width: 600px; max-height: 90vh; overflow-y: auto;">
                    <div style="background: linear-gradient(135deg, #0ea5e9 0%, #38bdf8 100%); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0;"><i class="fas fa-edit"></i> Edit Survey</h3>
                        <button onclick="document.getElementById('editSurveyModal').remove()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer;">&times;</button>
                    </div>
                    <div style="padding: 20px;">
                        <form id="editSurveyForm">
                            <div style="margin-bottom: 16px;">
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Survey Title *</label>
                                <input type="text" id="editSurveyTitle" required value="${this.escapeHtml(survey.title)}" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-edit-survey-title">
                            </div>
                            <div style="margin-bottom: 16px;">
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Description</label>
                                <textarea id="editSurveyDescription" rows="3" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="input-edit-survey-description">${this.escapeHtml(survey.description || '')}</textarea>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                                <div>
                                    <label style="display: block; margin-bottom: 6px; font-weight: 500;">Survey Type</label>
                                    <select id="editSurveyType" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" data-testid="select-edit-survey-type">
                                        <option value="training_feedback" ${survey.survey_type === 'training_feedback' ? 'selected' : ''}>Training Feedback</option>
                                        <option value="entry_survey" ${survey.survey_type === 'entry_survey' ? 'selected' : ''}>Entry Survey</option>
                                        <option value="exit_survey" ${survey.survey_type === 'exit_survey' ? 'selected' : ''}>Exit Survey</option>
                                        <option value="course_evaluation" ${survey.survey_type === 'course_evaluation' ? 'selected' : ''}>Course Evaluation</option>
                                    </select>
                                </div>
                                <div style="display: flex; flex-direction: column; gap: 8px; justify-content: flex-end;">
                                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                        <input type="checkbox" id="editSurveyRequired" ${survey.is_required ? 'checked' : ''} data-testid="checkbox-edit-survey-required">
                                        <span>Required</span>
                                    </label>
                                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                        <input type="checkbox" id="editSurveyPublished" ${survey.is_published ? 'checked' : ''} data-testid="checkbox-edit-survey-published">
                                        <span>Published</span>
                                    </label>
                                </div>
                            </div>
                            <div style="display: flex; gap: 12px; justify-content: flex-end; padding-top: 16px; border-top: 1px solid #e5e7eb;">
                                <button type="button" onclick="document.getElementById('editSurveyModal').remove()" class="btn-secondary" style="padding: 10px 20px;">Cancel</button>
                                <button type="submit" class="btn-primary" style="padding: 10px 20px;" data-testid="button-save-survey">
                                    <i class="fas fa-save"></i> Save Changes
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            document.getElementById('editSurveyForm').onsubmit = async (e) => {
                e.preventDefault();
                await this.updateSurvey(surveyId);
            };
        } catch (error) {
            console.error('Error loading survey:', error);
            alert('Error loading survey: ' + error.message);
        }
    }
    
    async updateSurvey(surveyId) {
        const data = {
            title: document.getElementById('editSurveyTitle').value,
            description: document.getElementById('editSurveyDescription').value,
            survey_type: document.getElementById('editSurveyType').value,
            is_required: document.getElementById('editSurveyRequired').checked,
            is_published: document.getElementById('editSurveyPublished').checked
        };
        
        try {
            const response = await fetch(`/api/teacher/surveys/${surveyId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data)
            });
            
            if (!response.ok) throw new Error('Failed to update survey');
            
            const result = await response.json();
            if (result.success) {
                document.getElementById('editSurveyModal')?.remove();
                alert('Survey updated successfully!');
                await this.loadSurveys();
            } else {
                throw new Error(result.error || 'Failed to update survey');
            }
        } catch (error) {
            console.error('Error updating survey:', error);
            alert('Error updating survey: ' + error.message);
        }
    }
    
    async deleteSurvey(surveyId) {
        if (!confirm('Are you sure you want to delete this survey? All responses will be lost.')) return;
        
        try {
            const response = await fetch(`/api/teacher/surveys/${surveyId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            if (!response.ok) throw new Error('Failed to delete survey');
            
            alert('Survey deleted!');
            await this.loadSurveys();
        } catch (error) {
            console.error('Error deleting survey:', error);
            alert('Error deleting survey: ' + error.message);
        }
    }
    
    async manageSurveyQuestions(surveyId) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'surveyQuestionsModal';
        modal.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
        modal.innerHTML = `
            <div style="background: white; border-radius: 12px; width: 95%; max-width: 900px; max-height: 90vh; overflow-y: auto;">
                <div style="background: linear-gradient(135deg, #0ea5e9 0%, #38bdf8 100%); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 10;">
                    <h3 style="margin: 0;"><i class="fas fa-list"></i> Manage Survey Questions</h3>
                    <button onclick="document.getElementById('surveyQuestionsModal').remove()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div style="padding: 20px;">
                    <div id="surveyQuestionsLoading" style="text-align: center; padding: 40px;">
                        <i class="fas fa-spinner fa-spin fa-2x"></i>
                        <p>Loading questions...</p>
                    </div>
                    <div id="surveyQuestionsContent" style="display: none;"></div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        await this.loadSurveyQuestions(surveyId);
    }
    
    async loadSurveyQuestions(surveyId) {
        try {
            const response = await fetch(`/api/teacher/surveys/${surveyId}`, {
                credentials: 'include'
            });
            
            if (!response.ok) throw new Error('Failed to load survey');
            
            const data = await response.json();
            
            document.getElementById('surveyQuestionsLoading').style.display = 'none';
            document.getElementById('surveyQuestionsContent').style.display = 'block';
            
            const questions = data.questions || [];
            const surveyTitle = data.survey?.title || 'Survey';
            
            document.getElementById('surveyQuestionsContent').innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h4 style="margin: 0;">${this.escapeHtml(surveyTitle)} - Questions (${questions.length})</h4>
                    <div style="display: flex; gap: 12px;">
                        <button onclick="teacherDashboard.showAISurveyQuestionGenerator('${surveyId}')" class="btn-secondary" style="padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none;" data-testid="button-ai-generate-survey">
                            <i class="fas fa-robot"></i> Generate with Artificial Intelligence
                        </button>
                        <button onclick="teacherDashboard.showAddSurveyQuestionForm('${surveyId}')" class="btn-primary" style="padding: 10px 20px;" data-testid="button-add-survey-question">
                            <i class="fas fa-plus"></i> Add Question
                        </button>
                    </div>
                </div>
                
                <div id="aiSurveyQuestionGeneratorContainer"></div>
                <div id="addSurveyQuestionFormContainer"></div>
                
                <div id="surveyQuestionsListContainer">
                    ${questions.length === 0 ? `
                        <div style="text-align: center; padding: 40px; color: #666; background: #f9fafb; border-radius: 12px;">
                            <i class="fas fa-question-circle" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                            <p>No questions added yet. Click "Add Question" to create your first question.</p>
                        </div>
                    ` : questions.map((q, idx) => `
                        <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div style="flex: 1;">
                                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                        <span style="background: #0ea5e9; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">Q${idx + 1}</span>
                                        <span style="background: #e5e7eb; padding: 2px 8px; border-radius: 4px; font-size: 12px; text-transform: capitalize;">${q.question_type}</span>
                                        ${q.is_required ? '<span style="color: #ef4444; font-size: 12px;">Required</span>' : ''}
                                    </div>
                                    <p style="margin: 0 0 4px 0; font-weight: 500;">${this.escapeHtml(q.question_text)}</p>
                                    ${q.question_text_ar ? `<p style="margin: 0; font-weight: 500; direction: rtl; text-align: right; color: #666;">${this.escapeHtml(q.question_text_ar)}</p>` : ''}
                                    ${(() => {
                                        const flatEn = this.flattenOptions(q.options);
                                        const flatAr = this.flattenOptions(q.options_ar);
                                        if (!flatEn.length) return '';
                                        const isCorrect = (i) => this.isCorrectAnswer(q.correct_answer, i);
                                        return `
                                        <div style="margin-top: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                                            <div>
                                                ${flatEn.map((opt, optIdx) => `
                                                    <div style="padding: 6px 12px; background: ${isCorrect(optIdx) ? '#dcfce7' : 'white'}; border: 1px solid ${isCorrect(optIdx) ? '#16a34a' : '#e5e7eb'}; border-radius: 6px; margin-top: 4px; font-size: 14px;">
                                                        ${isCorrect(optIdx) ? '<i class="fas fa-check-circle" style="color:#16a34a; margin-right:6px;"></i>' : ''}${this.escapeHtml(opt)}
                                                    </div>
                                                `).join('')}
                                            </div>
                                            ${flatAr.length > 0 ? `
                                                <div style="direction: rtl; text-align: right;">
                                                    ${flatAr.map((opt, optIdx) => `
                                                        <div style="padding: 6px 12px; background: ${isCorrect(optIdx) ? '#dcfce7' : 'white'}; border: 1px solid ${isCorrect(optIdx) ? '#16a34a' : '#e5e7eb'}; border-radius: 6px; margin-top: 4px; font-size: 14px;">
                                                            ${isCorrect(optIdx) ? '<i class="fas fa-check-circle" style="color:#16a34a; margin-left:6px;"></i>' : ''}${this.escapeHtml(opt)}
                                                        </div>
                                                    `).join('')}
                                                </div>
                                            ` : ''}
                                        </div>`;
                                    })()}
                                </div>
                                <div style="display: flex; flex-direction: column; gap: 8px;">
                                    <button type="button" onclick="teacherDashboard.showEditSurveyQuestionForm('${surveyId}', '${q.id}', ${JSON.stringify(q).replace(/"/g, '&quot;')})" class="btn-secondary" style="padding: 6px 10px; color: #0ea5e9;">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button type="button" onclick="teacherDashboard.deleteSurveyQuestion('${surveyId}', '${q.id}')" class="btn-secondary" style="padding: 6px 10px; color: #ef4444;">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            console.error('Error loading questions:', error);
            document.getElementById('surveyQuestionsLoading').innerHTML = `
                <div style="color: #ef4444;">
                    <i class="fas fa-exclamation-circle"></i> Error loading questions: ${error.message}
                </div>
            `;
        }
    }
    
    showAddSurveyQuestionForm(surveyId) {
        const container = document.getElementById('addSurveyQuestionFormContainer');
        container.innerHTML = `
            <div style="background: #f0f9ff; border: 2px solid #0ea5e9; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h5 style="margin: 0 0 16px 0; color: #0369a1;"><i class="fas fa-plus-circle"></i> Add New Question (Bilingual)</h5>
                <form id="addSurveyQuestionForm">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Question Text (English) *</label>
                            <textarea id="newSurveyQuestionText" required rows="2" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="Enter your question in English..."></textarea>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Question Text (Arabic) نص السؤال</label>
                            <textarea id="newSurveyQuestionTextAr" rows="2" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; direction: rtl; text-align: right;" placeholder="أدخل السؤال بالعربية..."></textarea>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Question Type</label>
                            <select id="newSurveyQuestionType" onchange="teacherDashboard.toggleSurveyOptionsField()" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;">
                                <option value="multiple_choice">Multiple Choice</option>
                                <option value="true_false">True/False</option>
                            </select>
                        </div>
                        <div style="display: flex; align-items: flex-end;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" id="newSurveyQuestionRequired" checked>
                                <span>Required</span>
                            </label>
                        </div>
                    </div>
                    <div id="surveyOptionsContainer" style="margin-bottom: 16px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Options - English (one per line)</label>
                                <textarea id="newSurveyQuestionOptions" rows="4" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" placeholder="Option A&#10;Option B&#10;Option C&#10;Option D" oninput="teacherDashboard.updateCorrectAnswerDropdown()"></textarea>
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Options - Arabic الخيارات (one per line)</label>
                                <textarea id="newSurveyQuestionOptionsAr" rows="4" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; direction: rtl; text-align: right;" placeholder="الخيار أ&#10;الخيار ب&#10;الخيار ج&#10;الخيار د"></textarea>
                            </div>
                        </div>
                    </div>
                    <div id="surveyCorrectAnswerContainer" style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 6px; font-weight: 500;">Correct Answer *</label>
                        <select id="newSurveyQuestionCorrectAnswer" required style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;">
                            <option value="">-- Enter options first --</option>
                        </select>
                    </div>
                    <div style="display: flex; gap: 12px; justify-content: flex-end;">
                        <button type="button" onclick="document.getElementById('addSurveyQuestionFormContainer').innerHTML=''" class="btn-secondary" style="padding: 10px 20px;">Cancel</button>
                        <button type="submit" class="btn-primary" style="padding: 10px 20px;">
                            <i class="fas fa-save"></i> Save Question
                        </button>
                    </div>
                </form>
            </div>
        `;
        
        document.getElementById('addSurveyQuestionForm').onsubmit = async (e) => {
            e.preventDefault();
            await this.addSurveyQuestion(surveyId);
        };
    }
    
    toggleSurveyOptionsField() {
        const type = document.getElementById('newSurveyQuestionType').value;
        const container = document.getElementById('surveyOptionsContainer');
        const correctAnswerContainer = document.getElementById('surveyCorrectAnswerContainer');
        
        if (type === 'true_false') {
            container.style.display = 'none';
            correctAnswerContainer.style.display = 'block';
            const select = document.getElementById('newSurveyQuestionCorrectAnswer');
            select.innerHTML = '<option value="">-- Select correct answer --</option><option value="0">True</option><option value="1">False</option>';
        } else {
            container.style.display = 'block';
            correctAnswerContainer.style.display = 'block';
            this.updateCorrectAnswerDropdown();
        }
    }
    
    updateCorrectAnswerDropdown() {
        const optionsText = document.getElementById('newSurveyQuestionOptions')?.value || '';
        const options = optionsText.split('\n').filter(o => o.trim());
        const select = document.getElementById('newSurveyQuestionCorrectAnswer');
        if (!select) return;
        
        if (options.length === 0) {
            select.innerHTML = '<option value="">-- Enter options first --</option>';
        } else {
            select.innerHTML = '<option value="">-- Select correct answer --</option>' + 
                options.map((opt, idx) => `<option value="${idx}">${this.escapeHtml(opt.trim())}</option>`).join('');
        }
    }
    
    async addSurveyQuestion(surveyId) {
        const questionType = document.getElementById('newSurveyQuestionType').value;
        let options = [];
        let optionsAr = [];
        
        if (questionType === 'multiple_choice') {
            options = document.getElementById('newSurveyQuestionOptions').value.split('\n').filter(o => o.trim());
            optionsAr = document.getElementById('newSurveyQuestionOptionsAr')?.value.split('\n').filter(o => o.trim()) || [];
        } else if (questionType === 'true_false') {
            options = ['True', 'False'];
            optionsAr = ['صحيح', 'خطأ'];
        }
        
        const correctAnswerSelect = document.getElementById('newSurveyQuestionCorrectAnswer');
        const correctAnswerIndex = correctAnswerSelect?.value !== '' ? parseInt(correctAnswerSelect.value) : null;
        
        const data = {
            question_text: document.getElementById('newSurveyQuestionText').value,
            question_text_ar: document.getElementById('newSurveyQuestionTextAr')?.value || '',
            question_type: questionType,
            options: options,
            options_ar: optionsAr,
            correct_answer: correctAnswerIndex,
            is_required: document.getElementById('newSurveyQuestionRequired').checked
        };
        
        try {
            const response = await fetch(`/api/teacher/surveys/${surveyId}/questions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data)
            });
            
            if (!response.ok) throw new Error('Failed to add question');
            
            const result = await response.json();
            if (result.success) {
                await this.loadSurveyQuestions(surveyId);
            } else {
                throw new Error(result.error || 'Failed to add question');
            }
        } catch (error) {
            console.error('Error adding question:', error);
            alert('Error adding question: ' + error.message);
        }
    }
    
    async deleteSurveyQuestion(surveyId, questionId) {
        if (!confirm('Are you sure you want to delete this question?')) return;
        
        try {
            const response = await fetch(`/api/teacher/surveys/${surveyId}/questions/${questionId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            if (!response.ok) throw new Error('Failed to delete question');
            
            await this.loadSurveyQuestions(surveyId);
        } catch (error) {
            console.error('Error deleting question:', error);
            alert('Error deleting question: ' + error.message);
        }
    }
    
    showEditSurveyQuestionForm(surveyId, questionId, question) {
        const container = document.getElementById('addSurveyQuestionFormContainer');
        const isTrueFalse = question.question_type === 'true_false';
        const options = this.flattenOptions(question.options);
        const optionsAr = this.flattenOptions(question.options_ar);
        const correctAnswer = question.correct_answer;
        const isCorrect = (i) => this.isCorrectAnswer(correctAnswer, i);
        
        container.innerHTML = `
            <div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h5 style="margin: 0 0 16px 0; color: #b45309;"><i class="fas fa-edit"></i> Edit Question</h5>
                <form id="editSurveyQuestionForm">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Question Text (English) *</label>
                            <textarea id="editSurveyQuestionText" required rows="2" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;">${this.escapeHtml(question.question_text || '')}</textarea>
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Question Text (Arabic) نص السؤال</label>
                            <textarea id="editSurveyQuestionTextAr" rows="2" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; direction: rtl; text-align: right;">${this.escapeHtml(question.question_text_ar || '')}</textarea>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">Question Type</label>
                            <select id="editSurveyQuestionType" onchange="teacherDashboard.toggleEditSurveyOptionsField()" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;">
                                <option value="multiple_choice" ${question.question_type === 'multiple_choice' ? 'selected' : ''}>Multiple Choice</option>
                                <option value="true_false" ${question.question_type === 'true_false' ? 'selected' : ''}>True/False</option>
                            </select>
                        </div>
                        <div style="display: flex; align-items: flex-end;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" id="editSurveyQuestionRequired" ${question.is_required ? 'checked' : ''}>
                                <span>Required</span>
                            </label>
                        </div>
                    </div>
                    <div id="editSurveyOptionsContainer" style="margin-bottom: 16px; ${isTrueFalse ? 'display: none;' : ''}">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Options - English (one per line)</label>
                                <textarea id="editSurveyQuestionOptions" rows="4" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;" oninput="teacherDashboard.updateEditCorrectAnswerDropdown()">${options.join('\\n')}</textarea>
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 6px; font-weight: 500;">Options - Arabic الخيارات (one per line)</label>
                                <textarea id="editSurveyQuestionOptionsAr" rows="4" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; direction: rtl; text-align: right;">${optionsAr.join('\\n')}</textarea>
                            </div>
                        </div>
                    </div>
                    <div id="editSurveyCorrectAnswerContainer" style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 6px; font-weight: 500;">Correct Answer *</label>
                        <select id="editSurveyQuestionCorrectAnswer" required style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;">
                            ${isTrueFalse ?
                                `<option value="">-- Select correct answer --</option>
                                 <option value="0" ${isCorrect(0) ? 'selected' : ''}>True</option>
                                 <option value="1" ${isCorrect(1) ? 'selected' : ''}>False</option>` :
                                `<option value="">-- Select correct answer --</option>
                                 ${options.map((opt, idx) => `<option value="${idx}" ${isCorrect(idx) ? 'selected' : ''}>${this.escapeHtml(opt)}</option>`).join('')}`
                            }
                        </select>
                    </div>
                    <div style="display: flex; gap: 12px; justify-content: flex-end;">
                        <button type="button" onclick="document.getElementById('addSurveyQuestionFormContainer').innerHTML=''" class="btn-secondary" style="padding: 10px 20px;">Cancel</button>
                        <button type="submit" class="btn-primary" style="padding: 10px 20px; background: #f59e0b;">
                            <i class="fas fa-save"></i> Update Question
                        </button>
                    </div>
                </form>
            </div>
        `;
        
        document.getElementById('editSurveyQuestionForm').onsubmit = async (e) => {
            e.preventDefault();
            await this.updateSurveyQuestion(surveyId, questionId);
        };

        // Bring the edit form into view (mirrors the exam-side fix).
        try {
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });
            const focusEl = document.getElementById('editSurveyQuestionText');
            if (focusEl) setTimeout(() => focusEl.focus({ preventScroll: true }), 250);
        } catch (_) { /* no-op */ }
    }

    toggleEditSurveyOptionsField() {
        const type = document.getElementById('editSurveyQuestionType').value;
        const container = document.getElementById('editSurveyOptionsContainer');
        const select = document.getElementById('editSurveyQuestionCorrectAnswer');
        
        if (type === 'true_false') {
            container.style.display = 'none';
            select.innerHTML = '<option value="">-- Select correct answer --</option><option value="0">True</option><option value="1">False</option>';
        } else {
            container.style.display = 'block';
            this.updateEditCorrectAnswerDropdown();
        }
    }
    
    updateEditCorrectAnswerDropdown() {
        const optionsText = document.getElementById('editSurveyQuestionOptions')?.value || '';
        const options = optionsText.split('\n').filter(o => o.trim());
        const select = document.getElementById('editSurveyQuestionCorrectAnswer');
        if (!select) return;
        
        const currentValue = select.value;
        if (options.length === 0) {
            select.innerHTML = '<option value="">-- Enter options first --</option>';
        } else {
            select.innerHTML = '<option value="">-- Select correct answer --</option>' + 
                options.map((opt, idx) => `<option value="${idx}" ${currentValue == idx ? 'selected' : ''}>${this.escapeHtml(opt.trim())}</option>`).join('');
        }
    }
    
    async updateSurveyQuestion(surveyId, questionId) {
        const questionType = document.getElementById('editSurveyQuestionType').value;
        let options = [];
        let optionsAr = [];
        
        if (questionType === 'multiple_choice') {
            options = document.getElementById('editSurveyQuestionOptions').value.split('\n').filter(o => o.trim());
            optionsAr = document.getElementById('editSurveyQuestionOptionsAr')?.value.split('\n').filter(o => o.trim()) || [];
        } else if (questionType === 'true_false') {
            options = ['True', 'False'];
            optionsAr = ['صحيح', 'خطأ'];
        }
        
        const correctAnswerSelect = document.getElementById('editSurveyQuestionCorrectAnswer');
        const correctAnswerIndex = correctAnswerSelect?.value !== '' ? parseInt(correctAnswerSelect.value) : null;
        
        const data = {
            question_text: document.getElementById('editSurveyQuestionText').value,
            question_text_ar: document.getElementById('editSurveyQuestionTextAr')?.value || '',
            question_type: questionType,
            options: options,
            options_ar: optionsAr,
            correct_answer: correctAnswerIndex,
            is_required: document.getElementById('editSurveyQuestionRequired').checked
        };
        
        try {
            const response = await fetch(`/api/teacher/surveys/${surveyId}/questions/${questionId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(data)
            });
            
            if (!response.ok) throw new Error('Failed to update question');
            
            const result = await response.json();
            if (result.success) {
                await this.loadSurveyQuestions(surveyId);
            } else {
                throw new Error(result.error || 'Failed to update question');
            }
        } catch (error) {
            console.error('Error updating question:', error);
            alert('Error updating question: ' + error.message);
        }
    }
    
    // ============================================
    // AI SURVEY QUESTION GENERATOR
    // ============================================
    
    showAISurveyQuestionGenerator(surveyId) {
        const container = document.getElementById('aiSurveyQuestionGeneratorContainer');
        container.innerHTML = `
            <div style="background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%); border: 2px solid #8b5cf6; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h5 style="margin: 0 0 16px 0; color: #6d28d9;">
                    <i class="fas fa-robot"></i> AI Question Generator
                </h5>
                <p style="color: #666; font-size: 14px; margin-bottom: 16px;">
                    Upload a document and let AI generate bilingual (English/Arabic) questions automatically.
                </p>
                
                <form id="aiSurveyGenerateForm">
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 6px; font-weight: 500;">Upload Document *</label>
                        <input type="file" id="aiSurveyDocumentFile" accept=".pdf,.doc,.docx,.txt,.ppt,.pptx" required 
                               style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; background: white;" 
                               data-testid="input-ai-survey-document">
                        <small style="color: #666;">Supported: PDF, DOC, DOCX, TXT, PPT, PPTX</small>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">True/False Questions</label>
                            <input type="number" id="aiSurveyRatingCount" min="0" max="20" value="5" 
                                   style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;"
                                   data-testid="input-ai-survey-tf-count">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 500;">MCQ Questions</label>
                            <input type="number" id="aiSurveyMCQCount" min="0" max="20" value="5" 
                                   style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;"
                                   data-testid="input-ai-survey-mcq-count">
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; margin-bottom: 6px; font-weight: 500;">Topic (Optional)</label>
                        <input type="text" id="aiSurveyTopic" placeholder="e.g., Course Content, Instructor" 
                               style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;"
                               data-testid="input-ai-survey-topic">
                    </div>
                    
                    <div style="display: flex; gap: 12px; justify-content: flex-end;">
                        <button type="button" onclick="document.getElementById('aiSurveyQuestionGeneratorContainer').innerHTML=''" class="btn-secondary" style="padding: 10px 20px;">Cancel</button>
                        <button type="submit" class="btn-primary" style="padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none;" data-testid="button-generate-ai-survey-questions">
                            <i class="fas fa-magic"></i> Generate Questions
                        </button>
                    </div>
                </form>
                
                <div id="aiSurveyGenerationProgress" style="display: none; margin-top: 16px; text-align: center; padding: 20px;">
                    <i class="fas fa-spinner fa-spin fa-2x" style="color: #667eea;"></i>
                    <p style="margin-top: 12px; color: #666;">AI is generating bilingual questions... This may take a moment.</p>
                </div>
                
                <div id="aiSurveyGenerationResult" style="display: none; margin-top: 16px;"></div>
            </div>
        `;
        
        document.getElementById('aiSurveyGenerateForm').onsubmit = async (e) => {
            e.preventDefault();
            await this.generateAISurveyQuestions(surveyId);
        };
    }
    
    async generateAISurveyQuestions(surveyId) {
        const fileInput = document.getElementById('aiSurveyDocumentFile');
        const mcqCount = document.getElementById('aiSurveyMCQCount').value;
        const ratingCount = document.getElementById('aiSurveyRatingCount').value;
        const topic = document.getElementById('aiSurveyTopic').value;
        
        if (!fileInput.files.length) {
            alert('Please select a document file');
            return;
        }
        
        if (!this.currentCourse?.id) {
            alert('Course ID not found. Please refresh and try again.');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('num_true_false', ratingCount);
        formData.append('num_mcq', mcqCount);
        formData.append('topic', topic);
        formData.append('target_type', 'survey');
        formData.append('target_id', surveyId);
        
        document.getElementById('aiSurveyGenerateForm').style.display = 'none';
        document.getElementById('aiSurveyGenerationProgress').style.display = 'block';
        
        const courseId = this.currentCourse.id;
        
        try {
            const response = await fetch(`/api/teacher/courses/${courseId}/generate-questions`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });
            
            const text = await response.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch (parseError) {
                console.error('Response was not JSON:', text.substring(0, 200));
                // Mirror the exam-side recovery UX: questions may already be saved.
                document.getElementById('aiSurveyGenerationProgress').style.display = 'none';
                document.getElementById('aiSurveyGenerateForm').style.display = 'block';
                const warnDiv = document.getElementById('aiSurveyGenerationResult');
                warnDiv.style.display = 'block';
                warnDiv.innerHTML = `
                    <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px;">
                        <h5 style="color: #b45309; margin: 0 0 8px 0;"><i class="fas fa-info-circle"></i> Generation may have completed</h5>
                        <p style="margin: 0; color: #92400e;">The server did not return a clear response (possibly a timeout). The questions may already be saved.</p>
                        <button type="button" onclick="teacherDashboard.loadSurveyQuestions('${surveyId}'); document.getElementById('aiSurveyQuestionGeneratorContainer').innerHTML='';" class="btn-primary" style="margin-top: 12px; padding: 8px 16px;">
                            <i class="fas fa-sync"></i> Refresh Questions
                        </button>
                    </div>
                `;
                return;
            }

            document.getElementById('aiSurveyGenerationProgress').style.display = 'none';

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to generate questions');
            }
            
            const resultDiv = document.getElementById('aiSurveyGenerationResult');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <div style="background: #dcfce7; border: 1px solid #16a34a; border-radius: 8px; padding: 16px;">
                    <h5 style="color: #16a34a; margin: 0 0 8px 0;"><i class="fas fa-check-circle"></i> Success!</h5>
                    <p style="margin: 0; color: #166534;">${data.message}</p>
                    <p style="margin: 8px 0 0 0; font-size: 14px; color: #666;">Questions have been added to the survey in both English and Arabic.</p>
                    <button onclick="teacherDashboard.loadSurveyQuestions('${surveyId}'); document.getElementById('aiSurveyQuestionGeneratorContainer').innerHTML='';" class="btn-primary" style="margin-top: 12px; padding: 8px 16px;">
                        <i class="fas fa-sync"></i> Refresh Questions
                    </button>
                </div>
            `;
            
        } catch (error) {
            console.error('Error generating questions:', error);
            document.getElementById('aiSurveyGenerationProgress').style.display = 'none';
            document.getElementById('aiSurveyGenerateForm').style.display = 'block';
            
            const resultDiv = document.getElementById('aiSurveyGenerationResult');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <div style="background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; padding: 16px;">
                    <h5 style="color: #ef4444; margin: 0 0 8px 0;"><i class="fas fa-exclamation-circle"></i> Error</h5>
                    <p style="margin: 0; color: #dc2626;">${error.message}</p>
                </div>
            `;
        }
    }

    // ============================================
    // ATTENDANCE MANAGEMENT METHODS
    // ============================================

    async loadAttendance() {
        if (!this.currentCourse) {
            alert('Please select a course first');
            return;
        }

        const dateInput = document.getElementById('teacherAttendanceDate');
        if (!dateInput.value) {
            dateInput.value = new Date().toISOString().split('T')[0];
        }
        
        const container = document.getElementById('courseAttendanceList');
        const summaryDiv = document.getElementById('attendanceSummary');
        
        container.innerHTML = '<div style="text-align: center; padding: 40px;"><i class="fas fa-spinner fa-spin fa-2x"></i><p>Loading attendance...</p></div>';
        
        try {
            const response = await fetch(`/api/attendance/class/${this.currentCourse.id}/date/${dateInput.value}`, {
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to load attendance');
            }
            
            this.attendanceData = data.students;
            
            const s = data.summary;
            summaryDiv.innerHTML = `
                <div class="summary-item">
                    <span class="summary-label">Total / الإجمالي:</span>
                    <span class="summary-value">${s.total}</span>
                </div>
                <div class="summary-item present">
                    <span class="summary-label">Present / حاضر:</span>
                    <span class="summary-value">${s.present}</span>
                </div>
                <div class="summary-item absent">
                    <span class="summary-label">Absent / غائب:</span>
                    <span class="summary-value">${s.absent}</span>
                </div>
                <div class="summary-item late">
                    <span class="summary-label">Late / متأخر:</span>
                    <span class="summary-value">${s.late}</span>
                </div>
                <div class="summary-item excused">
                    <span class="summary-label">Excused / معذور:</span>
                    <span class="summary-value">${s.excused}</span>
                </div>
            `;
            
            if (data.students.length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;"><i class="fas fa-users-slash fa-2x"></i><p>No enrolled students / لا يوجد طلاب مسجلين</p></div>';
                return;
            }
            
            container.innerHTML = `
                <table class="attendance-table">
                    <thead>
                        <tr>
                            <th style="width: 50px;">#</th>
                            <th>Student Name / اسم الطالب</th>
                            <th style="width: 180px;">Status / الحالة</th>
                            <th>Notes / ملاحظات</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.students.map((student, index) => `
                        <tr data-student-id="${student.id}">
                            <td>${index + 1}</td>
                            <td>
                                <div style="font-weight: 500;">${this.escapeHtml(student.full_name)}</div>
                                <div style="font-size: 12px; color: #666; direction: rtl;">${this.escapeHtml(student.full_name_ar || '')}</div>
                            </td>
                            <td>
                                <select class="attendance-status form-control" data-student-id="${student.id}" onchange="teacherDashboard.updateAttendanceSummary()">
                                    <option value="present" ${student.status === 'present' ? 'selected' : ''}>✓ Present / حاضر</option>
                                    <option value="absent" ${student.status === 'absent' ? 'selected' : ''}>✗ Absent / غائب</option>
                                    <option value="late" ${student.status === 'late' ? 'selected' : ''}>⏰ Late / متأخر</option>
                                    <option value="excused" ${student.status === 'excused' ? 'selected' : ''}>📋 Excused / معذور</option>
                                </select>
                            </td>
                            <td>
                                <input type="text" class="attendance-notes form-control" data-student-id="${student.id}" 
                                    value="${this.escapeHtml(student.notes || '')}" placeholder="Notes / ملاحظات">
                            </td>
                        </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            
        } catch (error) {
            console.error('Load attendance error:', error);
            container.innerHTML = `<div style="text-align: center; padding: 40px; color: #ef4444;"><i class="fas fa-exclamation-triangle fa-2x"></i><p>${error.message}</p></div>`;
        }
    }

    markAllPresent() {
        const selects = document.querySelectorAll('#courseAttendanceList .attendance-status');
        selects.forEach(select => {
            select.value = 'present';
        });
        this.updateAttendanceSummary();
    }

    updateAttendanceSummary() {
        const selects = document.querySelectorAll('#courseAttendanceList .attendance-status');
        const counts = { present: 0, absent: 0, late: 0, excused: 0, total: selects.length };
        
        selects.forEach(select => {
            counts[select.value] = (counts[select.value] || 0) + 1;
        });
        
        const summaryDiv = document.getElementById('attendanceSummary');
        if (summaryDiv) {
            summaryDiv.innerHTML = `
                <div class="summary-item">
                    <span class="summary-label">Total / الإجمالي:</span>
                    <span class="summary-value">${counts.total}</span>
                </div>
                <div class="summary-item present">
                    <span class="summary-label">Present / حاضر:</span>
                    <span class="summary-value">${counts.present}</span>
                </div>
                <div class="summary-item absent">
                    <span class="summary-label">Absent / غائب:</span>
                    <span class="summary-value">${counts.absent}</span>
                </div>
                <div class="summary-item late">
                    <span class="summary-label">Late / متأخر:</span>
                    <span class="summary-value">${counts.late}</span>
                </div>
                <div class="summary-item excused">
                    <span class="summary-label">Excused / معذور:</span>
                    <span class="summary-value">${counts.excused}</span>
                </div>
            `;
        }
    }

    async saveAttendance() {
        if (!this.currentCourse) {
            alert('Please select a course first');
            return;
        }

        const dateInput = document.getElementById('teacherAttendanceDate');
        if (!dateInput.value) {
            alert('Please select a date');
            return;
        }

        const records = [];
        const rows = document.querySelectorAll('#courseAttendanceList tbody tr[data-student-id]');
        
        rows.forEach(row => {
            const studentId = row.dataset.studentId;
            const statusSelect = row.querySelector('.attendance-status');
            const notesInput = row.querySelector('.attendance-notes');
            
            records.push({
                student_id: studentId,
                status: statusSelect ? statusSelect.value : 'present',
                notes: notesInput ? notesInput.value : ''
            });
        });
        
        if (records.length === 0) {
            alert('No attendance records to save');
            return;
        }
        
        try {
            const response = await fetch(`/api/attendance/class/${this.currentCourse.id}/date/${dateInput.value}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ records })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to save attendance');
            }
            
            alert(`Attendance saved successfully!\n${data.created} new records, ${data.updated} updated\n\nتم حفظ الحضور بنجاح`);
            
        } catch (error) {
            console.error('Save attendance error:', error);
            alert('Error saving attendance: ' + error.message);
        }
    }

    async printAttendance() {
        if (!this.currentCourse) {
            alert('Please select a course first');
            return;
        }

        const dateInput = document.getElementById('teacherAttendanceDate');
        if (!dateInput.value) {
            dateInput.value = new Date().toISOString().split('T')[0];
        }

        try {
            const response = await fetch(`/api/attendance/class/${this.currentCourse.id}/print/${dateInput.value}`, {
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to get print data');
            }
            
            const printData = data.print_data;
            const printWindow = window.open('', '_blank', 'width=800,height=600');
            
            printWindow.document.write(`
<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <title>Attendance List - ${printData.course.title}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Arial', 'Segoe UI', sans-serif; padding: 20px; color: #333; line-height: 1.4; }
        .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #1B5E20; padding-bottom: 15px; }
        .logos { display: flex; justify-content: center; gap: 40px; margin-bottom: 15px; }
        .logos img { height: 60px; }
        .app-name { font-size: 18px; font-weight: bold; color: #1B5E20; margin-bottom: 5px; }
        .doc-title { font-size: 22px; font-weight: bold; margin: 10px 0; color: #333; }
        .doc-title-ar { font-size: 20px; font-weight: bold; direction: rtl; }
        .course-info { margin: 15px 0; font-size: 14px; }
        .course-info strong { color: #1B5E20; }
        .date-info { font-size: 14px; color: #555; margin: 10px 0; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 12px; }
        th, td { border: 1px solid #ddd; padding: 10px 8px; text-align: left; }
        th { background-color: #1B5E20; color: white; font-weight: bold; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .status-present { color: #2e7d32; font-weight: bold; }
        .status-absent { color: #c62828; font-weight: bold; }
        .status-late { color: #f57c00; font-weight: bold; }
        .status-excused { color: #1565c0; font-weight: bold; }
        .summary { display: flex; justify-content: space-around; margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; }
        .summary-item { text-align: center; }
        .summary-label { font-size: 12px; color: #666; }
        .summary-value { font-size: 20px; font-weight: bold; display: block; }
        .summary-item.present .summary-value { color: #2e7d32; }
        .summary-item.absent .summary-value { color: #c62828; }
        .summary-item.late .summary-value { color: #f57c00; }
        .summary-item.excused .summary-value { color: #1565c0; }
        .footer { margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 11px; color: #666; display: flex; justify-content: space-between; }
        .signature-area { margin-top: 40px; display: flex; justify-content: space-between; }
        .signature-box { width: 200px; text-align: center; }
        .signature-line { border-top: 1px solid #333; margin-top: 40px; padding-top: 5px; font-size: 12px; }
        @media print { body { padding: 10px; } .no-print { display: none; } }
    </style>
</head>
<body>
    <div class="header">
        <div class="app-name">SkillPilot</div>
        <div class="doc-title">Daily Attendance List</div>
        <div class="doc-title-ar">قائمة الحضور اليومي</div>
    </div>
    
    <div class="course-info">
        <strong>Course / المقرر:</strong> ${printData.course.code ? `[${printData.course.code}]` : ''} ${printData.course.title}
        ${printData.course.title_ar ? ` / ${printData.course.title_ar}` : ''}
    </div>
    
    <div class="date-info">
        <strong>Date / التاريخ:</strong> ${printData.date_formatted}
    </div>
    
    <div class="summary">
        <div class="summary-item">
            <span class="summary-label">Total / الإجمالي</span>
            <span class="summary-value">${printData.summary.total}</span>
        </div>
        <div class="summary-item present">
            <span class="summary-label">Present / حاضر</span>
            <span class="summary-value">${printData.summary.present}</span>
        </div>
        <div class="summary-item absent">
            <span class="summary-label">Absent / غائب</span>
            <span class="summary-value">${printData.summary.absent}</span>
        </div>
        <div class="summary-item late">
            <span class="summary-label">Late / متأخر</span>
            <span class="summary-value">${printData.summary.late}</span>
        </div>
        <div class="summary-item excused">
            <span class="summary-label">Excused / معذور</span>
            <span class="summary-value">${printData.summary.excused}</span>
        </div>
    </div>
    
    <table>
        <thead>
            <tr>
                <th style="width: 40px;">#</th>
                <th>Student Name / اسم الطالب</th>
                <th style="width: 120px;">Status / الحالة</th>
                <th>Notes / ملاحظات</th>
            </tr>
        </thead>
        <tbody>
            ${printData.students.map(s => `
            <tr>
                <td>${s.seq}</td>
                <td>${s.full_name}${s.full_name_ar ? ` / ${s.full_name_ar}` : ''}</td>
                <td class="status-${s.status}">${s.status_display}</td>
                <td>${s.notes || ''}</td>
            </tr>
            `).join('')}
        </tbody>
    </table>
    
    <div class="signature-area">
        <div class="signature-box">
            <div class="signature-line">Instructor Signature / توقيع المدرب</div>
        </div>
        <div class="signature-box">
            <div class="signature-line">Admin Signature / توقيع المسؤول</div>
        </div>
    </div>
    
    <div class="footer">
        <span>Generated: ${printData.generated_at}</span>
        <span>SkillPilot Learning Platform</span>
    </div>
    
    <script>window.onload = function() { window.print(); };</script>
</body>
</html>
            `);
            
            printWindow.document.close();
            
        } catch (error) {
            console.error('Print attendance error:', error);
            alert('Error printing attendance: ' + error.message);
        }
    }
}

const teacherDashboard = new TeacherDashboard();

document.addEventListener('DOMContentLoaded', () => {
    if (window.app && window.app.loadTabData) {
        const originalLoadTabData = window.app.loadTabData.bind(window.app);
        window.app.loadTabData = function(tabName) {
            originalLoadTabData(tabName);
            if (tabName === 'teacher-dashboard') {
                teacherDashboard.init();
            }
        };
    }
});
