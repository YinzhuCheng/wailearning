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

# 测试 semesters API
response = requests.get(f"{BASE_URL}/semesters", headers=headers)
print(f"\nSemesters API: {response.status_code}")
if response.status_code != 200:
    print(f"错误: {response.text[:500]}")
else:
    print(f"成功: {response.json()}")

# 测试 dashboard stats API
response = requests.get(f"{BASE_URL}/dashboard/stats", headers=headers)
print(f"\nDashboard Stats API: {response.status_code}")
if response.status_code != 200:
    print(f"错误: {response.text[:500]}")
else:
    print(f"成功: {response.json()}")
