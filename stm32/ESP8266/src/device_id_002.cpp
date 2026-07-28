
/*
   ESP MQTT 透传固件（适配 STM32 门禁系统）
   支持 ESP32-S3 和 ESP-01S (ESP8266) 两个版本

   功能：
     后端通过 MQTT 发送 "OPEN_DOOR" → ESP 订阅收到 → UART 发给 STM32
     STM32 回复 "OK" → ESP 通过 MQTT 发回后端
     定时发送 "ONLINE" 心跳

   接线：
     ESP32-S3: GPIO17(RX) → STM32 PA9(TX), GPIO18(TX) → STM32 PA10(RX)
     ESP-01S:  TX(GPIO1)  → STM32 PA10(RX), RX(GPIO3) → STM32 PA9(TX)
     GND → GND

   烧录前修改：
     - ssid / password（WiFi）
     - mqtt_server（MQTT 服务器地址）
     - device_id（设备标识，必须与数据库中的设备名称一致）

   需要 Arduino 库：
     - PubSubClient by Nick O'Leary
*/

// ==================== 板子适配 ====================
#ifdef BOARD_ESP01S
  #include <ESP8266WiFi.h>
#else
  #include <WiFi.h>
#endif

#include <PubSubClient.h>

// ==================== 配置项（根据实际修改）====================
const char *ssid = "iPhone";             // WiFi 名称
const char *password = "123456889";      // WiFi 密码
const char *mqtt_server = "47.242.60.67"; // MQTT 服务器（运行后端的服务器IP公网）
const int mqtt_port = 1883;
const char *device_id = "002"; // 与数据库设备名称一致
// =============================================================

WiFiClient esp_client;
PubSubClient mqtt_client(esp_client);

// UART 接收缓冲
#define UART_BUF_SIZE 32
char uart_buf[UART_BUF_SIZE];
int uart_idx = 0;

// 心跳计时
unsigned long last_heartbeat = 0;
const unsigned long HEARTBEAT_INTERVAL = 30000; // 30 秒

// ==================== WiFi ====================
void setup_wifi()
{
  Serial.println("Scanning WiFi networks...");
  int n = WiFi.scanNetworks();
  if (n == 0)
  {
    Serial.println("No networks found!");
  }
  else
  {
    Serial.print(n);
    Serial.println(" networks found:");
    for (int i = 0; i < n; i++)
    {
      Serial.print("  ");
      Serial.print(WiFi.SSID(i));
      Serial.print(" (");
      Serial.print(WiFi.RSSI(i));
      Serial.println("dBm)");
    }
  }

  delay(10);
  Serial.println();
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int retry = 0;
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
    retry++;
    if (retry > 40)
    {
      Serial.println("\nWiFi Failed! Restarting...");
#ifdef BOARD_ESP01S
      ESP.reset();
#else
      ESP.restart();
#endif
    }
  }
  Serial.println();
  Serial.print("WiFi OK, IP: ");
  Serial.println(WiFi.localIP());
}

// ==================== MQTT 回调 ====================
void mqtt_callback(char *topic, byte *payload, unsigned int length)
{
  if (length == 9 && memcmp(payload, "OPEN_DOOR", 9) == 0)
  {
#ifdef BOARD_ESP01S
    Serial.print("OPEN_DOOR\n");
#else
    Serial1.print("OPEN_DOOR\n");
#endif
    Serial.println("Command: OPEN_DOOR -> STM32");
  }
  // 密码锁定命令
  else if (length == 4 && memcmp(payload, "LOCK", 4) == 0)
  {
#ifdef BOARD_ESP01S
    Serial.print("LOCK\n");
#else
    Serial1.print("LOCK\n");
#endif
    Serial.println("Command: LOCK -> STM32");
  }
  // 解除锁定命令
  else if (length == 6 && memcmp(payload, "UNLOCK", 6) == 0)
  {
#ifdef BOARD_ESP01S
    Serial.print("UNLOCK\n");
#else
    Serial1.print("UNLOCK\n");
#endif
    Serial.println("Command: UNLOCK -> STM32");
  }
}

// ==================== MQTT 重连 ====================
void reconnect()
{
  while (!mqtt_client.connected())
  {
    Serial.print("Connecting MQTT...");

    if (mqtt_client.connect(device_id))
    {
      Serial.println("OK");

      String command_topic = "door/";
      command_topic += device_id;
      command_topic += "/command";
      mqtt_client.subscribe(command_topic.c_str());
      Serial.print("Subscribed: ");
      Serial.println(command_topic);

      String status_topic = "door/";
      status_topic += device_id;
      status_topic += "/status";
      mqtt_client.publish(status_topic.c_str(), "ONLINE");
    }
    else
    {
      Serial.print("failed, rc=");
      Serial.print(mqtt_client.state());
      Serial.println(" retry in 5s");
      delay(5000);
    }
  }
}

// ==================== 初始化 ====================
void setup()
{
#ifdef BOARD_ESP01S
  // ESP-01S: 硬件串口同时用于调试和接 STM32
  Serial.begin(9600);
#else
  // ESP32-S3: USB 调试串口 + Serial1 接 STM32
  Serial.begin(115200);
  Serial1.begin(9600, SERIAL_8N1, 17, 18);
#endif

  Serial.println();
  Serial.println("=================================");
#ifdef BOARD_ESP01S
  Serial.println("ESP-01S Door Controller (MQTT)");
#else
  Serial.println("ESP32-S3 Door Controller (MQTT)");
#endif
  Serial.println("=================================");

  setup_wifi();

  mqtt_client.setServer(mqtt_server, mqtt_port);
  mqtt_client.setCallback(mqtt_callback);
  mqtt_client.setKeepAlive(60);
}

// ==================== 主循环 ====================
void loop()
{
  if (!mqtt_client.connected())
  {
    reconnect();
  }
  mqtt_client.loop();

  // 读 STM32 UART 回复
#ifdef BOARD_ESP01S
  while (Serial.available())
#else
  while (Serial1.available())
#endif
  {
#ifdef BOARD_ESP01S
    char c = Serial.read();
#else
    char c = Serial1.read();
#endif

    if (c == '\n')
    {
      uart_buf[uart_idx] = '\0';

      // 转发所有有效消息到后端（成功和失败事件）
      if (strcmp(uart_buf, "OK") == 0 ||
          strcmp(uart_buf, "PWD_OK") == 0 ||
          strcmp(uart_buf, "FP_OK") == 0 ||
          strcmp(uart_buf, "CARD_OK") == 0 ||
          strcmp(uart_buf, "PWD_ERR") == 0 ||
          strcmp(uart_buf, "FP_ERR") == 0 ||
          strcmp(uart_buf, "CARD_ERR") == 0)
      {
        String status_topic = "door/";
        status_topic += device_id;
        status_topic += "/status";
        mqtt_client.publish(status_topic.c_str(), uart_buf);

        // 调试输出
        Serial.print("UART -> MQTT: ");
        Serial.println(uart_buf);
      }

      uart_idx = 0;
      memset(uart_buf, 0, UART_BUF_SIZE);
    }
    else if (uart_idx < UART_BUF_SIZE - 1)
    {
      uart_buf[uart_idx++] = c;
    }
  }

  // 心跳
  if (millis() - last_heartbeat > HEARTBEAT_INTERVAL)
  {
    last_heartbeat = millis();

    String status_topic = "door/";
    status_topic += device_id;
    status_topic += "/status";
    mqtt_client.publish(status_topic.c_str(), "ONLINE");

    int rssi = WiFi.RSSI();
    String rssi_topic = "door/";
    rssi_topic += device_id;
    rssi_topic += "/rssi";
    mqtt_client.publish(rssi_topic.c_str(), String(rssi).c_str());
  }
}
