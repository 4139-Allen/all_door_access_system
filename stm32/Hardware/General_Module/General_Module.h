#ifndef __GENERALMODULE_H
#define __GENERALMODULE_H
#include "sys.h"
typedef struct
{
	GPIO_TypeDef* GPIOx;
	uint32_t GPIO_Pin;
}GeneralModule;

void GeneralModule_Init(GeneralModule *Module, GPIOMode_TypeDef GPIO_Mode);
uint8_t GeneralModule_Read(GeneralModule *Module);
void GeneralModule_Write(GeneralModule *Module, uint8_t value);
#endif

