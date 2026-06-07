
#include "mqtt_client.h"
#include "w5500.h"
#include <string.h>

/* ======================== MQTT 编码工具 ======================== */

/* 将剩余长度编码到 buf，返回占用字节数 */
static uint8_t MQTT_EncodeLength(uint8_t *buf, uint16_t len)
{
    uint8_t i = 0;
    do {
        buf[i] = len % 128;
        len /= 128;
        if (len > 0) buf[i] |= 0x80;
        i++;
    } while (len > 0 && i < 4);
    return i;
}

/* 从 buf 解码剩余长度，返回长度值 */
static uint16_t MQTT_DecodeLength(uint8_t *buf, uint8_t *bytes)
{
    uint16_t len = 0;
    uint8_t i, byte;
    *bytes = 0;
    for (i = 0; i < 4; i++) {
        byte = buf[i];
        len += (byte & 0x7F) << (i * 7);
        (*bytes)++;
        if (!(byte & 0x80)) break;
    }
    return len;
}

/* ======================== MQTT 报文构建 ======================== */

/* 构建 CONNECT 报文，返回总长度 */
static uint16_t MQTT_BuildConnect(uint8_t *buf, const char *client_id)
{
    uint16_t pos = 0;
    uint16_t client_id_len = strlen(client_id);
    uint16_t remaining;
    uint8_t len_bytes;

    /* 可变头部 + 载荷长度 */
    remaining = 10 + 2 + client_id_len;  // 固定头10B + client_id长度前缀2B + id

    /* 固定头 */
    buf[pos++] = MQTT_CONNECT;  // 控制字节
    len_bytes = MQTT_EncodeLength(buf + pos, remaining);
    pos += len_bytes;

    /* 可变头: 协议名 "MQTT" */
    buf[pos++] = 0x00; buf[pos++] = 0x04;
    buf[pos++] = 'M'; buf[pos++] = 'Q';
    buf[pos++] = 'T'; buf[pos++] = 'T';
    buf[pos++] = MQTT_VERSION;      /* 协议级别 */
    buf[pos++] = 0x02;              /* 连接标志: 清会话 + 无遗嘱/用户名/密码 */
    buf[pos++] = 0x00;              /* Keep Alive 高字节 */
    buf[pos++] = 60;                /* Keep Alive 低字节 (60s) */

    /* 载荷: Client ID */
    buf[pos++] = (client_id_len >> 8) & 0xFF;
    buf[pos++] = client_id_len & 0xFF;
    memcpy(buf + pos, client_id, client_id_len);
    pos += client_id_len;

    return pos;
}

/* 构建 SUBSCRIBE 报文，返回总长度 */
static uint16_t MQTT_BuildSubscribe(uint8_t *buf, const char *topic)
{
    uint16_t pos = 0;
    uint16_t topic_len = strlen(topic);
    uint16_t remaining;
    uint8_t len_bytes;

    remaining = 2 + 2 + topic_len + 1;  // packet_id(2) + topic_len(2) + topic + qos(1)

    buf[pos++] = MQTT_SUBSCRIBE;
    len_bytes = MQTT_EncodeLength(buf + pos, remaining);
    pos += len_bytes;

    /* Packet ID */
    buf[pos++] = 0x00; buf[pos++] = 0x01;

    /* Topic Filter */
    buf[pos++] = (topic_len >> 8) & 0xFF;
    buf[pos++] = topic_len & 0xFF;
    memcpy(buf + pos, topic, topic_len);
    pos += topic_len;

    /* QoS */
    buf[pos++] = MQTT_QOS0;

    return pos;
}

/* 构建 PUBLISH 报文，返回总长度 */
static uint16_t MQTT_BuildPublish(uint8_t *buf, const char *topic, uint8_t *payload, uint16_t payload_len)
{
    uint16_t pos = 0;
    uint16_t topic_len = strlen(topic);
    uint16_t remaining;
    uint8_t len_bytes;

    remaining = 2 + topic_len + payload_len;

    buf[pos++] = MQTT_PUBLISH | MQTT_QOS0;  // QoS 0, 无 Packet ID
    len_bytes = MQTT_EncodeLength(buf + pos, remaining);
    pos += len_bytes;

    /* Topic */
    buf[pos++] = (topic_len >> 8) & 0xFF;
    buf[pos++] = topic_len & 0xFF;
    memcpy(buf + pos, topic, topic_len);
    pos += topic_len;

    /* Payload */
    memcpy(buf + pos, payload, payload_len);
    pos += payload_len;

    return pos;
}

/* 构建 PINGREQ 报文 */
static uint16_t MQTT_BuildPingReq(uint8_t *buf)
{
    buf[0] = MQTT_PINGREQ;
    buf[1] = 0x00;
    return 2;
}

/* ======================== MQTT 接收解析 ======================== */

/* 处理收到的 MQTT 数据 */
static uint8_t MQTT_HandlePacket(mqtt_client_t *client, uint8_t *data, uint16_t len)
{
    uint8_t pos = 0;
    uint8_t len_bytes;
    uint16_t remaining;
    uint8_t packet_type;
    uint16_t topic_len;
    char *topic;
    uint8_t *payload;
    uint16_t payload_len;

    while (pos < len) {
        packet_type = data[pos] & 0xF0;

        /* 解析剩余长度 */
        remaining = MQTT_DecodeLength(data + pos + 1, &len_bytes);
        pos += 1 + len_bytes;

        if (remaining == 0 && pos > len) break;

        switch (packet_type) {
            case MQTT_CONNACK:
                /* 第1字节: 固定0, 第2字节: 返回码 */
                if (pos + 2 <= len && data[pos + 1] == 0x00) {
                    client->connected = 1;
                }
                pos += remaining;
                break;

            case MQTT_SUBACK:
                pos += remaining;
                break;

            case MQTT_PUBLISH:
                /* Topic 长度 */
                topic_len = (data[pos] << 8) | data[pos + 1];
                pos += 2;

                /* Topic */
                topic = (char *)(data + pos);
                pos += topic_len;

                /* Payload */
                payload = data + pos;
                payload_len = remaining - 2 - topic_len;
                pos += payload_len;

                /* 调用回调 */
                if (client->callback) {
                    client->callback(topic, payload, payload_len);
                }
                break;

            case MQTT_PINGRESP:
                pos += remaining;
                break;

            default:
                pos += remaining;
                break;
        }
    }
    return 1;
}

/* ======================== 公开 API ======================== */

/* 连接 MQTT Broker */
uint8_t MQTT_Connect(mqtt_client_t *client, uint8_t sock, uint8_t *ip, uint16_t port,
                     const char *client_id, mqtt_callback_t cb)
{
    uint16_t len;
    uint8_t retry;

    client->sock = sock;
    client->connected = 0;
    client->keepalive = 60;
    client->callback = cb;
    client->rx_len = 0;
    memcpy(client->server_ip, ip, 4);
    client->server_port = port;

    printf("[DBG] MQTT: Open socket %d...\n", sock);

    // 尝试打开 Socket，如果失败则硬件复位 W5500 后重试
    for (retry = 0; retry < 3; retry++) {
        if (W5500_Socket_Open(sock, Sn_MR_TCP)) {
            printf("[DBG] MQTT: Socket OPEN OK\n");
            break;
        }

        printf("[WARN] MQTT: Socket OPEN failed (attempt %d), resetting W5500...\n", retry + 1);

        // 硬件复位 W5500
        W5500_Reset();

        // 重新初始化网络配置（需要外部提供 netcfg）
        // 这里先尝试直接打开，如果还是失败，外部需要重新调用 W5500_Init
        W5500_DelayMs(100);
    }

    if (retry >= 3) {
        printf("[ERR] MQTT: Socket OPEN failed after 3 attempts!\n");
        return 0;
    }

    printf("[DBG] MQTT: TCP connect to %d.%d.%d.%d:%u...\n", ip[0], ip[1], ip[2], ip[3], port);
    /* 先建立 TCP 连接 */
    if (!W5500_Socket_Connect(sock, ip, port)) {
        printf("[ERR] MQTT: TCP CONNECT failed!\n");
        W5500_Socket_Close(sock);
        return 0;
    }
    printf("[DBG] MQTT: TCP CONNECT OK\n");

    /* TCP 连接建立后，再构建并发送 MQTT CONNECT 报文 */
    len = MQTT_BuildConnect(client->tx_buf, client_id);
    printf("[DBG] MQTT CONNECT raw: ");
    for (uint16_t di = 0; di < len; di++) printf("%02X ", client->tx_buf[di]);
    printf("(len=%u)\n", len);

    /* 使用 W5500_Socket_Send_Force 发送（使用单字节写入并重试，解决 Socket 0 TX Buffer 问题） */
    printf("[DBG] MQTT: Sending CONNECT packet with Force method...\n");
    if (W5500_Socket_Send_Force(sock, client->tx_buf, len) != len) {
        printf("[ERR] MQTT: SEND failed!\n");
        W5500_Socket_Close(sock);
        return 0;
    }
    printf("[DBG] MQTT: SEND OK\n");

    /* 等待 CONNACK */
    printf("[DBG] MQTT: Wait CONNACK...\n");
    for (uint16_t i = 0; i < 100; i++) {
        uint8_t sr = W5500_ReadByte(Sn_SR(sock));
        uint16_t rxrsr = W5500_ReadByte(Sn_RX_RSR(sock)) << 8;
        rxrsr |= W5500_ReadByte(Sn_RX_RSR(sock) + 1);
        uint16_t rlen = W5500_Socket_Recv(sock, client->rx_buf + client->rx_len,
                                           MQTT_BUF_SIZE - client->rx_len);
        if (rlen > 0) {
            printf("[DBG] MQTT: Recv %d bytes\n", rlen);
            client->rx_len += rlen;
            MQTT_HandlePacket(client, client->rx_buf, client->rx_len);
            client->rx_len = 0;
        }
        if (sr != 0x17 || rxrsr > 0) {
            printf("[DBG] MQTT: wait[%d] SR=0x%02X RX_RSR=%u rlen=%u\n", i, sr, rxrsr, rlen);
        }
        if (client->connected) break;
        W5500_DelayMs(50);
    }

    if (client->connected) {
        printf("[OK] MQTT: Connected to broker!\n");
    } else {
        printf("[ERR] MQTT: No CONNACK from broker!\n");
    }
    return client->connected;
}

/* 订阅主题 */
uint8_t MQTT_Subscribe(mqtt_client_t *client, const char *topic)
{
    uint16_t len;

    if (!client->connected) return 0;

    len = MQTT_BuildSubscribe(client->tx_buf, topic);
    return (W5500_Socket_Send_Force(client->sock, client->tx_buf, len) == len);
}

/* 发布消息 */
uint8_t MQTT_Publish(mqtt_client_t *client, const char *topic, uint8_t *payload, uint16_t len)
{
    uint16_t pkt_len;

    if (!client->connected) return 0;

    pkt_len = MQTT_BuildPublish(client->tx_buf, topic, payload, len);
    return (W5500_Socket_Send(client->sock, client->tx_buf, pkt_len) == pkt_len);
}

/* 轮询: 处理接收数据 */
uint8_t MQTT_Loop(mqtt_client_t *client)
{
    uint16_t rlen;

    if (!client->connected) return 0;

    /* 接收数据 */
    rlen = W5500_Socket_Recv(client->sock, client->rx_buf, MQTT_BUF_SIZE);
    if (rlen > 0) {
        MQTT_HandlePacket(client, client->rx_buf, rlen);
    }

    /* 检查连接状态 */
    if (W5500_Socket_GetStatus(client->sock) != SOCK_ESTABLISHED) {
        client->connected = 0;
        return 0;
    }

    return 1;
}

/* 发送 PINGREQ */
uint8_t MQTT_PingReq(mqtt_client_t *client)
{
    uint16_t len;
    if (!client->connected) return 0;
    len = MQTT_BuildPingReq(client->tx_buf);
    return (W5500_Socket_Send_Force(client->sock, client->tx_buf, len) == len);
}

/* 断开连接 */
void MQTT_Disconnect(mqtt_client_t *client)
{
    client->connected = 0;
    W5500_Socket_Disconnect(client->sock);
    W5500_Socket_Close(client->sock);
}
