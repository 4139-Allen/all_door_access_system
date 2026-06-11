#include "menu.h"
#include "lcd12864.h"
#include "Martix_KEY.h"
#include "password.h"
#include "string.h"
#include "delay.h"
#include "General_Module.h"
#include "usart.h"
#include "string.h"
#include "stdlib.h"
#include "stdio.h"
#include "AS608.h"

// 中文字库编码（GB2312）
// LCD12864 内置中文字库，每行8个中文字符位置（16像素/字符）

extern GeneralModule Buzzer;

// 声明外部锁定状态检查函数
extern uint8_t is_device_locked(void);

extern GeneralModule Relay;

extern uint8_t Read_UID(uint8_t *UID);

uint8_t disp = 0;
uint8_t sub_disp = 0;

uint8_t select = 0;
uint8_t lcd_clear_flag = 1;

uint8_t pwd_num = 0;
uint8_t pwd[6] = {0};

uint8_t Card_ID[4] = {0x00};

uint8_t card_manage_status = 0;
int8_t selected_card_id = -1;

uint8_t fp_manage_status = 0;
int8_t selected_fp_id = -1;
uint8_t ensure = 0;

uint8_t change_pwd_status = 0;
uint8_t new_pwd[6] = {0};
uint8_t confirm_new_pwd[6] = {0};

void menu(void)
{
    if (disp == 0 && sub_disp == 0 && pwd_num == 0)
    {
        if (rx_finish_flag)
        {
            rx_finish_flag = 0;
            if (memcmp(Password.unlock_password, rx_buf, password_length) == 0)
            {
                lcd_clear_flag = 1;
                lcd_draw_str(2, 0, "蓝牙开锁成功");
                GeneralModule_Write(&Relay, 1);
                delay_ms(1500);
                GeneralModule_Write(&Relay, 0);
            }
            else 
            {
                lcd_clear_flag = 1;
                lcd_draw_str(2, 0, "蓝牙开锁失败");
                GeneralModule_Write(&Buzzer, 0);
                delay_ms(1500);
                GeneralModule_Write(&Buzzer, 1);
            }
            memset(rx_buf, 0, password_length);
        }
    }

    // 刷卡检测（锁定状态下仍可刷卡，但不开门）
    if (Read_UID(Card_ID) == 0)
    {
        // 检查设备是否被锁定
        if (is_device_locked())
        {
            lcd_clear_flag = 1;
            lcd_draw_str(2, 0, "设备已锁定！");
            GeneralModule_Write(&Buzzer, 0);
            delay_ms(500);
            GeneralModule_Write(&Buzzer, 1);
        }
        else
        {
            for (uint8_t i = 0; i <= 2; i++)
            {
                if (Unlock_Card[i].card_exist && memcmp(Unlock_Card[i].card_id, Card_ID, 4) == 0)
                {
                    uint8_t buf[2];
                    lcd_clear_flag = 1;
                    lcd_draw_str(1, 0, "刷卡成功");
                    lcd_draw_str(2, 0, "ID:");
                    buf[0] = '0' + i;
                    buf[1] = '\0';
                    lcd_draw_str(2, 2, (const char *)buf);
                    GeneralModule_Write(&Relay, 1);
                    USART1_SendStr("CARD_OK\n");

                    delay_ms(1500);
                    GeneralModule_Write(&Relay, 0);
                    break;
                }
                if (i == 2)
                {
                    lcd_clear_flag = 1;
                    lcd_draw_str(2, 0, "刷卡失败");
                    GeneralModule_Write(&Buzzer, 0);

                    //上报刷卡错误
                    USART1_SendStr("CARD_ERR\n");

                    delay_ms(1500);
                    GeneralModule_Write(&Buzzer, 1);
                }
            }
        }
        memset(Card_ID, 0, sizeof(Card_ID));
    }

    // 指纹检测（锁定状态下仍可检测，但不开门）
    if (PAin(0) == 1)
    {
        // 检查设备是否被锁定
        if (is_device_locked())
        {
            lcd_clear_flag = 1;
            lcd_draw_str(2, 0, "设备已锁定！");
            GeneralModule_Write(&Buzzer, 0);
            delay_ms(500);
            GeneralModule_Write(&Buzzer, 1);
        }
        else
        {
            SearchResult seach;

            ensure = PS_GetImage();

            if (ensure == 0x00)
            {
                ensure = PS_GenChar(CharBuffer1);

                if (ensure == 0x00)
                {
                    ensure = PS_HighSpeedSearch(CharBuffer1, 0, 20, &seach);

                    if (ensure == 0x00 && seach.mathscore > 50)
                    {
                        uint8_t buf[2];
                        buf[0] = '0' + seach.pageID;
                        buf[1] = '\0';
                        lcd_clear_flag = 1;
                        lcd_draw_str(1, 0, "指纹开锁成功");
                        lcd_draw_str(2, 0, "ID:");
                        buf[0] = '0' + seach.pageID;
                        lcd_draw_str(2, 2, (const char *)buf);
                        lcd_clear_flag = 1;
                        GeneralModule_Write(&Relay, 1);
                        USART1_SendStr("FP_OK\n");

                        delay_ms(1500);
                        GeneralModule_Write(&Relay, 0);
                    }
                    else
                    {
                        lcd_clear_flag = 1;
                        lcd_draw_str(1, 0, "指纹不匹配");

                        GeneralModule_Write(&Buzzer, 0);

                        //上报指纹错误
                        USART1_SendStr("FP_ERR\n");

                        delay_ms(1000);
                        GeneralModule_Write(&Buzzer, 1);
                    }
                }
            }
        }
    }

    if (lcd_clear_flag)
    {
        lcd_clear_flag = 0;
        lcd_draw_str(0, 0, "                                                                ");
    }

    if (disp == 0)
    {
        if (sub_disp == 0)
        {
            lcd_draw_str(0, 0, "智能门禁管理系统");

            // 检查设备是否被锁定
            if (is_device_locked())
            {
                lcd_draw_str(3, 5, "已锁定");
                pwd_num = 0;
                memset(pwd, 0, password_length);
                return;  // 锁定状态下不处理密码输入
            }
            else
            {
                lcd_draw_str(3, 5, "输入");
            }

            if (pwd_num > 0)
            {
                for (uint8_t i = 1; i <= pwd_num; i++)
                {
                    lcd_draw_str(1, i, "*");
                }
                if (pwd_num == 6)
                {
                    if (memcmp(pwd, Password.unlock_password, password_length) == 0)
                    {
                        memset(pwd, 0, password_length);
                        lcd_clear_flag = 1;
                        lcd_draw_str(2, 0, "开锁成功");
                        GeneralModule_Write(&Relay, 1);
                        USART1_SendChar_NoEcho('P'); USART1_SendChar_NoEcho('W'); USART1_SendChar_NoEcho('D');
                        USART1_SendChar_NoEcho('_'); USART1_SendChar_NoEcho('O'); USART1_SendChar_NoEcho('K');
                        USART1_SendChar_NoEcho('\n');
                        delay_ms(1500);
                        key_handle();
                        pwd_num = 0;
                        GeneralModule_Write(&Relay, 0);
                    }
                    else
                    {
                        memset(pwd, 0, password_length);
                        lcd_clear_flag = 1;
                        lcd_draw_str(2, 0, "密码错误");
                        GeneralModule_Write(&Buzzer, 0);

                        //上报密码错误
                        USART1_SendStr("PWD_ERR\n");

                        delay_ms(1500);
                        key_handle();
                        pwd_num = 0;
                        GeneralModule_Write(&Buzzer, 1);
                    }
                }
            }
        }
        if (sub_disp == 1)
        {
            lcd_draw_str(0, 0, "请输入管理员密码");
            lcd_draw_str(3, 0, "返回");
            if (pwd_num > 0)
            {
                for (uint8_t i = 1; i <= pwd_num; i++)
                {
                    lcd_draw_str(1, i, "*");
                }
                if (pwd_num == 6)
                {
                    if (memcmp(pwd, Password.admin_password, password_length) == 0)
                    {
                        pwd_num = 0;
                        lcd_clear_flag = 1;
                        sub_disp = 0;
                        disp = 1;
                        memset(pwd, 0, password_length);
                    }
                    else
                    {

                        lcd_clear_flag = 1;
                        memset(pwd, 0, password_length);
                        lcd_draw_str(2, 0, "密码错误");
                        GeneralModule_Write(&Buzzer, 0);
                        delay_ms(1500);
                        key_handle();
                        pwd_num = 0;
                        GeneralModule_Write(&Buzzer, 1);
                    }
                }
            }
        }
    }
    if (disp == 1)
    {
        lcd_draw_str(select, 0, "*");
        lcd_draw_str(0, 2, "指纹管理");
        lcd_draw_str(1, 2, "密码管理");
        lcd_draw_str(2, 2, "卡片管理");
        lcd_draw_str(3, 0, "Back");
        lcd_draw_str(3, 5, "Enter");
    }
    if (disp == 2)
    {
        if (sub_disp == 0)
        {
            lcd_draw_str(select, 0, "*");
            lcd_draw_str(0, 1, "添加指纹");
            lcd_draw_str(1, 1, "删除指纹");
            lcd_draw_str(3, 0, "返回");
            lcd_draw_str(3, 5, "确认");
        }
        if (sub_disp == 1)
        {
            if (fp_manage_status == 0)
            {
                lcd_draw_str(0, 0, "请输入指纹ID");
                lcd_draw_str(1, 0, "范围0~4");
                lcd_draw_str(3, 0, "返回");
                if (selected_fp_id != -1)
                {
                    fp_manage_status = 1;
                    lcd_clear_flag = 1;
                }
            }
            if (fp_manage_status == 1)
            {
                lcd_draw_str(0, 0, "请按一次指纹");
                lcd_draw_str(3, 0, "返回");
                ensure = PS_GetImage();
                if (ensure == 0x00)
                {
                    ensure = PS_GenChar(CharBuffer1);
                    if (ensure == 0x00)
                    {
                        fp_manage_status = 2;
                        lcd_clear_flag = 1;
                    }
                }
            }
            if (fp_manage_status == 2)
            {
                lcd_draw_str(0, 0, "请再按一次指纹");
                lcd_draw_str(3, 0, "返回");
                ensure = PS_GetImage();
                if (ensure == 0x00)
                {
                    ensure = PS_GenChar(CharBuffer2);
                    if (ensure == 0x00)
                    {
                        fp_manage_status = 3;
                        lcd_clear_flag = 1;
                    }
                }
            }
            if (fp_manage_status == 3)
            {
                ensure = PS_Match();
                if (ensure == 0x00)
                {
                    ensure = PS_RegModel();
                    if (ensure == 0x00)
                    {
                        ensure = PS_StoreChar(CharBuffer2, selected_fp_id);
                        if (ensure == 0x00)
                        {
                            lcd_clear_flag = 1;
                            lcd_draw_str(1, 0, "录入成功");
                            fp_manage_status = 0;
                            disp = 0;
                            sub_disp = 0;
                            lcd_clear_flag = 1;
                            selected_fp_id = -1;
                            delay_ms(1500);
                        }
                        else
                        {
                            fp_manage_status = 0;
                            lcd_clear_flag = 1;
                            selected_fp_id = -1;
                            lcd_draw_str(0, 0, "指纹存储失败");
                            delay_ms(1500);
                        }
                    }
                    else
                    {
                        fp_manage_status = 0;
                        lcd_clear_flag = 1;
                        selected_fp_id = -1;
                        lcd_draw_str(0, 0, "指纹生成失败");
                        delay_ms(1500);
                    }
                }
                else
                {
                    fp_manage_status = 0;
                    lcd_clear_flag = 1;
                    selected_fp_id = -1;
                    lcd_draw_str(0, 0, "两次指纹不匹配");
                    delay_ms(1500);
                }
            }
        }
        if (sub_disp == 2)
        {
            lcd_draw_str(0, 0, "请输入删除ID");
            lcd_draw_str(1, 0, "范围0~4");
            lcd_draw_str(3, 0, "返回");
            if (selected_fp_id != -1)
            {
                ensure = PS_DeletChar(selected_fp_id, 1);
                if (ensure == 0x00)
                {
                    lcd_draw_str(2, 0, "删除成功");
                    selected_fp_id = -1;
                    sub_disp = 0;
                    disp = 0;
                    lcd_clear_flag = 1;
                    delay_ms(1500);
                }
                else
                {
                    lcd_draw_str(2, 0, "删除失败");
                    selected_fp_id = -1;
                    sub_disp = 0;
                    disp = 0;
                    lcd_clear_flag = 1;
                    delay_ms(1500);
                }
            }
        }
    }
    if (disp == 3)
    {
        if (sub_disp == 0)
        {
            lcd_draw_str(select, 0, "*");
            lcd_draw_str(0, 1, "修改开锁密码");
            lcd_draw_str(1, 1, "修改管理员密码");
            lcd_draw_str(3, 0, "返回");
            lcd_draw_str(3, 5, "确认");
        }
        if (sub_disp == 1)
        {
            if (change_pwd_status == 0)
            {
                lcd_draw_str(0, 0, "请输入新密码");
                lcd_draw_str(3, 0, "返回");
                if (pwd_num > 0)
                {
                    for (uint8_t i = 1; i <= pwd_num; i++)
                    {
                        lcd_draw_str(1, i, "*");
                    }
                    if (pwd_num == 6)
                    {
                        pwd_num = 0;
                        lcd_clear_flag = 1;
                        change_pwd_status = 1;
                    }
                }
            }
            if (change_pwd_status == 1)
            {
                lcd_draw_str(0, 0, "确认新密码");
                lcd_draw_str(3, 0, "返回");
                if (pwd_num > 0)
                {
                    for (uint8_t i = 1; i <= pwd_num; i++)
                    {
                        lcd_draw_str(1, i, "*");
                    }
                    if (pwd_num == 6)
                    {
                        pwd_num = 0;
                        lcd_clear_flag = 1;
                        change_pwd_status = 0;
                        disp = 0;
                        sub_disp = 0;
                        if (memcmp(new_pwd, confirm_new_pwd, password_length) == 0)
                        {
                            ChangePassword(0, confirm_new_pwd);
                            lcd_draw_str(2, 0, "修改成功");
                            delay_ms(1500);
                        }
                        else
                        {
                            lcd_draw_str(2, 0, "密码不一致");
                            delay_ms(1500);
                        }
                        memset(new_pwd, 0, password_length);
                        memset(confirm_new_pwd, 0, password_length);
                    }
                }
            }
        }
        if (sub_disp == 2)
        {
            if (change_pwd_status == 0)
            {
                lcd_draw_str(0, 0, "请输入新密码");
                lcd_draw_str(3, 0, "返回");
                if (pwd_num > 0)
                {
                    for (uint8_t i = 1; i <= pwd_num; i++)
                    {
                        lcd_draw_str(1, i, "*");
                    }
                    if (pwd_num == 6)
                    {
                        pwd_num = 0;
                        lcd_clear_flag = 1;
                        change_pwd_status = 1;
                    }
                }
            }
            if (change_pwd_status == 1)
            {
                lcd_draw_str(0, 0, "确认新密码");
                lcd_draw_str(3, 0, "返回");
                if (pwd_num > 0)
                {
                    for (uint8_t i = 1; i <= pwd_num; i++)
                    {
                        lcd_draw_str(1, i, "*");
                    }
                    if (pwd_num == 6)
                    {
                        pwd_num = 0;
                        lcd_clear_flag = 1;
                        change_pwd_status = 0;
                        disp = 0;
                        sub_disp = 0;
                        if (memcmp(new_pwd, confirm_new_pwd, password_length) == 0)
                        {
                            ChangePassword(1, confirm_new_pwd);
                            lcd_draw_str(2, 0, "修改成功");
                            delay_ms(1500);
                        }
                        else
                        {
                            lcd_draw_str(2, 0, "密码不一致");
                            delay_ms(1500);
                        }
                        memset(new_pwd, 0, password_length);
                        memset(confirm_new_pwd, 0, password_length);
                    }
                }
            }
        }
    }
    if (disp == 4)
    {

        if (sub_disp == 0)
        {
            lcd_draw_str(select, 0, "*");
            lcd_draw_str(0, 1, "添加卡片");
            lcd_draw_str(1, 1, "删除卡片");
            lcd_draw_str(3, 0, "返回");
            lcd_draw_str(3, 5, "确认");
        }
        if (sub_disp == 1)
        {
            if (card_manage_status == 0)
            {
                lcd_draw_str(0, 0, "请输入卡片ID");
                lcd_draw_str(1, 0, "范围0~2");
                lcd_draw_str(3, 0, "返回");
            }
            if (card_manage_status == 1)
            {
                lcd_draw_str(0, 1, "请刷卡");
                lcd_draw_str(3, 0, "返回");
                if (Read_UID(Card_ID) == 0)
                {
                    AddCard(selected_card_id, Card_ID);
                    card_manage_status = 0;
                    selected_card_id = -1;
                    memset(Card_ID, 0, sizeof(Card_ID));
                    lcd_draw_str(2, 1, "添加成功");
                    delay_ms(1500);
                    lcd_clear_flag = 1;
                    sub_disp = 0;
                    disp = 0;
                }
            }
        }
        if (sub_disp == 2)
        {
            lcd_draw_str(0, 0, "请输入删除ID");
            lcd_draw_str(1, 0, "范围0~2");
            lcd_draw_str(3, 0, "返回");
            if (selected_card_id != -1)
            {
                DelCard(selected_card_id);
                selected_card_id = -1;
                lcd_draw_str(2, 1, "删除成功");
                delay_ms(1500);
                lcd_clear_flag = 1;
                sub_disp = 0;
                disp = 0;
            }
        }
    }
}

void key_handle(void)
{
    if (disp == 0)
    {
        if (sub_disp == 0)
        {
            if (pwd_num < 6)
            {
                for (uint8_t i = 0; i <= 9; i++)
                {
                    if (key_value[i] == 1)
                    {
                        key_value[i] = 0;
                        lcd_clear_flag = 1;
                        pwd_num++;
                        pwd[pwd_num - 1] = '0' + i;
                    }
                }
            }
            else
            {
                for (uint8_t i = 0; i <= 9; i++)
                {
                    if (key_value[i] == 1)
                    {
                        key_value[i] = 0;
                        pwd_num = 6;
                    }
                }
            }
            if (key_value[14] == 1)
            {
                key_value[14] = 0;
                lcd_clear_flag = 1;
                pwd_num = 0;
                memset(pwd, 0, password_length);
            }
            if (key_value[15] == 1)
            {
                key_value[15] = 0;
                lcd_clear_flag = 1;
                sub_disp = 1;
                pwd_num = 0;
                memset(pwd, 0, password_length);
            }
        }
        if (sub_disp == 1)
        {
            if (pwd_num < 6)
            {
                for (uint8_t i = 0; i <= 9; i++)
                {
                    if (key_value[i] == 1)
                    {
                        key_value[i] = 0;
                        lcd_clear_flag = 1;
                        pwd_num++;
                        pwd[pwd_num - 1] = '0' + i;
                    }
                }
            }
            else
            {
                for (uint8_t i = 0; i <= 9; i++)
                {
                    if (key_value[i] == 1)
                    {
                        key_value[i] = 0;
                    }
                }
            }
            if (key_value[14] == 1)
            {
                key_value[14] = 0;
                lcd_clear_flag = 1;
                if (pwd_num > 0)
                {
                    pwd_num = 0;
                    memset(pwd, 0, password_length);
                }
                else
                {
                    sub_disp = 0;
                }
            }
        }
    }
    if (disp == 1)
    {
        if (key_value[13] == 1)
        {
            key_value[13] = 0;
            lcd_clear_flag = 1;
            if (select < 2)
            {
                select++;
            }
        }
        if (key_value[12] == 1)
        {
            key_value[12] = 0;
            lcd_clear_flag = 1;
            if (select > 0)
            {
                select--;
            }
        }
        if (key_value[14] == 1)
        {
            key_value[14] = 0;
            lcd_clear_flag = 1;
            disp = 0;
            select = 0;
        }
        if (key_value[15] == 1)
        {
            key_value[15] = 0;
            lcd_clear_flag = 1;
            disp = select + 2;
            select = 0;
        }
    }
    if (disp == 2)
    {
        if (sub_disp == 0)
        {
            if (key_value[13] == 1)
            {
                key_value[13] = 0;
                lcd_clear_flag = 1;
                if (select < 1)
                {
                    select++;
                }
            }
            if (key_value[12] == 1)
            {
                key_value[12] = 0;
                lcd_clear_flag = 1;
                if (select > 0)
                {
                    select--;
                }
            }
            if (key_value[14] == 1)
            {
                key_value[14] = 0;
                lcd_clear_flag = 1;
                disp = 1;
                select = 0;
            }
            if (key_value[15] == 1)
            {
                key_value[15] = 0;
                lcd_clear_flag = 1;
                sub_disp = select + 1;
                select = 0;
            }
        }
        if (sub_disp == 1)
        {
            if (fp_manage_status == 0)
            {
                for (uint8_t i = 0; i <= 4; i++)
                {
                    if (key_value[i] == 1)
                    {
                        key_value[i] = 0;
                        lcd_clear_flag = 1;
                        selected_fp_id = i;
                    }
                }
            }
            if (key_value[14] == 1)
            {
                key_value[14] = 0;
                lcd_clear_flag = 1;
                disp = 2;
                sub_disp = 0;
                select = 0;
                fp_manage_status = 0;
                selected_fp_id = -1;
            }
        }
        if (sub_disp == 2)
        {
            if (selected_fp_id == -1)
            {
                for (uint8_t i = 0; i <= 4; i++)
                {
                    if (key_value[i] == 1)
                    {
                        key_value[i] = 0;
                        lcd_clear_flag = 1;
                        selected_fp_id = i;
                    }
                }
            }
            if (key_value[14] == 1)
            {
                key_value[14] = 0;
                lcd_clear_flag = 1;
                disp = 2;
                sub_disp = 0;
                select = 0;
                selected_fp_id = -1;
            }
        }
    }
    if (disp == 3)
    {
        if (sub_disp == 0)
        {
            if (key_value[13] == 1)
            {
                key_value[13] = 0;
                lcd_clear_flag = 1;
                if (select < 1)
                {
                    select++;
                }
            }
            if (key_value[12] == 1)
            {
                key_value[12] = 0;
                lcd_clear_flag = 1;
                if (select > 0)
                {
                    select--;
                }
            }
            if (key_value[14] == 1)
            {
                key_value[14] = 0;
                lcd_clear_flag = 1;
                disp = 1;
                select = 0;
                pwd_num = 0;
                change_pwd_status = 0;
                memset(new_pwd, 0, password_length);
                memset(confirm_new_pwd, 0, password_length);
            }
            if (key_value[15] == 1)
            {
                key_value[15] = 0;
                lcd_clear_flag = 1;
                sub_disp = select + 1;
                select = 0;
                pwd_num = 0;
                change_pwd_status = 0;
                memset(new_pwd, 0, password_length);
                memset(confirm_new_pwd, 0, password_length);
            }
        }
        if (sub_disp == 1 || sub_disp == 2)
        {
            if (change_pwd_status == 0)
            {
                if (pwd_num < 6)
                {
                    for (uint8_t i = 0; i <= 9; i++)
                    {
                        if (key_value[i] == 1)
                        {
                            key_value[i] = 0;
                            lcd_clear_flag = 1;
                            pwd_num++;
                            new_pwd[pwd_num - 1] = '0' + i;
                        }
                    }
                }
                else
                {
                    for (uint8_t i = 0; i <= 9; i++)
                    {
                        if (key_value[i] == 1)
                        {
                            key_value[i] = 0;
                        }
                    }
                }
            }

            if (change_pwd_status == 1)
            {
                if (pwd_num < 6)
                {
                    for (uint8_t i = 0; i <= 9; i++)
                    {
                        if (key_value[i] == 1)
                        {
                            key_value[i] = 0;
                            lcd_clear_flag = 1;
                            pwd_num++;
                            confirm_new_pwd[pwd_num - 1] = '0' + i;
                        }
                    }
                }
                else
                {
                    for (uint8_t i = 0; i <= 9; i++)
                    {
                        if (key_value[i] == 1)
                        {
                            key_value[i] = 0;
                        }
                    }
                }
            }

            if (key_value[14] == 1)
            {
                key_value[14] = 0;
                lcd_clear_flag = 1;
                disp = 3;
                sub_disp = 0;
                select = 0;
                pwd_num = 0;
                change_pwd_status = 0;
                memset(new_pwd, 0, password_length);
                memset(confirm_new_pwd, 0, password_length);
            }
        }
    }
    if (disp == 4)
    {
        if (sub_disp == 0)
        {
            if (key_value[13] == 1)
            {
                key_value[13] = 0;
                lcd_clear_flag = 1;
                if (select < 1)
                {
                    select++;
                }
            }
            if (key_value[12] == 1)
            {
                key_value[12] = 0;
                lcd_clear_flag = 1;
                if (select > 0)
                {
                    select--;
                }
            }
            if (key_value[14] == 1)
            {
                key_value[14] = 0;
                lcd_clear_flag = 1;
                disp = 1;
                select = 0;
            }
            if (key_value[15] == 1)
            {
                key_value[15] = 0;
                lcd_clear_flag = 1;
                sub_disp = select + 1;
                select = 0;
            }
        }
        if (sub_disp == 1)
        {
            if (key_value[0] == 1)
            {
                key_value[0] = 0;
                lcd_clear_flag = 1;
                card_manage_status = 1;
                selected_card_id = 0;
            }
            if (key_value[1] == 1)
            {
                key_value[1] = 0;
                lcd_clear_flag = 1;
                card_manage_status = 1;
                selected_card_id = 1;
            }
            if (key_value[2] == 1)
            {
                key_value[2] = 0;
                lcd_clear_flag = 1;
                card_manage_status = 1;
                selected_card_id = 2;
            }
            if (key_value[14] == 1)
            {
                key_value[14] = 0;
                lcd_clear_flag = 1;
                if (card_manage_status == 0)
                {
                    sub_disp = 0;
                    select = 0;
                    card_manage_status = 0;
                    selected_card_id = -1;
                }
                if (card_manage_status == 1)
                {
                    select = 0;
                    card_manage_status = 0;
                }
            }
        }
        if (sub_disp == 2)
        {
            if (key_value[0] == 1)
            {
                key_value[0] = 0;
                lcd_clear_flag = 1;
                selected_card_id = 0;
            }
            if (key_value[1] == 1)
            {
                key_value[1] = 0;
                lcd_clear_flag = 1;
                selected_card_id = 1;
            }
            if (key_value[2] == 1)
            {
                key_value[2] = 0;
                lcd_clear_flag = 1;
                selected_card_id = 2;
            }
            if (key_value[14] == 1)
            {
                key_value[14] = 0;
                lcd_clear_flag = 1;
                sub_disp = 0;
                select = 0;
                card_manage_status = 0;
                selected_card_id = -1;
            }
        }
    }
}
