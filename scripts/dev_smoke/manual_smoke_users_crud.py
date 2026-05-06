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

# 1. 测试获取用户列表
response = requests.get(f"{BASE_URL}/users", headers=headers)
print(f"\n1. 获取用户列表: {response.status_code}")
for user in response.json():
    print(f"   - {user['username']}: {user['role']} (班级: {user['class_id']})")

# 2. 测试创建管理员
response = requests.post(
    f"{BASE_URL}/users",
    headers=headers,
    json={
        "username": "new_admin",
        "password": "test123456",
        "real_name": "新管理员",
        "role": "admin",
        "class_id": None
    }
)
print(f"\n2. 创建管理员: {response.status_code} - {response.json().get('username', '失败')}")

# 3. 测试创建任课教师
response = requests.post(
    f"{BASE_URL}/users",
    headers=headers,
    json={
        "username": "new_teacher",
        "password": "test123456",
        "real_name": "新任课教师",
        "role": "teacher",
        "class_id": 1
    }
)
print(f"3. 创建任课教师: {response.status_code} - {response.json().get('username', '失败')}")

# 4. 测试创建班主任
response = requests.post(
    f"{BASE_URL}/users",
    headers=headers,
    json={
        "username": "new_ct",
        "password": "test123456",
        "real_name": "新班主任",
        "role": "class_teacher",
        "class_id": 2
    }
)
print(f"4. 创建班主任: {response.status_code} - {response.json().get('username', '失败')}")

# 5. 测试修改用户
response = requests.put(
    f"{BASE_URL}/users/4",
    headers=headers,
    json={
        "real_name": "测试班主任（已修改）"
    }
)
print(f"5. 修改用户: {response.status_code} - {response.json().get('real_name', '失败')}")

# 6. 验证所有用户
response = requests.get(f"{BASE_URL}/users", headers=headers)
print(f"\n6. 最终用户列表:")
for user in response.json():
    print(f"   - {user['username']}: {user['role']} - {user['real_name']} (班级: {user['class_id']})")

print("\n✅ 所有测试完成！")
