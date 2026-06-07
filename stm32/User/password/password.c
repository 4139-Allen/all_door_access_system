#include "password.h"
#include "AT24CXX.h"
#include "string.h"
#include "stdlib.h"

const uint8_t default_admin_pwd[password_length] = {'8', '8', '8', '8', '8', '8'};	// 默认管理员密码888888
const uint8_t default_unlock_pwd[password_length] = {'1', '2', '3', '4', '5', '6'}; // 默认开锁密码123456

PASSWORD_TypeDef Password = {0, {0, 0, 0, 0, 0, 0}, {0, 0, 0, 0, 0, 0}};

CARD_TypeDef Unlock_Card[3] = {
	{0, {0, 0, 0, 0}},
	{0, {0, 0, 0, 0}},
	{0, {0, 0, 0, 0}},
};

// 读取密码和卡片
// mode 0检查是否初始化，并读取密码	1强制初始化，重置密码
void Password_Read(uint8_t mode)
{
	if (mode == 0) // 读取密码，检查是否初始化过
	{
		AT24CXX_Read(password_offset, (uint8_t *)&Password, sizeof(Password));
		if (Password.not_first_time != 0x55) // 初次使用密码锁,从FLASH读取到的第一个数据不是0x55,初始化
		{
			for (uint8_t i = 0; i <= 254; i++) // 0~254地址写0x00，255地址被用作检测是否存在at24c02所以不清空
			{
				AT24CXX_WriteOneByte(i, 0x00);
			}
			Password.not_first_time = 0x55;
			memcpy(&Password.admin_password, &default_admin_pwd, password_length);
			memcpy(&Password.unlock_password, &default_unlock_pwd, password_length);
			AT24CXX_Write(password_offset, (uint8_t *)&Password, sizeof(Password));
		}
	}
	else if (mode == 1) // 强制初始化，重置密码
	{
		for (uint8_t i = 0; i <= 254; i++) // 0~254地址写0x00，255地址被用作检测是否存在at24c02所以不清空
		{
			AT24CXX_WriteOneByte(i, 0x00);
		}
		Password.not_first_time = 0x55;
		memcpy(&Password.admin_password, &default_admin_pwd, password_length);
		memcpy(&Password.unlock_password, &default_unlock_pwd, password_length);
		AT24CXX_Write(password_offset, (uint8_t *)&Password, sizeof(Password));
	}

	// AT24CXX_Read(card_offset, (uint8_t *)&Unlock_Card, sizeof(Unlock_Card) * 3);
	AT24CXX_Read(card_offset, (uint8_t *)Unlock_Card, sizeof(Unlock_Card));
}

// user					0为用户	1为管理员
// new_password 	新密码，6位数
void ChangePassword(uint8_t user, uint8_t *new_password)
{
	if (user == 0)
	{
		memcpy(&Password.unlock_password, new_password, password_length);
	}
	if (user == 1)
	{
		memcpy(&Password.admin_password, new_password, password_length);
	}
	AT24CXX_Write(password_offset, (uint8_t *)&Password, sizeof(Password));
}

// 添加卡
// id			卡片号,支持0~2
// card_id	卡片id数据
/*
void AddCard(uint8_t id, uint8_t *card_id)
{
	Unlock_Card[id].card_exist = 1;
	memcpy(&Unlock_Card[id].card_id, card_id, 4);
	AT24CXX_Write(card_offset + id * sizeof(Unlock_Card), (uint8_t *)&Unlock_Card[id], sizeof(Unlock_Card));
}
*/
void AddCard(uint8_t id, uint8_t *card_id)
{
	Unlock_Card[id].card_exist = 1;

	memcpy(Unlock_Card[id].card_id, card_id, 4);
	AT24CXX_Write(card_offset + id * sizeof(CARD_TypeDef),(uint8_t *)&Unlock_Card[id],sizeof(CARD_TypeDef));
}

// 删除卡
// id			卡片号
/*
void DelCard(uint8_t id)
{
	uint8_t default_id[4] = {0, 0, 0, 0};
	Unlock_Card[id].card_exist = 0;
	memcpy(&Unlock_Card[id], default_id, 4);
	AT24CXX_Write(card_offset + id * sizeof(Unlock_Card), (uint8_t *)&Unlock_Card[id], sizeof(Unlock_Card));//Unlock_Card 是数组
}
*/
void DelCard(uint8_t id)
{
	uint8_t default_id[4] = {0, 0, 0, 0};

	Unlock_Card[id].card_exist = 0;
	memcpy(Unlock_Card[id].card_id, default_id, 4);

	AT24CXX_Write(card_offset + id * sizeof(CARD_TypeDef),(uint8_t *)&Unlock_Card[id],sizeof(CARD_TypeDef));
}