# 工程识别 Skill 用法

这个 skill 自带了一个可执行脚本 [scripts/project_scanner.py](../scripts/project_scanner.py)，适合在需要扫描嵌入式工作区、识别工程形态并生成标准化 Project Profile 时直接调用。

## 能力概览

- 扫描工作区根目录线索（CMakeLists.txt、CMakePresets.json、Makefile、*.ioc 等）
- 识别构建系统（cmake、make、idf 等）
- 从工具链文件和编译器名称中提取工具链线索
- 从 OpenOCD 配置、IDE 启动文件中提取目标芯片与探针线索
- 在构建目录中搜索 ELF/HEX/BIN 产物
- 检测串口设备（可选）
- 输出标准化的 YAML 格式 Project Profile

## 基础用法

```bash
# 扫描当前目录
python3 skills/project-intake/scripts/project_scanner.py --workspace .

# 扫描指定工作区
python3 skills/project-intake/scripts/project_scanner.py --workspace /path/to/project

# 扫描并检测串口
python3 skills/project-intake/scripts/project_scanner.py --workspace /path/to/project --scan-serial

# 输出为 JSON 格式
python3 skills/project-intake/scripts/project_scanner.py --workspace /path/to/project --json
```

## 常见模式

### 1. 完整工程扫描

```bash
python3 skills/project-intake/scripts/project_scanner.py \
  --workspace /repo/fw \
  --scan-serial \
  --verbose
```

扫描工作区所有线索，包括串口设备，输出详细的探测证据。

### 2. 仅识别构建系统

```bash
python3 skills/project-intake/scripts/project_scanner.py \
  --workspace /repo/fw
```

不扫描串口，快速识别构建系统、工具链和产物。

### 3. 带用户提示的扫描

```bash
python3 skills/project-intake/scripts/project_scanner.py \
  --workspace /repo/fw \
  --hint-mcu stm32f429zi \
  --hint-board nucleo-f429zi \
  --hint-probe stlink
```

用户提示会覆盖自动探测结果。

## 参数说明

| 参数 | 说明 |
| --- | --- |
| `--workspace` | 工作区根目录路径 |
| `--scan-serial` | 同时扫描串口设备 |
| `--hint-mcu` | 用户提示：目标 MCU |
| `--hint-board` | 用户提示：开发板名称 |
| `--hint-probe` | 用户提示：调试探针 |
| `--hint-toolchain` | 用户提示：工具链 |
| `--json` | 以 JSON 格式输出 Profile |
| `-v`, `--verbose` | 输出详细探测证据 |

## 返回码

- `0`：扫描成功，生成了 Project Profile（即使部分字段为空）
- `1`：工作区路径无效或不存在

## 与 Skill 的配合方式

在 `project-intake` skill 中，推荐工作流是：

1. 先根据用户输入确定工作区路径
2. 运行脚本扫描工作区，可选带上用户提示
3. 将脚本输出的 Profile 整理成简洁摘要
4. 根据识别结果推荐下一步 skill（build-cmake / flash-openocd / debug-gdb-openocd / serial-monitor）
5. 若存在歧义（多个候选），列出候选并请用户确认
