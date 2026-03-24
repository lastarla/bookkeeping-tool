# 开发说明

## 项目定位
- 这是账单导入、标准化、查询、汇总与本地可视化的核心仓库。
- 面向用户的入口是根目录 `README.md`、`bookkeeping` CLI 和本地 Web 看板。
- 这里承载真实业务逻辑；如果后续有 skill / agent / 其他上层集成，应尽量复用本仓库能力，而不是重复实现账单逻辑。

## 关键目录
- `server/bookkeeping/`
  - 核心 Python 业务代码。
- `server/bookkeeping/cli/`
  - Typer CLI 入口与各命令实现。
- `server/bookkeeping/services/`
  - 导入、查询、汇总等业务编排层。
- `server/bookkeeping/repositories/`
  - SQLite 读写。
- `server/bookkeeping/parsers/`
  - CSV / XLSX 解析。
- `server/bookkeeping/normalizers/`
  - 字段映射与标准化。
- `server/web/`
  - FastAPI 接口与 app 创建入口。
- `frontend/`
  - React + Vite 前端。
- `server/configs/mappings/`
  - 不同来源账单的字段映射配置。
- `server/data/`
  - 本地数据库与运行数据目录，不提交。

## 本地运行
### Python CLI
- 包入口定义在 `pyproject.toml`
- console script: `bookkeeping = "server.bookkeeping.cli.app:main"`
- 默认项目根目录通过 `server/bookkeeping/cli/common.py` 中的 `resolve_project_root()` 自动推导

常见命令：
- `bookkeeping --help`
- `bookkeeping import <file>`
- `bookkeeping query --json`
- `bookkeeping summary overview --json`
- `bookkeeping serve --open`
- `bookkeeping reset --yes`

### Web 后端
- CLI 方式：`bookkeeping serve --project-root ./bookkeeping_tool`
- 直接运行：`python -m server.run`

### 前端开发
- 目录：`frontend/`
- 常用命令：`npm install`、`npm run dev`
- Vite 开发服务默认 `http://127.0.0.1:5173`
- 后端默认 `http://127.0.0.1:8000`

## 数据与约束
- 默认 SQLite 路径：`server/data/bookkeeping.db`
- 导入依赖文件名元信息：文件名按 `_` 分段，第一个片段为 `owner`，第二个片段为 `platform`
- 用户 README 只保留用户上手所需信息；架构、目录职责、开发约束优先写在这里
- 新增 CLI / Web 能力时，尽量保持 service 层复用，不要把业务逻辑堆到 CLI 或路由层

## 提交与忽略
不要提交：
- `.venv/`
- `bookkeeping_tool.egg-info/`
- `server/data/`
- `frontend/node_modules/`
- `frontend/dist/`
- `__pycache__/`
- `*.pyc`
- 本地数据库、日志、IDE 配置

## 文档维护规则
- `README.md` 面向最终用户：讲清楚是什么、怎么安装、怎么用。
- `.claude/CLAUDE.md` 面向开发者与协作 agent：记录结构、约束、运行方式。
- 如果 README 中出现大段实现细节，优先迁移到这里或其他开发文档。
