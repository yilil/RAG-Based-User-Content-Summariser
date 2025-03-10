UI Design Figma Link(Dev mode)：https://www.figma.com/design/1BZN661uSi2y4FKDcd4RgZ/NextGen-AI-(Prototype)?node-id=0-1&m=dev
预览流程图：
```dot -Tpng diagram.dot -o diagram.png```

# 1. 环境搭建
1. Create a virtual environment

```python3 -m venv venv```

2. Activate the virtual environment

```source venv/bin/activate  # macOS/Linux```

```venv\Scripts\activate     # Windows```

3. Install project dependencies

```pip install -r requirements.txt```

# 2. To setup Gemini API Key
1.
```python set_api_key.py # enter your key``` 

2. then restart terminal and reactivate the virtual environment

```venv\Scripts\Activate.ps1  # Windows```

# 3. 额外库安装
1. langchain-google-genai Installation

```pip install -U langchain-google-genai```

2. Install `scikit-learn` for Similarity Search

```pip install scikit-learn```

3. bge-en-icl embedding model

```pip install sentence-transformers torch transformers```

4. Install Langchain community

```pip install langchain langchain-community```

# 4. 测试与数据准备
1. 安装 faker(随机生成测试数据)

```pip install faker```

2. 测试

```python manage.py test_rag```

此命令会执行：
- 清空数据库
- 生成测试数据(包括 Library A/B, Reddit 内容等)
- 构建 Embeddings 并写入数据库
- 建立 FAISS 索引
- 最后做一系列测试查询

# 5. 数据库迁移(初始化数据库)
若修改了模型结构(例如 RedditContent, StackOverflowContent 等)：
1. 生成迁移文件：

```python manage.py makemigrations```

2. 应用迁移：然后应用迁移到数据库：

```python manage.py migrate```

3. 检查迁移是否成功

```python manage.py showmigrations```

#### 6，爬虫模式
爬虫系统支持两种工作模式：

1. **即时索引模式**
   - 在爬取内容的同时立即进行向量化和索引
   - 索引完成后自动清除数据库中的原文内容以节省存储空间
   - 适用于需要立即搜索新内容的场景
   ```bash
   python manage.py test_rednote_crawler --url "your_url" --immediate-indexing
   ```

2. **存储模式**（default）
   - 仅将爬取的内容存入数据库，不进行索引
   - 适用于批量数据收集，稍后统一索引的场景
   ```bash
   python manage.py test_rednote_crawler --url "your_url"
   ```

3. **后续批量索引**
   - 对存储模式下收集的内容进行批量索引
   - 支持按平台筛选进行索引
   ```bash
   # 通过 API 触发索引
   curl -X POST http://localhost:8000/index_content/ -d "source=rednote"
   ```

> 注意：无论是即时索引还是后续批量索引，内容一旦被成功索引到 FAISS 中，原文将从数据库中清除以优化存储空间。原文内容会被保存在 FAISS 索引中用于后续检索。
2. 自定义管理命令 build_faiss

```python manage.py build_faiss```

# 7. 运行服务器
默认在 http://127.0.0.1:8000 提供服务
```python manage.py runserver```

# 8. 使用 RAG 进行查询
1. 在浏览器访问 http://127.0.0.1:8000, 即可打开搜索页面。
2. 输入查询语句, 如：

```Which library is recommended the most in r/study?```

3. 系统将调用后端：
- 利用 FAISS 查找相似文档；
- 结合retrieved documents进行回答；
- 最终在网页上渲染回答及相关信息。

# 9. 序列图参考
预览包含 Mermaid 图表的 Markdown 文档：
1. Install插件 "Markdown Preview Enhanced"
2. 使用 Ctrl+K V 打开预览
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
# 10, 可视化数据库内容
创建超级用户：
```python manage.py createsuperuser```
启动开发服务器并访问 Django Admin：
```python manage.py runserver```
```访问http://127.0.0.1:8000/admin```

# 11, 删除当前的索引库及索引 
```rm -rf faiss_index/ ```

# chromedriver下载：(爬虫时用到)
找到合适的版本下载后, 解压文件夹, 添加文件夹到：
```sudo mv chromedriver-mac-arm64.zip /usr/local/bin/```
运行test_selenium.py文件确保能够正确打印"Page title is: Google"

SEARCH_DEFAULT_TOP_K = 10
SEARCH_TEST_TOP_K = 5

# 项目启动步骤
后端: ```python manage.py runserver```
前端: ```cd Frontend```到Frontend文件夹使用 ```npm run dev```启动前端服务器
使用前端服务器提供的URL：“http://localhost:5173/static/”访问 he