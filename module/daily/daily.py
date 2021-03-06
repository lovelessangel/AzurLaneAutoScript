import numpy as np

from module.base.ocr import Digit
from module.base.utils import get_color
from module.combat.combat import Combat
from module.daily.assets import *
from module.equipment.fleet_equipment import DailyEquipment
from module.logger import logger
from module.ui.ui import page_daily, page_campaign, BACK_ARROW, DAILY_CHECK

DAILY_MISSION_LIST = [DAILY_MISSION_1, DAILY_MISSION_2, DAILY_MISSION_3]
OCR_REMAIN = Digit(OCR_REMAIN, letter=(255, 255, 255), back=(127, 127, 127), length=1, white_list='0123')
OCR_DAILY_FLEET_INDEX = Digit(OCR_DAILY_FLEET_INDEX, letter=(90, 154, 255), back=(24, 32, 49), length=1,
                              white_list='123456')
RECORD_OPTION = ('DailyRecord', 'daily')
RECORD_SINCE = (0,)


class Daily(Combat, DailyEquipment):
    daily_current: int
    daily_checked: list

    def is_active(self):
        color = get_color(image=self.device.image, area=DAILY_ACTIVE.area)
        color = np.array(color).astype(float)
        color = (np.max(color) + np.min(color)) / 2
        active = color > 30
        if active:
            logger.attr(f'Daily_{self.daily_current}', 'active')
        else:
            logger.attr(f'Daily_{self.daily_current}', 'inactive')
        return active

    def _wait_daily_switch(self):
        self.device.sleep((1, 1.2))

    def next(self):
        self.daily_current += 1
        logger.info('Switch to %s' % str(self.daily_current))
        self.device.click(DAILY_NEXT)
        self._wait_daily_switch()
        self.device.screenshot()

    def prev(self):
        self.daily_current -= 1
        logger.info('Switch to %s' % str(self.daily_current))
        self.device.click(DAILY_PREV)
        self._wait_daily_switch()
        self.device.screenshot()

    def daily_execute(self, remain):
        logger.hr(f'Daily {self.daily_current}')
        self.ui_click(click_button=DAILY_ENTER, check_button=DAILY_ENTER_CHECK, appear_button=DAILY_CHECK)

        def daily_end():
            return self.appear(DAILY_ENTER_CHECK) or self.appear(BACK_ARROW)

        button = DAILY_MISSION_LIST[self.config.DAILY_CHOOSE[self.daily_current] - 1]
        for n in range(remain):
            logger.hr(f'Count {n + 1}')
            self.ui_click(click_button=button, check_button=self.combat_appear, appear_button=DAILY_ENTER_CHECK)
            self.ui_ensure_index(self.config.FLEET_DAILY, letter=OCR_DAILY_FLEET_INDEX, prev_button=DAILY_FLEET_PREV,
                                 next_button=DAILY_FLEET_NEXT, fast=False, skip_first_screenshot=True)
            self.combat(emotion_reduce=False, save_get_items=False, expected_end=daily_end, balance_hp=False)

        self.ui_click(click_button=BACK_ARROW, check_button=DAILY_CHECK)
        self.device.sleep((1, 1.2))

    def daily_check(self, n=None):
        if not n:
            n = self.daily_current
        self.daily_checked.append(n)
        logger.info(f'Checked daily {n}')
        logger.info(f'Checked_list: {self.daily_checked}')

    def daily_run_one(self):
        self.ui_ensure(page_daily)
        self.device.sleep(0.2)
        self.device.screenshot()
        self.daily_current = 1

        logger.info(f'Checked_list: {self.daily_checked}')
        for _ in range(max(self.daily_checked)):
            self.next()

        while 1:
            if self.daily_current > 5:
                break
            if self.daily_current == 3:
                logger.info('Skip submarine daily.')
                self.daily_check()
                self.next()
                continue
            if not self.is_active():
                self.daily_check()
                self.next()
                continue
            remain = OCR_REMAIN.ocr(self.device.image)
            if remain == 0:
                self.daily_check()
                self.next()
                continue
            else:
                self.daily_execute(remain=remain)
                self.daily_check()
                # The order of daily tasks will be disordered after execute a daily, exit and re-enter to reset.
                # 打完一次之后每日任务的顺序会乱掉, 退出再进入来重置顺序.
                self.ui_ensure(page_campaign)
                break

    def daily_run(self):
        self.daily_checked = [0]

        while 1:
            self.daily_run_one()

            if max(self.daily_checked) >= 5:
                logger.info('Daily clear complete.')
                break

    def run(self):
        self.equipment_take_on()
        self.daily_run()
        self.equipment_take_off()
        self.ui_goto_main()

    def record_executed_since(self):
        return self.config.record_executed_since(option=RECORD_OPTION, since=RECORD_SINCE)

    def record_save(self):
        return self.config.record_save(option=RECORD_OPTION)
