"""
设备模拟器 —— 通过 MQTT 模拟物理门禁硬件

支持普通模式和交互模式，可模拟多种设备事件。

用法：
  python simulate_device.py <设备名...> [选项]

示例：
  python simulate_device.py 001                              # 普通模式
  python simulate_device.py 001 --interactive                 # 交互模式
  python simulate_device.py 001 002 --interactive             # 多设备交互
  python simulate_device.py 001 --broker 47.242.60.67        # 指定 MQTT 地址
"""
import argparse
import time
import threading
import sys
import paho.mqtt.client as mqtt

DEFAULT_BROKER = "47.242.60.67"
DEFAULT_PORT = 1883
TOPIC_PREFIX = "door"
HEARTBEAT_INTERVAL = 30

# 可用命令列表
COMMANDS = {
    "PWD_ERR": "密码错误（失败计数+1）",
    "FP_ERR": "指纹不匹配（失败计数+1）",
    "CARD_ERR": "未授权卡片（失败计数+1）",
    "PWD_OK": "密码验证成功（重置失败计数）",
    "FP_OK": "指纹验证成功（重置失败计数）",
    "CARD_OK": "刷卡验证成功（重置失败计数）",
    "OPENED": "开门确认回复",
    "ONLINE": "发送心跳上线",
}


class DeviceSimulator:
    """模拟一个门禁设备"""

    def __init__(self, device_name: str, broker: str, port: int):
        self.device_name = device_name
        self.broker = broker
        self.port = port
        self.running = False

        self.client = mqtt.Client(client_id=f"sim_{device_name}_{int(time.time())}")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._log(f"已连接 MQTT Broker: {self.broker}:{self.port}")
            topic = f"{TOPIC_PREFIX}/{self.device_name}/command"
            client.subscribe(topic, qos=1)
            self._log(f"已订阅: {topic}")
        else:
            self._log(f"MQTT 连接失败，返回码: {rc}", "ERR")

    def _on_disconnect(self, client, userdata, rc):
        if self.running:
            self._log(f"断开连接 (rc={rc})，将在后台重连...", "WARN")

    def _on_message(self, client, userdata, msg):
        """收到来自后端的命令"""
        payload = msg.payload.decode()
        self._log(f"收到命令: {payload}", "RECV")

        if payload == "OPEN_DOOR":
            self.send_status("OPENED")
            self._log(f"已回复 OPENED（开门确认）", "SEND")

        elif payload == "LOCK":
            self._log(f"设备已被锁定！", "LOCK")

        elif payload == "UNLOCK":
            self._log(f"设备已解锁", "UNLOCK")

    def send_status(self, payload: str):
        """向 MQTT 发送状态消息"""
        topic = f"{TOPIC_PREFIX}/{self.device_name}/status"
        self.client.publish(topic, payload, qos=1)

    def _heartbeat_loop(self):
        """定时心跳"""
        while self.running:
            self.client.publish(f"{TOPIC_PREFIX}/{self.device_name}/status", "ONLINE", qos=1)
            time.sleep(HEARTBEAT_INTERVAL)

    def _log(self, msg: str, tag: str = ""):
        """统一格式化输出，带上设备名"""
        prefix = {
            "SEND": "[>]", "RECV": "[<]", "LOCK": "[!]", "UNLOCK": "[+]",
            "WARN": "[*]", "ERR": "[x]", "": "[ ]",
        }.get(tag, "[ ]")
        print(f"{prefix} {self.device_name} {msg}")

    def start(self):
        """启动模拟器（后台运行）"""
        self.running = True
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()

        t = threading.Thread(target=self._heartbeat_loop, daemon=True)
        t.start()
        # 首次心跳立即发送，让设备快速上线
        self.client.publish(f"{TOPIC_PREFIX}/{self.device_name}/status", "ONLINE", qos=1)
        time.sleep(0.2)

    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()


def interactive_loop(simulators: list):
    """交互式命令循环"""
    devices = {s.device_name: s for s in simulators}
    names = list(devices.keys())
    single = len(names) == 1

    print(f"\n{'='*50}")
    print(f"  交互模式 - 设备: {', '.join(names)}")
    print(f"  输入命令后按 Enter 发送，输入 help 查看帮助")
    print(f"  多设备时用「设备名 命令」格式")
    print(f"{'='*50}\n")

    while True:
        try:
            raw = input("> ").strip()
            if not raw:
                continue

            parts = raw.split()
            cmd = parts[-1].upper()  # 最后一段是命令
            targets = parts[:-1] if len(parts) > 1 else names  # 前面的都是设备名

            if cmd == "EXIT" or cmd == "Q":
                print("[ ] 退出交互模式")
                break

            elif cmd == "HELP":
                print(f"\n  可用命令:")
                for c, desc in COMMANDS.items():
                    print(f"    {c:12s} {desc}")
                print(f"    {'HELP':12s} 显示帮助")
                print(f"    {'EXIT':12s} 退出交互模式\n")
                print(f"  格式:")
                print(f"    PWD_ERR            - 发送给所有设备")
                print(f"    001 PWD_ERR        - 只发给 001")
                print(f"    001 002 PWD_ERR    - 发给 001 和 002\n")
                continue

            elif cmd == "STATUS":
                print(f"\n  设备状态:")
                for name, sim in devices.items():
                    status = "已连接" if sim.running else "已断开"
                    print(f"    {name}: {status}")
                print()
                continue

            elif cmd not in COMMANDS:
                print(f"[?] 未知命令: {cmd}，输入 help 查看可用命令")
                continue

            # 发送命令
            for name in targets:
                sim = devices.get(name)
                if not sim:
                    print(f"[?] 未知设备: {name}，可选: {', '.join(names)}")
                    continue
                sim.send_status(cmd)
                print(f"[>] {name} 已发送 {cmd}")

        except (EOFError, KeyboardInterrupt):
            print("\n[ ] 退出交互模式")
            break


def main():
    parser = argparse.ArgumentParser(description="门禁设备 MQTT 模拟器")
    parser.add_argument("device_names", nargs="+", help="设备名（如 001 002 003）")
    parser.add_argument("--broker", default=DEFAULT_BROKER, help=f"MQTT 地址（默认 {DEFAULT_BROKER}）")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"MQTT 端口（默认 {DEFAULT_PORT}）")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互模式，手动输入命令")
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  设备: {', '.join(args.device_names)}")
    print(f"  Broker: {args.broker}:{args.port}")
    print(f"  模式: {'交互' if args.interactive else '普通'}")
    print(f"{'='*50}")

    simulators = []
    for name in args.device_names:
        sim = DeviceSimulator(name, args.broker, args.port)
        simulators.append(sim)
        sim.start()
        print(f"[✓] {name} 已启动")

    try:
        if args.interactive:
            interactive_loop(simulators)
        else:
            print("  运行中，按 Ctrl+C 停止\n")
            while any(s.running for s in simulators):
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n[ ] 正在停止...")
    finally:
        for sim in simulators:
            sim.stop()
        print("[✓] 已停止")


if __name__ == "__main__":
    main()
