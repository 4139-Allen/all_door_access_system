# 硬件说明

## 系统概述

基于 **STM32F103C8T6**（ARM Cortex-M3, 72MHz）的智能电子密码锁，通过 **ESP32-S3** WiFi 模块连接 MQTT Broker 实现物联网通信，支持四种开门方式：

1. **密码开门** — 4x4 矩阵键盘输入 6 位数字密码
2. **指纹开门** — AS608 光学指纹传感器
3. **刷卡开门** — MFRC522 RFID 读卡器
4. **远程开门** — MQTT 网络指令（来自后端服务器）

LCD12864 显示屏提供菜单式管理界面，可完成密码修改、指纹录入/删除、卡片注册/删除等操作。

## 硬件模块详情

### 1. AS608 指纹模块

| 项目 | 说明 |
|------|------|
| 芯片 | AS608 光学指纹传感器 |
| 通信 | UART (USART2, PA2-TX / PA3-RX, 57600 baud) |
| 检测引脚 | PA0（输入下拉，检测手指按压） |
| 数据包格式 | Header(0xEF01) + 4字节地址 + 包标识 + 长度 + 命令 + 数据 + 校验和 |

**主要功能：**
- `PS_GetImage()` — 采集指纹图像
- `PS_GenChar(BufferID)` — 生成特征文件
- `PS_HighSpeedSearch()` — 1:N 高速搜索（页范围 0-20，匹配分数 >50）
- `PS_StoreChar(BufferID, PageID)` — 存储模板到 Flash
- `PS_DeletChar(PageID, N)` — 删除指纹模板
- `PS_ReadSysPara()` — 读取系统参数（最大模板数、安全等级等）

**默认地址：** `0xFFFFFFFF`（广播地址）

### 2. AT24C02 EEPROM 存储模块

| 项目 | 说明 |
|------|------|
| 芯片 | AT24C02（256 字节 EEPROM） |
| 通信 | 软件 I2C（PB6-SCL, PB7-SDA, ~100kHz） |
| 设备地址 | 0xA0（写）/ 0xA1（读） |
| 写入延迟 | 10ms/字节 |

**EEPROM 数据布局（256 字节）：**

| 地址范围 | 数据 | 说明 |
|----------|------|------|
| 0 | `not_first_time` 标志 | 首次使用标志（0x55 = 已初始化） |
| 1-6 | 管理员密码 | 6 位 ASCII，默认 "888888" |
| 7-12 | 开门密码 | 6 位 ASCII，默认 "123456" |
| 13-28 | 卡片 0 | 1字节标志 + 4字节 UID + 填充 |
| 29-44 | 卡片 1 | 1字节标志 + 4字节 UID + 填充 |
| 45-60 | 卡片 2 | 1字节标志 + 4字节 UID + 填充 |
| 255 | 存活标志 | 0x55（用于检测 EEPROM 是否正常） |

### 3. MFRC522 RFID 模块

| 项目 | 说明 |
|------|------|
| 芯片 | MFRC522 (NXP) |
| 通信 | 软件 SPI（非硬件 SPI） |
| 协议 | ISO 14443A |
| 支持卡型 | Mifare Ultralight, Mifare One S50/S70, Mifare DESFire |

**引脚连接：**

| RC522 引脚 | STM32 引脚 | 功能 |
|-----------|-----------|------|
| SDA/CS | PA4 | SPI 片选 |
| SCK | PA5 | SPI 时钟 |
| MOSI | PA6 | SPI 数据输出 |
| MISO | PA7 | SPI 数据输入 |
| RST | PB0 | 硬件复位 |

**卡片注册：** 最多注册 3 张卡片（ID 0-2），每张卡片存储 4 字节 UID + 存在标志。

### 4. LCD12864 显示屏

| 项目 | 说明 |
|------|------|
| 控制器 | ST7920 兼容 |
| 分辨率 | 128x64 像素 |
| 接口 | 3 线串口模式 |

### 5. 4x4 矩阵键盘

| 项目 | 说明 |
|------|------|
| 行引脚 | PB12, PB13, PB14, PB15 |
| 列引脚 | PA8, PA9, PA10, PA11 |
| 扫描方式 | 行输出低电平，列读取 |

### 6. 通用 GPIO 模块 (General_Module)

继电器控制：PA1（输出高电平驱动继电器开锁）

## 网络通信模块

### ESP32-S3 WiFi 模块

> 目录名为 `ESP8266/`（历史原因），实际使用 **ESP32-S3** 开发板。

| 项目 | 说明 |
|------|------|
| 芯片 | ESP32-S3（乐鑫） |
| 框架 | Arduino (PlatformIO) |
| MQTT 库 | PubSubClient v2.8 |
| 调试串口 | USB Serial, 115200 baud |
| STM32 串口 | Serial1 (GPIO17-RX / GPIO18-TX), 9600 baud |
| 心跳间隔 | 30 秒 |

**功能：**
- 连接 WiFi 网络（STA 模式）
- 连接 Mosquitto MQTT Broker
- 订阅 `door/{device_id}/command` 接收开门指令
- 发布 `door/{device_id}/status` 上报状态（ONLINE/OK/PWD_OK/FP_OK/CARD_OK）
- 发布 `door/{device_id}/rssi` 上报 WiFi 信号强度
- UART 透传：MQTT 收到 `OPEN_DOOR` → 转发给 STM32；STM32 回复状态 → 发布到 MQTT

**接线（ESP32-S3 → STM32）：**

| ESP32-S3 引脚 | STM32 引脚 | 功能 |
|---------------|-----------|------|
| GPIO17 (RX) | PA9 (USART1_TX) | ESP32 接收 STM32 数据 |
| GPIO18 (TX) | PA10 (USART1_RX) | ESP32 发送数据到 STM32 |
| GND | GND | 共地 |

**配置项（`main.cpp` 中修改）：**
- `ssid` / `password` — WiFi 名称和密码
- `mqtt_server` — MQTT Broker 地址（服务器公网 IP）
- `mqtt_port` — MQTT 端口（默认 1883）
- `device_id` — 设备标识（必须与数据库中的设备名称一致，如 "001"）

### W5500 以太网模块（备选方案）

| 项目 | 说明 |
|------|------|
| 芯片 | W5500 (WIZnet) |
| 接口 | SPI 连接 STM32 |
| 特性 | 硬件 TCP/IP 协议栈，支持 8 路独立 Socket |
| 用途 | 备选网络方案（不依赖 WiFi） |

## 串口桥接脚本

`backend/serial_mqtt_bridge.py` 用于在没有 ESP32-S3 的情况下，通过电脑 USB 串口连接 STM32 并桥接到 MQTT：

**功能：**
- 自动检测 CH340 USB 串口（或手动选择）
- 订阅 `door/{DEVICE_ID}/command`，收到 `OPEN_DOOR` 时转发 `OPEN_DOOR\n` 到 STM32 串口
- 读取 STM32 串口响应（`OK`/`PWD_OK`/`FP_OK`/`CARD_OK`），发布到 MQTT 状态主题
- 每 30 秒发布 `ONLINE` 心跳
- 支持手动输入命令（调试用）

**使用场景：**
- 开发调试阶段，无需 ESP32-S3 硬件
- 通过电脑 USB 连接 STM32，运行 Python 脚本即可桥接 MQTT
- 生产环境建议使用 ESP32-S3 独立运行

## 固件目录结构

```
stm32/
├── User/                    # 用户应用代码
│   ├── main.c               # 主程序（初始化 + 主循环）
│   ├── menu/menu.c          # LCD 菜单管理
│   └── password/password.c  # 密码管理
├── AS608/                   # 指纹传感器驱动
├── AT24CXX/                 # EEPROM 存储驱动
├── RC522/                   # RFID 读卡器驱动
│   ├── rc522_config.c/h     # 引脚配置
│   └── rc522_function.c/h   # 功能函数
├── LCD12864/                # LCD 显示屏驱动
├── Martix_KEY/              # 矩阵键盘驱动
├── General_Module/          # 继电器控制
├── W5500/                   # 以太网/MQTT 驱动
│   ├── w5500.c/h            # W5500 SPI 驱动
│   └── mqtt_client.c/h      # MQTT 客户端
├── IIC/                     # 软件 I2C 总线驱动
├── System/                  # 系统库
│   ├── delay/               # 延时函数
│   ├── sys/                 # 系统配置
│   ├── timer/               # 定时器
│   └── usart/               # 串口驱动
├── Libraries/               # STM32 标准外设库 + CMSIS
└── ESP8266/                 # ESP32-S3 固件（PlatformIO 项目）
    ├── platformio.ini       # PlatformIO 配置
    └── src/main.cpp         # MQTT 透传固件
```

## 通信协议流程

```
用户操作           STM32              ESP32-S3            Mosquitto           后端
   │                │                   │                   │                  │
   │──密码/指纹/──→│                   │                   │                  │
   │  刷卡输入      │                   │                   │                  │
   │                │──验证成功──────→│                   │                  │
   │                │  "PWD_OK\n"       │──发布状态──────→│                  │
   │                │                   │  door/001/status  │──写入日志──→  │
   │                │                   │  "PWD_OK"         │──WS 通知───→  │
   │                │                   │                   │                  │
   │                │                   │                   │←──开门指令────│
   │                │                   │←──订阅消息──────│  "OPEN_DOOR"     │
   │                │←──UART 转发──────│                   │                  │
   │                │  "OPEN_DOOR\n"    │                   │                  │
   │                │──继电器开锁──→  │                   │                  │
   │                │──回复"OK\n"───→│                   │                  │
   │                │                   │──发布状态──────→│                  │
   │                │                   │  "OK"             │──WS 通知───→  │
   │                │                   │                   │                  │
   │                │                   │──心跳(30s)──────→│                  │
   │                │                   │  "ONLINE"         │──更新状态──→  │
```
