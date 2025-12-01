# Claude Context - Canvas LMS Automation

> **用途**: 上下文清空后，让 Claude 快速理解项目
> **更新**: 2025-12-01

---

## 项目概述

Canvas LMS 自动化工具 - PyQt6 GUI + Python 后端。

**核心功能**: TODO获取、作业自动化、测验自动化、Cookie管理

---

## 当前结构 (已重构)

```
canvas_decon/
├── config.py           # 全局配置
├── main.py             # 入口
├── core/               # 核心工具
│   ├── exceptions.py   # 异常层次
│   ├── security.py     # 路径安全
│   ├── canvas_api.py   # API客户端
│   └── log.py          # 日志
├── func/               # 业务逻辑 (可CLI运行)
│   ├── ai.py           # AI调用 (Gemini/Claude)
│   ├── getTodos.py     # TODO获取
│   ├── getHomework.py  # 作业自动化
│   ├── getQuiz_ultra.py# 测验自动化
│   └── ...
└── gui/                # UI层
    ├── qt.py           # 主窗口
    ├── init.py         # 初始化
    ├── processors.py   # 内容处理
    ├── handlers/       # 窗口处理器 (7个)
    ├── core/           # 数据管理
    ├── details/        # 详情管理
    ├── widgets/        # 自定义控件
    └── learn/          # 学习模块
```

---

## 已完成 ✅

| 阶段 | 内容 | 行数变化 |
|-----|------|---------|
| Phase 1 | gui/qt_utils/ 扁平化 → gui/handlers/ + processors.py + init.py | -166 |
| Phase 2 | func/utilModels + utilPromptFiles → ai.py | -123 |
| Core | 新增 core/ 模块 (exceptions, security, canvas_api, log) | +673 |
| Security | 修复API密钥泄露、路径遍历、裸except | - |

---

## 关键模块

| 文件 | 用途 |
|-----|------|
| `func/ai.py` | AI模型列表 + API调用 |
| `func/getHomework.py` | 作业: 获取→LLM→生成docx→提交 |
| `func/getQuiz_ultra.py` | 测验: 解析题目→LLM→提交答案 |
| `gui/handlers/auto_detail.py` | AutoDetail窗口处理 |
| `core/canvas_api.py` | Canvas API封装 (未完全集成) |

---

## 测试

```bash
python -c "from func.ai import get_all_models; print(get_all_models())"
python -c "from gui.qt import CanvasApp; print('OK')"
python main.py  # 运行GUI
```

---

## 用户偏好

- 紧凑但可读
- 可测试
- 不过度抽象
- 业务逻辑不变

---

## 待办 (可选)

1. 继续简化 gui/ (合并 core/ + details/)
2. 替换 print() → log
3. 集成 core/canvas_api.py
