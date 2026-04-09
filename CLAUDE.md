# iCostPort 项目指南

## 项目概述

iCostPort 是一个多源账单解析和分类系统，支持各种银行、支付平台等源格式的导入。

## 编码规范

### 注释与文档

- 所有 **Python 注释**（`#` 行注释、块说明）使用 **简体中文**
- 所有 **Python docstring**（模块、类、函数）使用 **简体中文**
- 修改已有英文注释时，优先改为中文或补充中文说明，与周围风格保持一致
- 标识符（模块名、变量、函数、类名）保持英文风格（与标准库/第三方 API 一致）

## 流水线架构

### 流水线阶段约束

端到端流水线顺序**必须固定**为：
```
parse_all → merge → processing → categorize → write_icost
```

### 各阶段职责

1. **CLI**: 仅负责参数解析和编排，**不在 `cli.py` 中堆叠业务逻辑**

2. **parse_all**: 调用已注册解析器列表

3. **merge**: 合并多源数据

4. **processing**: 至少包含以下步骤（固定顺序）
   - `dedupe`: 按日期+金额固定键去重
   - `filter`: 过滤
   - `organize/sort`: 整理排序

5. **categorize**: 固定顺序
   - 先 `rules`: 基于配置规则自动分类
   - 再 `ai_categorize`: 仅对未归类项或受配置约束的项进行 AI 分类

6. **write_icost**: 输出最终结果

### 编码原则

- 新增解析器时，**不得改动流水线公共接口**（输入/输出保持 `Transaction` 列表语义）
- 每个处理阶段应该是独立的、可复用的

## 配置管理

### 配置来源

- 配置统一来自 `config.yml`（或 `--config` 指定文件）
- 由 `core/settings.py` 负责加载与校验（使用 Pydantic）

### 配置字段约束

#### categories（必须）
- 是**封闭分类集**：一级分类 → 二级列表
- `rules` 和 AI 输出都**必须**落在白名单内

#### processing.dedupe
- `on_duplicate` 仅允许值：`keep_first` / `keep_last`

#### rules 结构
- 固定结构：`keywords`（非空列表）+ `primary`（一级分类）+ `secondary`（二级分类）

#### ai 配置
- 至少支持以下字段：
  - `enabled`: 是否启用 AI 分类
  - `provider`: AI 服务商
  - `base_url`: API 基础 URL
  - `model`: 模型名称
  - `api_key_env`: 环境变量名
  - `only_if_uncategorized`: 仅对未分类项处理
  - `max_items`: 最大处理数量
  - `timeout`: 超时时间

#### 安全约束
- **不要把敏感密钥硬编码进仓库文件**
- 敏感信息（API Key 等）**仅通过环境变量读取**

## 新增账单格式工作流（add-bill-format）

### 何时使用

用户提出"新增某银行/某平台导出格式"的解析支持时使用。

### 输入信息（执行前确认）

- 新格式文件类型与样例（CSV/XLSX/其他）
- 关键字段映射：日期、金额、收支类型、备注、账户、币种
- 异常行规则：空行、缺列、非法日期/金额如何处理

### 固定步骤清单

1. **新增 fixture**
   - 在 `tests/fixtures/` 新增脱敏样例文件
   - 最小可复现，覆盖常见与异常行

2. **实现解析器**
   - 在 `src/icostport/sources/` 新建解析器模块（例如 `bank_xxx.py`）
   - 实现统一解析函数，输出 `Transaction` 列表
   - 处理各种异常情况（缺列、空值、非法字段等）

3. **注册格式入口**
   - 在 `src/icostport/sources/registry.py` 注册该格式
   - 按扩展名或约定规则

4. **编写测试**
   - 在 `tests/test_sources/` 新增对应测试（例如 `test_bank_xxx.py`）
   - 至少覆盖以下场景：
     - 基本解析成功（行数与关键字段正确）
     - 金额与日期解析正确（含正负号、精度、日期格式）
     - 异常输入处理（缺列、空值、非法字段）
     - 注册生效（可被 registry 正确选中）

5. **运行并验证测试**
   ```bash
   uv run pytest tests/test_sources/test_bank_xxx.py
   # 必要时运行全部测试
   uv run pytest
   ```

6. **更新文档**（如需要）
   - 若新格式影响示例文档或配置说明
   - 同步更新 `README.md` 或 `config.example.yml` 中相关示例

### 必须遵守

- 不修改流水线公共接口：解析器输出保持 `Transaction` 列表语义
- 不在 `cli.py` 堆叠业务逻辑
- 解析结果必须可用于后续 `dedupe/filter/categorize/write_icost`
- 不硬编码敏感信息；密钥仅通过环境变量读取

### 交付检查（完成定义）

- [ ] 新增 fixture 已落地
- [ ] 解析器已实现
- [ ] registry 注册已完成
- [ ] 测试已编写并通过
- [ ] 不破坏已有测试
- [ ] 代码与命名风格符合项目规则
- [ ] 文档已更新（如需要）

## 开发工作流程

### 常见任务

#### 修复 Bug
1. 确认 Bug 的重现步骤
2. 编写或更新测试用例以覆盖 Bug 场景
3. 修复代码
4. 验证测试通过
5. 更新相关文档

#### 优化性能
1. 先测量/分析瓶颈
2. 制定优化方案
3. 实现变更
4. 验证性能改进
5. 确保测试通过

#### 添加新功能
1. 确认需求和设计
2. 编写测试用例
3. 实现功能
4. 验证测试通过
5. 更新文档

## 测试要求

### 覆盖范围

- 每新增一种源格式，必须同时新增对应 fixture 和单测
- CLI 改动必须包含 `tests/test_cli.py` 的回归用例（使用 `Click CliRunner` 或 subprocess）
- 至少覆盖：基本功能、边界情况、异常处理

### 运行测试

```bash
# 运行特定测试
uv run pytest tests/test_sources/test_xxx.py

# 运行全部测试
uv run pytest

# 带覆盖率
uv run pytest --cov=src/icostport
```


## 与我协作的建议

- 在修改流水线逻辑或配置结构前，先确认是否符合上述约束
- 对于新增源格式支持，直接告诉我样例文件或需求，我会按照工作流程完成
- 对于任何不明确的设计决策，可以查看最近的提交或配置示例
