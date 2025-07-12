# MediaCrawler API 实时搜索服务

为Next-GenAI项目提供小红书实时搜索和数据爬取的API服务。

## 项目架构

### 核心文件说明

#### `api_server.py` - API服务主程序
**作用**: FastAPI服务器，处理来自Next-GenAI的搜索请求

**核心功能**:
- 接收POST请求 (`/api/crawl`)
- 动态配置爬虫参数 (`config.KEYWORDS`, `config.CRAWLER_MAX_NOTES_COUNT`)
- 执行小红书爬虫任务
- 调用数据迁移模块
- 返回爬取和迁移结果

**关键流程**:
```python
# 1. 接收请求参数
{
  "query": "机器学习面试",
  "limit": 10
}

# 2. 动态设置配置
config.KEYWORDS = query
config.CRAWLER_MAX_NOTES_COUNT = limit
config.HEADLESS = True  # API模式强制无头

# 3. 执行爬虫 → MySQL存储
crawler = XiaoHongShuCrawler()
await crawler.start()

# 4. 数据迁移 → SQLite
migrate_recent_data()

# 5. 返回结果
{
  "success": true,
  "crawled_count": 10,
  "migrated_count": 8
}
```

#### `api_migration.py` - 数据迁移模块
**作用**: 将MySQL中的小红书数据迁移到Next-GenAI的SQLite数据库

**核心功能**:
- MySQL到SQLite的数据转换
- 数据清洗和质量过滤
- 去重处理
- 字段映射和格式转换

**数据处理流程**:
```python
# 1. 连接两个数据库
MySQL: media_crawler.xhs_note
SQLite: NextGen-AI/db/database.sqlite3.rednote_content

# 2. 数据质量过滤
- 内容长度检查 (>100字符)
- 话题标签占比控制 (<50%)
- 必要字段验证

# 3. 字段映射转换
MySQL字段 → SQLite字段:
note_id → thread_id
desc → content
nickname → author_name
time → created_at (时间戳转换)
liked_count → likes (数值转换，支持"1.2万"格式)

# 4. 去重插入
基于thread_id去重，避免重复数据
```

## 快速开始

### 系统要求
- Python 3.9+
- MySQL 8.0+
- Chrome浏览器

### 安装部署

1. **环境准备**
```bash
# 克隆项目
git clone <repository-url>
cd MediaCrawler

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# 安装依赖
pip install -r requirements.txt
playwright install
```

2. **数据库配置**
```bash
# 创建MySQL数据库
mysql -u root -p -e "CREATE DATABASE media_crawler;"

# 初始化表结构
python db.py
```

3. **配置文件**
```python
# config/base_config.py
PLATFORM = "xhs"
LOGIN_TYPE = "cookie"
COOKIES = "web_session=your_session_value"  # 从浏览器获取
HEADLESS = True
SAVE_DATA_OPTION = "db"

# config/db_config.py  
RELATION_DB_HOST = "localhost"
RELATION_DB_USER = "root"
RELATION_DB_PWD = "your_password"
RELATION_DB_NAME = "media_crawler"
```

4. **SQLite迁移路径配置**
```python
# media_platform/xhs/api_migration.py
SQLITE_PATH = '/path/to/NextGen-AI/Project/db/database.sqlite3'
```

5. **启动服务**
```bash
python api_server.py
```

服务运行在 `http://localhost:8001`

## Cookie获取方法

1. 浏览器访问 xiaohongshu.com
2. 登录账号
3. 开发者工具 → Network → 任意请求
4. 复制Cookie中的 `web_session` 值
5. 粘贴到配置文件 `COOKIES` 字段

## API使用

### 爬取接口
```bash
curl -X POST "http://localhost:8001/api/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "机器学习面试",
    "limit": 10
  }'
```

**请求参数**:
- `query`: 搜索关键词 (必填)
- `limit`: 爬取数量 1-20 (默认5)
- `platform`: 平台名称 (默认"rednote")

**响应示例**:
```json
{
  "success": true,
  "message": "爬虫: 成功爬取 10 条关于 '机器学习面试' 的帖子; 迁移: 成功迁移 8 条记录",
  "query": "机器学习面试",
  "limit": 10,
  "platform": "rednote",
  "timestamp": "2024-01-15T10:30:00",
  "crawled_count": 10,
  "migrated_count": 8
}
```

### 健康检查
```bash
curl "http://localhost:8001/api/health"
```

### 服务状态
```bash
curl "http://localhost:8001/api/status"
```

## 完整工作流程
```
Next-GenAI(启动实时搜索) → api_server.py（API接受POST指令） → XiaoHongShuCrawler → MySQL（存储在该项目数据库中） → api_migration.py（表单映射到Next-GenAI的SQLite中的rednote_content上） → SQLite → Next-GenAI -> 实时搜索中直接取rednote_content表单中top_5（即最新爬下并存储的5条）的数据并整合后生成prompt -> 为这五条数据一并生成embedding并存储 -> 输入prompt给LLM并返回结果呈现在前端 
```

**详细步骤**:

1. **接收请求** (`api_server.py`)
   - Next-GenAI发送搜索请求到 `/api/crawl`
   - 验证参数并记录日志

2. **动态配置** (`api_server.py`)
   ```python
   config.KEYWORDS = request.query
   config.CRAWLER_MAX_NOTES_COUNT = request.limit
   config.HEADLESS = True
   ```

3. **执行爬虫** (`api_server.py` → `XiaoHongShuCrawler`)
   - 启动小红书爬虫
   - 数据存储到MySQL的 `xhs_note` 表

4. **数据迁移** (`api_migration.py`)
   - 从MySQL读取最新数据
   - 数据清洗和质量过滤
   - 字段映射和格式转换
   - 去重插入到SQLite

5. **返回结果** (`api_server.py`)
   - 合并爬虫和迁移结果
   - 返回JSON响应给Next-GenAI

## 数据存储详解

### MySQL存储 (`xhs_note`表)
```sql
-- 小红书原始数据
CREATE TABLE xhs_note (
    id INT PRIMARY KEY,
    note_id VARCHAR(50),     -- 帖子ID
    title VARCHAR(500),      -- 标题
    desc TEXT,              -- 内容
    nickname VARCHAR(100),   -- 作者昵称
    time BIGINT,            -- 时间戳
    liked_count VARCHAR(20), -- 点赞数
    video_url TEXT,         -- 视频链接
    tag_list TEXT           -- 标签列表
);
```

### SQLite迁移 (`rednote_content`表)
```sql
-- Next-GenAI标准格式
CREATE TABLE rednote_content (
    id INTEGER PRIMARY KEY,
    source VARCHAR(20),      -- 来源: "rednote"
    content_type VARCHAR(10), -- 类型: "note"/"video"
    thread_id VARCHAR(50),   -- 帖子ID
    thread_title VARCHAR(500), -- 标题
    author_name VARCHAR(100), -- 作者
    content TEXT,           -- 内容
    created_at DATETIME,    -- 创建时间
    likes INTEGER,          -- 点赞数
    tags TEXT              -- 标签
);
```

### 数据映射关系
| MySQL字段 | SQLite字段 | 转换逻辑 |
|-----------|-----------|----------|
| note_id | thread_id | 直接映射 |
| desc | content | 直接映射 |
| nickname | author_name | 直接映射 |
| time | created_at | 毫秒时间戳→日期时间 |
| liked_count | likes | "1.2万"→12000 |
| type | content_type | "normal"→"note" |

## 故障排除

### 1. API服务问题
```bash
# 检查服务状态
curl "http://localhost:8001/api/health"

# 查看日志
python api_server.py  # 前台运行查看日志
```

### 2. 爬虫登录问题
```bash
# 检查配置
grep -n "LOGIN_TYPE\|COOKIES" config/base_config.py

# 常见错误修复
LOGIN_TYPE = "cookie"  # 必须是单数形式
COOKIES = "web_session=有效值"  # 不能为空
```

### 3. 数据库连接问题
```bash
# 测试MySQL连接
mysql -h localhost -u root -p media_crawler

# 检查表结构
mysql -u root -p -e "USE media_crawler; DESCRIBE xhs_note;"
```

### 4. 数据迁移问题
```bash
# 检查SQLite路径
ls -la /path/to/NextGen-AI/Project/db/database.sqlite3

# 测试迁移功能
python -c "from media_platform.xhs.api_migration import migrate_recent_data; print(migrate_recent_data(limit=1))"
```

## 配置优化

### 爬取控制
```python
# config/base_config.py
CRAWLER_MAX_NOTES_COUNT = 20  # 单次最大爬取数量
CRAWLER_MAX_SLEEP_SEC = 4     # 请求间隔(秒)
MAX_CONCURRENCY_NUM = 1       # 并发数
ENABLE_GET_COMMENTS = False   # 是否爬取评论
```

### 性能调优
- **请求频率**: 调整 `CRAWLER_MAX_SLEEP_SEC` 避免被封
- **并发控制**: 保持 `MAX_CONCURRENCY_NUM = 1` 降低风险
- **数据质量**: 在 `api_migration.py` 中调整过滤条件

## 集成到Next-GenAI

### Python调用示例
```python
import requests

def search_rednote(query, limit=10):
    """调用MediaCrawler API搜索小红书内容"""
    try:
        response = requests.post(
            "http://localhost:8001/api/crawl",
            json={"query": query, "limit": limit},
            timeout=300  # 5分钟超时
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}

# 使用示例
result = search_rednote("Python编程技巧", 15)
if result["success"]:
    print(f"爬取了 {result['crawled_count']} 条数据")
    print(f"迁移了 {result['migrated_count']} 条数据")
else:
    print(f"请求失败: {result.get('error')}")
```

### 异步调用示例
```python
import asyncio
import aiohttp

async def async_search_rednote(query, limit=10):
    """异步调用MediaCrawler API"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8001/api/crawl",
            json={"query": query, "limit": limit}
        ) as response:
            return await response.json()

# 使用示例
result = asyncio.run(async_search_rednote("机器学习", 10))
```

## 监控和维护

### 日志监控
```bash
# 查看实时日志
tail -f api_server.log

# 监控关键指标
grep -E "(成功|失败|错误)" api_server.log | tail -20
```

### 定期维护
- **Cookie更新**: 每周检查并更新Cookie
- **数据清理**: 定期清理MySQL中的旧数据
- **性能监控**: 监控API响应时间和成功率

## 安全建议

- 控制爬取频率避免账号风险
- 定期轮换Cookie保持登录状态
- 监控API调用频率
- 备份重要配置和数据
- 遵守小红书使用条款

