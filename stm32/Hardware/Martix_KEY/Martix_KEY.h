#ifndef __MARTIXKEY_H
#define __MARTIXKEY_H
#include "sys.h"

#define COL_1_Port	GPIOB
#define COL_1_Pin		GPIO_Pin_15

#define COL_2_Port	GPIOB
#define COL_2_Pin		GPIO_Pin_14

#define COL_3_Port	GPIOB
#define COL_3_Pin		GPIO_Pin_13

#define COL_4_Port	GPIOB
#define COL_4_Pin		GPIO_Pin_12

#define ROW_1_Port	GPIOA
#define ROW_1_Pin		GPIO_Pin_15

#define ROW_2_Port	GPIOB
#define ROW_2_Pin		GPIO_Pin_3

#define ROW_3_Port	GPIOB
#define ROW_3_Pin		GPIO_Pin_4

#define ROW_4_Port	GPIOB
#define ROW_4_Pin		GPIO_Pin_5

#define READ_GPIO(a,b)	(!GPIO_ReadInputDataBit(a,b))

void MartixKEY_Init(void);
uint8_t MartixKEY_Scan(void);
void Get_Key(void);

#define number_of_key	16
extern uint8_t key_released[number_of_key];
extern uint8_t key_value[number_of_key];
#endif
