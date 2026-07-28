import requests
import uuid

BASE_URL = "http://localhost:8000"

def test_health():
    print("Testing /health endpoint...")
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}
    print("Health check OK!")

def test_auth_flow():
    print("Testing auth flow (registration and login)...")
    email = f"testuser_{uuid.uuid4().hex[:6]}@example.com"
    password = "testpassword123"
    name = "Test Student"
    
    # 1. Register user
    reg_payload = {
        "name": name,
        "email": email,
        "password": password,
        "role": "student"
    }
    resp = requests.post(f"{BASE_URL}/auth/register", json=reg_payload)
    assert resp.status_code == 201, f"Reg failed: {resp.text}"
    reg_data = resp.json()
    assert "access_token" in reg_data
    assert reg_data["name"] == name
    assert reg_data["role"] == "student"
    token = reg_data["access_token"]
    user_id = reg_data["user_id"]
    print(f"Registration OK! user_id={user_id}")
    
    # 2. Login user
    login_payload = {
        "email": email,
        "password": password
    }
    resp = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    login_data = resp.json()
    assert "access_token" in login_data
    assert login_data["user_id"] == user_id
    token = login_data["access_token"] # Use the new token for subsequent requests
    print("Login OK!")
    
    # 3. Get /me endpoint with token
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    assert resp.status_code == 200, f"Get /me failed: {resp.text}"
    me_data = resp.json()
    assert me_data["id"] == user_id
    assert me_data["email"] == email
    print("/auth/me OK!")

    # 4. Get student dashboard
    resp = requests.get(f"{BASE_URL}/api/students/{user_id}/dashboard", headers=headers)
    assert resp.status_code == 200, f"Get student dashboard failed: {resp.text}"
    student_dash = resp.json()
    assert "mastery_score" in student_dash
    assert "current_streak" in student_dash
    print("Student dashboard endpoint OK!")

    # 5. Try accessing faculty dashboard as student (should fail with 403)
    resp = requests.get(f"{BASE_URL}/api/faculty/dashboard", headers=headers)
    assert resp.status_code == 403, f"Expected 403 for student accessing faculty dashboard, got: {resp.status_code}"
    print("Faculty dashboard protection OK!")

    # 6. List courses as student
    resp = requests.get(f"{BASE_URL}/api/courses", headers=headers)
    assert resp.status_code == 200, f"List courses failed: {resp.text}"
    assert isinstance(resp.json(), list)
    print("List courses as student OK!")

    # 7. Register a teacher and verify faculty dashboard
    teacher_email = f"teacher_{uuid.uuid4().hex[:6]}@example.com"
    teacher_payload = {
        "name": "Test Teacher",
        "email": teacher_email,
        "password": "teacherpassword123",
        "role": "teacher"
    }
    resp = requests.post(f"{BASE_URL}/auth/register", json=teacher_payload)
    assert resp.status_code == 201, f"Teacher registration failed: {resp.text}"
    teacher_token = resp.json()["access_token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

    resp = requests.get(f"{BASE_URL}/api/faculty/dashboard", headers=teacher_headers)
    assert resp.status_code == 200, f"Get faculty dashboard failed: {resp.text}"
    faculty_dash = resp.json()
    assert "class_avg_mastery" in faculty_dash
    assert "total_students" in faculty_dash
    print("Faculty dashboard endpoint OK!")

    # 8. List courses as teacher
    resp = requests.get(f"{BASE_URL}/api/courses", headers=teacher_headers)
    assert resp.status_code == 200, f"List courses failed: {resp.text}"
    assert isinstance(resp.json(), list)
    print("List courses as teacher OK!")

if __name__ == "__main__":
    test_health()
    test_auth_flow()
    print("All API integration tests passed successfully!")
