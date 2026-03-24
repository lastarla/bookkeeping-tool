# bookkeeping-tool

一个本地账单导入、标准化、查询与可视化工具。

它支持读取 CSV / XLSX 账单文件，将数据清洗后写入 SQLite，并提供命令行查询、汇总和本地 Web 看板。

## 适合做什么

- 导入本地账单文件
- 自动提取 `owner` / `platform`
- 避免重复导入同一份文件
- 查询交易明细
- 按月份、分类、平台、方向做汇总
- 在本地浏览收支概览和趋势

## 安装

面向普通 CLI 用户，推荐两种方式。

### 方案一：pipx 安装（推荐）

```bash
pipx install "git+https://github.com/<org>/bookkeeping-tool.git"
```

安装后验证：

```bash
bookkeeping --help
```

### 方案二：虚拟环境安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "git+https://github.com/<org>/bookkeeping-tool.git"
```

安装后验证：

```bash
bookkeeping --help
```

如果你的 Python 环境受 PEP 668 限制，优先使用 `pipx` 或虚拟环境安装。

## 文件命名规则

导入时会从文件名提取来源信息：

- 文件名按 `_` 分段
- 第一个片段是 `owner`
- 第二个片段是 `platform`
- 没有第二个片段时，`platform = None`

例如：

- `example.csv` -> `owner=example`
- `example_alipay_2025.csv` -> `owner=example, platform=alipay`
- `example_wx_2025.xlsx` -> `owner=example, platform=wx`

## CLI 快速开始

### 导入账单

```bash
bookkeeping import ./material/example_alipay.csv --project-root ./bookkeeping-tool
```

### 查询交易

```bash
bookkeeping query --project-root ./bookkeeping-tool --owner example --platform alipay --limit 5 --json
```

### 汇总概览

```bash
bookkeeping summary overview --project-root ./bookkeeping-tool --view monthly --month 2025-03 --json
```

### 启动本地服务

```bash
bookkeeping serve --project-root ./bookkeeping-tool
```

### 清空数据库

```bash
bookkeeping reset --project-root ./bookkeeping-tool --yes
```

## Web 看板

项目同时提供本地 Web 看板：

- 后端：FastAPI
- 前端：React + TypeScript + Vite

### 启动后端

```bash
cd ./bookkeeping-tool
python -m server.run
```

默认地址：

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`

### 启动前端

```bash
cd ./bookkeeping-tool/frontend
npm install
npm run dev
```

开发模式下：

- 前端默认 `http://127.0.0.1:5173`
- `/api` 会代理到 `http://127.0.0.1:8000`

## 当前支持的能力

- 导入 `.csv` 和 `.xlsx` 账单
- 保存原始行和标准化交易
- 基于文件 hash 做重复导入判断
- 按日期、owner、platform、direction、category 查询
- 按 month / category / owner / platform / direction 汇总
- 通过 Web 页面查看概览、分类、趋势和交易明细

## 常见使用路径

最常见的一条路径是：

1. 安装 `bookkeeping`
2. 导入账单文件
3. 用 CLI 做查询或汇总
4. 启动本地 Web 看板查看结果

如果你是开发者，项目结构、运行方式和约束请查看 `.claude/CLAUDE.md`。
