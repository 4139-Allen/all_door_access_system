#include "stm32f10x.h"

#include "string.h"
#include "stdio.h"

#include "usart.h"
#include "timer.h"
#include "delay.h"

#include "rc522_config.h"
#include "rc522_function.h"
#include "Martix_KEY.h"
#include "General_Module.h"
#include "lcd12864.h"
#include "AT24CXX.h"
#include "AS608.h"

#include "password.h"
#include "menu.h"


uint8_t Read_UID(uint8_t *UID);

// 前向声明
uint32_t millis(void);

// 外部变量声明
extern uint8_t lcd_clear_flag;

// 设备锁定状态（密码错误次数过多时锁定）
volatile uint8_t device_locked = 0;
volatile uint32_t lock_timestamp = 0;
#define LOCK_DURATION_MS 300000  // 锁定5分钟（300秒）

// 系统时间计数（毫秒）
volatile uint32_t sys_tick_ms = 0;

GeneralModule Buzzer =
{
    .GPIOx = GPIOB,
    .GPIO_Pin = GPIO_Pin_1,
};

GeneralModule Relay =
{
    .GPIOx = GPIOB,
    .GPIO_Pin = GPIO_Pin_11,
};

uint8_t RC522_UID[4];
uint8_t RC522_UID_Save[4];

int main(void)
{
    NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_AFIO, ENABLE);
    GPIO_PinRemapConfig(GPIO_Remap_SWJ_JTAGDisable, ENABLE);
    delay_init();
    uart_init(9600);
    uart2_init(57600);
    PS_StaGPIO_Init();
    GeneralModule_Init(&Buzzer, GPIO_Mode_Out_PP);
    GeneralModule_Init(&Relay, GPIO_Mode_Out_PP);
    GeneralModule_Write(&Relay, 0); // 继电器高电平触发，初始化后拉??
    MartixKEY_Init();
    lcd_init();

    AT24CXX_Init();
		lcd_draw_str(0,0,"init EEPROM..");//检测24c02直到检测成功
		while(AT24CXX_Check())
		{
			lcd_draw_str(1,0,"init failed");
		}
		lcd_draw_str(0,0,"                                                                ");//清屏
		lcd_draw_str(0,0,"Initializing system");
		Password_Read(0);
		lcd_draw_str(0,0,"                                                                ");//清屏
	
    RC522_Init();
    PcdReset();
    M500PcdConfigISOType('A');  // 配置为 ISO14443A 模式（Mifare 卡）


    Timer2_Init(1999, 719);

    while (1)
    {
        // 检查锁定状态是否过期
        if (device_locked)
        {
            if (millis() - lock_timestamp >= LOCK_DURATION_MS)
            {
                device_locked = 0;
                lcd_draw_str(3, 0, "                ");  // 清除锁定提示
            }
        }

        menu();
        key_handle();

        if (rx_finish_flag)
        {
            rx_finish_flag = 0;

            // 远程开门命令
            if (rx_cnt == 10 && memcmp(rx_buf, "OPEN_DOOR\n", 10) == 0)
            {
                if (!device_locked)
                {
                    GeneralModule_Write(&Relay, 1); // 高电平触发
                    delay_ms(1500);
                    GeneralModule_Write(&Relay, 0); // 拉低，关

                    USART1_SendStr("OK\n");
                }
                else
                {
                    USART1_SendStr("LOCKED\n");
                }
            }
            // 锁定命令（后端发送）
            else if (rx_cnt == 5 && memcmp(rx_buf, "LOCK\n", 5) == 0)
            {
                device_locked = 1;
                lock_timestamp = millis();
                lcd_clear_flag = 1;
                lcd_draw_str(3, 0, "Device Locked!");
            }
            // 解除锁定命令（后端发送）
            else if (rx_cnt == 7 && memcmp(rx_buf, "UNLOCK\n", 7) == 0)
            {
                device_locked = 0;
                lcd_clear_flag = 1;
                lcd_draw_str(3, 0, "                ");
            }

            memset(rx_buf, 0, rx1_buf_size);
            rx_cnt = 0;
        }
    }
}

/**
 * @brief  检查设备是否被锁定
 * @return 1=锁定, 0=正常
 */
uint8_t is_device_locked(void)
{
    return device_locked;
}

/**
 * @brief  获取系统运行时间（毫秒）
 */
uint32_t millis(void)
{
    extern volatile uint32_t sys_tick_ms;
    return sys_tick_ms;
}

uint8_t Read_UID(uint8_t *UID)
{
    uint8_t sta = 1;
    uint8_t ucArray_ID[4];
    uint8_t ucStatusReturn = 0;

    ucStatusReturn = PcdRequest(PICC_REQALL, ucArray_ID);
    if (ucStatusReturn == MI_OK)
    {
        if (PcdAnticoll(UID) == MI_OK)
        {
            sta = 0;
        }
    }
    PcdHalt();

    return sta;
}

void TIM2_IRQHandler(void)
{
    if (TIM_GetITStatus(TIM2, TIM_IT_Update) == SET)
    {
        sys_tick_ms++;  // 系统时间计数（1ms中断）
        Get_Key();
        TIM_ClearITPendingBit(TIM2, TIM_IT_Update);
    }
}
