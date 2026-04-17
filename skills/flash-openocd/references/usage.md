# OpenOCD 烧录 Skill 用法

这个 skill 自带了一个可执行脚本 [scripts/openocd_flasher.py](../scripts/openocd_flasher.py)，适合在需要探测探针、组装 OpenOCD 配置、执行烧录与校验时直接调用。

## 能力概览

- 检测 OpenOCD 是否可用并获取版本信息
- 自动探测已连接的调试探针（ST-Link、CMSIS-DAP、J-Link）
- 扫描工作区中的 OpenOCD 配置文件线索
- 验证固件产物存在性和类型
- 组装并执行完整的 OpenOCD 烧录命令
- 支持 ELF/HEX 直接烧录和 BIN 带地址烧录
- 可选校验和复位控制
- 输出结构化的烧录结果报告

## 基础用法

```bash
# 探测 OpenOCD 环境和已连接探针
python3 skills/flash-openocd/scripts/openocd_flasher.py --detect

# 扫描工作区中的 OpenOCD 配置线索
python3 skills/flash-openocd/scripts/openocd_flasher.py --scan-configs /path/to/project

# 烧录 ELF（自动探测探针）
python3 skills/flash-openocd/scripts/openocd_flasher.py \
  --artifact /path/to/firmware.elf \
  --target target/stm32f4x.cfg

# 烧录 BIN（需要指定基地址）
python3 skills/flash-openocd/scripts/openocd_flasher.py \
  --artifact /path/to/firmware.bin \
  --target target/stm32f4x.cfg \
  --base-address 0x08000000
```

## 常见模式

### 1. 环境与探针探测

```bash
python3 skills/flash-openocd/scripts/openocd_flasher.py --detect
```

输出 OpenOCD 版本和已连接的调试探针列表。

### 2. 使用接口 + 目标配置烧录

```bash
python3 skills/flash-openocd/scripts/openocd_flasher.py \
  --artifact build/debug/app.elf \
  --interface stlink \
  --target target/stm32f4x.cfg
```

### 3. 使用板级配置烧录

```bash
python3 skills/flash-openocd/scripts/openocd_flasher.py \
  --artifact build/debug/app.elf \
  --config board/st_nucleo_f4.cfg
```

板级配置通常已包含接口和目标定义，无需再单独指定。

### 4. 烧录 BIN 文件

```bash
python3 skills/flash-openocd/scripts/openocd_flasher.py \
  --artifact build/firmware.bin \
  --interface cmsis-dap \
  --target target/stm32f1x.cfg \
  --base-address 0x08000000
```

BIN 文件必须提供 `--base-address`，否则脚本会拒绝执行。

### 5. 跳过校验或复位

```bash
python3 skills/flash-openocd/scripts/openocd_flasher.py \
  --artifact build/app.elf \
  --config board/st_nucleo_f4.cfg \
  --no-verify \
  --no-reset
```

### 6. 扫描工作区配置线索

```bash
python3 skills/flash-openocd/scripts/openocd_flasher.py \
  --scan-configs /repo/fw
```

在工作区中搜索 `openocd*.cfg`、`.vscode/launch.json` 等配置线索。

## 参数说明

| 参数 | 说明 |
| --- | --- |
| `--detect` | 探测 OpenOCD 环境和已连接探针 |
| `--artifact` | 固件产物路径（ELF、HEX 或 BIN） |
| `--interface` | 调试接口：`stlink`、`cmsis-dap`、`daplink`、`jlink` |
| `--target` | OpenOCD 目标配置文件 |
| `--config` | 额外的 OpenOCD `-f` 配置，可重复 |
| `--base-address` | BIN 文件的烧录基地址（十六进制） |
| `--no-verify` | 跳过烧录后校验 |
| `--no-reset` | 烧录后不复位目标 |
| `--no-detect` | 禁止自动探测调试接口 |
| `--scan-configs` | 扫描指定目录中的 OpenOCD 配置线索 |
| `--openocd-command` | 自定义 OpenOCD 烧录命令（覆盖自动生成） |
| `-v`, `--verbose` | 输出详细日志 |

## 返回码

- `0`：烧录成功（含校验通过）
- `1`：参数非法、依赖缺失、探针连接失败、烧录失败、或校验失败

## 与 Skill 的配合方式

在 `flash-openocd` skill 中，推荐工作流是：

1. 先根据用户输入或 `Project Profile` 确定产物路径和 OpenOCD 配置
2. 若不确定探针状态，先用 `--detect` 确认
3. 组装合适的烧录参数（接口 + 目标，或板级配置）
4. 将脚本输出的烧录结果整理成简洁摘要
5. 更新 `Project Profile`，交给 `serial-monitor` 或 `debug-gdb-openocd`
