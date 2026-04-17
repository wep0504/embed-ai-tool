---
name: project-intake
description: 当需要检查嵌入式固件工作区、调用自带脚本识别工程形态，并为构建、烧录、调试或串口监视准备上下文时使用。
---

# 工程识别

## 适用场景

- 当前工作区还没有完成工程画像识别。
- 用户想知道仓库使用的板卡、探针、构建系统或固件产物。
- 下游 skill 在安全执行前，需要一份标准化的工程上下文。
- 需要快速了解一个陌生嵌入式工程的基本形态。

## 必要输入

- 工作区路径。若用户未指定，则默认使用当前仓库根目录。
- 可选提示，例如 MCU 名称、板卡、调试探针或期望的工具链。

## 自动探测

- 脚本自动扫描 `CMakeLists.txt`、`CMakePresets.json`、`Makefile`、`.vscode/launch.json`、`*.ioc`、`sdkconfig`、`openocd*.cfg` 等根目录线索。
- 先识别构建系统，再识别工具链线索，最后识别目标芯片与调试探针线索。
- 在常见构建目录中搜索 `*.elf`、`*.hex`、`*.bin` 产物。
- 可选扫描串口设备，自动识别 CH340、CP210x、CMSIS-DAP 等常见设备。
- 如果存在多个同样合理的候选，脚本会列出候选而不是静默猜测。

## 执行步骤

1. 先阅读 [references/usage.md](references/usage.md)，确认本次是完整扫描、带提示扫描，还是仅需要串口检测。
2. 运行自带脚本 [scripts/project_scanner.py](scripts/project_scanner.py)，使用 `--workspace` 指定工作区路径。
3. 若用户提供了 MCU、板卡或探针信息，使用 `--hint-mcu`、`--hint-board`、`--hint-probe` 传入。
4. 若需要串口信息，加上 `--scan-serial`。
5. 读取脚本输出的 Project Profile，重点关注构建系统、工具链、产物和探针字段。
6. 根据识别结果推荐下一步 skill，并在需要时请用户补充歧义字段。

## 失败分流

- 当工作区看起来是嵌入式工程，但构建元数据损坏或互相矛盾时，返回 `project-config-error`。
- 当下游流程需要固件产物，但无法安全解析到任何产物时，返回 `artifact-missing`。
- 当探测得到多个有效板卡、探针、预设或产物时，返回 `ambiguous-context`。
- 不要猜测目标板卡或探针，应明确以 `blocked` 停止并等待补充信息。

## 平台说明

- 自带脚本使用 Python 标准库（串口扫描可选依赖 pyserial），因此扫描路径本身是跨平台的。
- 路径格式和可执行文件后缀规则遵循 [platform-compatibility.md](/home/leo/work/open-git/em_skill/shared/platform-compatibility.md)。
- 只有当工作区或宿主探测足以明确串口信息时，才记录串口名称。

## 输出约定

- 无论信息是否完整，都要返回一份 `Project Profile`。
- 对每个不明显字段给出证据来源，例如推断出探针或产物的文件路径。
- 在 `build-cmake`、`flash-openocd`、`debug-gdb-openocd`、`serial-monitor` 中推荐一个下一步 skill。

## 交接关系

- 面向构建的成功识别结果交给 `build-cmake`。
- 已有有效产物且带有 OpenOCD 线索的结果交给 `flash-openocd` 或 `debug-gdb-openocd`。
- 已明确串口或波特率的结果交给 `serial-monitor`。