---
name: add-bill-format
description: 为 iCostPort 新增银行或支付平台账单格式的解析支持
---

# Skill: 新增账单格式（add-bill-format）

## 何时使用

- 用户提出"新增某银行/某平台导出格式"的解析支持时使用。
- 目标是以最小改动接入新源格式，保持现有流水线接口不变。

## 输入信息（执行前确认）

- 新格式文件类型与样例（CSV/XLSX/其他）。
- 关键字段映射：日期、金额、收支类型、备注、账户、币种。
- 异常行规则：空行、缺列、非法日期/金额如何处理。

## 固定步骤清单

### 1. 新增 fixture
在 `tests/fixtures/` 新增脱敏样例文件（最小可复现，覆盖常见与异常行）。

### 2. 实现解析器
在 `src/icostport/sources/` 新建解析器模块（例如 `bank_xxx.py`）：
- 实现统一解析函数，输出 `Transaction` 列表
- 处理各种异常情况（缺列、空值、非法字段等）

### 3. 注册格式入口
在 `src/icostport/sources/registry.py` 注册该格式（按扩展名或约定规则）。

### 4. 编写测试
在 `tests/test_sources/` 新增对应测试（例如 `test_bank_xxx.py`）。

测试至少覆盖以下场景：
- 基本解析成功（行数与关键字段正确）
- 金额与日期解析正确（含正负号、精度、日期格式）
- 异常输入处理（缺列、空值、非法字段）
- 注册生效（可被 registry 正确选中）

### 5. 运行并验证测试
```bash
uv run pytest tests/test_sources/test_bank_xxx.py
# 必要时运行全部测试
uv run pytest
```

### 6. 更新文档
若新格式影响示例文档或配置说明，同步更新 `README.md` 或 `config.example.yml` 中相关示例。

## 必须遵守

- 不修改流水线公共接口：解析器输出保持 `Transaction` 列表语义
- 不在 `cli.py` 堆叠业务逻辑
- 解析结果必须可用于后续 `dedupe/filter/categorize/write_icost`
- 不硬编码敏感信息；密钥仅通过环境变量读取

## 交付检查（完成定义）

- [ ] 新增 fixture 已落地
- [ ] 解析器已实现
- [ ] registry 注册已完成
- [ ] 测试已编写并通过
- [ ] 不破坏已有测试
- [ ] 代码与命名风格符合项目规则
- [ ] 文档已更新（如需要）
