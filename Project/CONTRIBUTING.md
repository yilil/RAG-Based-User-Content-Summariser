1，流程图：



2，项目结构图：
（readme格式到时候直接复制上去）
## 项目结构图

下面是项目的主要目录和文件结构，以及它们各自的功能说明：

Project/
├── .git/                     # Git 版本控制目录
├── .gitignore                # Git 忽略文件配置
├── .gitattributes            # Git LFS 跟踪配置
├── Frontend/                 # 前端代码 (Vue/React/etc. - 独立项目)
│   ├── node_modules/         # 前端依赖
│   ├── public/
│   ├── src/                  # 前端源代码
│   ├── package.json          # 前端项目配置与依赖
│   └── ...                   # 其他前端配置文件 (vite.config.js, etc.)
├── django_apps/              # Django 应用目录
│   ├── __init__.py
│   ├── search/               # 核心搜索与 RAG 应用
│   │   ├── __init__.py
│   │   ├── admin.py          # Django Admin 配置
│   │   ├── apps.py           # 应用配置
│   │   ├── crawler.py        # RedNote 爬虫实现 (Selenium)
│   │   ├── models.py         # 数据库模型定义 (RedditContent, RednoteContent, ContentIndex 等)
│   │   ├── views.py          # Django 视图 (处理 /search, /index_content 等请求)
│   │   ├── urls.py           # URL 路由配置
│   │   ├── utils.py          # 实用工具函数 (如 get_embeddings)
│   │   ├── tests.py          # 应用测试
│   │   ├── index_service/    # 索引与检索服务核心逻辑
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # IndexService 类 (整合入口)
│   │   │   ├── faiss_manager.py  # FAISS 和 BM25 索引管理 (空索引库初始化，索引加载、保存、搜索)
│   │   │   ├── indexer.py        # 内容索引器 (Embedding 生成、写入 FAISS 和 ContentIndex)
│   │   │   ├── hybrid_retriever.py # 混合检索器 (结合key words score(BM25), embedding score, Votes/Likes Score, 归一化后合并排序)
│   │   │   ├── result_processor.py # 结果处理器 (特别是推荐类查询的排序和格式化)
│   │   │   ├── rating_processor.py # 情感/评分处理器 (用于推荐排序)
│   │   │   └── text_preprocessor.py # 文本预处理器 (用于 BM25 等)
│   │   ├── management/       # Django 管理命令
│   │   │   ├── __init__.py
│   │   │   └── commands/
│   │   │       ├── __init__.py
│   │   │       ├── test_rednote_crawler.py # 运行 RedNote 爬虫的命令
│   │   │       ├── initialize_index.py    # (已弃用) 初始化索引命令
│   │   │       ├── index_content.py       # (已弃用) 索引内容命令
│   │   │       ├── test_data_generator.py # 生成测试数据
│   │   │       └── test_rag.py            # RAG 功能测试命令
│   │   └── migrations/       # 数据库结构变更记录
│   │       └── ...
│   └── memory/               # 对话记忆管理应用
│       ├── __init__.py
│       ├── models.py         # 对话记忆模型
│       ├── service.py        # 记忆存储与读取服务
│       └── ...
├── search_process/           # RAG 流程中与 LLM 交互相关的处理逻辑
│   ├── __init__.py
│   ├── prompt_generator/     # Prompt 生成
│   │   ├── __init__.py
│   │   └── generator.py      # 构建发送给 LLM 的完整 Prompt
│   ├── query_classification/ # 查询分类
│   │   ├── __init__.py
│   │   └── classification.py # 使用 LLM 判断查询类型
│   ├── langchain_parser.py   # 解析 LangChain/LLM 返回结果
│   └── prompt_sender.py      # 发送 Prompt 给 LLM (Gemini)
├── faiss_index/              # FAISS 索引存储目录 (Git LFS 跟踪)
│   ├── reddit/
│   │   ├── index.faiss (在下方“RAG模块/索引构建与存储”部分具体介绍)
│   │   └── index.pkl
│   ├── stackoverflow/
│   │   ├── index.faiss
│   │   └── index.pkl
│   └── rednote/
│       ├── index.faiss
│       └── index.pkl
├── venv/                     # Python 虚拟环境 (不在 Git 中)
├── .env                      # 环境变量 (如 API Key, 不在 Git 中)
├── db.sqlite3                # SQLite 数据库文件 (Git LFS 跟踪)
├── manage.py                 # Django 项目管理脚本
├── requirements.txt          # Python 依赖列表
├── set_api_key.py            # 设置 API Key 的脚本
├── README.md                 # 项目说明文档
└── diagram.dot               # Graphviz 流程图定义文件







3，前端：

Chinese version:
1. 目录结构
Frontend/ – Vite + React（TypeScript）单页应用
src/pages/SummaryPage.tsx – 聊天式搜索界面（会话、模板、自动滚动）
src/components/Sidebar.tsx – 模型 / 平台选择器 + 聊天列表 + 会话持久化
src/components/QuestionTemplates.tsx – 动态提示面板，显示在输入框上方，失焦后延迟隐藏
src/lib/session.ts – 负责获取 / 缓存 sessionid cookie，并在每次 fetch 时自动携带
vite.config.ts – 将 /api 代理到 Django(8000)，开发阶段无 CORS 烦恼

2. 构建 & 本地调试
cd Frontend
npm install        # 安装 React / Vite / Tailwind 等依赖
npm run dev        # 启动热更新 http://localhost:5173
npm run build      # 生产环境打包，输出到 Frontend/dist

3. 网络约定
所有请求均走 /api/*，由 Vite 反向代理
认证只用 cookie：
fetch("/api/search/", {
  method: "POST",
  credentials: "include",      // 关键：发送并接收 sessionid
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ ... })
})
SPA 首次加载会访问 /api/sessionKey/；Django 返回的 Set-Cookie: sessionid=... 之后自动随请求发送

4. 状态流程
Sidebar 触发 newChat(platform) → React Context 把 {chatId, platform, messages: []} 存到 localStorage
SummaryPage 渲染当前会话
用户提交 → onUpdateMessages("User: ...") → fetch → onUpdateMessages("Bot: ...")
每次搜索结束后，再拉取 /api/getMemory/ 补全历史


5. 交互细节
新消息后 自动滚动到底部；切换会话时滚到顶部
QuestionTemplates 绝对定位在输入框上方；无模板时直接隐藏
样式采用 Tailwind，max-w-screen-lg mx-auto 保证搜索栏 & 消息宽度始终 100%
所有按钮与输入框均带 aria-label，深色模式自动适配


### 6. 样式 & 主题（如何快速改 UI）

#### 6.1 Tailwind 入口
所有全局样式集中在 `Frontend/src/index.css`  
Tailwind 在 `tailwind.config.ts` 里做了两件事：
1. 设定蔚蓝（`primary`）和青绿（`accent`）两种主色；
2. 开启 `darkMode:"class"`——给 `<html class="dark">` 即可进入深色模式。

#### 6.2 修改宽度 / 排版
组件里凡是出现  
```tsx
<div className="max-w-screen-lg mx-auto px-4">
max-w-screen-lg 控制最大宽度，可改成 max-w-screen-xl 或移除让其 100% 宽
px-4 控制左右内边距，单位 1 = 0.25rem

6.3 改变搜索栏位置 / 样式
搜索栏位于 SummaryPage.tsx：
<form className="sticky bottom-0 bg-white dark:bg-zinc-900 ...">

把 sticky bottom-0 换成 fixed bottom-4 left-1/2 -translate-x-1/2 可悬浮在页面底部
加 shadow-lg rounded-full 就能得到圆角浮窗效果


6.4 调整聊天气泡
ChatBubble 组件（位于 src/components/ChatBubble.tsx）：
<div className={`p-3 rounded-lg ${isUser ? "bg-primary-500 text-white ml-auto" : "bg-zinc-200"}`}>

改 bg-primary-500 => bg-rose-500 可把用户气泡改成粉色
加入 prose 类让 Markdown 自动排版


6.5 新增主题
在 tailwind.config.ts:
theme: {
  extend: {
    colors: {
      brand: {  DEFAULT:"#188a8d",  light:"#34c8cc" },
    }
  }
}
然后组件里直接写 bg-brand / hover:bg-brand-light 即可。
Tip：修改完 tailwind.config.ts 需重启 npm run dev 才会生效。
```

4，后端：

# 后端search.views.py调用顺序

#### **步骤 1: 接收请求和日志记录**
- **输入**: 请求体（`request.body`）中包含了`search_query`（搜索查询），`source`（平台，如'reddit'），`filter_value`（过滤条件），`llm_model`（模型类型），`session_id`（会话ID）等数据。
- **方法**: 
  - `json.loads(request.body.decode('utf-8'))` 用来解析请求体中的 JSON 数据。
  - `logger.info()`、`logger.debug()` 用于日志记录，帮助调试和跟踪请求。

#### **步骤 2: 获取最近的记忆**
- **输入**: `session_id`、`platform` 和 `topic`（从请求中获取）。
- **方法**: 
  - `MemoryService.get_recent_memory(session_id, limit=10, platform=platform, topic=topic)` 获取最近的记忆。该方法会返回一个包含会话相关记忆的列表。

#### **步骤 3: FAISS 相似文档检索**
- **输入**: `search_query`（搜索查询）和 `platform`（平台），平台的选择默认是'reddit'。
- **方法**:
  - `index_service.faiss_manager.get_index_size()` 获取当前索引的大小。
  - `HybridRetriever.retrieve(query=search_query, top_k=10, relevance_threshold=0.6)` 使用 FAISS 索引和 BM25 算法进行搜索，返回相似文档。

#### **步骤 4: 分类查询类型**
- **输入**: `search_query`（搜索查询），`llm_model`（模型类型）。
- **方法**:
  - `classify_query(search_query, llm_model)` 识别查询类型（如推荐类查询），返回分类结果。通过正则表达式提取分类ID。
  - 使用 `re.search(r">(\d+)<", ...)` 提取分类ID。

#### **步骤 5: 根据查询类型选择处理逻辑**
- **推荐类查询处理**:
  - **输入**: `retrieved_docs`（检索到的文档），`search_query`（搜索查询）。
  - **方法**:
    - `index_service.result_processor.process_recommendations()` 处理推荐逻辑，返回推荐的文档。
    - `format_recommendation_results()` 格式化推荐结果，生成文本形式的推荐结果。
    - `MemoryService.add_to_memory(session_id, search_query, answer)` 将推荐结果保存到记忆中。
  
  如果是推荐类查询，则直接返回格式化的推荐结果，并标记`llm_model`为"recommendation_processor"。

- **非推荐类查询处理**:
  - **输入**: `search_query`（搜索查询），`retrieved_docs`（检索到的文档），`recent_memory`（最近的记忆）。
  - **方法**:
    - `generate_prompt()` 生成用于 LLM（大语言模型）的提示（prompt）。
    - `send_prompt()` 通过线程池异步发送请求到 LLM 服务，获取回答。
    - `parse_langchain_response()` 解析 LLM 的响应，获取答案和元数据。
    - `MemoryService.add_to_memory(session_id, search_query, answer)` 保存回答到记忆。

#### **步骤 6: 返回搜索结果**
- **输入**: `answer`（搜索回答），`metadata`（元数据），`llm_model`（模型类型），`recent_memory`（最近的记忆）。
- **方法**:
  - `JsonResponse()` 返回JSON格式的响应，包含搜索结果、元数据和历史记忆。

---

# 前后端交互API描述

## 1. 请求处理入口：`search(request)`

### 🔸 前端发送：
- **方法**：`POST`
- **路径**：例如 `/search/`
- **请求体（Body）示例**：
```json
{
  "search_query": "如何使用Python爬取Reddit数据？",
  "source": "reddit",
  "filter_value": null,
  "llm_model": "gemini-pro",
  "session_id": "abc123",
  "topic": "python爬虫"
}
```

### 🔸 后端返回：
- **返回数据示例**：
```json
{
  "result": "根据您的查询，为您推荐以下内容...",
  "metadata": {
    "query_type": "recommendation",
    "processing": "direct"
  },
  "llm_model": "recommendation_processor",
  "history": [...]
}
```

---

## 2. 会话管理相关接口

### (1) 获取或创建Session：`sessionKey(request)`

- **方法**：`POST`
- **返回数据示例**：
```json
{
  "session_id": "abc123"
}
```

---

### (2) 获取指定Session的Memory：`getMemory(request)`

- **方法**：`GET`
- **参数**：
  - `session_id`
- **返回数据示例**：
```json
{
  "memory": [...]
}
```

---

### (3) 获取全部Session及历史对话：`getAllChat(request)`

- **方法**：`GET`
- **返回数据示例**：
```json
{
  "sessions": [
    {
      "session_id": "abc123",
      "platform": "reddit",
      "topic": "python爬虫",
      "memory_data": [...],
      "updated_at": "2025-04-26T12:30:45"
    },
    ...
  ]
}
```

---

# 查询分类逻辑

- 后端通过 `classify_query(search_query, llm_model)` 返回一个带有分类编码的字符串，格式例如：
  ```
  ">1<"
  ```

- **分类编码对应表**：

| 编号 | 类别名称 |
| :--- | :--- |
| 1 | Recommendation class（推荐类） |
| 2 | Knowledge interpretation class（知识解读类） |
| 3 | Opinion Discussion（观点讨论类） |
| 4 | Operation instruction and tutorial method class（操作指导与教程方法类） |
| 5 | Specific scenarios（特定场景类） |
| 6 | Information and real-time dynamic class（信息与实时动态类） |




(2), 数据库结构(每个表单的结构、表头、存储的数据内容)及相关文件位置
## 数据库设计

NextGen-AI项目采用Django ORM框架管理数据库，主要包含以下数据表单，存储从不同平台获取的内容数据以及相关检索索引信息。
文件位于`/django_apps/search/models.py`

### 主要数据表单

#### ContentIndex表
此表用于跟踪哪些内容已被成功索引，存储了内容的唯一标识和索引相关信息：
- `source`: 数据来源平台（如reddit、stackoverflow、rednote等）
- `thread_id`: 内容的唯一标识符
- `embedding_key`: 对应FAISS索引中的向量标识

#### RedditContent表
存储从Reddit平台抓取的内容：
- `source`: 固定为"reddit"
- `content_type`: 内容类型，如"post"
- `thread_id`: Reddit帖子的唯一ID
- `thread_title`: 帖子标题
- `url`: 帖子链接
- `author_name`: 作者用户名
- `content`: 帖子正文与评论内容的组合
- `created_at`: 创建时间
- `subreddit`: 发布的子版块名
- `upvotes`: 获得的点赞数

#### StackOverflowContent表
存储从Stack Overflow平台抓取的问答内容：
- `source`: 固定为"stackoverflow"
- `content_type`: 内容类型，如"question"
- `thread_id`: 问题的唯一ID
- `thread_title`: 问题标题
- `url`: 问题链接
- `author_name`: 提问者用户名
- `content`: 问题正文、评论及回答的组合
- `created_at`: 创建时间
- `tags`: 问题标签，以逗号分隔
- `vote_score`: 问题的投票得分

#### RednoteContent表
存储从小红书（RedNote）平台抓取的内容：
- `source`: 固定为"rednote"
- `content_type`: 内容类型，如"note"
- `thread_id`: 笔记的唯一ID
- `thread_title`: 笔记标题
- `url`: 笔记链接
- `author_name`: 作者用户名
- `content`: 笔记正文内容
- `created_at`: 创建时间
- `tags`: 笔记标签，以逗号分隔
- `likes_count`: 获得的点赞数



(3), 数据库中内容的存储方式：
API(Stackoverflow & Reddit平台)：
#### Stack Overflow数据获取
Stack Overflow数据通过官方API进行抓取，主要实现在`django_apps/search/stackoverflow_crawler.py`中：

1. **查询方式**：
   - 关键词搜索：使用Stack Exchange API的`/search`端点进行问题搜索
   - 标签组合搜索：使用`/questions`端点配合标签参数进行过滤

2. **数据处理流程**：
   - 初始化`StackOverflowFetcher`类，设置API参数（如排序方式、每页数量）
   - 执行问题搜索（`search_questions`方法）获取问题列表
   - 对每个问题获取评论（`fetch_comments_for_question`方法）
   - 对每个问题获取回答（`fetch_answers_for_question`方法），优先排序已接受答案
   - 组合问题、评论和答案构建完整内容
   - 将内容存储到`StackOverflowContent`表中

3. **数据多样性策略**：
   - 从JSON配置文件加载多样化查询和标签组合
   - 使用标签组合（如"python+django"、"javascript+react"等）增加内容多样性
   - 按不同排序方式（如按投票数、按活跃度）获取内容

#### Reddit数据获取
Reddit数据通过PRAW（Python Reddit API Wrapper）获取，主要实现在`django_apps/search/reddit_crawler.py`中：

1. **查询方式**：
   - 使用`subreddit.search`方法进行关键词搜索
   - 支持跨所有子版块（subreddit="all"）的综合搜索

2. **数据处理流程**：
   - 初始化Reddit API客户端（`create_reddit_instance`函数）
   - 执行关键词搜索获取帖子列表
   - 对每个帖子获取评论（`fetch_comments_for_post`函数），按点赞数排序
   - 组合帖子正文和评论构建完整内容
   - 将内容存储到`RedditContent`表中

3. **数据质量保障**：
   - 记录时保留帖子原始时间戳，使用Python的`timezone.utc`确保时区一致
   - 记录帖子投票分数（upvotes），为后续检索排序提供参考
   - 添加请求间隔（`time.sleep`）避免触发API限制




爬虫(Rednote平台)：
## RedNote 爬虫

RedNote (小红书) 爬虫利用 `Selenium` 及其反检测扩展 `selenium-stealth` 来模拟浏览器行为，抓取指定 URL 页面的笔记内容。

-   **核心实现**:
    -   **主要逻辑**: 位于 `django_apps/search/crawler.py` 文件中的 `crawl_rednote_page` 函数。该函数负责：
        1.  **初始化 WebDriver**: 配置 `Selenium WebDriver` (Chrome)，应用 `selenium-stealth` 设置以避免被检测，并处理特定平台（如 macOS ARM）的 `ChromeDriver` 路径。
        2.  **登录**: 注入提供的 `cookies` (目前硬编码在管理命令中) 以模拟登录状态。
        3.  **页面加载与滚动**: 打开目标 URL，模拟人类向下滚动 (`human_like_scroll`) 以动态加载更多笔记。
        4.  **笔记遍历**: 查找页面上的笔记链接 (`a.cover.ld.mask`)，并限制处理数量（`MAX_POSTS`）。
        5.  **数据提取**: 对每个笔记链接：
            -   安全点击进入笔记详情页 (`safe_click_by_selector`)。
            -   提取笔记标题、正文内容 (`div.note-content`)、作者、发布日期、点赞数、标签等信息。
            -   解析日期 (`parse_xiaohongshu_date`) 和点赞数 (`parse_likes_count`) 为标准格式。
        6.  **数据库交互**:
            -   **查重**: 使用笔记 URL 中的唯一 ID (`thread_id`) 在 `RednoteContent` 表中查找是否已存在记录。
            -   **更新**: 如果记录已存在且**尚未被索引** (目前还没有实现，应该根据ContentIndex中是否有相同thread_id的数据来判断是否被索引过)，则更新其元数据（标题、作者、点赞数等）。如果已被索引，则跳过。
            -   **创建**: 如果记录不存在，则创建新的 `RednoteContent` 条目，并将抓取到的**完整 `content` 存入数据库**。
        7.  **即时索引 (可选)**: 如果 `--immediate-indexing` 标志被激活，将新创建或待更新的数据库对象 (`db_obj`) 及其文本内容 (`content_text`) 加入待处理列表。
        8.  **返回列表**: 爬虫结束后，返回新创建的 `RednoteContent` 对象列表。
    -   **管理命令**: 位于 `django_apps/search/management/commands/test_rednote_crawler.py`，提供了 `test_rednote_crawler` 命令，用于接收 URL 和 `--immediate-indexing` 参数，并调用 `crawl_rednote_page`。

-   **运行模式**:
    1.  **存储模式 (默认)**:
        -   执行命令: `python manage.py test_rednote_crawler --url "小红书某内容URL"`
        -   逻辑: 仅执行上述**核心实现**中的数据提取和数据库交互（创建或更新记录），**确保 `content` 字段包含抓取到的文本**。此模式下**不进行** Embedding 生成或 FAISS 索引操作。适用于先批量抓取，后续统一索引的场景。
    2.  **即时索引模式**:
        -   执行命令: `python manage.py test_rednote_crawler --url "你的小红书URL" --immediate-indexing`
        -   逻辑: 在**核心实现**的基础上，当一个笔记被创建或确定需要更新（因为它之前未被索引）后：
            -   该笔记对象和其文本内容会被暂存。
            -   在爬取循环结束后，系统会遍历所有暂存的笔记。
            -   对每个笔记调用 `index_service.indexer.index_crawled_item` 函数（该函数由爬虫模块内初始化的全局 `index_service` 实例提供）。
            -   `index_crawled_item` 内部会:
                -   调用 Embedding 模型生成文本内容的向量。
                -   将向量、文本和元数据添加到内存中的 FAISS 索引。
                -   为数据库中的笔记对象设置 `embedding_key` (目前是 UUID)。
                -   **将数据库中该笔记的 `content` 字段设置为空 (`None`)** 以节省空间。
                -   在 `ContentIndex` 表中创建一条记录，标记该笔记已被索引。
            -   所有笔记处理完毕后，调用 `index_service.faiss_manager.save_index()` 将内存中的 FAISS 索引（包括新增的 Embeddings）和元数据变更**一次性保存到磁盘** (`index.faiss` 和 `index.pkl`)。

-   **批量索引 (爬取后)**: 对于使用**存储模式**收集的数据（`content` 字段有值，`embedding_key` 为空），可以通过标准的索引 API 端点进行后续的批量索引：
    ```bash
    # 对 rednote 平台所有未被索引的内容进行索引
    curl -X POST http://localhost:8000/index_content/ -d "source=rednote"
    ```
    这个请求会触发 `views.py` 中的 `index_content` 逻辑，查找 `ContentIndex` 中没有记录的 `RednoteContent` 条目，并对其进行 Embedding 和索引，最终同样会将 `content` 字段清空。

-   **依赖与设置**:
    -   需要安装 `selenium`, `selenium-stealth`。
    -   需要正确配置 `ChromeDriver` 并确保其在系统 PATH 中可访问（具体参考主 README 的爬虫设置部分，注意 macOS ARM 的特殊处理已在 `crawler.py` 中实现）。
    -   登录所需的 `Cookies` 目前**硬编码**在管理命令 `test_rednote_crawler.py` 文件中，实际部署或多人协作时可能需要改进为更灵活的配置方式。



(4), 

## RAG 系统 

以下内容详细介绍检索增强生成 (Retrieval-Augmented Generation, RAG) 模块，包括 Embedding 生成、索引构建与管理、混合检索机制以及 Prompt 构建逻辑。

### Embedding 生成 

-   **模型**: Embedding 使用 `BAAI/bge-base-en` 模型生成，通过 `langchain_huggingface.HuggingFaceEmbeddings` 包装器调用。
-   **实现**: 核心 Embedding 逻辑封装在 `django_apps/search/utils.py` 文件中的 `get_embeddings` 函数。该函数初始化模型，配置在可用时使用 CUDA，并设置 `normalize_embeddings=True`。
-   **过程**: `django_apps.search.index_service.indexer.Indexer` 类使用初始化时传入的 Embedding 模型将文本内容转换为向量。具体来说，`_batch_create_embeddings` 方法在调用 `self.embedding_model.embed_documents()` 之前处理批量文本和预处理（去除空格、基础长度限制）。


### 索引构建与存储

-   **存储结构与内容**:
    -   **物理位置**: FAISS 相关数据按平台存储在 `faiss_index/` 目录下的子目录中（例如 `faiss_index/reddit/`, `faiss_index/rednote/`）。
    -   **核心文件**: 每个平台子目录下包含两个关键文件：
        1.  **`index.faiss`**:
            -   **内容**: 存储 **FAISS 索引结构本身** 以及 **Embedding 向量数据**。FAISS 索引结构是一种经过优化的数据结构，用于根据输入的查询向量快速找到存储在其中的最相似的 Embedding 向量。Embedding 向量（由文本内容转换而来）是构建此索引结构的核心数据，并直接嵌入在该文件内部，而非单独存放。
            -   **用途**: 实现高效的向量相似性搜索。
        2.  **`index.pkl`**:
            -   **内容**: 存储与 `index.faiss` 中每个 Embedding 向量相对应的**元数据 (Metadata)** 和 **映射关系 (Mapping)**。元数据包括文档的来源、`thread_id`、`content_type`、作者名称、创建时间、以及特定平台的字段（如点赞/投票数、标签等）。映射关系则建立了 FAISS 内部向量 ID 与 LangChain `Document` 对象（及其元数据）存储 ID 之间的关联。
            -   **用途**: 由 LangChain 的 `FAISS` 库在加载索引时使用，配合 `index.faiss` 文件，能够将搜索结果还原为包含完整上下文信息的 `Document` 对象。
    -   **数据库跟踪**: Django 模型 `ContentIndex` (`django_apps/search/models.py`) 在数据库层面记录哪些内容条目（通过 `source` 和 `thread_id` 唯一识别）已被成功处理并纳入 FAISS 索引中。

-   **索引流程**:
    -   **触发索引**: 对存储在数据库中的内容进行索引的主要方式是向 `/index_content/` 端点发送 HTTP POST 请求。
        ```bash
        # 为特定平台建立索引 (例如 rednote)
        curl -X POST http://localhost:8000/index_content/ -d "source=rednote"

        # 为所有平台建立索引
        curl -X POST http://localhost:8000/index_content/ -d "source=all"
        ```
    -   **后端逻辑**: 该请求由 `django_apps/search/views.py` 中的 `index_content` 视图处理。
        1.  **确定平台**: 根据 POST 请求数据确定需要索引的平台。
        2.  **查找未索引内容**: 查询对应平台的内容模型（例如 `RednoteContent`），通过比较 `ContentIndex` 表中已记录的 `thread_id`，找出尚未被索引的条目。
        3.  **调用索引器**: 如果找到未索引条目，则调用 `index_service.indexer.index_platform_content()`。
        4.  **处理条目**: `Indexer.index_platform_content` 方法 (`django_apps/search/index_service/indexer.py` 中) 遍历这些未索引的条目：
            -   **生成 Embedding**: 调用 `_batch_create_embeddings` 为条目的 `content` 字段生成 Embedding 向量。
            -   **添加至 FAISS**: 调用 `faiss_manager.add_texts()` 将文本内容、元数据和生成的 Embedding 添加到内存中的 FAISS 索引（更新 `index.faiss` 和 `index.pkl` 的内存表示）。
            -   **记录索引状态**: 在 `ContentIndex` 数据库表中创建一条新记录，标记该 `thread_id` 已被索引。
            -   **清空原文**: **关键步骤** - 成功将 Embedding 和元数据添加到 FAISS 并记录到 `ContentIndex` 后，将原始数据库记录（如 `RednoteContent` 对象）的 `content` 字段更新为 `None`，以节省数据库存储空间。
            -   **保存到磁盘**: 当一批或所有未索引条目处理完毕后，调用 `faiss_manager.save_index()` 将内存中更新后的 FAISS 索引 (`index.faiss`) 和元数据存储 (`index.pkl`) 原子性地写入磁盘文件。
    -   **"Skipping object..." 日志**: (以下是针对出现该日志的情况说明)
        -   **现象**: 在运行索引命令时，可能会看到类似 `Skipping object with ID xx due to empty content` 的日志信息。
        -   **原因**: 这通常发生在以下情况：某个内容条目**之前已经被成功索引过**，因此其在数据库中的 `content` 字段已被清空（设为 `None`）。但后来由于某种原因（例如数据库手动操作、迁移问题或其他未知错误），该条目在 `ContentIndex` 表中对应的记录**被意外删除了**。当索引流程再次运行时，它根据 `ContentIndex` 表判断该条目是“未索引”的，但在尝试读取其 `content` 字段以生成 Embedding 时发现是空的，因此只能跳过处理并打印此日志。
        -   **影响**: 这通常不影响系统的正常检索功能（因为该条目的向量和元数据仍在 FAISS 文件中），但它提示可能存在数据不一致的情况。
    -   **弃用命令**: **请勿使用** 旧的管理命令 `python manage.py initialize_index` 或 `python manage.py index_content`。这些已被弃用。当前正确的触发方式是使用上面描述的 `/index_content/` POST 请求。


### 混合检索

-   **概念**: 系统采用混合检索策略，结合语义相似性（通过 FAISS 进行向量搜索）、关键字相关性（BM25 文本搜索）以及社交媒体可信度（投票/点赞数），以提高检索文档的相关性。
-   **实现**: 核心逻辑位于 `HybridRetriever` 类 (`django_apps/search/index_service/hybrid_retriever.py`) 中。主要的 `retrieve` 方法执行以下步骤：
    1.  **候选集获取**: 使用 FAISS 向量相似性搜索 (`faiss_manager.search`) 和 BM25 文本搜索 (`faiss_manager.search_bm25`) 获取初始候选文档集。这里使用较大的 `top_k` 乘数以确保有足够广泛的候选池。
    2.  **文档池化**: 将两个搜索的结果合并到一个以文档 ID 为键的字典中，以进行去重。
    3.  **分数提取**: 记录每个唯一文档的 BM25 分数、Embedding 相似度分数和投票分数（通过 `get_doc_vote_score` 从元数据中提取的点赞/投票数）。
    4.  **归一化**: 对池中所有文档的每种检索方法（BM25、Embedding、投票）的分数分别进行归一化处理，映射到 [0, 1] 区间（使用 `normalize` 和 `normalize_embedding_list` 方法）。
    5.  **加权组合**: 使用可配置的权重（在 `django_apps/search/views.py` 中初始化 `HybridRetriever` 时定义，例如 `bm25_weight=0.25`, `embedding_weight=0.55`, `vote_weight=0.2`）组合归一化后的分数，计算每个文档的最终相关性分数。
    6.  **阈值过滤**: 过滤掉组合相关性分数低于指定 `relevance_threshold`（例如 0.5 或 0.6，在 `views.py` 中设置，主 README 可能也有提及）的文档。
    7.  **排序**: 剩余文档按最终组合分数降序排列。
    8.  **Top-K 选择**: 返回分数最高的 `k` 个文档。
-   **BM25 初始化**: BM25 索引在加载 FAISS 索引时于 `FaissManager` (`django_apps/search/index_service/faiss_manager.py`) 内通过 `_initialize_bm25_from_faiss` 进行初始化。它使用存储在 FAISS Docstore (`index.pkl`) 中的文本作为其语料库。


### 推荐类处理逻辑

#### 1. 处理流程

1. **接收查询与文档**  
   接收用户的推荐类查询以及检索到的相关文档集合。

2. **提取推荐项**  
   使用 LLM 从检索到的文档中提取所有推荐项目及其相关信息。

3. **情感分析与评分**  
   对每个推荐项的相关帖子内容进行情感分析，并映射为 1–5 分制评分。

4. **计算综合分数**  
   根据情感评分、帖子点赞数和提及次数计算综合得分。

5. **排序与返回**  
   按综合得分降序排序，返回前 K 个格式化的推荐结果。

#### 2. 核心实现逻辑

##### 2.1 提取推荐项目

- **提示词构建** (`_build_extraction_prompt`)  
  要求 LLM 从文档中识别所有推荐项目，并为每个项目提取：  
  - 项目名称  
  - 所有提及该项目的帖子  
    - 帖子原文内容  
    - 帖子点赞数  
    - 基于情感的评分（1–5 分）  
  - 项目评论摘要（2–3 句）

- **调用 LLM** (`_call_llm_for_extraction`)  
  使用 Gemini 处理文本并从响应中解析出 JSON 格式的数据。

##### 2.2 推荐项处理

对每个提取出的项目，系统会：

1. 计算 **总点赞数** (`total_upvotes`)  
2. 对每条帖子调用 `_analyze_sentiment` 进行情感分析  
3. 计算 **平均情感评分** (`avg_rating = round(avg_rating, 2)`)  
4. 统计 **提及次数** (`mentions`)  
5. 构建包含以下字段的推荐对象：
   ```python
   recommendation = {
       'name': item['name'],
       'total_upvotes': total_upvotes,
       'avg_rating': avg_rating,
       'mentions': mentions,
       'posts': posts_with_ratings,
       'summary': item.get('summary', '没有摘要')
   }
```
#### 2.3 情感分析与评分

- **使用**: `RatingProcessor`  
  - **内容提取**: `_extract_item_related_content`  
  - **情感分类**: `"very positive"`, `"positive"`, `"neutral"`, `"negative"`, `"very negative"`  
  - **评分映射**: `sentiment_to_rating` → `[5.0, 4.0, 3.0, 2.0, 1.0]`  

#### 2.4 综合分数计算

- **方法**: `_calculate_scores`  
- **加权组成**:  
  - 情感评分组件 (`rating_component`): 权重 0.4  
  - 点赞组件 (`upvote_component`): 权重 0.35  
  - 提及组件 (`mention_component`): 权重 0.25  
- **计算公式**:  
综合得分 = 0.4 × avg_rating + 0.35 × normalized_upvotes + 0.25 × normalized_mentions

#### 2.5 排序与格式化结果
- _format_results 将排序后的推荐项转换为文档对象
- 每个文档包含格式化内容，显示项目名称、评分、点赞数、得分详情和评论详情
- 所有原始数据保存在文档的 `metadata` 字段，便于前端进一步处理  

#### 3. 调试与扩展

- 系统在LLM调用失败时会返回模拟数据，便于测试和开发  

- **TODO**  
1. **JSON 解析安全性**  
   - 目前通过正则修复无效转义  
   - 后续应通过提示词约束输出格式  
2. **情感分析提示词优化**  
   - 验证 LLM 对五类情感的区分是否足够准确  
3. **相关内容提取鲁棒性**  
   - 保证相同查询能稳定地提取相同内容  



### Prompt 生成与retrieved documents充分性判断 
(
-   **Prompt 结构**: 发送给 LLM 的最终 Prompt 由 `search_process/prompt_generator/generator.py` 中的 `generate_prompt` 函数构建。它包含：
    -   角色定义（基于平台）。
    -   用户查询。
    -   最近的聊天记录（通过 `MemoryService` 获取）。
    -   检索到的文档（如果数量足够）。
    -   输出格式说明。
    -   基于查询分类的特定指令。 )




-   **文档充分性检查**: RAG 上下文（检索到的文档）仅在 `HybridRetriever` 检索到 **至少 5 （目前设置的数量，之后会根据情况优化调整）个** 文档时才包含在 Prompt 中。此检查直接在 `generate_prompt` 函数内进行：
    ```python
    # search_process/prompt_generator/generator.py
    # ...
    if len(retrieved_docs) >= 5:
        prompt.append(
            "## Relevant Documents\\n"
            # ... 在 prompt 中包含文档 ...
        )
    else:
        prompt.append (
            "No relevant documents were retrieved. Please attempt to answer based on your general knowledge.\\n\\n"
        )
    ```
    -   如果检索到的文档少于 5 个，Prompt 会指示 LLM 根据其通用知识进行回答。
    -   注意：`HybridRetriever` 本身可能已根据 `relevance_threshold` 过滤了文档，因此传递给 `generate_prompt` 的最终数量可能少于最初请求的 `top_k`。





—------
# 15. Frontend
| Path | Purpose |
| `Frontend/` : Vite + React (TypeScript) single-page app
| `Project/` : Django backend (runs on `127.0.0.1:8000`)
| `.env` : Front-end env vars (`VITE_BACKEND_URL`)
| `src/pages/SummaryPage.tsx` : Chat-like search screen
| `src/components/Sidebar.tsx` : Model selector + chat list
| `src/components/QuestionTemplates.tsx` : Search suggestions popup


### How to run:
```bash
cd Frontend
npm run dev
```

