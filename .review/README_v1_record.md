# 批阅记录

- **源文件**：README.md
- **源文件路径**：e:/code/memory/README.md
- **源文件版本**：未知
- **批阅时间**：20260911_1341
- **批阅版本**：v1
- **批注数量**：0
  - 评论：0
  - 删除：0
  - 后插：0
  - 前插：0

---

## 操作指令

> 指令已按**从后往前**排列（倒序），请严格按照顺序从上到下逐条执行。
> 每条指令提供了「文本锚点」用于精确定位，请优先通过锚点文本匹配来确认目标位置，blockIndex 仅作辅助参考。

---

## 原始数据（JSON）

> 如需精确操作，可使用以下 JSON 数据。其中 `blockIndex` 是基于空行分割的块索引（从0开始），`startOffset` 是目标文本在块内的字符偏移量（从0开始），可用于区分同一块内的重复文本。

```json
{
  "fileName": "README.md",
  "docVersion": "未知",
  "reviewVersion": 1,
  "annotationCount": 0,
  "rawMarkdown": "# AML Memory Adapter (skeleton)\r\n\r\n本地验证 AML 的 Add/Search 链路,无需报名、无需 Key。\r\n\r\n## 1. 安装 & 启动\r\npip install -r requirements.txt\r\npython -m uvicorn app:app --host 127.0.0.1 --port 8000\r\n\r\n## 2. 冒烟测试端点\r\ncurl http://127.0.0.1:8000/health\r\ncurl -X POST http://127.0.0.1:8000/add -H \"Content-Type: application/json\" \\\r\n  -d '{\"content\":\"Rob lives in Sweden\",\"type\":\"fact\",\"scope\":\"speaker_1\"}'\r\ncurl -X POST http://127.0.0.1:8000/search -H \"Content-Type: application/json\" \\\r\n  -d '{\"query\":\"Where does Rob live?\",\"scope\":\"speaker_1\",\"top_k\":3}'\r\n\r\n## 3. 跑通整条 Add->Search->eval_input.jsonl\r\npython make_eval_jsonl.py\r\n# 产出 eval_input.jsonl(含 retrieved_context 字段,pipeline.py 直接消费)\r\n\r\n## 4. (可选)接 AML 官方 pipeline 出真实分数\r\n# 克隆官方仓库拿 data/<bench>/pipeline.py,配好 OpenAI 兼容的\r\n# ANSWER_API_BASE / JUDGE_API_BASE 环境变量后:\r\n#   python data/locomo-refined/pipeline.py answer   --input eval_input.jsonl --output answers.jsonl\r\n#   python data/locomo-refined/pipeline.py evaluate --input eval_input.jsonl --answers answers.jsonl --output judge.jsonl\r\n# 注意:完整评测需要 AML 私有盲测集 + 申请的 AML Key,本地只能跑自有数据。\r\n",
  "annotations": []
}
```