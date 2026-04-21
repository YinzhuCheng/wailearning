# 家长端口 - BIMSA-CLASS

家长端口是 BIMSA-CLASS 教学管理系统的子项目，供家长通过家长码查看孩子相关信息。

## 功能特点

- ✅ **家长码绑定**：通过 8 位家长码快速绑定学生
- ✅ **成绩查询**：查看学生各科目成绩和排名
- ✅ **班级通知**：查看班级和学校通知
- ✅ **作业查看**：查看班级作业和截止日期
- ✅ **数据统计**：查看平均成绩、出勤率等统计
- ✅ **前端本地绑定态**：绑定后在浏览器本地保存 `parent_code`、学生与班级信息

## 技术栈

- **框架**: Vue.js 3
- **构建工具**: Vite
- **UI组件**: Element Plus
- **HTTP客户端**: Axios

## 快速开始

### 1. 安装依赖

```bash
cd parent-portal
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5174

### 3. 配置后端API

修改 `vite.config.js` 中的 proxy 配置：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://your-backend-server:8001',  // 修改为你的后端地址
      changeOrigin: true
    }
  }
}
```

## 使用说明

### 家长码获取与使用说明

家长码由教师或班主任在后台为学生生成，默认有效期为 365 天。

注意：

- 家长端当前采用“家长码即绑定凭证”的轻量模式
- 前端会先调用 `/api/parent/verify/{code}` 验证，再调用 `/api/parent/student/{code}` 获取学生基础信息
- 后端当前不会在学生信息接口中回显家长码本身

### 页面说明

1. **登录页**：输入家长码进行绑定
2. **首页**：查看统计数据和最近成绩
3. **成绩页**：按学期筛选查看成绩
4. **通知页**：查看班级通知
5. **作业页**：查看班级作业

## 项目结构

```
parent-portal/
├── src/
│   ├── api/
│   │   └── index.js        # API 请求封装
│   ├── router/
│   │   └── index.js        # 路由配置
│   ├── views/
│   │   ├── Login.vue       # 登录页
│   │   ├── Home.vue        # 首页
│   │   ├── Scores.vue      # 成绩页
│   │   ├── Notifications.vue # 通知页
│   │   └── Homework.vue    # 作业页
│   ├── App.vue             # 根组件
│   └── main.js             # 入口文件
├── index.html
├── package.json
└── vite.config.js
```

## API 接口（当前实现）

后端 API 需要实现以下接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/parent/verify/{code}` | GET | 验证家长码并返回学生姓名、班级名称 |
| `/api/parent/student/{code}` | GET | 获取学生基础信息（不回显家长码） |
| `/api/parent/scores/{code}` | GET | 获取成绩列表 |
| `/api/parent/notifications/{code}` | GET | 获取通知列表 |
| `/api/parent/homework/{code}` | GET | 获取作业列表 |
| `/api/parent/stats/{code}` | GET | 获取统计数据 |

详细 API 文档请参考主项目 README 与后端 Swagger 文档。
