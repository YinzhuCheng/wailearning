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

# 测试班级API
response = requests.get(f"{BASE_URL}/classes", headers=headers)
print(f"班级API状态: {response.status_code}")
if response.status_code == 200:
    print(f"班级数据: {response.json()[:2]}")
else:
    print(f"班级API错误: {response.text[:200]}")

# 测试用户API
response = requests.get(f"{BASE_URL}/users", headers=headers)
print(f"\n用户API状态: {response.status_code}")
if response.status_code == 200:
    print(f"用户数据: {response.json()[:2]}")
else:
    print(f"用户API错误: {response.text[:200]}")
