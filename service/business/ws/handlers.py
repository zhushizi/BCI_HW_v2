from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from infrastructure.communication.websocket_service import MainWebSocketService
from service.business.protocol.heartbeat_frame import HeartbeatFrame

@dataclass(frozen=True)
class ActionCommand:
    trial_index: int
    action: str
    channel: str


@dataclass(frozen=True)
class PendingAction:
    trial_index: int
    action: str


class PendingActionStore:
    def __init__(self) -> None:
        self.value: Optional[PendingAction] = None


class ParadigmHandler:
    def __init__(
        self,
        *,
        logger: logging.Logger,
        on_action_command: Callable[[int, str, str], bool],
        pending_action_store: PendingActionStore,
        action_left: str,
        action_right: str,
        channel_left: str,
        channel_right: str,
    ) -> None:
        self._logger = logger
        self._on_action_command = on_action_command
        self._pending_action_store = pending_action_store
        self._action_left = action_left
        self._action_right = action_right
        self._channel_left = channel_left
        self._channel_right = channel_right

    def on_paradigm_action_command(self, msg: Dict[str, Any]) -> None:
        cmd = self._parse_action_command(msg)
        if not cmd:
            return
        self._logger.info(
            "收到范式动作指令: trial_index=%s, action=%s",
            cmd.trial_index,
            cmd.action,
        )
        ok = False
        try:
            ok = bool(self._on_action_command(cmd.trial_index, cmd.action, cmd.channel))
        except Exception as e:
            self._logger.error(f"下发动作指令失败: {e}")
        if ok:
            self._pending_action_store.value = PendingAction(cmd.trial_index, cmd.action)

    def _parse_action_command(self, msg: Dict[str, Any]) -> Optional[ActionCommand]:
        params = msg.get("params") or {}
        trial_index = int(params.get("trial_index", 0) or 0)
        action = str(params.get("action", "") or "")
        if action not in (self._action_left, self._action_right):
            if action:
                self._logger.warning(f"未知动作指令，已忽略: action={action}")
            return None
        channel = self._channel_left if action == self._action_left else self._channel_right
        return ActionCommand(trial_index=trial_index, action=action, channel=channel)


class SerialHandler:
    """接收串口数据并识别 Treat_OK 帧（AB 模式 0x03）；分片到达时先组帧再校验。"""
    MAX_RECV_BUFFER = 256

    def __init__(
        self,
        *,
        ws: MainWebSocketService,
        logger: logging.Logger,
        pending_action_store: PendingActionStore,
    ) -> None:
        self._ws = ws
        self._logger = logger
        self._pending_action_store = pending_action_store
        self._recv_buffer = bytearray()

    def on_serial_data(self, data: bytes) -> None:
        if not data:
            return
        self._recv_buffer.extend(data)
        if len(self._recv_buffer) > self.MAX_RECV_BUFFER:
            self._recv_buffer = self._recv_buffer[-self.MAX_RECV_BUFFER:]
        self._try_consume_treat_ok_frames()

    def _try_consume_treat_ok_frames(self) -> None:
        """从 _recv_buffer 中尽量解析并消费完整的 Treat_OK 帧（每帧 13 字节）。"""
        while len(self._recv_buffer) >= HeartbeatFrame.FRAME_SIZE:
            if bytes(self._recv_buffer[0:2]) != HeartbeatFrame.FRAME_HEADER:
                self._recv_buffer.pop(0)
                continue
            frame = bytes(self._recv_buffer[:HeartbeatFrame.FRAME_SIZE])
            if not HeartbeatFrame.is_treat_ok_frame(frame, self._logger):
                self._recv_buffer.pop(0)
                continue
            del self._recv_buffer[:HeartbeatFrame.FRAME_SIZE]
            self._logger.info("收到下位机 Treat_OK 帧 (0x03): %s", frame.hex())
            self._handle_treat_ok_frame()

    def contains_treat_ok_frame(self, data: bytes) -> bool:
        """判断缓冲区是否包含至少一帧完整的 Treat_OK 帧。"""
        if len(data) < HeartbeatFrame.FRAME_SIZE:
            return False
        for i in range(len(data) - HeartbeatFrame.FRAME_SIZE + 1):
            if data[i : i + 2] != HeartbeatFrame.FRAME_HEADER:
                continue
            frame = data[i : i + HeartbeatFrame.FRAME_SIZE]
            if HeartbeatFrame.is_treat_ok_frame(frame, self._logger):
                return True
        return False

    def _handle_treat_ok_frame(self) -> None:
        if not self._pending_action_store.value:
            self._logger.warning("收到 Treat_OK 帧，但无待完成动作")
            return
        trial_index = self._pending_action_store.value.trial_index
        action = self._pending_action_store.value.action
        self._pending_action_store.value = None
        self._send_action_complete(trial_index, action)

    def _send_action_complete(self, trial_index: int, action: str) -> None:
        self._ws.send_exo_action_complete(trial_index=trial_index, executed_action=action)
        self._logger.info(
            "收到 Treat_OK 帧，已发送 main.exo_action_complete: trial_index=%s, action=%s",
            trial_index,
            action,
        )


class StopSessionHandler:
    def __init__(
        self,
        *,
        logger: logging.Logger,
        on_stop_session: Callable[[Optional[float]], None],
        load_countdown_minutes: Callable[[], Optional[float]],
    ) -> None:
        self._logger = logger
        self._on_stop_session = on_stop_session
        self._load_countdown_minutes = load_countdown_minutes

    def on_main_stop_session(self, msg: Dict[str, Any]) -> None:
        try:
            countdown_minutes = self._load_countdown_minutes()
            if self._on_stop_session:
                self._on_stop_session(countdown_minutes)
        except Exception:
            self._logger.exception("处理 main.stop_session 失败")
