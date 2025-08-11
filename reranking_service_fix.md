
# 重排序服务配置修复

## 问题
重排序服务没有正确读取配置文件中的模型配置，而是使用了硬编码的默认模型。

## 修复方案
修改 `rag_system/services/reranking_service.py` 中的模型配置读取逻辑：

```python
# 原代码 (第23行左右)
self.model_name = self.config.get('model_name', 'cross-encoder/ms-marco-MiniLM-L-6-v2')

# 修复后的代码
self.model_name = self.config.get('model_name') or self.config.get('model', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
```

## 配置文件确认
确保 config/development.yaml 中有正确的重排序配置：

```yaml
reranking:
  provider: siliconflow
  model: BAAI/bge-reranker-v2-m3
  model_name: BAAI/bge-reranker-v2-m3  # 添加这行以确保兼容性
  api_key: sk-test-update-123456789
  base_url: https://api.siliconflow.cn/v1
  batch_size: 32
  max_length: 512
  timeout: 30
```
