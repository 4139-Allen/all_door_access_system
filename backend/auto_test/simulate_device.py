"""
设备模拟器 —— 通过 MQTT 模拟物理门禁硬件

作用：
  1. 定时发心跳（ONLINE），让后端认为设备在线
  2. 订阅开门命令（OPEN_DOOR），自动回复 OPENED
  3. 配合自动化测试，无需真实硬件即可测试开门流程

用法：
  python simulate_device.py <设备名> [--broker 服务器IP]

示例：
  python simulate_device.py 001
  python simulate_device.py 001 --broker 47.242.179.46
  python simulate_device.py 001 --broker 127.0.0.1
"""
import argparse
import time
import threading
import paho.mqtt.client as mqtt

# 默认 MQTT 配置（和 backend/.env 保持一致）
DEFAULT_BROKER = "47.242.179.46"
DEFAULT_PORT = 1883
TOPIC_PREFIX = "door"
HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）
REDIS_TTL = 70           # 跟后端 Redis TTL 一致，心跳间隔 < TTL 即可


class DeviceSimulator:
    """模拟一个门禁设备"""

    def __init__(self, device_name: str, broker: str, port: int):
        self.device_name = device_name
        self.broker = broker
        self.port = port
        self.running = False

        self.client = mqtt.Client(client_id=f"sim_{device_name}")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[✓] 已连接 MQTT Broker: {self.broker}:{self.port}")
            # 订阅命令主题
            topic = f"{TOPIC_PREFIX}/{self.device_name}/command"
            client.subscribe(topic, qos=1)
            print(f"[✓] 已订阅: {topic}")
        else:
            print(f"[✗] MQTT 连接失败，返回码: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        print(f"[!] MQTT 断开连接 (rc={rc})，5 秒后重连...")
        if self.running:
            time.sleep(5)
            try:
                client.reconnect()
            except Exception as e:
                print(f"[✗] 重连失败: {e}")

    def _on_message(self, client, userdata, msg):
        """收到命令后自动回复"""
        payload = msg.payload.decode()
        print(f"[<] 收到命令 [{msg.topic}]: {payload}")

        if payload == "OPEN_DOOR":
            # 回复 OPENED → 后端确认开门成功
            status_topic = f"{TOPIC_PREFIX}/{self.device_name}/status"
            client.publish(status_topic, "OPENED", qos=1)
            print(f"[>] 已回复 OPENED -> {status_topic}")

        elif payload == "UNLOCK":
            print("[ ] 收到解锁指令（无需回复）")

        elif payload == "LOCK":
            print("[ ] 收到锁定指令（无需回复）")

        else:
            print(f"[?] 未知命令: {payload}")

    def _send_heartbeat(self):
        """定时发送心跳保持在线"""
        topic = f"{TOPIC_PREFIX}/{self.device_name}/status"
        while self.running:
            self.client.publish(topic, "ONLINE", qos=1)
            print(f"[>] 心跳: ONLINE -> {topic}")
            time.sleep(HEARTBEAT_INTERVAL)

    def start(self):
        """启动模拟器"""
        self.running = True
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()

            # 启动心跳线程
            heartbeat_thread = threading.Thread(target=self._send_heartbeat, daemon=True)
            heartbeat_thread.start()

            print(f"\n{'='*50}")
            print(f"  设备模拟器运行中: {self.device_name}")
            print(f"  Broker: {self.broker}:{self.port}")
            print(f"  心跳: 每 {HEARTBEAT_INTERVAL} 秒")
            print(f"{'='*50}")
            print("  按 Ctrl+C 停止\n")

            # 主线程保持运行
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[ ] 正在停止...")
        except Exception as e:
            print(f"[✗] 错误: {e}")
        finally:
            self.stop()

    def stop(self):
        """停止模拟器"""
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        print("[✓] 设备模拟器已停止")


def main():
    parser = argparse.ArgumentParser(description="门禁设备 MQTT 模拟器")
    parser.add_argument("device_name", help="设备名（如 DEV-001）")
    parser.add_argument("--broker", default=DEFAULT_BROKER, help=f"MQTT Broker 地址（默认 {DEFAULT_BROKER}）")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"MQTT 端口（默认 {DEFAULT_PORT}）")
    args = parser.parse_args()

    simulator = DeviceSimulator(args.device_name, args.broker, args.port)
    simulator.start()


if __name__ == "__main__":
    main()
