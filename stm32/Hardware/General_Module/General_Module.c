#include "General_Module.h"
#include <stm32f10x_gpio.h>
#include <stm32f10x_rcc.h>

void GeneralModule_Init(GeneralModule *Module, GPIOMode_TypeDef GPIO_Mode)
{
	GPIO_InitTypeDef GPIO_InitStructure;
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_GPIOB | RCC_APB2Periph_GPIOC | RCC_APB2Periph_GPIOD, ENABLE);

	GPIO_InitStructure.GPIO_Pin = Module->GPIO_Pin;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode;
	GPIO_Init(Module->GPIOx, &GPIO_InitStructure);

	GPIO_SetBits(Module->GPIOx, Module->GPIO_Pin);
}

uint8_t GeneralModule_Read(GeneralModule *Module)
{
	return GPIO_ReadInputDataBit(Module->GPIOx, Module->GPIO_Pin);
}

void GeneralModule_Write(GeneralModule *Module, uint8_t value)
{
	GPIO_WriteBit(Module->GPIOx, Module->GPIO_Pin, (BitAction)value);
}
