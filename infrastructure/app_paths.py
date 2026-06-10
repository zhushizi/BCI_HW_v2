"""
应用根目录与资源路径解析（源码运行 / PyInstaller 打包后通用）。

打包时请将 runtime 目录一并打入（例如 --add-data 'runtime;runtime'），
config.json 中 *_exe 使用相对路径，如 runtime/ParadigmOne/ParadigmOne.exe。
"""

from __future__ import annotations

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


LOCAL_LOGIN_FLAG_FILENAME = "local_login_initialized.flag"
USER_DATA_DIR_NAME = ".bci_hw"


def _legacy_local_login_flag_path() -> Path:
    """旧版打包后在 exe 旁写入的标记路径（仅兼容读取）。"""
    return Path(sys.executable).resolve().parent / "infrastructure" / "config" / LOCAL_LOGIN_FLAG_FILENAME


def get_local_login_flag_path() -> Path:
    """
    本机首次登录标记文件，存在则表示已在本机完成过首次登录提醒。

    开发：infrastructure/config/local_login_initialized.flag
    打包：用户目录 ~/.bci_hw/local_login_initialized.flag（与登录凭据同目录，不在 exe 旁建 infrastructure）
    """
    if not getattr(sys, "frozen", False):
        return get_project_root() / "infrastructure" / "config" / LOCAL_LOGIN_FLAG_FILENAME
    return Path.home() / USER_DATA_DIR_NAME / LOCAL_LOGIN_FLAG_FILENAME


def local_login_flag_exists() -> bool:
    """检查本机是否已有首次登录标记（含旧版 exe 旁路径）。"""
    if get_local_login_flag_path().is_file():
        return True
    if getattr(sys, "frozen", False):
        return _legacy_local_login_flag_path().is_file()
    return False


def get_config_file_path() -> Path:
    """配置文件路径；打包后优先使用包内（_MEIPASS/_internal）配置，不自动外拷。"""
    dev_path = get_project_root() / "infrastructure" / "config" / "config.json"
    if not getattr(sys, "frozen", False):
        return dev_path

    exe_dir = Path(sys.executable).resolve().parent
    external = exe_dir / "infrastructure" / "config" / "config.json"
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "infrastructure" / "config" / "config.json"

    if bundled.is_file():
        return bundled

    if external.is_file():
        return external

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


def to_config_storage_path(path: str | Path) -> str:
    """将路径规范为 config.json 中保存的 runtime/ 相对路径（正斜杠）。"""
    raw = str(path).strip()
    if not raw:
        return raw
    p = Path(raw)
    if p.is_absolute():
        try:
            rel = p.resolve().relative_to(get_bundle_root().resolve())
            return rel.as_posix()
        except ValueError:
            parts = p.parts
            if "runtime" in parts:
                idx = parts.index("runtime")
                return Path(*parts[idx:]).as_posix()
            return p.as_posix()
    return p.as_posix()


def normalize_config_exe_paths_for_storage(
    data: dict, keys: Iterable[str] = EXE_CONFIG_KEYS
) -> dict:
    """写回 config.json 前，将 *_exe 统一为 runtime/ 相对路径。"""
    if not data:
        return data
    out = dict(data)
    for key in keys:
        val = out.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = to_config_storage_path(val.strip())
    return out
