---
name: stm32-hal-development
description: Develop STM32 firmware on CubeMX-generated HAL projects, including peripheral configuration, BSP driver structure, interrupt-safe code, and hardware-aware troubleshooting. Use when Codex needs STM32 HAL implementation guidance rather than generic C advice.
---

# STM32 HAL Development

Treat this skill as the working playbook for CubeMX-based STM32 projects.

## Workflow

1. Read [references/core-guidelines.md](references/core-guidelines.md) first.
2. Keep all custom code inside `USER CODE` regions unless the project has an explicit non-CubeMX extension point.
3. Configure peripherals in CubeMX, regenerate code, then add application or BSP logic.
4. Read additional references only as needed:
   - [references/peripheral-driver-guide.md](references/peripheral-driver-guide.md) for sensor and bus drivers
   - [references/hal-quick-reference.md](references/hal-quick-reference.md) for API lookups
   - [references/troubleshooting-guide.md](references/troubleshooting-guide.md) for failure analysis
   - [references/usage-examples.md](references/usage-examples.md) for implementation patterns
5. Reuse [assets/bsp-template.c](assets/bsp-template.c) and [assets/bsp-template.h](assets/bsp-template.h) when starting a new BSP module.

## Notes

- Prioritize hardware constraints, interrupt safety, and regeneration safety over local code convenience.
- Do not modify CubeMX-generated initialization files directly when the same change belongs in the `.ioc` configuration.

## 适用场景

- 工作区是基于 STM32CubeMX 生成的 HAL 工程（含 `.ioc`、`Core/`、`Drivers/`）。
- 需要在不破坏代码再生能力的前提下新增外设驱动、BSP 层或应用逻辑。
- 需要排查中断优先级、时序、DMA/缓存一致性、外设初始化顺序等硬件相关问题。
- 用户请求偏向 STM32 HAL 具体实现，而非通用 C 语言建议。

## 必要输入

- 最小输入：目标工程根目录（含 `.ioc` 与 `Core/Src`）。
- 推荐输入：芯片型号（如 `STM32F407VG`）、开发板型号、外设清单（UART/I2C/SPI/CAN 等）。
- 可选输入：编译器与工具链（CubeIDE/Keil/IAR/CMake）、时钟树要求、实时性约束。

## 自动探测

- 统一优先级：显式输入 > 工作区线索 > 历史上下文 > 默认值。
- 若多个候选同样合理且选择错误会破坏流程，标记为 ambiguous-context 并停止猜测。
- 自动识别 `.ioc`、`main.c`、`stm32xx_hal_conf.h`、`stm32xx_it.c` 和 `MX_*_Init` 函数，判断工程结构与外设启用状态。
- 自动判断可扩展位置：优先 `USER CODE BEGIN/END` 区域，其次项目自定义 BSP/应用目录。

## 执行步骤

1. 先阅读 `references/core-guidelines.md`，确认本次改动属于配置层、驱动层还是应用层。
2. 如果需求涉及引脚、时钟或外设模式变更，先在 `.ioc` 中完成配置并触发代码再生。
3. 将业务逻辑写入 `USER CODE` 区域或独立 BSP 模块，避免覆盖生成代码。
4. 对中断/DMA 相关逻辑，补充并检查：中断优先级、临界区保护、回调路径和错误处理。
5. 编译并进行最小功能验证，记录关键证据（编译结果、串口日志、波形/寄存器现象）。
6. 输出改动摘要、风险点和建议下游动作（烧录、调试、协议验证）。

## 失败分流

- `project-config-error`：`.ioc` 配置冲突、时钟树非法、外设参数不兼容或生成代码结构异常。
- `environment-missing`：缺少 CubeMX/工具链/编译器等必要环境导致无法验证。
- `artifact-missing`：缺少可用工程文件、关键 HAL 源文件或编译产物。
- `target-response-abnormal`：编译通过但硬件行为异常（中断不进、DMA 不触发、外设无响应等）。
- `ambiguous-context`：存在多个同样合理的芯片/板卡/工程入口且无法安全自动选择。

## 平台说明

- 核心 HAL 开发方法跨平台一致，但工程构建链路受 IDE 与工具链影响较大。
- Windows 常见为 CubeIDE/Keil/IAR；Linux/macOS 多见 CMake + GCC 交叉编译链。
- 若涉及烧录与在线调试，需结合上游/下游 skill 的探针与驱动配置差异进行处理。

## 输出约定

- `status`：`success | partial | blocked | failed`
- `summary`：1-3 行说明本次完成内容（配置变更、代码落点、功能结果）。
- `evidence`：编译日志、关键文件路径、外设行为证据（日志/波形/寄存器）。
- `next_actions`：建议下一步（如烧录验证、RTOS 调试、协议联调）。
- 如有更新，写回 `Project Profile` 的 `chip_family`、`board`、`enabled_peripherals`。

## 交接关系

- 成功后：推荐交给 `build-cmake`/`build-keil`/`build-iar` 进行构建，再交给烧录与调试类 skill 验证。
- 部分成功（仅完成代码改动未验证硬件）后：推荐交给 `flash-openocd` 或 `debug-jlink` 做板级确认。
- 阻塞时：若缺芯片/板卡关键信息，返回 `ambiguous-context` 并明确所需最小补充信息。
- 不交接直接结束：当需求仅为文档说明或概念解释且无工程执行动作时，直接给出结论并结束。
