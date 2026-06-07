#ifndef __LCD_H
#define __LCD_H

#include "stm32f10x.h"      // STM32标准库头文件
#include "delay.h"          // 延时函数头文件


/* 函数声明 */
#define LCD_CS_GPIO_PIN		GPIO_Pin_8
#define LCD_CS_GPIO_PORT	GPIOB

#define LCD_CLK_GPIO_PIN	GPIO_Pin_9
#define LCD_CLK_GPIO_PORT	GPIOB

#define LCD_SID_GPIO_PIN	GPIO_Pin_10
#define LCD_SID_GPIO_PORT	GPIOB

/* 12864使用的引脚定义*/
#define LCD_CS(a)			if(a) GPIO_SetBits(LCD_CS_GPIO_PORT, LCD_CS_GPIO_PIN);\
							else  GPIO_ResetBits(LCD_CS_GPIO_PORT, LCD_CS_GPIO_PIN);
							
#define LCD_CLK(a)			if(a) GPIO_SetBits(LCD_CLK_GPIO_PORT, LCD_CLK_GPIO_PIN);\
							else  GPIO_ResetBits(LCD_CLK_GPIO_PORT, LCD_CLK_GPIO_PIN);

#define LCD_SID(a)			if(a) GPIO_SetBits(LCD_SID_GPIO_PORT, LCD_SID_GPIO_PIN);\
							else  GPIO_ResetBits(LCD_SID_GPIO_PORT, LCD_SID_GPIO_PIN);
											
void lcd_gpio_config(void);
void lcd_init(void);
void lcd_draw_str(unsigned char column, unsigned char row, const char *str);
void lcd_draw_num(unsigned char column, unsigned char row, uint16_t  num);
void lcd_write_data(unsigned char data);
void lcd_clear_line(uint8_t line);
void Update_Cursor(uint8_t pos);
void Update_SubCursor(uint8_t pos);

/* LCD12864绘图相关函数 */
void lcd_clear(void);
void lcd_draw_picture(const unsigned char *data);
void lcd_draw_dots(unsigned char x, unsigned char y, unsigned char color);
void lcd_draw_Hline(unsigned char x0, unsigned char y0, unsigned char x1, unsigned char color);
void lcd_draw_Vline(unsigned char x0, unsigned char y0, unsigned char y1, unsigned char color);
#endif /* __LCD_H */

