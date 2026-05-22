"""
串口日志用：识别并剥离心跳帧（与 service.business.protocol.HeartbeatFrame 协议一致）。
仅按帧形态判断，不做校验和，避免日志路径触发 warning。
"""

from __future__ import annotations

FRAME_HEADER = bytes([0x55, 0xAA])
FRAME_LENGTH = 0x0D
FRAME_SIZE = 13
HEARTBEAT_MODE = 0xAB
HEARTBEAT_FROM_DEVICE = 0x01
HEARTBEAT_TO_DEVICE = 0x02


def looks_like_heartbeat_frame(data: bytes) -> bool:
    """是否为 13 字节心跳 ping(0x01) 或 pong(0x02) 帧。"""
    if len(data) != FRAME_SIZE:
        return False
    if data[0:2] != FRAME_HEADER:
        return False
    if data[2] != FRAME_LENGTH:
        return False
    if data[4] != HEARTBEAT_MODE:
        return False
    return data[5] in (HEARTBEAT_FROM_DEVICE, HEARTBEAT_TO_DEVICE)


def strip_heartbeat_frames(data: bytes) -> bytes:
    """从收发缓冲中移除完整心跳帧，返回剩余字节（供非心跳日志打印）。"""
    if not data:
        return b""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        if i + FRAME_SIZE <= n and looks_like_heartbeat_frame(data[i : i + FRAME_SIZE]):
            i += FRAME_SIZE
            continue
        out.append(data[i])
        i += 1
    return bytes(out)
