# ESP-IDF 环境安装 Skill 用法

这个 skill 自带了一个可执行脚本 [scripts/idf_setup.py](../scripts/idf_setup.py)，适合在需要安装、探测或管理 ESP-IDF 环境时直接调用。

## 能力概览

- 检测已安装的 ESP-IDF 环境及版本
- 列出可用的 ESP-IDF 发布版本
- 根据用户选择的版本和区域执行安装
- 支持国内镜像源（乐鑫 CDN + 清华 pip）和 GitHub 官方源
- 输出环境变量配置命令
- 输出结构化的安装结果报告

## 基础用法

```bash
# 探测已安装的 ESP-IDF 环境
python3 skills/idf-setup/scripts/idf_setup.py --detect

# 列出可用版本
python3 skills/idf-setup/scripts/idf_setup.py --list-versions

# 安装指定版本（海外用户）
python3 skills/idf-setup/scripts/idf_setup.py \
  --install --version v5.3.2 --region global

# 安装指定版本（国内用户，使用镜像加速）
python3 skills/idf-setup/scripts/idf_setup.py \
  --install --version v5.3.2 --region china

# 安装到自定义路径
python3 skills/idf-setup/scripts/idf_setup.py \
  --install --version v5.3.2 --region china --install-dir /opt/esp-idf

# 获取环境变量配置命令
python3 skills/idf-setup/scripts/idf_setup.py --setup-env --idf-path ~/esp/esp-idf
```

## 常见模式

### 1. 环境探测

```bash
python3 skills/idf-setup/scripts/idf_setup.py --detect
```

输出已安装的 ESP-IDF 路径、版本和工具链状态。

### 2. 国内用户完整安装流程

```bash
# 列出版本
python3 skills/idf-setup/scripts/idf_setup.py --list-versions

# 安装（自动使用乐鑫镜像和清华 pip 源）
python3 skills/idf-setup/scripts/idf_setup.py \
  --install --version v5.3.2 --region china

# 激活环境（用户需手动执行）
. ~/esp/esp-idf/export.sh
```

### 3. 海外用户完整安装流程

```bash
python3 skills/idf-setup/scripts/idf_setup.py \
  --install --version v5.3.2 --region global

. ~/esp/esp-idf/export.sh
```

## 参数说明

| 参数 | 说明 |
| --- | --- |
| `--detect` | 探测已安装的 ESP-IDF 环境 |
| `--list-versions` | 列出可用的 ESP-IDF 发布版本 |
| `--install` | 执行安装 |
| `--version` | ESP-IDF 版本号（如 `v5.3.2`） |
| `--region` | 安装源区域：`china`（国内镜像）或 `global`（GitHub 官方） |
| `--install-dir` | 安装目标路径（默认 `~/esp/esp-idf`） |
| `--setup-env` | 输出环境变量配置命令 |
| `--idf-path` | 指定 IDF 路径（用于 `--setup-env`） |
| `-v`, `--verbose` | 输出详细日志 |

## 国内外镜像源对比

| 项目 | 国内（china） | 海外（global） |
|------|--------------|----------------|
| Git 仓库 | `https://gitee.com/EspressifSystems/esp-idf.git` | `https://github.com/espressif/esp-idf.git` |
| 工具链下载 | `IDF_GITHUB_ASSETS=dl.espressif.cn/github_assets` | GitHub Releases |
| Python 包 | `https://pypi.tuna.tsinghua.edu.cn/simple` | PyPI 官方源 |

## 故障排查

### git 未安装

症状：`git: command not found`

解决：
```bash
# Ubuntu/Debian
sudo apt install git

# macOS
xcode-select --install

# Windows
# 下载 https://git-scm.com/download/win
```

### Python 版本不满足

ESP-IDF v5.x 需要 Python 3.8+。检查版本：
```bash
python3 --version
```

### install.sh 失败

常见原因：
1. 磁盘空间不足（ESP-IDF 完整安装约需 2-3 GB）
2. 网络超时（国内用户请使用 `--region china`）
3. 缺少系统依赖（Ubuntu: `sudo apt install git wget flex bison gperf python3 python3-pip python3-venv cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0`）

## 返回码

- `0`：操作成功
- `1`：参数非法、依赖缺失、网络失败或安装失败

## 与 Skill 的配合方式

在 `idf-setup` skill 中，推荐工作流是：

1. 先用 `--detect` 确认是否已有可用的 ESP-IDF 环境
2. 若需要安装，先用 `--list-versions` 让用户选择版本
3. 确认用户位置（国内/海外），选择合适的安装源
4. 安装完成后，提示用户执行 `source export.sh` 激活环境
5. 更新 `Project Profile`，交给 `build-idf`
