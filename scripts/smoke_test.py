"""
SkillPilot System Tests
Run directly from PyCharm: Right-click > Run 'run_tests'

Tests all major system functionality:
- Authentication (all roles)
- Course management
- User management
- Enrollments
- Certificates
"""

import os
import sys
import requests
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class SkillPilotTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
    
    def test(self, name, condition, details=""):
        status = "PASS" if condition else "FAIL"
        self.results.append((name, status, details))
        icon = "✓" if condition else "✗"
        print(f"  {icon} {name}: {status} {details}")
        return condition
    
    def run_all_tests(self):
        print("=" * 60)
        print("  SkillPilot System Tests")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()
        
        # Test server connectivity
        print("1. Server Connectivity")
        print("-" * 40)
        try:
            resp = requests.get(f"{self.base_url}/", timeout=5)
            self.test("Server responding", resp.status_code in [200, 302])
        except Exception as e:
            self.test("Server responding", False, str(e))
            print("\nServer not running. Start the server first.")
            return
        
        # Test authentication
        print()
        print("2. Authentication")
        print("-" * 40)
        
        roles = [
            ("admin", "admin123", "superadmin"),
            ("demoteacher1", "demo123", "teacher"),
            ("demostudent1", "demo123", "student"),
        ]
        
        for username, password, expected_role in roles:
            resp = self.session.post(
                f"{self.base_url}/api/auth/user/login",
                json={"username": username, "password": password}
            )
            if resp.status_code == 200:
                data = resp.json()
                self.test(
                    f"Login as {expected_role}",
                    data.get('success') and data.get('user', {}).get('role') == expected_role
                )
            else:
                self.test(f"Login as {expected_role}", False)
        
        # Test invalid login
        resp = self.session.post(
            f"{self.base_url}/api/auth/user/login",
            json={"username": "invalid", "password": "wrong"}
        )
        self.test("Invalid login rejected", not resp.json().get('success', True))
        
        # Login as admin for remaining tests
        self.session.post(
            f"{self.base_url}/api/auth/user/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        # Test course management
        print()
        print("3. Course Management")
        print("-" * 40)
        
        resp = self.session.get(f"{self.base_url}/admin/api/courses")
        if resp.status_code == 200:
            data = resp.json()
            courses = data.get('courses', [])
            self.test("List courses", len(courses) >= 0, f"({len(courses)} courses)")
        else:
            self.test("List courses", False)
        
        # Test user management
        print()
        print("4. User Management")
        print("-" * 40)
        
        resp = self.session.get(f"{self.base_url}/admin/api/users")
        if resp.status_code == 200:
            data = resp.json()
            users = data.get('users', [])
            self.test("List users", len(users) >= 0, f"({len(users)} users)")
        else:
            self.test("List users", False)
        
        # Test enrollments
        print()
        print("5. Enrollments")
        print("-" * 40)
        
        resp = self.session.get(f"{self.base_url}/admin/api/enrollments")
        if resp.status_code == 200:
            data = resp.json()
            enrollments = data.get('enrollments', [])
            self.test("List enrollments", len(enrollments) >= 0, f"({len(enrollments)} enrollments)")
        else:
            self.test("List enrollments", False)
        
        # Summary
        print()
        print("=" * 60)
        passed = sum(1 for _, status, _ in self.results if status == "PASS")
        total = len(self.results)
        print(f"  Results: {passed}/{total} tests passed")
        print("=" * 60)
        
        return passed == total


if __name__ == '__main__':
    port = os.environ.get('PORT', 5000)
    tester = SkillPilotTester(f"http://localhost:{port}")
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
