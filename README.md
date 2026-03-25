# bookkeeping-tool

一个本地账单导入、标准化、查询与可视化工具。

支持导入 CSV / XLSX 账单，写入本地 SQLite，并通过 CLI 和本地 Web 页面查看数据。

## 安装

### 方式一：Homebrew（macOS 推荐）

```bash
brew install lastarla/tap/bookkeeping-tool
```

如果你已经添加过 tap，也可以直接：

```bash
brew install bookkeeping-tool
```

### 方式二：pipx

推荐使用 HTTPS：

```bash
pipx install "git+https://github.com/lastarla/bookkeeping-tool.git"
```

如果你已经配置了 GitHub SSH，也可以：

```bash
pipx install "git+ssh://git@github.com/lastarla/bookkeeping-tool.git"
```

安装后验证：

```bash
bookkeeping --help
```

如果你的 Python 环境受 PEP 668 限制，优先使用 `pipx` 或虚拟环境安装。

## 卸载

### 卸载 Homebrew 安装

```bash
brew uninstall bookkeeping-tool
brew untap lastarla/tap  # 可选：不再需要该 tap 时
```

### 卸载 pipx 安装

```bash
pipx uninstall bookkeeping-tool
```

### 卸载虚拟环境安装

```bash
deactivate
rm -rf .venv
```

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

## 快速开始

`--project-root` 表示运行数据根目录。默认解析顺序：

1. `--project-root`
2. 环境变量 `BOOKKEEPING_PROJECT_ROOT`
3. 当前命令执行目录

### 1. 导入账单

```bash
bookkeeping import ./material/example_alipay.csv --project-root ./bookkeeping-tool-data
```

### 2. 查询交易

```bash
bookkeeping query --project-root ./bookkeeping-tool-data --limit 5 --json
```

### 3. 查看汇总

```bash
bookkeeping summary overview --project-root ./bookkeeping-tool-data --view monthly --month 2025-03 --json
```

### 4. 启动本地页面

```bash
bookkeeping serve --project-root ./bookkeeping-tool-data
```

打开：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

### 5. 清空数据库

```bash
bookkeeping reset --project-root ./bookkeeping-tool-data --yes
```

## 自定义 mappings（可选）

如果你想覆盖内置字段映射，可以准备一个目录，里面放 `csv.json` / `xlsx.json`：

```bash
bookkeeping import ./material/example_alipay.csv --project-root ./bookkeeping-tool-data --mapping-dir ./my-mappings --json
```

## 当前支持的能力

- 导入 `.csv` 和 `.xlsx` 账单
- 保存原始行和标准化交易
- 基于文件 hash 做重复导入判断
- 按日期、owner、platform、direction、category 查询
- 按 month / category / owner / platform / direction 汇总
- 通过 Web 页面查看概览、分类、趋势和交易明细

## 开发说明

如果你需要一键清理旧产物并重新构建发布包，可以在仓库根目录执行：

```bash
./scripts/build-release.sh
```

也可以这样执行：

```bash
sh ./scripts/build-release.sh
```

这个脚本会自动：

1. 清理 `build/`、`dist/`、`*.egg-info` 等旧产物
2. 构建前端静态资源
3. 执行 `python -m build`
4. 产出最终发布包到 `dist/`

### 自动发版

前置条件：

- 已安装 `gh`
- 已执行 `gh auth login`
- `bookkeeping-tool` 和 `homebrew-tap` 都已配置 GitHub SSH push 权限
- `homebrew-tap` 位于 `../homebrew-tap`
- 执行前，`bookkeeping-tool` 和 `homebrew-tap` 两个仓库工作区都必须是干净状态

日常使用步骤：

1. 在 `bookkeeping-tool` 修改代码
2. 更新 `pyproject.toml` 中的版本号
3. 先手动提交 `bookkeeping-tool` 当前版本的所有改动
4. 在仓库根目录执行：

```bash
./scripts/release.sh
```

这个脚本会自动：

1. 执行 `./scripts/build-release.sh`
2. push `bookkeeping-tool` 当前分支
3. 创建并 push 对应 tag
4. 用 `gh` 创建 GitHub Release
5. 下载 release tarball 并计算 sha256
6. 更新并提交 `../homebrew-tap/Formula/bookkeeping-tool.rb`
7. push `homebrew-tap`

发版完成后可验证：

```bash
brew install lastarla/tap/bookkeeping-tool
bookkeeping --help
```

如果本机已经安装过旧版本，也可以：

```bash
brew upgrade bookkeeping-tool
bookkeeping --help
```

常用参数：

- 预演（不发布）：

```bash
./scripts/release.sh --dry-run
```

- 跳过构建（只走发布链路）：

```bash
./scripts/release.sh --skip-build
```

- 自定义 GitHub Release 文案：

```bash
./scripts/release.sh --notes "Release v0.1.1"
```

开发结构、运行方式、构建和发布流程见：

- `.claude/CLAUDE.md`
