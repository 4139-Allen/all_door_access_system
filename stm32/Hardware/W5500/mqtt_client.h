#ifndef __MQTT_CLIENT_H
#define __MQTT_CLIENT_H

#include "stm32f10x.h"

/* MQTT 版本 */
#define MQTT_VERSION        0x04  /* v3.1.1 */

/* 连接状态 */
#define MQTT_DISCONNECTED   0
#define MQTT_CONNECTED      1

/* 固定报文类型 */
#define MQTT_CONNECT        0x10
#define MQTT_CONNACK        0x20
#define MQTT_PUBLISH        0x30
#define MQTT_SUBSCRIBE      0x82
#define MQTT_SUBACK         0x90
#define MQTT_PINGREQ        0xC0
#define MQTT_PINGRESP       0xD0

/* MQTT QoS */
#define MQTT_QOS0           0x00
#define MQTT_QOS1           0x02

/* 最大报文长度 */
#define MQTT_BUF_SIZE       256

/* MQTT 回调: 收到消息时调用 */
typedef void (*mqtt_callback_t)(char *topic, uint8_t *payload, uint16_t len);

/* MQTT 客户端结构体 */
typedef struct {
    uint8_t  sock;              /* W5500 socket 号 */
    uint8_t  connected;         /* 是否已连接 */
    uint16_t keepalive;         /* 保活间隔 (秒) */

    /* 缓冲区 */
    uint8_t  tx_buf[MQTT_BUF_SIZE];
    uint8_t  rx_buf[MQTT_BUF_SIZE];
    uint16_t rx_len;            /* 当前接收数据长度 */

    /* 回调 */
    mqtt_callback_t callback;

    /* 服务器信息 */
    uint8_t  server_ip[4];
    uint16_t server_port;
} mqtt_client_t;

/* API */
uint8_t MQTT_Connect(mqtt_client_t *client, uint8_t sock, uint8_t *ip, uint16_t port,
                     const char *client_id, mqtt_callback_t cb);
uint8_t MQTT_Subscribe(mqtt_client_t *client, const char *topic);
uint8_t MQTT_Publish(mqtt_client_t *client, const char *topic, uint8_t *payload, uint16_t len);
uint8_t MQTT_Loop(mqtt_client_t *client);
uint8_t MQTT_PingReq(mqtt_client_t *client);
void    MQTT_Disconnect(mqtt_client_t *client);

#endif /* __MQTT_CLIENT_H */
