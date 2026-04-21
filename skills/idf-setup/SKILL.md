---
name: idf-setup
description: 当需要安装或管理 ESP-IDF 开发环境，包括版本选择和国内外安装源切换时使用。
---

# ESP-IDF 环境安装

## 适用场景

- 用户需要在本机安装 ESP-IDF 开发环境。
- 用户希望切换或升级已有的 ESP-IDF 版本。
- 需要确认当前 ESP-IDF 环境是否就绪（idf.py 可用、工具链完整）。
- 国内用户需要使用乐鑫镜像源加速下载。

## 必要输入

- 用户确认的 ESP-IDF 版本号（如 `v5.3.2`、`v5.2.5`），脚本可列出可用版本供选择。
- 用户位置：`china`（国内）或 `global`（海外），决定安装源和 pip 镜像。
- 可选的安装目标路径，默认为 `~/esp/esp-idf`。

## 自动探测

- 检查 `IDF_PATH` 环境变量是否已设置且指向有效的 ESP-IDF 目录。
- 扫描 `~/.espressif` 目录确认工具链安装状态。
- 扫描常见安装路径：`~/esp/esp-idf`、`/opt/esp-idf`、`C:\Espressif\frameworks\esp-idf`。
- 若已有安装，报告版本号和完整性状态，而不是直接覆盖。
- 若存在多个安装，返回 `ambiguous-context` 并列出所有候选。

## 执行步骤

1. 先阅读 [references/usage.md](references/usage.md)，确认本次是环境探测、列出版本，还是执行安装。
2. 若不确定环境状态，先运行自带脚本 [scripts/idf_setup.py](scripts/idf_setup.py) 的 `--detect` 模式确认。
3. 若用户未指定版本，使用 `--list-versions` 列出可用版本供用户选择。
4. 确认用户位置（国内/海外），使用 `--install --version <ver> --region <china|global>` 执行安装。
5. 安装完成后，使用 `--setup-env` 获取环境变量配置命令，提示用户执行。
6. 将安装路径和版本信息写回 `Project Profile`。

## 失败分流

- 当缺少 `git` 或 `python3` 时，返回 `environment-missing`。
- 当网络不可达或下载中断时，返回 `connection-failure`。
- 当 `install.sh` 执行失败（依赖缺失、磁盘空间不足）时，返回 `environment-missing`。
- 当存在多个已安装版本且用户未明确选择时，返回 `ambiguous-context`。
- 当安装路径无写入权限时，返回 `permission-problem`。

## 平台说明

- Linux/macOS 使用 `install.sh` 和 `export.sh`，Windows 使用 `install.bat` 和 `export.bat`。
- 国内用户设置 `IDF_GITHUB_ASSETS=dl.espressif.cn/github_assets` 加速工具链下载。
- 国内用户设置 `PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple` 加速 Python 包安装。
- Windows 上推荐使用 ESP-IDF Tools Installer 作为替代方案。

## 输出约定

- 输出安装命令、IDF 路径、版本号、所用安装源。
- 在 `Project Profile` 中写入 `idf_path`、`idf_version`、`idf_target`（若已配置）。
- 成功后推荐用户执行 `source export.sh` 激活环境，然后使用 `build-idf` 开始编译。

## 交接关系

- 当环境安装成功后，将结果交给 `build-idf` 开始编译流程。
- 当用户需要配置特定芯片目标时，也交给 `build-idf` 执行 `set-target`。
