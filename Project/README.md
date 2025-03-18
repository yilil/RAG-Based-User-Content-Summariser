# NextGen-AI 项目

## UI 设计与流程图
- [Figma 设计链接](https://www.figma.com/design/1BZN661uSi2y4FKDcd4RgZ/NextGen-AI-(Prototype)?node-id=0-1&m=dev) (开发模式)

## 1. 环境搭建

### 1.1 创建虚拟环境
```bash
python3 -m venv venv
```

### 1.2 激活虚拟环境
```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
# 或
venv\Scripts\Activate.ps1  # PowerShell
```

### 1.3 安装项目依赖
```bash
pip install -r requirements.txt
```

## 2. 配置 Gemini API Key

```bash
python set_api_key.py  # 输入你的 API Key
```
然后重启终端并重新激活虚拟环境。

## 3. 初始化 FAISS 索引

在使用搜索功能之前，必须先初始化 FAISS 索引：

```bash
# 初始化所有平台的索引
python manage.py initialize_index --source=all

# 或者初始化特定平台的索引
python manage.py initialize_index --source=reddit
python manage.py initialize_index --source=stackoverflow
python manage.py initialize_index --source=rednote
```

初始化后，将数据库内容添加到索引中：

```bash
python manage.py index_content --source=all
```

> **注意**：每次添加新内容到数据库后，都需要运行 `index_content` 命令来更新索引。



### 3.1 索引文件结构与检索机制

 - FAISS索引系统使用两个关键文件存储数据：
    - index.faiss: 存储向量索引结构，用于快速相似性搜索
    - index.pkl: 存储文档内容和元数据(来源、ID、作者等)，与向量索引中的ID一一对应

系统使用混合检索方法提高结果相关性

### 3.2 相关性阈值与文档数量要求
- 系统仅返回相关度超过阈值(默认0.6)的文档
- RAG仅在找到至少5个高质量相关文档时激活
- 当相关文档不足时，系统回退到直接回答模式

## 4. 测试与数据准备

# 运行测试
```bash
python manage.py test_rag
```

此命令会执行：
- 生成测试数据(包括 Library A/B, Reddit 内容等)
- 构建 Embeddings 并写入数据库
- 建立 FAISS 索引
- 执行一系列测试查询

## 5. 数据库迁移

当修改模型结构时，需要进行数据库迁移：

```bash
# 1. 生成迁移文件
python manage.py makemigrations

# 2. 应用迁移到数据库
python manage.py migrate

# 3. 检查迁移状态
python manage.py showmigrations
```

## 6. 爬虫模式

爬虫系统支持两种工作模式：

### 6.1 即时索引模式
- 爬取内容的同时立即进行向量化和索引
- 索引完成后自动清除数据库中的原文内容以节省存储空间
- 适用于需要立即搜索新内容的场景

```bash
python manage.py test_rednote_crawler --url "your_url" --immediate-indexing
```

### 6.2 存储模式 (默认)
- 仅将爬取的内容存入数据库，不进行索引
- 适用于批量数据收集，稍后统一索引的场景

```bash
python manage.py test_rednote_crawler --url "your_url"
```

### 6.3 后续批量索引
   - 对存储模式下收集的内容进行批量索引
   - 支持按平台筛选进行索引
   ```bash
   # 通过 API 触发索引
   curl -X POST http://localhost:8000/index_content/ -d "source=rednote"
   ```

> **注意**：无论是即时索引还是后续批量索引，内容一旦被成功索引到 FAISS 中，原文将从数据库中清除以优化存储空间。原文内容会被保存在 FAISS 索引中用于后续检索。

## 7. 运行服务器

```bash
python manage.py runserver
```

服务器默认在 http://127.0.0.1:8000 提供服务。

## 8. 使用 RAG 进行查询

1. 在浏览器访问 http://127.0.0.1:8000
2. 输入查询语句，例如：`Which library is recommended the most in r/study?`
3. 系统将：
   - 利用 FAISS 查找相似文档
   - 结合检索到的文档进行回答
   - 在网页上渲染回答及相关信息

## 9. 流程图参考
#### 序列图

```mermaid
sequenceDiagram
    %% 主要角色定义
    actor User
    participant Views as SearchView
    participant Memory as MemoryService
    participant Index as IndexService
    participant FAISS as FaissManager
    participant Embed as EmbeddingModel
    participant LLM as GeminiAI
    participant DB as Database

    %% 搜索流程
    rect rgb(200, 220, 255)
        Note over User,DB: Search Flow
        User->>Views: POST /search/ with query
        Views->>Memory: get_recent_memory(session_id)
        Memory-->>Views: recent chat history
        
        Views->>Index: faiss_search(query, platform)
        Index->>Embed: embed_query(query)
        Embed-->>Index: query_vector
        
        Index->>FAISS: similarity_search(query_vector)
        FAISS->>DB: get metadata for matches
        DB-->>FAISS: document metadata
        FAISS-->>Index: similar documents
        
        Index->>LLM: process_search_query(query, docs, chat_history)
        LLM-->>Index: generated response
        
        Index-->>Views: {answer, metadata, docs}
        Views->>Memory: add_to_memory(user_query, ai_response)
        Views-->>User: render response with template
    end

    %% 索引构建流程
    rect rgb(220, 200, 255)
        Note over User,DB: Index Building Flow
        User->>Index: build_faiss_index(platform)
        Index->>DB: get_unindexed_content()
        DB-->>Index: content_objects
        
        loop For each batch
            Index->>Embed: embed_documents(texts)
            Embed-->>Index: document_vectors
            Index->>FAISS: add_embeddings(vectors, metadata)
            Index->>DB: update_index_status()
        end
        
        Index->>FAISS: save_index()
        FAISS-->>Index: index saved
        Index-->>User: index build complete
    end
```

#### 生成序列图
预览 Mermaid 图表：
1. 安装插件 "Markdown Preview Enhanced"
2. 使用 Ctrl+K V 打开预览

#### 系统流程图

![系统流程图](diagram.png)

#### 生成流程图

系统流程图使用 Graphviz DOT 语言定义。要将 DOT 文件转换为图像，请使用以下命令：

```bash
# 安装 Graphviz (如果尚未安装)
# Ubuntu/Debian
sudo apt-get install graphviz

# macOS
brew install graphviz

# Windows (使用 Chocolatey)
choco install graphviz

# 生成 PNG 图像
dot -Tpng diagram.dot -o diagram.png
```

## 10. 可视化数据库内容

```bash
# 创建超级用户
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver
```

访问 Django Admin：http://127.0.0.1:8000/admin

## 11. 管理索引

删除当前的索引库：
```bash
rm -rf faiss_index/
```

## 12. 爬虫配置

### ChromeDriver 下载
找到合适的版本下载后，解压并添加到系统路径：
```bash
sudo mv chromedriver-mac-arm64.zip /usr/local/bin/
```

运行 `test_selenium.py` 文件确保能够正确打印 "Page title is: Google"

## 13. 配置参数

- `SEARCH_DEFAULT_TOP_K = 10`
- `SEARCH_TEST_TOP_K = 5`

## 14. 项目启动步骤

### 后端
```bash
python manage.py runserver
```

### 前端
```bash
cd Frontend
npm run dev
```

# 15. 将本地数据（sqlite + faiss相关）push到github上 以及数据获取

## 将本地数据（sqlite + faiss相关）push到github上

## 安装Git LFS (需要添加到README中)
brew install git-lfs  # macOS
which git-lfs
git-lfs install

## 设置Git LFS
git lfs install

## 跟踪SQLite数据库文件
git lfs track "*.sqlite3"
git lfs track "*.db"

## 跟踪FAISS索引文件
git lfs track "*.faiss"
git lfs track "*.pkl"

## 检查哪些文件已被Git LFS跟踪
git lfs ls-files


## 数据文件：
本项目包含以下预构建的数据文件以便快速开始测试：

- **SQLite数据库** (`db.sqlite3`): 包含已爬取和处理的内容数据
- **FAISS索引目录** (`faiss_index/`): 包含各平台的预构建向量索引
  - `faiss_index/reddit/`: Reddit数据索引
  - `faiss_index/stackoverflow/`: StackOverflow数据索引
  - `faiss_index/rednote/`: Rednote数据索引

### 获取数据文件：
通过Git LFS管理。克隆项目后，运行以下命令获取数据文件

安装Git LFS (如果尚未安装)
macOS: brew install git-lfs
Ubuntu: sudo apt-get install git-lfs
Windows: choco install git-lfs
初始化Git LFS
git lfs install
拉取LFS文件
git lfs pull

### 数据文件提交：
# 1. 先提交.gitattributes文件和README修改
git add .gitignore .gitattributes README.md
git commit -m "Add Git LFS configuration and update README"

# 2. 然后添加数据库和索引文件
git add db.sqlite3 faiss_index/
# 此时Git LFS应该会显示跟踪信息，如：
# "Tracking db.sqlite3"
# "Tracking faiss_index/reddit/index.faiss"

# 3. 提交大文件
git commit -m "Add SQLite database and FAISS indexes via Git LFS"

# 4. 推送到GitHub
git push origin main  # 或您使用的分支名

使用前端服务器提供的 URL：http://localhost:5173/static/ 访问