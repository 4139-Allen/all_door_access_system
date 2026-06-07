#include "w5500.h"
#include <stdio.h>

static uint8_t W5500_SPI_Transfer_Byte(uint8_t data)
{
    uint8_t i, ret = 0;
    
    for (i = 0; i < 8; i++) {
        // 在SCK低电平时设置MOSI数据
        if (data & 0x80)  W5500_MOSI_H();
        else              W5500_MOSI_L();
        
        // 延时让MOSI数据稳定
        { volatile int d; for(d=0;d<10;d++); }
        
        // SCK拉高（上升沿，W5500在此刻采样MOSI）
        W5500_SCK_H();
        
        // 读取MISO（W5500在SCK下降沿输出数据）
        ret <<= 1;
        if (W5500_MISO_GET()) ret |= 1;
        
        // 保持SCK高电平一段时间
        { volatile int d; for(d=0;d<10;d++); }
        
        // SCK拉低
        W5500_SCK_L();
        
        // 保持SCK低电平，准备下一个bit
        { volatile int d; for(d=0;d<10;d++); }
        
        data <<= 1;
    }
    return ret;
}

void W5500_GPIO_Init(void)
{
    GPIO_InitTypeDef gpio;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_GPIOB | RCC_APB2Periph_GPIOC, ENABLE);

    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    gpio.GPIO_Mode  = GPIO_Mode_Out_PP;

    gpio.GPIO_Pin = W5500_SCK_PIN;
    GPIO_Init(W5500_SCK_PORT, &gpio);

    gpio.GPIO_Pin = W5500_MOSI_PIN;
    GPIO_Init(W5500_MOSI_PORT, &gpio);

    gpio.GPIO_Pin = W5500_CS_PIN;
    GPIO_Init(W5500_CS_PORT, &gpio);

    gpio.GPIO_Pin = W5500_RST_PIN;
    GPIO_Init(W5500_RST_PORT, &gpio);

    gpio.GPIO_Mode  = GPIO_Mode_IN_FLOATING;
    gpio.GPIO_Pin = W5500_MISO_PIN;
    GPIO_Init(W5500_MISO_PORT, &gpio);

    W5500_CS_H();
    W5500_SCK_L();
    W5500_RST_H();
}

void W5500_Reset(void)
{
    printf("[DBG] W5500: Hardware reset start...\n");
    W5500_RST_L();
    W5500_DelayMs(50);  // 保持低电平至少50ms
    W5500_RST_H();
    W5500_DelayMs(100); // 复位后等待100ms让芯片稳定
    printf("[DBG] W5500: Hardware reset complete\n");
}

void W5500_Write(uint16_t addr, uint8_t *data, uint16_t len)
{
    uint16_t i;
    uint8_t ctrl;
    uint16_t offset;

    /* W5500 VDM (Variable Data Length Mode) SPI frame:
     *   [Offset high byte] [Offset low byte] [Control byte] [Data...]
     *
     * 地址编码: bits[15:11] = BSB, bits[10:0] = 块内偏移
     * 控制字节: bits[7:3]=BSB, bit[2]=RWB(1=Write), bits[1:0]=OM(00=VDM)
     */
    ctrl = ((addr >> 11) & 0x1F) << 3;  // BSB in bits[7:3]
    ctrl |= (1 << 2);                    // RWB = 1 (Write)
    ctrl |= 0x00;                        // OM = 00 (VDM)
    offset = addr & 0x07FF;              // 11-bit 块内偏移

    // 调试输出：打印地址和控制字节
    if (addr >= 0x8000 && addr < 0xA000) {  // TX缓冲区地址范围
        printf("[DBG_WRITE] addr=0x%04X ctrl=0x%02X offset=0x%03X len=%u\n", addr, ctrl, offset, len);
    }

    W5500_CS_L();
    // CS拉低后等待稳定
    { volatile int d; for(d=0;d<5;d++); }
    
    W5500_SPI_Transfer_Byte((offset >> 8) & 0xFF);  // Offset high byte
    W5500_SPI_Transfer_Byte(offset & 0xFF);          // Offset low byte
    W5500_SPI_Transfer_Byte(ctrl);                   // Control byte (BSB+RWB+OM)
    
    // 调试：打印第一个要写入的数据字节
    if (addr >= 0x8000 && addr < 0xA000 && len > 0) {
        printf("[DBG_WRITE] First data byte: 0x%02X\n", data[0]);
    }
    
    for (i = 0; i < len; i++) {
        uint8_t ret = W5500_SPI_Transfer_Byte(data[i]);  // Data
        // 调试：打印前几个字节的SPI返回
        if (addr >= 0x8000 && addr < 0xA000 && i < 3) {
            printf("[DBG_WRITE] SPI write byte %d: sent=0x%02X ret=0x%02X\n", i, data[i], ret);
        }
    }
    
    // CS拉高前等待
    { volatile int d; for(d=0;d<5;d++); }
    W5500_CS_H();
}

void W5500_Read(uint16_t addr, uint8_t *data, uint16_t len)
{
    uint16_t i;
    uint8_t ctrl;
    uint16_t offset;

    ctrl = ((addr >> 11) & 0x1F) << 3;  // BSB in bits[7:3]
    ctrl |= (0 << 2);                    // RWB = 0 (Read)
    ctrl |= 0x00;                        // OM = 00 (VDM)
    offset = addr & 0x07FF;              // 11-bit 块内偏移

    W5500_CS_L();
    // CS拉低后等待稳定
    { volatile int d; for(d=0;d<5;d++); }
    
    W5500_SPI_Transfer_Byte((offset >> 8) & 0xFF);  // Offset high byte
    W5500_SPI_Transfer_Byte(offset & 0xFF);          // Offset low byte
    W5500_SPI_Transfer_Byte(ctrl);                   // Control byte (BSB+RWB+OM)
    for (i = 0; i < len; i++) {
        data[i] = W5500_SPI_Transfer_Byte(0x00);
    }
    
    // CS拉高前等待
    { volatile int d; for(d=0;d<5;d++); }
    W5500_CS_H();
}

uint8_t W5500_WriteByte(uint16_t addr, uint8_t data)
{
    W5500_Write(addr, &data, 1);
    return data;
}

uint8_t W5500_ReadByte(uint16_t addr)
{
    uint8_t data;
    W5500_Read(addr, &data, 1);
    return data;
}

void W5500_Init(w5500_netinfo_t *net)
{
    // 注意：复位已在main.c中执行，这里只配置网络参数

    // 配置TX/RX缓冲区大小（每个socket 2KB TX + 2KB RX）
    // TMSR = 0x55, RMSR = 0x55 (默认值，但显式配置确保正确)
    W5500_WriteByte(W5500_ADDR(0x00, 0x1E), 0x55);  // TMSR
    W5500_WriteByte(W5500_ADDR(0x00, 0x1F), 0x55);  // RMSR
    
    // 验证缓冲区大小配置
    uint8_t tmsr = W5500_ReadByte(W5500_ADDR(0x00, 0x1E));
    uint8_t rmsr = W5500_ReadByte(W5500_ADDR(0x00, 0x1F));
    printf("[DBG] W5500: TMSR=0x%02X RMSR=0x%02X\n", tmsr, rmsr);

    // 配置网络参数
    W5500_Write(W5500_GAR, net->gateway, 4);
    W5500_Write(W5500_SUBR, net->subnet, 4);
    W5500_Write(W5500_SHAR, net->mac, 6);
    W5500_Write(W5500_SIPR, net->ip, 4);

    W5500_WriteByte(W5500_RTR, 0x07);
    W5500_WriteByte(W5500_RTR + 1, 0xD0);
    W5500_WriteByte(W5500_RCR, 8);
    
    printf("[DBG] W5500: Network config complete\n");
}

/* ======================== Socket Operations ======================== */

#define W5500_SRC_PORT_BASE  50000
static uint16_t next_src_port = 0;

uint8_t W5500_Socket_Open(uint8_t sock, uint8_t protocol)
{
    if (sock > 7) return 0;

    printf("[DBG] W5500: Socket%d OPEN - before CLOSE status=0x%02X\n", sock, W5500_ReadByte(Sn_SR(sock)));
    
    // 清除中断寄存器
    W5500_WriteByte(Sn_IR(sock), 0xFF);
    W5500_DelayMs(5);
    
    // 先清零MR寄存器
    W5500_WriteByte(Sn_MR(sock), 0x00);
    W5500_DelayMs(10);
    
    // 强制关闭socket
    W5500_WriteByte(Sn_CR(sock), Sn_CR_CLOSE);
    W5500_DelayMs(20);
    
    // 再次清除中断
    W5500_WriteByte(Sn_IR(sock), 0xFF);
    W5500_DelayMs(5);
    
    // 等待状态变为CLOSED
    {
        uint16_t timeout = 0;
        uint8_t status;
        while (timeout < 100) {
            status = W5500_ReadByte(Sn_SR(sock));
            if (status == SOCK_CLOSED) break;
            
            // 每50次重试发送一次CLOSE
            if (timeout % 50 == 0 && timeout > 0) {
                W5500_WriteByte(Sn_CR(sock), Sn_CR_CLOSE);
            }
            
            W5500_DelayMs(5);
            timeout++;
        }
        printf("[DBG] W5500: Socket%d after CLOSE wait status=0x%02X (timeout=%d)\n", sock, status, timeout);
        
        // 如果仍然不是CLOSED，强制重置该socket的所有寄存器
        if (status != SOCK_CLOSED) {
            printf("[DBG] W5500: Socket%d force reset registers...\n", sock);
            W5500_WriteByte(Sn_MR(sock), 0x00);
            W5500_WriteByte(Sn_CR(sock), Sn_CR_CLOSE);
            W5500_WriteByte(Sn_IR(sock), 0xFF);
            W5500_WriteByte(Sn_IMR(sock), 0x00);  // 禁用中断
            W5500_DelayMs(50);
            status = W5500_ReadByte(Sn_SR(sock));
            printf("[DBG] W5500: Socket%d after force reset status=0x%02X\n", sock, status);
        }
    }
    
    // 设置协议模式
    W5500_WriteByte(Sn_MR(sock), protocol);
    W5500_DelayMs(10);
    
    // 验证MR是否写入成功
    uint8_t mr_check = W5500_ReadByte(Sn_MR(sock));
    printf("[DBG] W5500: Socket%d MR check: wrote=0x%02X, read=0x%02X\n", sock, protocol, mr_check);
    
    if (mr_check != protocol) {
        printf("[ERR] W5500: Socket%d MR write failed!\n", sock);
        return 0;
    }

    /* Sn_PORT MUST be set before OPEN command */
    {
        uint16_t port = W5500_SRC_PORT_BASE + (next_src_port++);
        if (next_src_port > 1000) next_src_port = 0;
        W5500_WriteByte(Sn_PORT(sock), (port >> 8) & 0xFF);
        W5500_WriteByte(Sn_PORT(sock) + 1, port & 0xFF);
    }
    W5500_DelayMs(2);

    // 发送OPEN命令
    W5500_WriteByte(Sn_CR(sock), Sn_CR_OPEN);
    W5500_DelayMs(20);
    
    // 等待状态变为INIT
    {
        uint16_t timeout = 0;
        uint8_t status;
        while (timeout < 100) {
            status = W5500_ReadByte(Sn_SR(sock));
            if (status == SOCK_INIT) {
                printf("[DBG] W5500: Socket%d OPEN success! status=0x%02X\n", sock, status);
                return 1;
            }
            W5500_DelayMs(5);
            timeout++;
        }
        printf("[DBG] W5500: Socket%d OPEN timeout, final status=0x%02X\n", sock, status);
    }
    
    return 0;
}

uint8_t W5500_Socket_Connect(uint8_t sock, uint8_t *ip, uint16_t port)
{
    uint8_t status;
    uint16_t timeout = 0;

    if (sock > 7) return 0;

    W5500_Write(Sn_DIPR(sock), ip, 4);
    W5500_WriteByte(Sn_DPORT(sock), (port >> 8) & 0xFF);
    W5500_WriteByte(Sn_DPORT(sock) + 1, port & 0xFF);

    printf("[DBG] W5500: Socket%d CONNECT to %d.%d.%d.%d:%u...\n", sock, ip[0], ip[1], ip[2], ip[3], port);
    W5500_WriteByte(Sn_CR(sock), Sn_CR_CONNECT);
    W5500_DelayMs(5);

    while (timeout < 500) {
        status = W5500_ReadByte(Sn_SR(sock));
        if (status == SOCK_ESTABLISHED) {
            printf("[DBG] W5500: Socket%d ESTABLISHED\n", sock);
            return 1;
        }
        if (status == SOCK_CLOSED) {
            printf("[WARN] W5500: Socket%d CLOSED during connect (timeout=%d)\n", sock, timeout);
            return 0;
        }
        if (timeout > 0 && timeout % 50 == 0) {
            printf("[DBG] W5500: Socket%d state=0x%02X (waiting...)\n", sock, status);
        }
        W5500_DelayMs(10);
        timeout++;
    }
    printf("[ERR] W5500: Socket%d CONNECT timeout, last state=0x%02X\n", sock, status);
    return 0;
}

uint8_t W5500_Socket_Disconnect(uint8_t sock)
{
    W5500_WriteByte(Sn_CR(sock), Sn_CR_DISCON);
    return 1;
}

uint8_t W5500_Socket_Close(uint8_t sock)
{
    W5500_WriteByte(Sn_CR(sock), Sn_CR_CLOSE);
    return 1;
}

uint16_t W5500_Socket_Send(uint8_t sock, uint8_t *buf, uint16_t len)
{
    uint16_t free_size, timeout = 0;
    uint16_t tx_wr;
    uint8_t sr;

    if (len == 0 || sock > 7) { printf("[DBG] W5500_Socket_Send: invalid params len=%u sock=%u\n", len, sock); return 0; }

    sr = W5500_ReadByte(Sn_SR(sock));
    if (sr != SOCK_ESTABLISHED) { printf("[DBG] W5500_Socket_Send: Sn_SR=0x%02X != ESTABLISHED\n", sr); return 0; }

    while (timeout < 200) {
        free_size = W5500_ReadByte(Sn_TX_FSR(sock)) << 8;
        free_size |= W5500_ReadByte(Sn_TX_FSR(sock) + 1);
        if (free_size >= len) break;
        W5500_DelayMs(5);
        timeout++;
    }
    if (timeout >= 200) { printf("[DBG] W5500_Socket_Send: TX_FSR timeout, free_size=%u need=%u\n", free_size, len); return 0; }

    tx_wr = W5500_ReadByte(Sn_TX_WR(sock)) << 8;
    tx_wr |= W5500_ReadByte(Sn_TX_WR(sock) + 1);
    printf("[SEND] Sn_TX_WR init=%u FSR=%u\n", tx_wr, free_size);
    printf("[SEND] Writing to TXBUF addr=0x%04X (Sn_TXBUF=%u + offset=%u)\n", 
           (uint16_t)(Sn_TXBUF(sock) + tx_wr), (uint16_t)Sn_TXBUF(sock), tx_wr);
    { uint16_t di; for (di = 0; di < (len > 16 ? 16 : len); di++) printf("%02X ", buf[di]); printf("(len=%u)\n", len); }

    W5500_Write(Sn_TXBUF(sock) + tx_wr, buf, len);

    /* 立即用单字节方式读取第一个字节验证 */
    if (len > 0) {
        uint8_t test_read = W5500_ReadByte(Sn_TXBUF(sock) + tx_wr);
        printf("[SEND] Single-byte verify after write: read=0x%02X (expected 0x%02X) %s\n",
               test_read, buf[0], (test_read == buf[0]) ? "OK" : "FAIL");
    }

    /* Read back and verify TX buffer content */
    {
        uint8_t vbuf[64];
        uint16_t vlen = (len > sizeof(vbuf)) ? sizeof(vbuf) : len;
        uint16_t vi, verr = 0;
        W5500_Read(Sn_TXBUF(sock) + tx_wr, vbuf, vlen);
        printf("[SEND] Verify TXBUF: ");
        for (vi = 0; vi < vlen; vi++) { printf("%02X ", vbuf[vi]); if (vbuf[vi] != buf[vi]) verr++; }
        printf("(%u errors)\n", verr);
    }

    tx_wr += len;
    {
        uint8_t wr[2];
        wr[0] = (tx_wr >> 8) & 0xFF;
        wr[1] = tx_wr & 0xFF;
        printf("[SEND] Writing Sn_TX_WR with value=%u (0x%02X 0x%02X)\n", tx_wr, wr[0], wr[1]);
        W5500_Write(Sn_TX_WR(sock), wr, 2);
        W5500_DelayMs(10);  // 增加等待时间
        
        // 验证Sn_TX_WR是否写入成功
        uint8_t verify_wr[2];
        W5500_Read(Sn_TX_WR(sock), verify_wr, 2);
        uint16_t verify_val = (verify_wr[0] << 8) | verify_wr[1];
        printf("[SEND] Verify Sn_TX_WR: wrote=%u, read=%u %s\n", tx_wr, verify_val, 
               (verify_val == tx_wr) ? "OK" : "MISMATCH!");
    }

    W5500_WriteByte(Sn_CR(sock), Sn_CR_SEND);
    W5500_DelayMs(10);
    
    // 读取发送前的状态
    printf("[SEND] After SEND cmd: Sn_SR=0x%02X Sn_IR=0x%02X\n", 
           W5500_ReadByte(Sn_SR(sock)), W5500_ReadByte(Sn_IR(sock)));

    timeout = 0;
    while (timeout < 200) {
        uint8_t ir = W5500_ReadByte(Sn_IR(sock));
        uint8_t sr = W5500_ReadByte(Sn_SR(sock));
        
        if (timeout % 50 == 0) {
            printf("[SEND] Poll[%d]: Sn_IR=0x%02X Sn_SR=0x%02X\n", timeout, ir, sr);
        }
        
        if (ir & 0x08) {  // SEND_OK
            W5500_WriteByte(Sn_IR(sock), 0x08);
            printf("[SEND] OK (Sn_IR=0x%02X Sn_SR=0x%02X)\n", ir, sr);
            return len;
        }
        if (ir & 0x10) {  // TIMEOUT
            W5500_WriteByte(Sn_IR(sock), 0x10);
            printf("[SEND] TIMEOUT (Sn_IR=0x%02X Sn_SR=0x%02X)\n", ir, sr);
            return 0;
        }
        if (sr == SOCK_CLOSED || sr == SOCK_CLOSE_WAIT) {
            printf("[SEND] Socket closed unexpectedly (Sn_SR=0x%02X)\n", sr);
            return 0;
        }
        
        W5500_DelayMs(5);
        timeout++;
    }
    printf("[SEND] SEND poll timeout, Sn_SR=0x%02X Sn_IR=0x%02X\n", 
           W5500_ReadByte(Sn_SR(sock)), W5500_ReadByte(Sn_IR(sock)));
    return 0;
}

uint16_t W5500_Socket_Recv(uint8_t sock, uint8_t *buf, uint16_t len)
{
    uint16_t recv_size;
    uint16_t rx_rd;

    if (sock > 7) return 0;

    recv_size = W5500_ReadByte(Sn_RX_RSR(sock)) << 8;
    recv_size |= W5500_ReadByte(Sn_RX_RSR(sock) + 1);
    if (recv_size == 0) return 0;

    if (recv_size > len) recv_size = len;

    rx_rd = W5500_ReadByte(Sn_RX_RD(sock)) << 8;
    rx_rd |= W5500_ReadByte(Sn_RX_RD(sock) + 1);

    W5500_Read(Sn_RXBUF(sock) + rx_rd, buf, recv_size);

    rx_rd += recv_size;
    {
        uint8_t wr[2];
        wr[0] = (rx_rd >> 8) & 0xFF;
        wr[1] = rx_rd & 0xFF;
        W5500_Write(Sn_RX_RD(sock), wr, 2);
    }

    W5500_WriteByte(Sn_CR(sock), Sn_CR_RECV);

    return recv_size;
}

uint8_t W5500_Socket_GetStatus(uint8_t sock)
{
    return W5500_ReadByte(Sn_SR(sock));
}

// 诊断函数：测试不同BSB值的TX缓冲区可写性
void W5500_Diagnose_TX_Buffer(void)
{
    uint8_t test_data[] = {0xAA, 0x55, 0x10, 0x0F};
    uint8_t read_back;
    uint16_t bsb;
    
    printf("\n[DIAG] ===== W5500 TX Buffer Diagnosis =====\n");
    
    // 测试BSB从0x08到0x1F的TX缓冲区
    for (bsb = 0x08; bsb <= 0x1F; bsb++) {
        uint16_t addr = (bsb << 11) | 0x000;  // 偏移为0
        
        // 尝试写入测试数据
        W5500_Write(addr, test_data, 4);
        
        // 立即读回验证
        read_back = W5500_ReadByte(addr);
        
        if (read_back == test_data[0]) {
            printf("[DIAG] BSB=0x%02X (addr=0x%04X): WRITE SUCCESS! read=0x%02X expected=0x%02X\n",
                   bsb, addr, read_back, test_data[0]);
        } else {
            printf("[DIAG] BSB=0x%02X (addr=0x%04X): FAIL read=0x%02X expected=0x%02X\n",
                   bsb, addr, read_back, test_data[0]);
        }
    }
    
    printf("[DIAG] ===== Diagnosis Complete =====\n\n");
    
    // 分析可用的Socket
    printf("[DIAG] ===== Socket Analysis =====\n");
    printf("[DIAG] Based on W5500 datasheet:\n");
    printf("[DIAG]   Socket 0: TX BSB=0x10, RX BSB=0x18\n");
    printf("[DIAG]   Socket 1: TX BSB=0x11, RX BSB=0x19\n");
    printf("[DIAG]   Socket 2: TX BSB=0x12, RX BSB=0x1A\n");
    printf("[DIAG]   Socket 3: TX BSB=0x13, RX BSB=0x1B\n");
    printf("[DIAG]   Socket 4: TX BSB=0x14, RX BSB=0x1C\n");
    printf("[DIAG]   Socket 5: TX BSB=0x15, RX BSB=0x1D\n");
    printf("[DIAG]   Socket 6: TX BSB=0x16, RX BSB=0x1E\n");
    printf("[DIAG]   Socket 7: TX BSB=0x17, RX BSB=0x1F\n");
    printf("[DIAG] ===== End Analysis =====\n\n");
}

// 强制发送函数：使用单字节写入并重试，解决 Socket 0 TX Buffer 写入问题
uint16_t W5500_Socket_Send_Force(uint8_t sock, uint8_t *buf, uint16_t len)
{
    uint16_t tx_wr;
    uint8_t sr;
    uint16_t retry;
    uint16_t i;

    if (len == 0 || sock > 7) return 0;

    sr = W5500_ReadByte(Sn_SR(sock));
    if (sr != SOCK_ESTABLISHED) {
        printf("[SEND_FORCE] Socket not ESTABLISHED (0x%02X)\n", sr);
        return 0;
    }

    // 获取当前 TX 写指针
    tx_wr = W5500_ReadByte(Sn_TX_WR(sock)) << 8;
    tx_wr |= W5500_ReadByte(Sn_TX_WR(sock) + 1);
    printf("[SEND_FORCE] Sn_TX_WR=%u, len=%u\n", tx_wr, len);

    // 先测试 TX Buffer 的可写性
    printf("[SEND_FORCE] Testing TX buffer writability...\n");
    {
        uint8_t test_val = 0xA5;
        uint8_t read_back;
        uint16_t test_addr = Sn_TXBUF(sock) + tx_wr;

        // 写入测试值
        W5500_WriteByte(test_addr, test_val);
        W5500_DelayMs(2);
        read_back = W5500_ReadByte(test_addr);

        if (read_back != test_val) {
            printf("[SEND_FORCE] TX buffer test FAILED! wrote=0x%02X read=0x%02X\n", test_val, read_back);
            printf("[SEND_FORCE] Socket %d TX buffer is damaged, trying alternative approach...\n", sock);

            // 尝试使用不同的地址偏移
            printf("[SEND_FORCE] Trying with offset +2048...\n");
            test_addr = Sn_TXBUF(sock) + 2048;
            W5500_WriteByte(test_addr, test_val);
            W5500_DelayMs(2);
            read_back = W5500_ReadByte(test_addr);

            if (read_back == test_val) {
                printf("[SEND_FORCE] Alternative address works! Using offset 2048\n");
                tx_wr = 2048;  // 使用偏移 2048
            } else {
                printf("[SEND_FORCE] Alternative address also failed. Cannot send data.\n");
                return 0;
            }
        } else {
            printf("[SEND_FORCE] TX buffer test OK\n");
        }
    }

    // 尝试写入 TX Buffer，最多重试 5 次
    for (retry = 0; retry < 5; retry++) {
        uint8_t write_ok = 1;

        printf("[SEND_FORCE] Attempt %d: Writing %u bytes...\n", retry + 1, len);

        // 使用单字节写入方式
        for (i = 0; i < len; i++) {
            W5500_WriteByte(Sn_TXBUF(sock) + tx_wr + i, buf[i]);
        }

        // 验证写入
        for (i = 0; i < len; i++) {
            uint8_t read_back = W5500_ReadByte(Sn_TXBUF(sock) + tx_wr + i);
            if (read_back != buf[i]) {
                printf("[SEND_FORCE] Verify fail at byte %d: wrote=0x%02X read=0x%02X\n",
                       i, buf[i], read_back);
                write_ok = 0;
                break;
            }
        }

        if (write_ok) {
            printf("[SEND_FORCE] Write OK on attempt %d\n", retry + 1);

            // 更新 Sn_TX_WR
            tx_wr += len;
            W5500_WriteByte(Sn_TX_WR(sock), (tx_wr >> 8) & 0xFF);
            W5500_WriteByte(Sn_TX_WR(sock) + 1, tx_wr & 0xFF);

            // 发送 SEND 命令
            W5500_WriteByte(Sn_IR(sock), 0xFF);  // 清除所有中断
            W5500_WriteByte(Sn_CR(sock), Sn_CR_SEND);
            W5500_DelayMs(5);

            // 等待发送完成
            {
                uint16_t timeout = 0;
                while (timeout < 300) {
                    uint8_t ir = W5500_ReadByte(Sn_IR(sock));
                    if (ir & 0x08) {  // SEND_OK
                        W5500_WriteByte(Sn_IR(sock), 0x08);
                        printf("[SEND_FORCE] OK! (ir=0x%02X)\n", ir);
                        return len;
                    }
                    if (ir & 0x10) {  // TIMEOUT
                        W5500_WriteByte(Sn_IR(sock), 0x10);
                        printf("[SEND_FORCE] TIMEOUT (ir=0x%02X)\n", ir);
                        return 0;
                    }
                    W5500_DelayMs(10);
                    timeout++;
                }
                printf("[SEND_FORCE] Poll timeout\n");
            }
            return 0;
        }

        // 写入失败，等待后重试
        printf("[SEND_FORCE] Write failed, retrying...\n");
        W5500_DelayMs(50);
    }

    printf("[SEND_FORCE] All attempts failed!\n");
    return 0;
}

void W5500_DelayMs(uint32_t ms)
{
    uint32_t i, j;
    for (i = 0; i < ms; i++) {
        for (j = 0; j < 7200; j++);
    }
}

