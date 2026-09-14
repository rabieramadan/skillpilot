/**
 * Student Courses Module
 * Handles course browsing, preview, and enrollment for students
 */

class StudentCoursesManager {
    constructor() {
        this.enrolledCourses = [];
        this.availableCourses = [];
    }

    /**
     * Initialize student courses page
     */
    async init() {
        console.log('Initializing Student Courses Manager...');
        await this.loadCourses();
    }

    /**
     * Load enrolled and available courses
     */
    async loadCourses() {
        try {
            const response = await fetch('/api/classes/my-courses', {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.enrolledCourses = data.enrolled_courses || [];
            this.availableCourses = data.available_courses || [];

            this.renderEnrolledCourses();
            this.renderAvailableCourses();
            
        } catch (error) {
            console.error('Error loading courses:', error);
            this.showErrorMessage('Failed to load courses');
        }
    }

    /**
     * Render enrolled courses
     */
    renderEnrolledCourses() {
        const container = document.getElementById('studentEnrolledCourses');
        if (!container) return;

        if (this.enrolledCourses.length === 0) {
            container.innerHTML = `
                <p style="text-align: center; color: #999; padding: 40px;">
                    <i class="fas fa-info-circle"></i> You haven't enrolled in any courses yet. Browse available courses below to get started!
                </p>
            `;
            return;
        }

        container.innerHTML = this.enrolledCourses.map(course => this.renderCourseCard(course, true)).join('');
    }

    /**
     * Render available courses
     */
    renderAvailableCourses() {
        const container = document.getElementById('studentAvailableCourses');
        if (!container) return;

        if (this.availableCourses.length === 0) {
            container.innerHTML = `
                <p style="text-align: center; color: #999; padding: 40px;">
                    <i class="fas fa-check-circle"></i> You're enrolled in all available courses!
                </p>
            `;
            return;
        }

        container.innerHTML = this.availableCourses.map(course => this.renderCourseCard(course, false)).join('');
    }

    /**
     * Render a course card with preview
     */
    renderCourseCard(course, isEnrolled) {
        const courseTypeLabels = {
            'prompt_engineering': 'Prompt Engineering',
            'ethics_certificate': 'Ethics Certificate',
            'agentic_ai': 'Agentic AI'
        };

        const courseTypeColors = {
            'prompt_engineering': '#3498db',
            'ethics_certificate': '#e74c3c',
            'agentic_ai': '#9b59b6'
        };

        const courseType = course.course_type || 'prompt_engineering';
        const typeName = courseTypeLabels[courseType] || courseType;
        const typeColor = courseTypeColors[courseType] || '#95a5a6';

        // Course image (use preview_image or default)
        const imageUrl = course.preview_image || '/static/images/default-course.png';
        
        // Payment status
        const isFree = course.is_free !== false;
        const price = course.price || 0;
        
        return `
            <div class="course-preview-card" data-testid="course-card-${course.class_id}">
                <!-- Course Image -->
                <div class="course-image" style="background-image: url('${imageUrl}');">
                    <div class="course-type-badge" style="background: ${typeColor};">
                        ${typeName}
                    </div>
                    ${isFree ? 
                        '<div class="course-price-badge" style="background: #27ae60;">FREE</div>' : 
                        `<div class="course-price-badge" style="background: #e74c3c;">${price} OMR</div>`
                    }
                </div>
                
                <!-- Course Info -->
                <div class="course-info">
                    <h3 class="course-title">${course.title}</h3>
                    <p class="course-description">
                        ${course.preview_description || course.description || 'No description available'}
                    </p>
                    
                    <!-- Course Details -->
                    <div class="course-details">
                        <div class="course-detail-item">
                            <i class="fas fa-calendar"></i>
                            <span>${course.semester || 'N/A'}</span>
                        </div>
                        ${course.schedule ? `
                            <div class="course-detail-item">
                                <i class="fas fa-clock"></i>
                                <span>${course.schedule}</span>
                            </div>
                        ` : ''}
                    </div>
                    
                    <!-- Course Contents (TOC) -->
                    ${course.preview_toc ? `
                        <div class="course-toc">
                            <h4><i class="fas fa-list"></i> What You'll Learn:</h4>
                            <div class="course-toc-content">
                                ${course.preview_toc}
                            </div>
                        </div>
                    ` : ''}
                    
                    <!-- Action Button -->
                    <div class="course-actions">
                        ${isEnrolled ? 
                            `<button class="btn-success" disabled data-testid="button-enrolled-${course.class_id}">
                                <i class="fas fa-check-circle"></i> Enrolled
                            </button>` :
                            `<button class="btn-primary" onclick="window.studentCoursesManager.enrollInCourse('${course.class_id}', ${!isFree})" data-testid="button-enroll-${course.class_id}">
                                <i class="fas fa-plus-circle"></i> ${isFree ? 'Enroll Now' : 'Enroll (Payment Required)'}
                            </button>`
                        }
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Enroll in a course
     */
    async enrollInCourse(classId, requiresPayment) {
        if (!confirm(`Are you sure you want to enroll in this course?${requiresPayment ? '\n\nThis is a paid course. You will need to make a payment to AIAC@unizwa.edu.om and wait for admin verification.' : ''}`)) {
            return;
        }

        try {
            const response = await fetch('/api/classes/enroll', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    class_id: classId
                })
            });

            const data = await response.json();

            if (response.ok) {
                if (requiresPayment) {
                    alert(`Enrollment request submitted!\n\nPlease make your payment to: AIAC@unizwa.edu.om\nAmount: ${data.amount || 'See course details'}\n\nOnce payment is verified by an administrator, you will gain access to the course.`);
                } else {
                    alert('Successfully enrolled in the course!');
                }
                
                // Reload courses
                await this.loadCourses();
                
                // Refresh course types for role-based UI
                if (window.coursesManager) {
                    await window.coursesManager.loadUserCourseTypes();
                    await window.coursesManager.applyRoleBasedUI();
                }
            } else {
                alert(data.error || 'Failed to enroll in course');
            }
            
        } catch (error) {
            console.error('Error enrolling in course:', error);
            alert('Error enrolling in course. Please try again.');
        }
    }

    /**
     * Show error message
     */
    showErrorMessage(message) {
        const containers = [
            document.getElementById('studentEnrolledCourses'),
            document.getElementById('studentAvailableCourses')
        ];

        containers.forEach(container => {
            if (container) {
                container.innerHTML = `
                    <p style="text-align: center; color: #e74c3c; padding: 40px;">
                        <i class="fas fa-exclamation-triangle"></i> ${message}
                    </p>
                `;
            }
        });
    }
}

// Create global instance
window.studentCoursesManager = new StudentCoursesManager();
