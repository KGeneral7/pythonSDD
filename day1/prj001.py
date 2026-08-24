#########################匯入模組#########################
import pygame as pg

#########################遊戲基本設定#########################
HEIGHT = 600
WIDTH = 800
FPS = 60
BACKGROUND_COLOR = (15, 23, 42)

#########################初始化設定#########################
init = pg.init()

#########################遊戲視窗設定#########################
screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("打磚塊遊戲")
clock = pg.time.Clock()

#########################主程式#########################
#  遊戲主迴圈
running = True
while running:
    # 設定遊戲迴圈的執行速度
    clock.tick(FPS)
    # 處理事件
    for event in pg.event.get():
        if event.type == pg.QUIT:  # 按螢幕上方按鈕就關閉
            running = False
        elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:  # 按下ESC鍵就關閉
            running = False
    # 清除畫面
    screen.fill(BACKGROUND_COLOR)
    # 更新畫面顯示
    pg.display.flip()

#########################遊戲結束設定#########################
#  退出 Pygame
pg.quit()
