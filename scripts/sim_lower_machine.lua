------------------------------------------------
-- 配置区：按你的协议修改这里
------------------------------------------------

-- 心跳帧（下位机 -> 上位机 ping，0xAB/0x01）
local HEARTBEAT_HEX = "55 AA 0D 00 AB 01 00 00 00 00 00 01 B8"

-- AB 模式子类型（第6个字节）
local AB_HEARTBEAT_PING   = 0x01   -- 下位机心跳 ping
local AB_HEARTBEAT_PONG   = 0x02   -- 上位机心跳 pong（本脚本仅接收，不发送）
local AB_TREAT_OK         = 0x03   -- 下位机治疗完成（原 ASCII Treat_OK）

-- 协议中用于区分不同帧类型的“命令字”（第5个字节）
local CMD_HEARTBEAT   = 0xAB   -- 心跳/Treat_OK 帧命令字（用于不打印）
local CMD_EVAL_FRAME  = 0xAE   -- 评估帧命令字
local CMD_CMD_FRAME   = 0xCD   -- 命令帧命令字
local CMD_DATA_FRAME  = 0xDA   -- 数据帧命令字

-- 评估帧 & 命令帧的应答帧：55 AA 0D 00 DD 00 00 00 00 00 0x01 + 两字节校验
local ACK_BASE = {
    0x55, 0xAA, 0x0D, 0x00,
    0xDD,
    0x00, 0x00, 0x00, 0x00, 0x00,
    0x01,
}

-- Treat_OK 帧：55 AA 0D 00 AB 03 00 00 00 00 00 + 两字节校验（与上位机 HeartbeatFrame 一致）
local TREAT_OK_BASE = {
    0x55, 0xAA, 0x0D, 0x00,
    0xAB,
    AB_TREAT_OK,
    0x00, 0x00, 0x00, 0x00, 0x00,
}

-- 断帧：帧长合法范围（第3字节为帧长度时的 min/max）
local FRAME_LEN_MIN = 4
local FRAME_LEN_MAX = 128

------------------------------------------------
-- 工具函数
------------------------------------------------

local function build_frame_with_sum16(base_bytes)
    local sum = 0
    for i = 1, #base_bytes do
        sum = sum + base_bytes[i]
    end
    sum = sum % 0x10000
    local hi = math.floor(sum / 0x100)
    local lo = sum % 0x100
    local tmp = {}
    for i = 1, #base_bytes do
        tmp[i] = base_bytes[i]
    end
    tmp[#tmp + 1] = hi
    tmp[#tmp + 1] = lo
    return string.char(table.unpack(tmp))
end

local function hex_to_bin(hex)
    return (hex):fromHex()
end

local function is_ab_mode_frame(frame)
    return #frame >= 6 and frame:byte(5) == CMD_HEARTBEAT
end

------------------------------------------------
-- 预生成要发送的固定帧
------------------------------------------------

local HEARTBEAT_FRAME = hex_to_bin(HEARTBEAT_HEX)
local ACK_FRAME       = build_frame_with_sum16(ACK_BASE)
local TREAT_OK_FRAME  = build_frame_with_sum16(TREAT_OK_BASE)

------------------------------------------------
-- 自动断帧：接收缓冲区
------------------------------------------------

local recv_buf = ""

-- 处理“完整一帧”的逻辑
local function on_one_frame(data)
    if #data < 5 then
        return
    end
    local b1, b2 = data:byte(1), data:byte(2)
    if b1 ~= 0x55 or b2 ~= 0xAA then
        return
    end
    local cmd = data:byte(5) or 0
    if cmd == CMD_EVAL_FRAME or cmd == CMD_CMD_FRAME then
        log.info("frame", "eval/cmd frame, send ACK")
        log.info("ack_tx", ACK_FRAME:toHex(" "))
        apiSendUartData(ACK_FRAME)
        return
    end
    if cmd == CMD_DATA_FRAME then
        log.info("frame", "data frame, handle timer by byte9")
        handle_data_frame(data)
    end
end

-- 根据 55 AA + 第3字节长度 从缓冲中取出完整帧并回调
local function drain_frames()
    while #recv_buf >= 3 do
        local b1, b2 = recv_buf:byte(1), recv_buf:byte(2)
        if b1 ~= 0x55 or b2 ~= 0xAA then
            recv_buf = recv_buf:sub(2)
            goto continue
        end
        local frame_len = recv_buf:byte(3)
        if frame_len < FRAME_LEN_MIN or frame_len > FRAME_LEN_MAX then
            recv_buf = recv_buf:sub(2)
            log.warn("frame", "invalid frame len 0x%02X, skip 1 byte", frame_len)
            goto continue
        end
        if #recv_buf < frame_len then
            break
        end
        local frame = recv_buf:sub(1, frame_len)
        recv_buf = recv_buf:sub(frame_len + 1)
        -- AB 模式帧（心跳 pong 等）接收时不打印，避免刷屏
        if not is_ab_mode_frame(frame) then
            log.info("uart_rx", frame:toHex(" "))
        end
        on_one_frame(frame)
        ::continue::
    end
end

------------------------------------------------
-- 倒计时相关
------------------------------------------------

local treat_timer_id = nil

local function cancel_treat_timer()
    if treat_timer_id then
        sys.timerStop(treat_timer_id)
        treat_timer_id = nil
    end
end

local function send_treat_ok()
    log.info("treat", "send Treat_OK frame (0xAB/0x03)")
    log.info("treat_ok_tx", TREAT_OK_FRAME:toHex(" "))
    apiSendUartData(TREAT_OK_FRAME)
end

function handle_data_frame(data)
    if #data < 9 then
        log.warn("frame", "data frame too short")
        return
    end
    local time_byte = data:byte(9) or 0
    if time_byte == 0 then
        log.info("timer", "time_byte=0, cancel timer, send ACK")
        log.info("ack_tx", ACK_FRAME:toHex(" "))
        cancel_treat_timer()
        apiSendUartData(ACK_FRAME)
        return
    end
    local ms = time_byte * 1000
    log.info("timer", "start treat timer, seconds=", time_byte)
    cancel_treat_timer()
    treat_timer_id = sys.timerStart(function()
        treat_timer_id = nil
        send_treat_ok()
    end, ms)
end

------------------------------------------------
-- 串口接收：只做缓冲 + 断帧
------------------------------------------------

uartReceive = function(data)
    if not data or #data == 0 then
        return
    end
    recv_buf = recv_buf .. data
    drain_frames()
end

------------------------------------------------
-- 心跳任务：每 2 秒发一次心跳帧（心跳不打印）
------------------------------------------------

sys.taskInit(function()
    while true do
        apiSendUartData(HEARTBEAT_FRAME)
        sys.wait(2000)
    end
end)
