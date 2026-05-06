import requests

BASE_URL = "http://localhost:8001/api"

response = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "admin", "password": "admin123"}
)
print(f"✅ 登录状态: {response.status_code}")
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("\n1. 测试积分统计:")
response = requests.get(f"{BASE_URL}/points/stats", headers=headers)
print(f"   状态: {response.status_code}")
if response.status_code == 200:
    stats = response.json()
    print(f"   学生总数: {stats['total_students']}")
    print(f"   活跃学生: {stats['active_students']}")
    print(f"   发放积分: {stats['total_points_distributed']}")
    print(f"   兑换积分: {stats['total_points_exchanged']}")

print("\n2. 测试积分规则:")
response = requests.get(f"{BASE_URL}/points/rules", headers=headers)
print(f"   状态: {response.status_code}")
if response.status_code == 200:
    rules = response.json()
    print(f"   规则数量: {len(rules)}")
    for rule in rules[:3]:
        print(f"   - {rule['name']}: {rule['points']}分")

print("\n3. 测试积分商品:")
response = requests.get(f"{BASE_URL}/points/items", headers=headers)
print(f"   状态: {response.status_code}")
if response.status_code == 200:
    items = response.json()
    print(f"   商品数量: {len(items)}")
    for item in items[:3]:
        print(f"   - {item['name']}: {item['points_cost']}积分 ({item['item_type']})")

print("\n4. 测试积分排行:")
response = requests.get(f"{BASE_URL}/points/ranking?limit=5", headers=headers)
print(f"   状态: {response.status_code}")
if response.status_code == 200:
    ranking = response.json()
    print(f"   前5名:")
    for i, r in enumerate(ranking):
        print(f"   {i+1}. {r['student_name']} - {r['total_points']}积分 ({r['class_name']})")

print("\n✅ 积分系统API测试完成!")
