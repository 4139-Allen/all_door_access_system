#ifndef __W5500_H
#define __W5500_H

#include "stm32f10x.h"

/* ======================== Pin Definitions ======================== */
#define W5500_SCK_PORT       GPIOA
#define W5500_SCK_PIN        GPIO_Pin_1

#define W5500_MISO_PORT      GPIOA
#define W5500_MISO_PIN       GPIO_Pin_8

#define W5500_MOSI_PORT      GPIOA
#define W5500_MOSI_PIN       GPIO_Pin_11

#define W5500_CS_PORT        GPIOA
#define W5500_CS_PIN         GPIO_Pin_12

#define W5500_RST_PORT       GPIOC
#define W5500_RST_PIN        GPIO_Pin_13

/* ======================== SPI Macros ======================== */
#define W5500_CS_L()         GPIO_ResetBits(W5500_CS_PORT, W5500_CS_PIN)
#define W5500_CS_H()         GPIO_SetBits(W5500_CS_PORT, W5500_CS_PIN)
#define W5500_SCK_L()        GPIO_ResetBits(W5500_SCK_PORT, W5500_SCK_PIN)
#define W5500_SCK_H()        GPIO_SetBits(W5500_SCK_PORT, W5500_SCK_PIN)
#define W5500_MOSI_L()       GPIO_ResetBits(W5500_MOSI_PORT, W5500_MOSI_PIN)
#define W5500_MOSI_H()       GPIO_SetBits(W5500_MOSI_PORT, W5500_MOSI_PIN)
#define W5500_MISO_GET()     GPIO_ReadInputDataBit(W5500_MISO_PORT, W5500_MISO_PIN)
#define W5500_RST_L()        GPIO_ResetBits(W5500_RST_PORT, W5500_RST_PIN)
#define W5500_RST_H()        GPIO_SetBits(W5500_RST_PORT, W5500_RST_PIN)

/* ======================== 16-bit Address Helper ======================== */
/* W5500 地址编码: BSB 占 bits[15:11], 偏移占 bits[10:0]
   SPI 帧中 BSB 放在控制字节, 偏移放在地址字节 */
#define W5500_ADDR(bsb, off)  ((((bsb) & 0x1F) << 11) | ((off) & 0x07FF))

/* ======================== Common Registers (BSB=0x00) ======================== */
#define W5500_MR             W5500_ADDR(0x00, 0x00)
#define W5500_GAR            W5500_ADDR(0x00, 0x01)
#define W5500_SUBR           W5500_ADDR(0x00, 0x05)
#define W5500_SHAR           W5500_ADDR(0x00, 0x09)
#define W5500_SIPR           W5500_ADDR(0x00, 0x0F)
#define W5500_INTLEVEL       W5500_ADDR(0x00, 0x13)
#define W5500_IR             W5500_ADDR(0x00, 0x15)
#define W5500_IMR            W5500_ADDR(0x00, 0x16)
#define W5500_SIR            W5500_ADDR(0x00, 0x17)
#define W5500_SIMR           W5500_ADDR(0x00, 0x18)
#define W5500_RTR            W5500_ADDR(0x00, 0x19)
#define W5500_RCR            W5500_ADDR(0x00, 0x1B)
#define W5500_PTMR           W5500_ADDR(0x00, 0x1C)
#define W5500_PIDR           W5500_ADDR(0x00, 0x3E)  /* 实际为 0x3E */
#define W5500_VERSION        W5500_ADDR(0x00, 0x39)  /* VERSIONR @ offset 0x0039, read: 0x04 */

/* ======================== Socket n Registers (BSB = 0x01 + n) ======================== */
#define Sn_MR(n)    W5500_ADDR(0x01 + (n), 0x00)
#define Sn_CR(n)    W5500_ADDR(0x01 + (n), 0x01)
#define Sn_IR(n)    W5500_ADDR(0x01 + (n), 0x02)
#define Sn_SR(n)    W5500_ADDR(0x01 + (n), 0x03)
#define Sn_PORT(n)  W5500_ADDR(0x01 + (n), 0x04)
#define Sn_DIPR(n)  W5500_ADDR(0x01 + (n), 0x0C)
#define Sn_DPORT(n) W5500_ADDR(0x01 + (n), 0x10)
#define Sn_MSSR(n)  W5500_ADDR(0x01 + (n), 0x12)
#define Sn_TOS(n)   W5500_ADDR(0x01 + (n), 0x15)
#define Sn_TTL(n)   W5500_ADDR(0x01 + (n), 0x16)
#define Sn_TX_FSR(n) W5500_ADDR(0x01 + (n), 0x20)
#define Sn_TX_RD(n) W5500_ADDR(0x01 + (n), 0x22)
#define Sn_TX_WR(n) W5500_ADDR(0x01 + (n), 0x24)
#define Sn_RX_RSR(n) W5500_ADDR(0x01 + (n), 0x26)
#define Sn_RX_RD(n) W5500_ADDR(0x01 + (n), 0x28)
#define Sn_IMR(n)   W5500_ADDR(0x01 + (n), 0x2C)  // Socket Interrupt Mask Register

/* Socket TX/RX buffers */
/* According to W5500 datasheet: TX BSB = 0x10+n, RX BSB = 0x18+n */
#define Sn_TXBUF(n) W5500_ADDR(0x10 + (n), 0x000)
#define Sn_RXBUF(n) W5500_ADDR(0x18 + (n), 0x000)

/* ======================== Socket Mode ======================== */
#define Sn_MR_CLOSE          0x00
#define Sn_MR_TCP            0x01
#define Sn_MR_UDP            0x02

/* ======================== Socket Commands ======================== */
#define Sn_CR_OPEN           0x01
#define Sn_CR_LISTEN         0x02
#define Sn_CR_CONNECT        0x04
#define Sn_CR_DISCON         0x08
#define Sn_CR_CLOSE          0x10
#define Sn_CR_SEND           0x20
#define Sn_CR_SEND_MAC       0x21
#define Sn_CR_SEND_KEEP      0x22
#define Sn_CR_RECV           0x40

/* ======================== Socket Status ======================== */
#define SOCK_CLOSED          0x00
#define SOCK_INIT            0x13
#define SOCK_SYNSENT         0x15
#define SOCK_SYNRECV         0x16
#define SOCK_ESTABLISHED     0x17
#define SOCK_FIN_WAIT        0x18
#define SOCK_CLOSING         0x1A
#define SOCK_TIME_WAIT       0x1B
#define SOCK_CLOSE_WAIT      0x1C
#define SOCK_LAST_ACK        0x1D
#define SOCK_UDP             0x22
#define SOCK_IPRAW           0x32
#define SOCK_MACRAW          0x42

/* ======================== Network Config Structure ======================== */
typedef struct {
    uint8_t mac[6];
    uint8_t ip[4];
    uint8_t gateway[4];
    uint8_t subnet[4];
} w5500_netinfo_t;

/* ======================== API Declarations ======================== */
void     W5500_GPIO_Init(void);
void     W5500_Reset(void);
void     W5500_Init(w5500_netinfo_t *net);
void     W5500_Write(uint16_t addr, uint8_t *data, uint16_t len);
void     W5500_Read(uint16_t addr, uint8_t *data, uint16_t len);
uint8_t  W5500_WriteByte(uint16_t addr, uint8_t data);
uint8_t  W5500_ReadByte(uint16_t addr);

/* Socket Operations */
uint8_t  W5500_Socket_Open(uint8_t sock, uint8_t protocol);
uint8_t  W5500_Socket_Connect(uint8_t sock, uint8_t *ip, uint16_t port);
uint8_t  W5500_Socket_Disconnect(uint8_t sock);
uint8_t  W5500_Socket_Close(uint8_t sock);
uint16_t W5500_Socket_Send(uint8_t sock, uint8_t *buf, uint16_t len);
uint16_t W5500_Socket_Send_Force(uint8_t sock, uint8_t *buf, uint16_t len);  // 强制发送，使用单字节写入并重试
uint16_t W5500_Socket_Recv(uint8_t sock, uint8_t *buf, uint16_t len);
uint8_t  W5500_Socket_GetStatus(uint8_t sock);

/* Diagnostic */
void     W5500_Diagnose_TX_Buffer(void);

/* Utility */
void     W5500_DelayMs(uint32_t ms);

#endif /* __W5500_H */
