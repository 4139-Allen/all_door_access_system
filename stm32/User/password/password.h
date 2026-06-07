#ifndef __PASSWORD_H
#define __PASSWORD_H
#include "sys.h"

#define password_length 6

typedef struct
{
	uint8_t not_first_time;
	uint8_t admin_password[password_length];
	uint8_t unlock_password[password_length];
}PASSWORD_TypeDef;

typedef struct
{
	uint8_t card_exist;
	uint8_t card_id[4];
}CARD_TypeDef;

#define password_offset 0
#define card_offset sizeof(PASSWORD_TypeDef)
	
void Password_Read(uint8_t mode);
void ChangePassword(uint8_t user, uint8_t *new_password);
void AddCard(uint8_t id, uint8_t *card_id);
void DelCard(uint8_t id);

extern PASSWORD_TypeDef Password;
extern CARD_TypeDef Unlock_Card[3];
#endif

