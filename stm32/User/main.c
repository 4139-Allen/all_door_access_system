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
		lcd_draw_str(0,0,"初始化EEPROM中");//检测24c02直到检测成功
		while(AT24CXX_Check())
		{
			lcd_draw_str(1,0,"初始化失败");
		}
		lcd_draw_str(0,0,"                                                                ");//清屏
		lcd_draw_str(0,0,"正在初始化系统");
		Password_Read(0);
		lcd_draw_str(0,0,"                                                                ");//清屏
	
    RC522_Init();
    PcdReset();
    PcdAntennaOff();
    delay_ms(100);
    PcdAntennaOn();

    Timer2_Init(1999, 719);

    while (1)
    {
        menu();
        key_handle();

        if (rx_finish_flag)
        {
            rx_finish_flag = 0;

            if (rx_cnt == 10 && memcmp(rx_buf, "OPEN_DOOR\n", 10) == 0)
            {
                GeneralModule_Write(&Relay, 1); // 高电平触发
                delay_ms(1500);
                GeneralModule_Write(&Relay, 0); // 拉低，关

                USART_SendData(USART1, 'O');
                while (USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET);
                USART_SendData(USART1, 'K');
                while (USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET);
                USART_SendData(USART1, '\n');
                while (USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET);
            }

            memset(rx_buf, 0, rx1_buf_size);
            rx_cnt = 0;
        }
    }
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
        Get_Key();
        TIM_ClearITPendingBit(TIM2, TIM_IT_Update);
    }
}
