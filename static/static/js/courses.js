/**
 * Courses Module
 * Handles course enrollment, payment, and role-based UI rendering
 */

class CoursesManager {
    constructor() {
        this.enrolledCourseTypes = new Set();
        this.initialized = false;
    }

    /**
     * Initialize courses manager
     */
    async init() {
        if (this.initialized) return;
        
        console.log('Initializing Courses Manager...');
        await this.loadUserCourseTypes();
        await this.applyRoleBasedUI();
        this.initialized = true;
    }

    /**
     * Load user's enrolled course types
     */
    async loadUserCourseTypes() {
        try {
            const response = await fetch('/api/classes/user-course-types', {
                credentials: 'include'
            });

            if (!response.ok) {
                // Handle auth errors gracefully - user might not be logged in yet
                if (response.status === 401 || response.status === 500) {
                    console.log('User not authenticated or error fetching course types');
                    this.enrolledCourseTypes = new Set();
                    return this.enrolledCourseTypes;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.enrolledCourseTypes = new Set(data.course_types || []);
            console.log('Enrolled course types:', Array.from(this.enrolledCourseTypes));
            
            return this.enrolledCourseTypes;
        } catch (error) {
            console.log('Could not load course types (user may not be logged in):', error.message);
            this.enrolledCourseTypes = new Set();
            return this.enrolledCourseTypes;
        }
    }

    /**
     * Apply role-based UI rendering based on enrolled course types
     */
    async applyRoleBasedUI() {
        // Course type to menu items mapping
        const courseFeatures = {
            'prompt_engineering': [
                'chat',
                'library',
                'survey',
                'exit-exam',
                'exit-survey',
                'my-certificates',
                'course-materials'
            ],
            'ethics_certificate': [
                'ethics-certificate'
            ],
            'agentic_ai': [
                'agentic-ai-lab'
            ]
        };

        // Get all menu items
        const menuItems = document.querySelectorAll('.right-side-menu .menu-item');

        menuItems.forEach(menuItem => {
            const tab = menuItem.getAttribute('data-tab');
            
            // Skip non-student-specific items (admin, profile, etc.)
            if (!menuItem.classList.contains('student-only')) {
                return;
            }

            // Always show my-courses and my-classes tabs for students
            if (tab === 'my-courses' || tab === 'my-classes') {
                menuItem.style.display = '';
                return;
            }

            // Check if this feature belongs to any enrolled course type
            let hasAccess = false;
            
            for (const courseType of this.enrolledCourseTypes) {
                const features = courseFeatures[courseType] || [];
                if (features.includes(tab)) {
                    hasAccess = true;
                    break;
                }
            }

            // Show/hide menu item
            if (hasAccess) {
                menuItem.style.display = '';
            } else {
                menuItem.style.display = 'none';
            }
        });

        // Special handling for Ethics Certificate - check access
        if (this.enrolledCourseTypes.has('ethics_certificate')) {
            await this.checkEthicsAccess();
        }
    }

    /**
     * Check if user has access to Ethics Certificate
     */
    async checkEthicsAccess() {
        try {
            const response = await fetch('/api/ethics/check-access', {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            const ethicsMenuItem = document.querySelector('.menu-item[data-tab="ethics-certificate"]');
            if (ethicsMenuItem) {
                if (data.has_access) {
                    ethicsMenuItem.style.display = '';
                } else {
                    ethicsMenuItem.style.display = 'none';
                    console.log('Ethics Certificate access denied:', data.reason);
                }
            }
        } catch (error) {
            console.error('Error checking ethics access:', error);
        }
    }

    /**
     * Enroll in a course
     */
    async enrollInCourse(classId) {
        try {
            const response = await fetch('/api/classes/enroll', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ class_id: classId })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Enrollment failed');
            }

            return data;
        } catch (error) {
            console.error('Error enrolling in course:', error);
            throw error;
        }
    }

    /**
     * Refresh UI after enrollment
     */
    async refreshAfterEnrollment() {
        await this.loadUserCourseTypes();
        await this.applyRoleBasedUI();
        
        // Reload classes if on that tab
        if (window.app && typeof window.app.loadMyClasses === 'function') {
            await window.app.loadMyClasses();
        }
    }
}

// Initialize global instance
window.coursesManager = new CoursesManager();
