import requests

BASE_URL = "http://localhost:8001/api"

# 登录
response = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "admin", "password": "admin123"}
)
print(f"✅ 登录状态: {response.status_code}")
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 1. 测试获取日志列表
response = requests.get(f"{BASE_URL}/logs", headers=headers)
print(f"\n1. 获取日志列表: {response.status_code}")
if response.status_code == 200:
    logs_data = response.json()
    print(f"   总日志数: {logs_data['total']}")
    for log in logs_data['data'][:3]:
        print(f"   - [{log['action']}] {log['target_type']}: {log['username']} - {log['details']}")

# 2. 测试日志统计
response = requests.get(f"{BASE_URL}/logs/stats/summary", headers=headers)
print(f"\n2. 日志统计: {response.status_code}")
if response.status_code == 200:
    stats = response.json()
    print(f"   今日日志: {stats['today']}")
    print(f"   总日志数: {stats['total']}")

# 3. 测试筛选
response = requests.get(f"{BASE_URL}/logs?action=登录", headers=headers)
print(f"\n3. 筛选登录日志: {response.status_code}")
if response.status_code == 200:
    logs_data = response.json()
    print(f"   登录日志数: {logs_data['total']}")

print("\n✅ 日志API测试完成！")
