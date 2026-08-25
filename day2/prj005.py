#########################匯入模組#########################
import pygame as pg

#########################遊戲基本設定#########################
HEIGHT = 600
WIDTH = 800
FPS = 60

BACKGROUND_COLOR = (15, 23, 42)
PADDLE_COLOR = (241, 245, 249)
BALL_COLOR = (100, 100, 100)
BRICK_COLORS = [
    (244, 114, 182),  # 粉紅色
    (255, 179, 71),  # 橘色
    (255, 205, 86),  # 黃色
    (75, 192, 192),  # 青色
    (54, 162, 235),  # 藍色
]

#########################初始化設定#########################
init = pg.init()

#########################遊戲視窗設定#########################
screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("打磚塊遊戲")
clock = pg.time.Clock()


#########################物件類別#########################
class Brick:
    """磚塊會保存自己的位置、顏色與是否存在"""

    def __init__(self, x, y, width, height, color):
        self.rect = pg.Rect(x, y, width, height)
        self.color = color
        self.alive = True

    def draw(self, surface):
        """繪製磚塊"""
        if self.alive:
            pg.draw.rect(
                surface, self.color, self.rect, border_radius=5
            )  # border_radius是調方塊的角用


class Paddle:
    def __init__(self):
        self.rect = pg.Rect(0, 0, 120, 16)
        self.rect.midbottom = (WIDTH // 2, HEIGHT - 34)
        self.speed = 8

    def update(self, keys):
        direction = 0
        if keys[pg.K_LEFT] or keys[pg.K_a]:
            direction -= 1
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            direction += 1

        self.rect.x += direction * self.speed
        self.rect.x = max(0, min(self.rect.x, WIDTH - self.rect.width))

    def draw(self, surface):
        pg.draw.rect(surface, PADDLE_COLOR, self.rect, border_radius=8)


class Ball:
    def __init__(self, paddle):
        self.radius = 9
        self.position = pg.Vector2(0, 0)
        self.velocity = pg.Vector2(5, -5)
        self.rect = pg.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.lounched = False
        self.reset(paddle)

    def reset(self, paddle):
        self.launched = False
        self.position.update(paddle.rect.centerx, paddle.rect.top - self.radius)
        self.velocity.update(5, -5)
        self.rect.center = (round(self.position.x), round(self.position.y))

    def lounch(self):
        self.launched = True

    def update(self, paddle):
        if not self.launched:
            self.position.update(
                paddle.rect.centerx, paddle.rect.top - self.radius
            )  # 球體的position的中心會跟著底板的中心位置更新
        else:
            self.position += self.velocity
            if self.position.x - self.radius <= 0:
                self.position.x = self.radius
                self.velocity.x *= -1
            elif self.position.x + self.radius >= WIDTH:
                self.position.x = WIDTH - self.radius
                self.velocity.x *= -1

            if self.position.y - self.radius <= 0:
                self.position.y = self.radius
                self.velocity.y *= -1

            if self.position.y + self.radius >= HEIGHT:
                self.reset(paddle)

            if self.rect.colliderect(paddle.rect):
                self.position.y = paddle.rect.top - self.radius
                self.velocity.y *= -1

        self.rect.center = (round(self.position.x), round(self.position.y))

    def draw(self, surface):
        pg.draw.circle(surface, BALL_COLOR, self.rect.center, self.radius)


#########################定義函式區#########################
def create_bricks():
    """用同一份 Brick 類別建立多個磚塊，並回傳磚塊列表"""

    bricks = []
    brick_width = 72
    brick_height = 24
    padding = 8
    rows = 5
    cols = 9
    start_x = 44
    start_y = 70

    for row in range(rows):
        for col in range(cols):
            x = start_x + col * (brick_width + padding)
            y = start_y + row * (brick_height + padding)
            color = BRICK_COLORS[row]
            brick = Brick(x, y, brick_width, brick_height, color)
            bricks.append(brick)

    return bricks


#########################磚塊#########################
bricks = create_bricks()

#########################底板#########################
paddle = Paddle()

#########################球#########################
ball = Ball(paddle)

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
        elif event.type == pg.KEYDOWN:  # 按下ESC鍵就關閉
            if event.key == pg.K_ESCAPE:
                running = False
            elif event.key == pg.K_SPACE:  # 按下空白鍵就發射球
                ball.lounch()

    # 取得按鍵狀態
    keys = pg.key.get_pressed()
    paddle.update(keys)
    ball.update(paddle)

    # 清除畫面
    screen.fill(BACKGROUND_COLOR)

    # 繪製磚塊與底板
    for brick in bricks:
        brick.draw(screen)
    paddle.draw(screen)
    ball.draw(screen)
    # 更新畫面顯示
    pg.display.flip()

#########################遊戲結束設定#########################
#  退出 Pygame
pg.quit()
