#!/usr/bin/env python3
"""ESP-IDF 环境安装工具。

为 idf-setup skill 提供可重复调用的执行入口，支持：
- 探测已安装的 ESP-IDF 环境
- 列出可用版本
- 根据区域选择安装源执行安装
- 输出环境变量配置命令
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILLS_DIR = _SCRIPT_DIR.parent.parent
for _candidate in [_SKILLS_DIR / "shared", _SKILLS_DIR.parent / "shared"]:
    if (_candidate / "tool_config.py").exists():
        sys.path.insert(0, str(_candidate))
        break
from tool_config import get_tool_path, set_tool_path

CHINA_GIT_URL = "https://gitee.com/EspressifSystems/esp-idf.git"
GLOBAL_GIT_URL = "https://github.com/espressif/esp-idf.git"
CHINA_GITHUB_ASSETS = "dl.espressif.cn/github_assets"
CHINA_PIP_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
DEFAULT_INSTALL_DIR = Path.home() / "esp" / "esp-idf"
COMMON_PATHS = [
    Path.home() / "esp" / "esp-idf",
    Path("/opt/esp-idf"),
    Path.home() / "esp-idf",
]
if platform.system() == "Windows":
    COMMON_PATHS.append(Path("C:/Espressif/frameworks/esp-idf"))


@dataclass
class IDFInstallation:
    path: Path
    version: str | None
    valid: bool


@dataclass
class SetupResult:
    status: str
    summary: str
    idf_path: str | None = None
    idf_version: str | None = None
    region: str | None = None
    failure_category: str | None = None
    evidence: list[str] = field(default_factory=list)


def _get_idf_version(idf_path: Path) -> str | None:
    version_file = idf_path / "version.txt"
    if version_file.exists():
        try:
            return version_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    tools_json = idf_path / "tools" / "idf_tools.py"
    if tools_json.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(tools_json), "version"],
                capture_output=True, text=True, timeout=10, cwd=str(idf_path),
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True, text=True, timeout=10, cwd=str(idf_path),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _is_valid_idf(idf_path: Path) -> bool:
    return (
        idf_path.is_dir()
        and (idf_path / "tools" / "idf.py").exists()
        and (idf_path / "components").is_dir()
    )


def detect_installations() -> list[IDFInstallation]:
    installations: list[IDFInstallation] = []
    seen: set[str] = set()

    idf_env = os.environ.get("IDF_PATH")
    if idf_env:
        p = Path(idf_env).resolve()
        if p.is_dir() and str(p) not in seen:
            seen.add(str(p))
            installations.append(IDFInstallation(
                path=p, version=_get_idf_version(p), valid=_is_valid_idf(p),
            ))

    for candidate in COMMON_PATHS:
        p = candidate.resolve()
        if p.is_dir() and str(p) not in seen:
            seen.add(str(p))
            installations.append(IDFInstallation(
                path=p, version=_get_idf_version(p), valid=_is_valid_idf(p),
            ))

    return installations


def list_versions(verbose: bool = False) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "--refs", GLOBAL_GIT_URL],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print("❌ 无法获取版本列表，请检查网络连接")
            return []
    except FileNotFoundError:
        print("❌ 未找到 git 命令")
        return []
    except subprocess.TimeoutExpired:
        print("❌ 获取版本列表超时")
        return []

    versions: list[str] = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("refs/tags/")
        if len(parts) == 2:
            tag = parts[1].strip()
            if tag.startswith("v") and not tag.endswith("^{}"):
                versions.append(tag)

    versions.sort(key=lambda v: [int(x) if x.isdigit() else 0 for x in v.lstrip("v").replace("-", ".").split(".")], reverse=True)
    return versions


def install_idf(version: str, region: str, install_dir: Path, verbose: bool = False) -> SetupResult:
    evidence: list[str] = []

    if not shutil.which("git"):
        return SetupResult(status="failure", summary="git 未安装", failure_category="environment-missing",
                           evidence=["需要安装 git"])
    if not shutil.which("python3") and not shutil.which("python"):
        return SetupResult(status="failure", summary="python3 未安装", failure_category="environment-missing",
                           evidence=["需要安装 python3 (3.8+)"])

    git_url = CHINA_GIT_URL if region == "china" else GLOBAL_GIT_URL
    evidence.append(f"Git 源: {git_url}")
    evidence.append(f"安装路径: {install_dir}")
    evidence.append(f"版本: {version}")

    env = os.environ.copy()
    if region == "china":
        env["IDF_GITHUB_ASSETS"] = CHINA_GITHUB_ASSETS
        env["PIP_INDEX_URL"] = CHINA_PIP_INDEX
        evidence.append(f"IDF_GITHUB_ASSETS={CHINA_GITHUB_ASSETS}")
        evidence.append(f"PIP_INDEX_URL={CHINA_PIP_INDEX}")

    install_dir.parent.mkdir(parents=True, exist_ok=True)

    if install_dir.exists() and (install_dir / ".git").exists():
        print(f"ℹ️ 目录已存在，切换到版本 {version}")
        try:
            subprocess.run(["git", "fetch", "--tags"], cwd=str(install_dir),
                           capture_output=True, timeout=120, env=env)
            result = subprocess.run(["git", "checkout", version], cwd=str(install_dir),
                                    capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return SetupResult(status="failure", summary=f"切换版本失败: {result.stderr.strip()}",
                                   failure_category="project-config-error", evidence=evidence)
            subprocess.run(["git", "submodule", "update", "--init", "--recursive"],
                           cwd=str(install_dir), capture_output=True, timeout=600, env=env)
        except subprocess.TimeoutExpired:
            return SetupResult(status="failure", summary="git 操作超时",
                               failure_category="connection-failure", evidence=evidence)
    else:
        print(f"📥 克隆 ESP-IDF {version} ...")
        try:
            cmd = ["git", "clone", "--branch", version, "--recursive", "--depth", "1", git_url, str(install_dir)]
            evidence.append(f"克隆命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
            if result.returncode != 0:
                return SetupResult(status="failure", summary=f"克隆失败: {result.stderr.strip()[:200]}",
                                   failure_category="connection-failure", evidence=evidence)
        except subprocess.TimeoutExpired:
            return SetupResult(status="failure", summary="克隆超时（600 秒）",
                               failure_category="connection-failure", evidence=evidence)

    print("🔧 安装工具链 ...")
    is_win = platform.system() == "Windows"
    install_script = install_dir / ("install.bat" if is_win else "install.sh")
    if not install_script.exists():
        return SetupResult(status="failure", summary=f"安装脚本不存在: {install_script}",
                           failure_category="project-config-error", evidence=evidence)

    try:
        if is_win:
            cmd = [str(install_script), "all"]
        else:
            cmd = ["bash", str(install_script), "all"]
        evidence.append(f"安装命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200, env=env,
                                cwd=str(install_dir))
        if result.returncode != 0:
            last_lines = result.stderr.strip().split("\n")[-10:]
            evidence.append("安装失败输出（末尾）:")
            evidence.extend(last_lines)
            return SetupResult(status="failure", summary="工具链安装失败",
                               failure_category="environment-missing", evidence=evidence)
    except subprocess.TimeoutExpired:
        return SetupResult(status="failure", summary="工具链安装超时（1200 秒）",
                           failure_category="connection-failure", evidence=evidence)

    actual_version = _get_idf_version(install_dir) or version
    set_tool_path("idf-path", str(install_dir))

    return SetupResult(
        status="success",
        summary=f"ESP-IDF {actual_version} 安装成功",
        idf_path=str(install_dir),
        idf_version=actual_version,
        region=region,
        evidence=evidence,
    )


def setup_env(idf_path: Path) -> None:
    if not _is_valid_idf(idf_path):
        print(f"❌ {idf_path} 不是有效的 ESP-IDF 目录")
        return

    is_win = platform.system() == "Windows"
    if is_win:
        export_script = idf_path / "export.bat"
        print(f"\n请在命令行中执行：\n  {export_script}")
    else:
        export_script = idf_path / "export.sh"
        print(f"\n请在终端中执行：\n  . {export_script}")

    print(f"\n或将以下内容添加到 shell 配置文件中：")
    print(f"  export IDF_PATH={idf_path}")
    if not is_win:
        print(f"  . {export_script}")


def print_detect_report(installations: list[IDFInstallation]) -> None:
    print("\n📊 ESP-IDF 环境探测结果：")
    if not installations:
        print("  ❌ 未找到已安装的 ESP-IDF")
        print("  💡 使用 --install 安装，或使用 --list-versions 查看可用版本")
        return

    for inst in installations:
        status = "✅" if inst.valid else "⚠️"
        ver = f" ({inst.version})" if inst.version else " (版本未知)"
        print(f"  {status} {inst.path}{ver}")
        if not inst.valid:
            print(f"     ⚠️ 目录结构不完整，可能需要重新安装")

    idf_env = os.environ.get("IDF_PATH")
    if idf_env:
        print(f"\n  当前 IDF_PATH: {idf_env}")
    else:
        print("\n  ⚠️ IDF_PATH 未设置，请执行 source export.sh 激活环境")

    espressif_dir = Path.home() / ".espressif"
    if espressif_dir.exists():
        print(f"  工具链目录: {espressif_dir}")
    else:
        print(f"  ⚠️ 工具链目录 {espressif_dir} 不存在")


def print_setup_result(result: SetupResult) -> None:
    status_icon = {"success": "✅", "failure": "❌", "blocked": "⚠️"}.get(result.status, "❓")
    print(f"\n📊 安装结果: {status_icon} {result.summary}")

    if result.idf_path:
        print(f"  IDF 路径: {result.idf_path}")
    if result.idf_version:
        print(f"  IDF 版本: {result.idf_version}")
    if result.region:
        region_name = "国内镜像" if result.region == "china" else "GitHub 官方"
        print(f"  安装源:   {region_name}")

    if result.evidence:
        print("\n📝 证据:")
        for line in result.evidence[:15]:
            print(f"  {line}")

    if result.failure_category:
        print(f"\n  失败分类: {result.failure_category}")

    if result.status == "success" and result.idf_path:
        print(f"\n💡 下一步：执行以下命令激活环境")
        is_win = platform.system() == "Windows"
        if is_win:
            print(f"  {result.idf_path}\\export.bat")
        else:
            print(f"  . {result.idf_path}/export.sh")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ESP-IDF 环境安装工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --detect
  %(prog)s --list-versions
  %(prog)s --install --version v5.3.2 --region china
  %(prog)s --install --version v5.3.2 --region global
  %(prog)s --setup-env --idf-path ~/esp/esp-idf
        """,
    )
    parser.add_argument("--detect", action="store_true", help="探测已安装的 ESP-IDF 环境")
    parser.add_argument("--list-versions", action="store_true", help="列出可用版本")
    parser.add_argument("--install", action="store_true", help="执行安装")
    parser.add_argument("--version", help="ESP-IDF 版本号（如 v5.3.2）")
    parser.add_argument("--region", choices=["china", "global"], help="安装源区域")
    parser.add_argument("--install-dir", help=f"安装目标路径（默认 {DEFAULT_INSTALL_DIR}）")
    parser.add_argument("--setup-env", action="store_true", help="输出环境变量配置命令")
    parser.add_argument("--idf-path", help="指定 IDF 路径（用于 --setup-env）")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.detect:
        installations = detect_installations()
        print_detect_report(installations)
        return 0 if any(i.valid for i in installations) else 1

    if args.list_versions:
        versions = list_versions(verbose=args.verbose)
        if not versions:
            return 1
        print("📋 可用 ESP-IDF 版本（最新在前）：")
        for i, v in enumerate(versions[:20], 1):
            print(f"  {i}. {v}")
        if len(versions) > 20:
            print(f"  ... 共 {len(versions)} 个版本")
        return 0

    if args.setup_env:
        idf_path = Path(args.idf_path) if args.idf_path else DEFAULT_INSTALL_DIR
        setup_env(idf_path.resolve())
        return 0

    if args.install:
        if not args.version:
            print("❌ 请通过 --version 指定要安装的版本（如 v5.3.2）")
            return 1
        if not args.region:
            print("❌ 请通过 --region 指定安装源区域（china 或 global）")
            return 1
        install_dir = Path(args.install_dir).resolve() if args.install_dir else DEFAULT_INSTALL_DIR
        result = install_idf(args.version, args.region, install_dir, verbose=args.verbose)
        print_setup_result(result)
        return 0 if result.status == "success" else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
