import requests

BASE_URL = "http://localhost:8001/api"

# 登录
response = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "admin", "password": "admin123"}
)
print(f"登录状态: {response.status_code}")
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 测试创建班主任
response = requests.post(
    f"{BASE_URL}/users",
    headers=headers,
    json={
        "username": "test_teacher2",
        "password": "test123456",
        "real_name": "测试班主任2",
        "role": "class_teacher",  # 前端发送的值
        "class_id": 1
    }
)
print(f"\n创建班主任状态: {response.status_code}")
print(f"响应内容: {response.text[:500]}")
