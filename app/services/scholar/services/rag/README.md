# Vector Search Integration - Vertex AI Vector Search

本项目已从 Qdrant 迁移到 Google Cloud Vertex AI Vector Search，提供更强大的向量搜索能力。

## 配置说明

### 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# Vertex AI 基础配置
VERTEX_PROJECT_ID=your-gcp-project-id
VERTEX_LOCATION=us-central1

# Vertex AI Vector Search 配置
VERTEX_INDEX_ID=your-vector-index-id
VERTEX_ENDPOINT_ID=your-endpoint-id
VERTEX_DEPLOYED_INDEX_ID=your-deployed-index-id

# 向量存储后端选择（默认为 vertex）
VECTOR_STORE_BACKEND=vertex
```

### Google Cloud 认证

确保您的环境已正确配置 Google Cloud 认证：

1. **服务账号密钥文件**：
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
   ```

2. **或使用 gcloud CLI**：
   ```bash
   gcloud auth application-default login
   ```

## Vertex AI Vector Search 设置

### 1. 创建 Vector Search Index

```python
from app.services.scholar.services.rag.vertex_vector_store import VertexVectorStore

# 创建向量存储实例
vector_store = VertexVectorStore()

# 创建新的索引
index_id = vector_store.create_index(
    display_name="my-vector-index",
    dimensions=768,  # 根据您的嵌入模型调整
    distance_measure="COSINE_DISTANCE"
)
```

### 2. 创建 Index Endpoint

在 Google Cloud Console 中：
1. 导航到 Vertex AI > Vector Search
2. 创建新的 Index Endpoint
3. 记录 Endpoint ID

### 3. 部署 Index 到 Endpoint

```python
# 部署索引到端点
success = vector_store.deploy_index(
    index_id="your-index-id",
    endpoint_id="your-endpoint-id",
    deployed_index_id="my-deployed-index"
)
```

## 使用方法

### 基本向量操作

```python
from app.services.scholar.services.rag.vector_store_factory import VectorStoreFactory

# 创建向量存储实例
vector_store = VectorStoreFactory.create_vector_store()

# 插入向量
vectors = [
    {
        "id": "doc_1",
        "vector": [0.1, 0.2, 0.3, ...],  # 768维向量
        "metadata": {"doc_id": "document_1", "type": "text"}
    }
]
vector_store.upsert_vectors(vectors)

# 搜索相似向量
query_vector = [0.1, 0.2, 0.3, ...]
results = vector_store.search_vectors(
    query_vector=query_vector,
    limit=10
)

# 获取特定文档的向量
doc_vectors = vector_store.get_vectors("document_1")
```

### 在 RAG 服务中使用

```python
from app.services.scholar.services.rag_service import DomainRAGService

# RAG 服务自动使用 Vertex AI Vector Search
rag_service = DomainRAGService()

# 生成知识图谱
result = rag_service.run({
    "doc_id": "document_1",
    "threshold": 0.5
})

# 查询
result = rag_service.run({
    "query": "用户查询文本"
})
```

## 特性

### Vertex AI Vector Search 优势

1. **高性能**：支持大规模向量搜索
2. **自动扩展**：根据负载自动调整资源
3. **高可用性**：Google Cloud 基础设施保障
4. **集成性**：与其他 Google Cloud 服务无缝集成
5. **安全性**：企业级安全和访问控制

### 支持的距离度量

- `COSINE_DISTANCE`：余弦距离（推荐用于文本嵌入）
- `DOT_PRODUCT_DISTANCE`：点积距离
- `EUCLIDEAN_DISTANCE`：欧几里得距离

### 向量维度支持

- 支持 1-2048 维向量
- 推荐使用 768 维（BERT/OpenAI 嵌入标准）

## 故障排除

### 常见问题

1. **认证错误**：
   - 确保 `GOOGLE_APPLICATION_CREDENTIALS` 正确设置
   - 验证服务账号具有必要权限

2. **索引未找到**：
   - 检查 `VERTEX_INDEX_ID` 配置
   - 确保索引在正确的项目和区域

3. **端点连接失败**：
   - 验证 `VERTEX_ENDPOINT_ID` 和 `VERTEX_DEPLOYED_INDEX_ID`
   - 确保索引已成功部署到端点

### 权限要求

服务账号需要以下权限：
- `aiplatform.indexes.get`
- `aiplatform.indexes.create`
- `aiplatform.indexEndpoints.get`
- `aiplatform.indexEndpoints.deploy`
- `aiplatform.indexEndpoints.queryVectors`

## 性能优化

### 批量操作

```python
# 批量插入向量（推荐）
large_vector_batch = [...]  # 大量向量数据
vector_store.upsert_vectors(large_vector_batch)
```

### 搜索优化

```python
# 使用适当的 topk 值
results = vector_store.search_vectors(
    query_vector=query_vector,
    limit=50  # 根据需求调整
)
```

## 监控和日志

系统会自动记录以下信息：
- 向量操作性能指标
- 错误和异常
- API 调用统计

查看日志：
```bash
# 查看应用日志
tail -f /var/log/python-middleware/app.log
```

## 迁移说明

本项目已完全迁移到 Vertex AI Vector Search：
- ✅ Qdrant 依赖已移除
- ✅ 配置已更新为 Vertex AI
- ✅ 所有向量操作使用 Vertex AI API
- ✅ 向后兼容的接口保持不变

如需技术支持，请参考 Google Cloud Vertex AI Vector Search 官方文档。
