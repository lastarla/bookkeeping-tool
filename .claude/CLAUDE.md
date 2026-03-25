# 开发说明

## 项目定位
- 这是账单导入、标准化、查询、汇总与本地可视化的核心仓库。
- 面向用户的入口是根目录 `README.md`、`bookkeeping` CLI 和本地 Web 看板。
- 这里承载真实业务逻辑；如果后续有 skill / agent / 其他上层集成，应尽量复用本仓库能力，而不是重复实现账单逻辑。

## 关键目录
- `src/bookkeeping_tool/`
  - 核心 Python 包根。
- `src/bookkeeping_tool/cli/`
  - Typer CLI 入口与各命令实现。
- `src/bookkeeping_tool/services/`
  - 导入、查询、汇总等业务编排层。
- `src/bookkeeping_tool/repositories/`
  - SQLite 读写。
- `src/bookkeeping_tool/parsers/`
  - CSV / XLSX 解析。
- `src/bookkeeping_tool/normalizers/`
  - 字段映射与标准化。
- `src/bookkeeping_tool/web/`
  - FastAPI 接口与 app 创建入口。
- `src/bookkeeping_tool/configs/mappings/`
  - 不同来源账单的字段映射配置。
- `frontend/`
  - React + Vite 前端源码。
- `data/`
  - 本地开发时可选的运行数据根目录，不提交。

## 本地运行
### Python CLI
- 包入口定义在 `pyproject.toml`
- console script: `bookkeeping = "bookkeeping_tool.cli.app:main"`
- `--project-root` 表示运行数据根目录
- 默认运行数据根目录解析顺序：`--project-root` > `BOOKKEEPING_PROJECT_ROOT` > 当前工作目录

常见命令：
- `bookkeeping --help`
- `bookkeeping import <file>`
- `bookkeeping query --json`
- `bookkeeping summary overview --json`
- `bookkeeping serve --open`
- `bookkeeping reset --yes`

### Web 后端
- 最短开发启动命令：`PYTHONPATH=src python -m bookkeeping_tool.run`
- 如果想显式指定运行数据目录：`BOOKKEEPING_PROJECT_ROOT=./bookkeeping-tool-data PYTHONPATH=src python -m bookkeeping_tool.run`
- 安装后的 CLI 方式：`bookkeeping serve --project-root ./bookkeeping-tool-data`
- 默认端口 `http://127.0.0.1:8000`
- 如果 8000 被占用，先释放端口再启动

### 前端开发
- 目录：`frontend/`
- 最短开发启动命令：`cd frontend && npm install && npm run dev`
- Vite 开发服务默认 `http://127.0.0.1:5173`
- 前端开发时通常配合后端开发命令一起开：`PYTHONPATH=src python -m bookkeeping_tool.run`

### 开发态工作流
#### 只改 Python / 后端代码
1. 修改 `src/bookkeeping_tool/` 下的代码
2. 在仓库根目录执行：`PYTHONPATH=src python -m bookkeeping_tool.run`
3. 或只验证 CLI：`PYTHONPATH=src python -m bookkeeping_tool.cli.app --help`
4. 这一步不会生成安装包，代码仍然直接来自 `src/bookkeeping_tool/`

#### 只改前端代码
1. 修改 `frontend/src/` 下的代码
2. 前端开发：`cd frontend && npm install && npm run dev`
3. 后端开发：在仓库根目录执行 `PYTHONPATH=src python -m bookkeeping_tool.run`
4. 这一步也不会生成安装包；前端页面来自 Vite dev server，Python 代码仍来自 `src/bookkeeping_tool/`

### 构建与发布
#### 统一构建入口（推荐）
- 在仓库根目录执行：`./scripts/build-release.sh`
- 或：`sh ./scripts/build-release.sh`
- 这个脚本会自动：
  1. 清理 `build/`、`dist/`、`*.egg-info`、`src/bookkeeping_tool.egg-info`
  2. 执行前端构建
  3. 执行 `python -m build`
  4. 产出最终发布包到 `dist/`

#### 前端单独构建
1. 执行：`cd frontend && npm install && npm run build`
2. 构建产物输出到：`src/bookkeeping_tool/web/static/`
3. 这些静态文件会在后续 `python -m build` 时一起进入 Python 包

#### Python 包单独构建
1. 回到仓库根目录：`cd /Users/starlee/life_space/book/bookkeeping-tool`
2. 如需手动清理：`rm -rf build dist *.egg-info src/bookkeeping_tool.egg-info`
3. 如果前端有改动，先执行前端构建
4. 执行：`python -m build`
5. 产物目录：`dist/`
6. 产物内容：
   - `dist/*.whl`
   - `dist/*.tar.gz`

#### 构建完成后代码在哪
- Python 源码仍在：`src/bookkeeping_tool/`
- 前端构建产物在：`src/bookkeeping_tool/web/static/`
- 可发布安装包在：`dist/`
- 安装后代码会进入目标环境的 `site-packages/bookkeeping_tool/...`
- 安装后不应再出现顶层 `server/...`

#### 本地发布 / 安装验证
- 用 pip 安装构建产物：`pip install dist/*.whl`
- 用 pipx 安装构建产物：`pipx install dist/*.whl`
- 安装后验证：
  - `bookkeeping --help`
  - `bookkeeping serve --project-root <data-dir>`
  - 包内资源 `bookkeeping_tool.configs.mappings` 与 `bookkeeping_tool.web.static` 可正常读取

## 数据与约束
- 默认 SQLite 路径：`<project_root>/data/bookkeeping.db`
- 导入依赖文件名元信息：文件名按 `_` 分段，第一个片段为 `owner`，第二个片段为 `platform`
- 用户 README 只保留用户上手所需信息；架构、目录职责、开发约束优先写在这里
- 新增 CLI / Web 能力时，尽量保持 service 层复用，不要把业务逻辑堆到 CLI 或路由层

## 提交与忽略
不要提交：
- `.venv/`
- `*.egg-info/`
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
