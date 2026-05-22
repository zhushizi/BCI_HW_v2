"""
应用根目录与资源路径解析（源码运行 / PyInstaller 打包后通用）。

打包时请将 runtime 目录一并打入（例如 --add-data 'runtime;runtime'），
config.json 中 *_exe 使用相对路径，如 runtime/ParadigmOne/ParadigmOne.exe。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Iterable

# config.json 中需要解析为绝对路径的可执行文件配置项
EXE_CONFIG_KEYS: tuple[str, ...] = (
    "decoder_exe",
    "websocket_exe",
    "ssmvep_exe_up",
    "ssvep_exe_up",
    "mi_exe_up",
    "ssmvep_exe_down",
    "ssvep_exe_down",
    "mi_exe_down",
)


def get_project_root() -> Path:
    """源码运行：仓库根目录（含 main.py、runtime/）。"""
    return Path(__file__).resolve().parents[1]


def get_bundle_root() -> Path:
    """
    资源根目录：开发时为项目根；打包后优先 _MEIPASS（内含 runtime/），
    否则为可执行文件所在目录（onedir 旁路 runtime/）。
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            base = Path(meipass)
            if (base / "runtime").is_dir() or (base / "infrastructure").is_dir():
                return base
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "runtime").is_dir():
            return exe_dir
        if meipass:
            return Path(meipass)
        return exe_dir
    return get_project_root()


def get_config_file_path() -> Path:
    """配置文件路径；打包后优先使用 exe 旁可写的 infrastructure/config/config.json。"""
    dev_path = get_project_root() / "infrastructure" / "config" / "config.json"
    if not getattr(sys, "frozen", False):
        return dev_path

    exe_dir = Path(sys.executable).resolve().parent
    external = exe_dir / "infrastructure" / "config" / "config.json"
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "infrastructure" / "config" / "config.json"

    if external.is_file():
        return external

    if bundled.is_file():
        try:
            external.parent.mkdir(parents=True, exist_ok=True)
            if not external.is_file():
                shutil.copy2(bundled, external)
            return external
        except OSError:
            return bundled

    return dev_path


def resolve_resource_path(path: str | Path) -> Path:
    """将 config 中的相对路径解析为绝对路径（已绝对则原样 resolve）。"""
    p = Path(str(path).strip())
    if not p or p == Path("."):
        return p
    if p.is_absolute():
        return p.resolve()
    return (get_bundle_root() / p).resolve()


def resolve_config_exe_paths(data: dict, keys: Iterable[str] = EXE_CONFIG_KEYS) -> dict:
    """解析配置字典中的可执行文件相对路径。"""
    if not data:
        return data
    out = dict(data)
    for key in keys:
        val = out.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = str(resolve_resource_path(val.strip()))
    return out
