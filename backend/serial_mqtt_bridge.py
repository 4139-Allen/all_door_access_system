"""
串口转 MQTT 桥接脚本
通过 CH340 连接 STM32，转发开门命令到 MQTT，并将设备状态上报到 MQTT

硬件连接：
  STM32 PA9 (TX)  -> CH340 RXD
  STM32 PA10 (RX) <- CH340 TXD
  GND             <-> GND

用法：
  python serial_mqtt_bridge.py

环境变量（可选，有默认值）：
  SERIAL_PORT       串口号，如 COM3（默认自动检测 CH340）
  MQTT_BROKER_HOST  MQTT 地址（默认 127.0.0.1）
  MQTT_BROKER_PORT  MQTT 端口（默认 1883）
  MQTT_USERNAME     MQTT 用户名（默认空）
  MQTT_PASSWORD     MQTT 密码（默认空）
  MQTT_TOPIC_PREFIX MQTT 主题前缀（默认 door）
  DEVICE_ID         设备编号（默认 001）

依赖：
  pip install pyserial paho-mqtt
"""

import os
import serial
import serial.tools.list_ports
import paho.mqtt.client as mqtt
import threading
import time
import sys

# ==================== 配置（优先读环境变量） ====================
SERIAL_PORT = os.getenv('SERIAL_PORT')       # None = 自动检测
SERIAL_BAUD = 9600

MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', '127.0.0.1')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_TOPIC_PREFIX = os.getenv('MQTT_TOPIC_PREFIX', 'door')
DEVICE_ID = os.getenv('DEVICE_ID', '001')

# ==================== 全局变量 ====================
ser = None
mqtt_client = None
serial_lock = threading.Lock()     # 保护串口读写
running = True


def find_ch340_port():
    """自动查找 CH340 串口"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'CH340' in port.description or 'CH340' in port.hwid:
            print(f"[串口] 找到 CH340: {port.device} - {port.description}")
            return port.device
    if ports:
        print("[串口] 未找到 CH340，可用串口:")
        for i, port in enumerate(ports):
            print(f"  {i + 1}. {port.device} - {port.description}")
        try:
            choice = int(input("请选择串口编号: ")) - 1
            if 0 <= choice < len(ports):
                return ports[choice].device
        except (ValueError, IndexError):
            pass
    return None


def open_serial(port):
    """打开串口并清空缓冲区"""
    ser_obj = serial.Serial(port, SERIAL_BAUD, timeout=0.1)
    ser_obj.reset_input_buffer()
    ser_obj.reset_output_buffer()
    return ser_obj


# ==================== MQTT 回调 ====================

def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] 已连接到 {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        topic = f"{MQTT_TOPIC_PREFIX}/{DEVICE_ID}/command"
        client.subscribe(topic, qos=1)
        print(f"[MQTT] 已订阅: {topic}")
        status_topic = f"{MQTT_TOPIC_PREFIX}/{DEVICE_ID}/status"
        client.publish(status_topic, "ONLINE", qos=1)
        print(f"[MQTT] 已发送上线状态: {status_topic} -> ONLINE")
    else:
        print(f"[MQTT] 连接失败，返回码: {rc}")


def on_mqtt_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"[MQTT] 意外断开 (rc={rc})，将自动重连...")


def on_mqtt_message(client, userdata, msg):
    """MQTT 消息回调 - 收到开门命令，转发到串口"""
    payload = msg.payload.decode().strip()
    print(f"[MQTT] 收到命令 [{msg.topic}]: {payload}")

    if payload != "OPEN_DOOR":
        return

    with serial_lock:
        if not ser or not ser.is_open:
            print("[串口] 未连接，无法发送命令")
            return
        ser.write(b"OPEN_DOOR\n")
        print("[串口] 已发送: OPEN_DOOR\\n")


# ==================== 串口读取 ====================

def serial_reader():
    """串口读取线程 - 接收 STM32 上报的状态"""
    global ser, running
    buffer = ""
    while running:
        try:
            with serial_lock:
                is_open = ser and ser.is_open
                waiting = ser.in_waiting if is_open else 0

            if is_open and waiting > 0:
                with serial_lock:
                    data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        print(f"[串口] 收到: {line}")
                        publish_status(line)
            else:
                time.sleep(0.05)
        except Exception as e:
            if running:
                print(f"[错误] 串口读取失败: {e}")
                time.sleep(1)


def publish_status(message):
    """将 STM32 消息转发到 MQTT"""
    if not mqtt_client:
        return
    status_topic = f"{MQTT_TOPIC_PREFIX}/{DEVICE_ID}/status"
    mqtt_client.publish(status_topic, message, qos=1)
    print(f"[MQTT] 已上报: {status_topic} -> {message}")


# ==================== 心跳 ====================

def send_heartbeat():
    """心跳线程 - 每 30 秒发送 ONLINE"""
    while running:
        try:
            if mqtt_client and mqtt_client.is_connected():
                status_topic = f"{MQTT_TOPIC_PREFIX}/{DEVICE_ID}/status"
                mqtt_client.publish(status_topic, "ONLINE", qos=1)
            time.sleep(30)
        except Exception as e:
            print(f"[错误] 心跳发送失败: {e}")
            time.sleep(5)


# ==================== 主程序 ====================

def main():
    global ser, mqtt_client, running

    print("=" * 60)
    print("STM32 串口转 MQTT 桥接工具")
    print("=" * 60)
    print(f"设备编号: {DEVICE_ID}")
    print(f"MQTT Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    print()

    # 1. 查找并打开串口
    port = SERIAL_PORT or find_ch340_port()
    if not port:
        print("[错误] 未找到可用串口，请检查 CH340 连接")
        sys.exit(1)

    try:
        ser = open_serial(port)
        print(f"[串口] 已打开 {port}，波特率 {SERIAL_BAUD}")
    except Exception as e:
        print(f"[错误] 打开串口失败: {e}")
        sys.exit(1)

    # 2. 连接 MQTT
    try:
        mqtt_client = mqtt.Client(client_id=f"serial-bridge-{DEVICE_ID}", clean_session=True)
        if MQTT_USERNAME:
            mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        mqtt_client.on_connect = on_mqtt_connect
        mqtt_client.on_disconnect = on_mqtt_disconnect
        mqtt_client.on_message = on_mqtt_message
        mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
        mqtt_client.loop_start()
        print(f"[MQTT] 正在连接 {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}...")
    except Exception as e:
        print(f"[错误] MQTT 连接失败: {e}")
        print("[提示] 请确保 MQTT Broker 已启动 (docker compose up -d mosquitto)")
        ser.close()
        sys.exit(1)

    # 3. 启动后台线程
    threading.Thread(target=serial_reader, daemon=True).start()
    threading.Thread(target=send_heartbeat, daemon=True).start()

    print()
    print("=" * 60)
    print("桥接已启动！等待命令...")
    print("开门命令: 在 MQTT 客户端发送 OPEN_DOOR 到 door/001/command")
    print("按 Ctrl+C 退出")
    print("=" * 60)
    print()

    # 4. 主循环 - 手动发送命令
    try:
        while running:
            try:
                user_input = input()
                cmd = user_input.strip().upper()
                if cmd == "QUIT":
                    break
                if not cmd:
                    continue
                with serial_lock:
                    if ser and ser.is_open:
                        ser.write((user_input.strip() + "\n").encode())
                        print(f"[串口] 已发送: {user_input.strip()}")
                    else:
                        print("[串口] 未连接")
            except EOFError:
                break
    except KeyboardInterrupt:
        pass

    # 5. 清理
    print("\n[退出] 正在关闭...")
    running = False
    if mqtt_client:
        status_topic = f"{MQTT_TOPIC_PREFIX}/{DEVICE_ID}/status"
        mqtt_client.publish(status_topic, "OFFLINE", qos=1)
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    with serial_lock:
        if ser:
            ser.close()
    print("[退出] 已关闭")


if __name__ == "__main__":
    main()
