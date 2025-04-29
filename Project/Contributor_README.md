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
  - `HybridRetriever.retrieve(query=search_query, top_k=20, relevance_threshold=0.5)` 使用 FAISS 索引和 BM25 算法进行搜索，返回相似文档。

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


