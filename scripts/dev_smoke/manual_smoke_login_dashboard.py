import requests
import json

BASE_URL = "http://localhost:8001"

def smoke_login():
    print("=" * 60)
    print("1. 测试登录")
    print("=" * 60)
    
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"✓ 登录成功，获取到token: {token[:20]}...")
            return token
        else:
            print(f"✗ 登录失败: {response.status_code} - {response.text[:200]}")
            print(f"请求头: {response.request.headers}")
            return None
    except Exception as e:
        print(f"✗ 登录请求失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def smoke_semesters(token):
    print("\n" + "=" * 60)
    print("2. 测试获取学期列表")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/api/semesters", headers=headers)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            semesters = response.json()
            print(f"✓ 成功获取 {len(semesters)} 个学期:")
            for s in semesters:
                print(f"  - {s.get('name')} (年份: {s.get('year')})")
            return semesters
        else:
            print(f"✗ 获取学期失败: {response.text}")
            return []
    except Exception as e:
        print(f"✗ 获取学期请求失败: {e}")
        return []

def smoke_dashboard(token, semester=''):
    print("\n" + "=" * 60)
    print(f"3. 测试Dashboard API (semester='{semester}')")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    params = {"semester": semester} if semester else {}
    
    try:
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers, params=params)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            stats = response.json()
            print("✓ Dashboard数据加载成功:")
            print(f"  - 学生总数: {stats.get('total_students')}")
            print(f"  - 班级数量: {stats.get('total_classes')}")
            print(f"  - 成绩记录: {stats.get('total_scores')}")
            print(f"  - 平均成绩: {stats.get('avg_score')}")
            print(f"  - 考勤率: {stats.get('attendance_rate')}%")
            return True
        else:
            print(f"✗ Dashboard加载失败: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Dashboard请求失败: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("班级管理系统 API 测试")
    print("=" * 60)
    
    # 测试登录
    token = smoke_login()
    if not token:
        print("\n✗ 登录失败，停止测试")
        return
    
    # 测试获取学期
    semesters = smoke_semesters(token)
    
    # 测试Dashboard (不指定学期)
    smoke_dashboard(token)
    
    # 测试Dashboard (指定学期)
    if semesters:
        first_semester = semesters[0].get('name')
        smoke_dashboard(token, first_semester)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
