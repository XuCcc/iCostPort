# iCostPort
— 将各类银行、支付平台账单导出为ICost的 CSV 格式。

## ✨ 特性

- **多源支持** — 支持支付宝、京东、美团、拼多多、微信等主流平台账单格式
- **自动分类** — 基于关键词规则自动分类，并可接入 AI 进行智能分类
- **数据清洗** — 去重、过滤、排序等处理能力
- **标准输出** — 生成易于导入的 CSV 格式（含日期、金额、分类等字段）
- **灵活配置** — YAML 配置分类体系和处理规则，支持环境变量存储敏感信息

## 🚀 快速开始

### 安装

```bash
git clone <repo-url>
cd iCostPort
uv sync
```

### 基本用法

```bash
# 将单个或多个账单文件转换为 CSV
uv run icostport convert /path/to/bill1.csv /path/to/bill2.csv \
  --config config.yml \
  --output result.csv
```

### 输出格式

生成的 CSV 包含以下字段（可直接导入记账软件）：

| 字段 | 说明 |
|------|------|
| 日期 | 交易时间（格式：`YYYY年MM月DD日 HH:MM:SS`） |
| 类型 | 交易类型（收入/支出） |
| 金额 | 交易金额 |
| 一级分类 | 分类（如：餐饮、交通、购物） |
| 二级分类 | 子分类（如：三餐、打车、日用品） |
| 账户1 | 来源账户 |
| 账户2 | 目标账户 |
| 备注 | 交易说明 |
| 货币 | 币种 |
| 标签 | 自定义标签 |

## ⚙️ 配置

### 创建配置文件

从示例配置复制：

```bash
cp config.example.yml config.yml
```

### 关键配置项

#### `categories`（必须）

定义分类体系（一级分类 → 二级分类列表）：

```yaml
categories:
  餐饮:
    - 三餐
    - 夜宵
  交通:
    - 公交地铁
    - 打车
  购物:
    - 日用品
    - 数码
```

#### `rules`

基于关键词的自动分类规则：

```yaml
rules:
  - keywords: ["麦当劳", "肯德基", "外卖"]
    primary: 餐饮
    secondary: 三餐
  - keywords: ["地铁", "公交"]
    primary: 交通
    secondary: 公交地铁
```

#### `processing`

数据处理配置：

```yaml
processing:
  dedupe:
    enabled: true
    on_duplicate: keep_first  # keep_first 或 keep_last
  filter:
    min_amount: 0.01
    excluded_keywords: ["测试数据"]
```

#### `ai`（可选）

启用 AI 智能分类：

```yaml
ai:
  enabled: true
  provider: openai
  base_url: https://api.openai.com/v1
  model: gpt-4-mini
  api_key_env: OPENAI_API_KEY      # 只通过环境变量读取密钥
  only_if_uncategorized: true       # 仅对未分类项处理
  max_items: 50
  timeout: 30
```

### 配置查找顺序

当不传 `--config` 时，按以下顺序查找：

1. 环境变量 `ICOSTPORT_CONFIG`
2. 当前目录 `./config.yml`
3. 用户目录 `~/.config/icostport/config.yml`

若都不存在，使用内置最小配置。

## 📋 命令行选项

```bash
uv run icostport convert [OPTIONS] [PATHS]...

参数：
  PATHS                    输入文件路径（支持多个）

选项：
  -c, --config PATH        配置文件路径
  -o, --output PATH        输出 CSV 路径（必须）
  --account-parse          解析输出账户字段（默认关闭）
  --only-expense / --all-types  仅保留支出（默认开启）
  -v, --verbose            详细日志输出
```

## 📝 支持的账单格式

| 源 | 文件格式 | 说明 |
|----|---------|------|
| 支付宝 | CSV | 账单导出 |
| 京东 | CSV | 交易流水 |
| 美团 | CSV | 账单导出 |
| 拼多多 | CSV | 订单列表 |
| 微信 | CSV | 账单导出 |

## 🔄 处理流程

```
解析 (parse_all)
  ↓
合并 (merge) → 去重 (dedupe) → 过滤 (filter) → 排序 (organize)
  ↓
分类 (categorize)
  ├─ 规则分类 (rules)
  └─ AI 分类 (ai_categorize)
  ↓
输出 CSV (write_icost)
```