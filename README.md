# iCostPort

将多来源账单文件转换为 ICost 可导入的 `.xlsx`。

## 配置文件

- 推荐从 `config.example.yml` 复制为你的实际配置。
- 支持的关键分区：`categories`、`rules`、`processing`、`ai`。
- 配置使用 `PyYAML + pydantic` 校验，启动时会检查：
  - `categories` 必须是 `一级分类 -> 二级分类列表`；
  - 每个 `rules` 项都必须包含 `keywords`、`primary`、`secondary`；
  - 若 `categories` 非空，`rules` 的分类组合必须在白名单内；
  - `processing.dedupe.on_duplicate` 仅支持 `keep_first` / `keep_last`。

## CLI `--config` 查找顺序

当不传 `--config` 时，按以下顺序查找配置文件：

1. 环境变量 `ICOSTPORT_CONFIG`
2. 当前目录 `./config.yml`
3. 用户目录 `~/.config/icostport/config.yml`

若都不存在，则回退到内置最小默认配置（主要用于开发与测试）。
