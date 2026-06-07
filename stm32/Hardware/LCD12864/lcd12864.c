#include "stm32f10x.h" // STM32标准库头文件#include "delay.h"          // 延时函数头文件
#include "lcd12864.h"
#include <stm32f10x_gpio.h>
#include <stm32f10x_rcc.h>

/* LCD12864内部字库显示的DDRAM地址，每个地址占16*16个像素点 */
static unsigned char lcd_str_addr[4][8] = {
	{0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87},
	{0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97},
	{0x88, 0x89, 0x8A, 0x8B, 0x8C, 0x8D, 0x8E, 0x8F},
	{0x98, 0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F}};

/**
 * @brief  LCD12864使用到的引脚配置
 * @param  无
 * @retval 无
 */
void lcd_gpio_config(void)
{
	GPIO_InitTypeDef GPIO_InitStructure;

	/* 开启GPIOA时钟 */
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);

	/* PA7(CS), PA5(CLK), PA6(SID)引脚配置 */
	GPIO_InitStructure.GPIO_Pin = LCD_CS_GPIO_PIN | LCD_CLK_GPIO_PIN | LCD_SID_GPIO_PIN;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_Init(GPIOB, &GPIO_InitStructure);

	/* 控制引脚初始状态全部输出低电平 */
	LCD_CS(0);
	LCD_CLK(0);
	LCD_SID(0);
}

/**
 * @brief  LCD12864串行发送一个字节数据
 * @param  byte: 一个字节数据
 * @retval 无
 */
static void lcd_send_byte(unsigned char byte)
{
	unsigned char i;

	for (i = 0; i < 8; i++)
	{
		LCD_CLK(0);
		LCD_SID(byte & (0x80 >> i)); // 按位发送
		delay_us(5);
		LCD_CLK(1);
	}
}

/**
 * @brief  LCD12864写命令
 * @param  cmd: 要发送的命令
 * @retval 无
 */
static void lcd_write_cmd(unsigned char cmd)
{
	LCD_CS(1);
	delay_us(30);
	lcd_send_byte(0xf8);	   // 写命令
	lcd_send_byte(0xf0 & cmd); // 写高4位指令
	lcd_send_byte(cmd << 4);   // 写低4位指令
	LCD_CS(0);
}

/**
 * @brief  LCD12864写数据
 * @param  data: 要发送的数据
 * @retval 无
 */
void lcd_write_data(unsigned char data)
{
	LCD_CS(1);
	delay_us(30);
	lcd_send_byte(0xfa);		// 写数据
	lcd_send_byte(0xf0 & data); // 写高4位数据
	lcd_send_byte(data << 4);	// 写低4位数据
	LCD_CS(0);
}

/**
 * @brief  LCD12864初始化
 * @param  无
 * @retval 无
 */
void lcd_init(void)
{
	lcd_gpio_config();
	delay_ms(50);		 // 上电自检延时
	lcd_write_cmd(0x30); // 选择基本指令集，8bit数据流
	delay_ms(1);
	lcd_write_cmd(0x0c); // 开显示，关闭光标
	delay_ms(1);
	lcd_write_cmd(0x01); // 清除显示
	delay_ms(30);
}

/**
 * @brief  LCD12864显示字符串
 * @param  column: 行地址0~3，row: 列地址0~7
 * @retval 无
 */
void lcd_draw_str(unsigned char column, unsigned char row, const char *str)
{
	/* 设置显示的行/列地址 */
	lcd_write_cmd(lcd_str_addr[column][row]);

	/* 逐个字符写入 */
	while (*str)
	{
		lcd_write_data(*str++);
	}
}

// 辅助函数：数字转字符串
void num2str(uint16_t num, char *buf)
{
	int i = 0;
	if (num == 0)
	{
		buf[i++] = '0';
	}
	else
	{
		while (num > 0)
		{
			buf[i++] = '0' + (num % 10);
			num /= 10;
		}
	}
	buf[i] = '\0';

	// 反转字符串
	int len = i;
	for (int j = 0; j < len / 2; j++)
	{
		char temp = buf[j];
		buf[j] = buf[len - 1 - j];
		buf[len - 1 - j] = temp;
	}
}

// LCD数字显示函数
void lcd_draw_num(unsigned char column, unsigned char row, uint16_t num)
{
	char str_buf[6]; // 缓冲区大小=位数+1（如65535需要5+1=6字节）
	num2str(num, str_buf);
	lcd_draw_str(column, row, str_buf); // 调用现有的字符串显示函数
}

/* x轴按位显示的位码表 */
static const unsigned char set_pix_bit[8] = {0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01};

/* 显示缓冲区 */
static unsigned char disp_buff[8][64] = {0};

/**
 * @brief  设置LCD12864显示坐标
 * @param  x: x轴坐标0~127, y: y轴坐标0~63
 * @retval 无
 */
static void lcd_setXY(unsigned char x, unsigned char y)
{
	if (y >= 32)
	{
		/* 下半屏 */
		lcd_write_cmd(0x80 + (y - 32)); // y坐标
		lcd_write_cmd(0x88 + (x >> 4)); // x坐标
	}
	else
	{
		/* 上半屏 */
		lcd_write_cmd(0x80 + y);
		lcd_write_cmd(0x80 + (x >> 4));
	}
}

/**
 * @brief  清空屏幕
 * @param  无
 * @retval 无
 */
void lcd_clear(void)
{
	unsigned char x, y;

	lcd_write_cmd(0x34); // 切换到扩展指令集

	for (y = 0; y < 64; y++)
	{
		lcd_setXY(0, y); // 设置显示坐标
		for (x = 0; x < 8; x++)
		{
			/* 因为x轴一个地址对应16个像素点，可以连续发送两个字节数据 */
			lcd_write_data(0x00);
			lcd_write_data(0x00);
		}
	}

	lcd_write_cmd(0x36); // 打开绘图显示
	lcd_write_cmd(0x30); // 回到基本指令集
}

#define TEXT_LINE_HEIGHT 16 // 每行文本占16像素高度

/**
 * @brief  清空指定文本行（图形模式适配）
 * @param  line: 行号（0~3）
 */
void lcd_clear_line(uint8_t line)
{
	if (line >= 4)
		return; // 假设最大4行文本

	lcd_write_cmd(0x34); // 切换到扩展指令集（绘图模式）

	// 计算起始Y坐标
	uint8_t start_y = line * TEXT_LINE_HEIGHT;

	// 清除该行对应的所有像素行
	for (uint8_t y = start_y; y < start_y + TEXT_LINE_HEIGHT; y++)
	{
		lcd_setXY(0, y); // X从0开始
		for (uint8_t x = 0; x < 8; x++)
		{						  // 128像素宽度需要8个地址（每个地址16像素）
			lcd_write_data(0x00); // 低字节清零
			lcd_write_data(0x00); // 高字节清零
		}
	}

	lcd_write_cmd(0x36); // 打开绘图显示
	lcd_write_cmd(0x30); // 返回基本指令集
}

/**
 * @brief  显示图片，注意显示起点坐标固定是(0, 0)
 * @param  无
 * @retval 无
 */
void lcd_draw_picture(const unsigned char *data)
{
	unsigned char x, y;

	lcd_write_cmd(0x34); // 切换到扩展指令集

	for (y = 0; y < 64; y++)
	{
		lcd_setXY(0, y);
		for (x = 0; x < 8; x++)
		{
			lcd_write_data(*data++);
			lcd_write_data(*data++);
		}
	}

	lcd_write_cmd(0x36); // 打开绘图显示
	lcd_write_cmd(0x30); // 回到基本指令集
}

/**
  * @brief  在LCD显示范围内绘制任意点
			x坐标范围是：0~127，y坐标范围是：0~63
  * @param  x: x轴坐标, y: y轴坐标, color: 颜色值，1：点亮像素，0：不点亮
  * @retval 无
  */
void lcd_draw_dots(unsigned char x, unsigned char y, unsigned char color)
{
	lcd_write_cmd(0x34); // 切换到扩展指令集

	/* 超出显示范围，退出函数 */
	if ((x >= 128) || (y >= 64))
		return;

	/* 设置x, y坐标 */
	lcd_setXY(x, y);

	/* 填充显示缓冲区数据 */
	if (color == 1)
	{
		/* 点亮某点像素 */
		disp_buff[x >> 3][y] |= 0x00;
		disp_buff[(x >> 3) + 1][y] |= set_pix_bit[x & 0x07];
	}
	else
	{
		/* 熄灭某点像素 */
		disp_buff[x >> 3][y] |= 0x00;
		disp_buff[(x >> 3) + 1][y] &= ~set_pix_bit[x & 0x07];
	}

	/* 输出数据到LCD显示 */
	if ((x >> 3) % 2 != 0) // 判断x轴0~15个显示数据的奇偶性
	{
		/* 奇数 */
		lcd_write_data(disp_buff[x >> 3][y]);
		lcd_write_data(disp_buff[(x >> 3) + 1][y]);
	}
	else
	{
		/* 偶数 */
		lcd_write_data(disp_buff[(x >> 3) + 1][y]);
		lcd_write_data(disp_buff[x >> 3][y]);
	}

	lcd_write_cmd(0x36); // 打开绘图显示
	lcd_write_cmd(0x30); // 回到基本指令集
}

/**
 * @brief  绘制水平线
 * @param  x0: x轴起点, y0: y0轴起点, x1: x轴结束点, color: 颜色值，1点亮像素，0不点亮
 * @retval 无
 */
void lcd_draw_Hline(unsigned char x0, unsigned char y0, unsigned char x1, unsigned char color)
{
	/* 超出显示范围，退出函数 */
	if ((x0 >= 128) || (y0 >= 64) || (x1 >= 128))
		return;

	for (; x1 >= x0; x0++)
		lcd_draw_dots(x0, y0, color);
}

/**
 * @brief  绘制垂直线
 * @param  x0: x轴起点, y0: y轴起点, y1: y轴结束点, color: 颜色值，1点亮像素，0不点亮
 * @retval 无
 */
void lcd_draw_Vline(unsigned char x0, unsigned char y0, unsigned char y1, unsigned char color)
{
	/* 超出显示范围，退出函数 */
	if ((x0 >= 128) || (y0 >= 64) || (y1 >= 64))
		return;

	for (; y1 >= y0; y0++)
		lcd_draw_dots(x0, y0, color);
}

void Update_Cursor(uint8_t pos)
{
	lcd_clear_line(0);
	lcd_clear_line(1);
	lcd_clear_line(2);

	switch (pos)
	{
	case 0:
		lcd_draw_str(0, 1, "*");
		break;
	case 1:
		lcd_draw_str(1, 1, "*");
		break;
	case 2:
		lcd_draw_str(2, 1, "*");
		break;
	}
}

// 子菜单光标更新
void Update_SubCursor(uint8_t pos)
{
	lcd_clear_line(1);
	lcd_clear_line(2);
	switch (pos)
	{
	case 0:
		lcd_draw_str(1, 1, "*");
		break;
	case 1:
		lcd_draw_str(2, 1, "*");
		break;
	}
}
