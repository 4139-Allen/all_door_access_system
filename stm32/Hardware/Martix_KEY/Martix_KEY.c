#include "Martix_KEY.h"
#include <stm32f10x_rcc.h>
#include <stm32f10x_gpio.h>
uint8_t key_released[number_of_key] = {0};
uint8_t key_value[number_of_key] = {0};

void MartixKEY_Init(void)
{
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOC, ENABLE);
}

static void MartixKEY_OUT(GPIO_TypeDef *GPIOx, uint32_t GPIO_Pin)
{
	GPIO_InitTypeDef GPIO_InitStructure;

	GPIO_InitStructure.GPIO_Pin = GPIO_Pin;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
	GPIO_Init(GPIOx, &GPIO_InitStructure);
	GPIO_ResetBits(GPIOx, GPIO_Pin);
}

static void MartixKEY_IN(GPIO_TypeDef *GPIOx, uint32_t GPIO_Pin)
{
	GPIO_InitTypeDef GPIO_InitStructure;

	GPIO_InitStructure.GPIO_Pin = GPIO_Pin;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
	GPIO_Init(GPIOx, &GPIO_InitStructure);
}

static void MartixKEY_COL_OUT(void)
{
	MartixKEY_OUT(COL_1_Port, COL_1_Pin);
	MartixKEY_OUT(COL_2_Port, COL_2_Pin);
	MartixKEY_OUT(COL_3_Port, COL_3_Pin);
	MartixKEY_OUT(COL_4_Port, COL_4_Pin);
	MartixKEY_IN(ROW_1_Port, ROW_1_Pin);
	MartixKEY_IN(ROW_2_Port, ROW_2_Pin);
	MartixKEY_IN(ROW_3_Port, ROW_3_Pin);
	MartixKEY_IN(ROW_4_Port, ROW_4_Pin);
}

static void MartixKEY_ROW_OUT(void)
{
	MartixKEY_IN(COL_1_Port, COL_1_Pin);
	MartixKEY_IN(COL_2_Port, COL_2_Pin);
	MartixKEY_IN(COL_3_Port, COL_3_Pin);
	MartixKEY_IN(COL_4_Port, COL_4_Pin);
	MartixKEY_OUT(ROW_1_Port, ROW_1_Pin);
	MartixKEY_OUT(ROW_2_Port, ROW_2_Pin);
	MartixKEY_OUT(ROW_3_Port, ROW_3_Pin);
	MartixKEY_OUT(ROW_4_Port, ROW_4_Pin);
}

uint8_t MartixKEY_Scan(void)
{
	uint8_t value = 0;

	MartixKEY_COL_OUT();
	if (READ_GPIO(ROW_1_Port, ROW_1_Pin))
	{
		MartixKEY_ROW_OUT();
		if (READ_GPIO(COL_1_Port, COL_1_Pin))
		{
			value = 1;
		}
		else if (READ_GPIO(COL_2_Port, COL_2_Pin))
		{
			value = 2;
		}
		else if (READ_GPIO(COL_3_Port, COL_3_Pin))
		{
			value = 3;
		}
		else if (READ_GPIO(COL_4_Port, COL_4_Pin))
		{
			value = 4;
		}
	}

	else if (READ_GPIO(ROW_2_Port, ROW_2_Pin))
	{
		MartixKEY_ROW_OUT();
		if (READ_GPIO(COL_1_Port, COL_1_Pin))
		{
			value = 5;
		}
		else if (READ_GPIO(COL_2_Port, COL_2_Pin))
		{
			value = 6;
		}
		else if (READ_GPIO(COL_3_Port, COL_3_Pin))
		{
			value = 7;
		}
		else if (READ_GPIO(COL_4_Port, COL_4_Pin))
		{
			value = 8;
		}
	}
	else if (READ_GPIO(ROW_3_Port, ROW_3_Pin))
	{
		MartixKEY_ROW_OUT();
		if (READ_GPIO(COL_1_Port, COL_1_Pin))
		{
			value = 9;
		}
		else if (READ_GPIO(COL_2_Port, COL_2_Pin))
		{
			value = 10;
		}
		else if (READ_GPIO(COL_3_Port, COL_3_Pin))
		{
			value = 11;
		}
		else if (READ_GPIO(COL_4_Port, COL_4_Pin))
		{
			value = 12;
		}
	}
	else if (READ_GPIO(ROW_4_Port, ROW_4_Pin))
	{
		MartixKEY_ROW_OUT();
		if (READ_GPIO(COL_1_Port, COL_1_Pin))
		{
			value = 13;
		}
		else if (READ_GPIO(COL_2_Port, COL_2_Pin))
		{
			value = 14;
		}
		else if (READ_GPIO(COL_3_Port, COL_3_Pin))
		{
			value = 15;
		}
		else if (READ_GPIO(COL_4_Port, COL_4_Pin))
		{
			value = 16;
		}
	}
	return value;
}

void Get_Key(void)  //按键防抖处理，防止按键长按触发
{
	switch (MartixKEY_Scan())
	{
	case 0:
		for (uint8_t i = 0; i < number_of_key; i++)
		{
			key_released[i] = 1;     //按键已经松开，可以再次按下
		}
		break;
	case 1: // 1
		if (key_released[1] == 1)
		{
			key_released[1] = 0;
			key_value[1] = 1;
		}
		break;
	case 2: // 2
		if (key_released[2] == 1)
		{
			key_released[2] = 0;
			key_value[2] = 1;
		}
		break;
	case 3: // 3
		if (key_released[3] == 1)
		{
			key_released[3] = 0;
			key_value[3] = 1;
		}
		break;
	case 4: //+
		if (key_released[12] == 1)
		{
			key_released[12] = 0;
			key_value[12] = 1;
		}
		break;
	case 5: // 4
		if (key_released[4] == 1)
		{
			key_released[4] = 0;
			key_value[4] = 1;
		}
		break;
	case 6: // 5
		if (key_released[5] == 1)
		{
			key_released[5] = 0;
			key_value[5] = 1;
		}
		break;
	case 7: // 6
		if (key_released[6] == 1)
		{
			key_released[6] = 0;
			key_value[6] = 1;
		}
		break;
	case 8: //-
		if (key_released[13] == 1)
		{
			key_released[13] = 0;
			key_value[13] = 1;
		}
		break;
	case 9: // 7
		if (key_released[7] == 1)
		{
			key_released[7] = 0;
			key_value[7] = 1;
		}
		break;
	case 10: // 8
		if (key_released[8] == 1)
		{
			key_released[8] = 0;
			key_value[8] = 1;
		}
		break;
	case 11: // 9
		if (key_released[9] == 1)
		{
			key_released[9] = 0;
			key_value[9] = 1;
		}
		break;
	case 12: // Back
		if (key_released[14] == 1)
		{
			key_released[14] = 0;
			key_value[14] = 1;
		}
		break;
	case 13: //*
		if (key_released[10] == 1)
		{
			key_released[10] = 0;
			key_value[10] = 1;
		}
		break;
	case 14: // 0
		if (key_released[0] == 1)
		{
			key_released[0] = 0;
			key_value[0] = 1;
		}
		break;
	case 15: // #
		if (key_released[11] == 1)
		{
			key_released[11] = 0;
			key_value[11] = 1;
		}
		break;
	case 16: // Enter
		if (key_released[15] == 1)
		{
			key_released[15] = 0;
			key_value[15] = 1;
		}
		break;
	default:
		break;
	}
}
