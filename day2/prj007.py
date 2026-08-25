#########################匯入模組#########################
import pygame as pg

#########################遊戲基本設定#########################
HEIGHT = 600
WIDTH = 800
FPS = 60

BACKGROUND_COLOR = (15, 23, 42)
PADDLE_COLOR = (241, 245, 249)
BALL_COLOR = (100, 100, 100)
TEXT_COLOR = PADDLE_COLOR
INITIAL_LIVES = 3
BRICK_SCORE = 10
SURVIVAL_SECONDS = 300
SURVIVAL_TIME = SURVIVAL_SECONDS * 1000

BRICK_WIDTH = 72
BRICK_HEIGHT = 24
BRICK_PADDING = 8
BRICK_ROWS = 5
BRICK_COLS = 9
BRICK_START_X = 44
BRICK_START_Y = 70
BRICK_ROW_STEP = BRICK_HEIGHT + BRICK_PADDING

INITIAL_SPAWN_INTERVAL = 15000
SPAWN_INTERVAL_DECREASE = 1000
MIN_SPAWN_INTERVAL = 5000

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

# 新指令：pg.font.Font會建立字型物件，None代表使用Pygame預設字型。
font = pg.font.Font(None, 28)
title_font = pg.font.Font(None, 54)


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
        missed = False

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
                missed = True
                self.reset(paddle)

        self.rect.center = (round(self.position.x), round(self.position.y))
        return missed

    def draw(self, surface):
        pg.draw.circle(surface, BALL_COLOR, self.rect.center, self.radius)


#########################定義函式區#########################
def draw_text(surface, text_font, text, position, color=TEXT_COLOR):
    # 新指令：font.render把文字轉成可繪製的畫面物件，True代表啟用反鋸齒。
    text_surface = text_font.render(text, True, color)
    # 新指令：surface.blit把文字畫面物件放到指定位置。
    surface.blit(text_surface, position)


def all_bricks_destroyed(bricks):
    """檢查是否所有磚塊都已經被消除。"""
    for brick in bricks:
        if brick.alive:
            return False
    return True


def draw_end_screen(surface, game_state, score):
    """繪製勝利或失敗畫面。"""
    if game_state == "game_over":
        title = "GAME OVER"
    else:
        title = "YOU WIN"

    draw_text(surface, title_font, title, (WIDTH // 2 - 150, 230))
    draw_text(surface, font, f"Final Score: {score}", (WIDTH // 2 - 100, 300))
    draw_text(surface, font, "Press R to Restart", (WIDTH // 2 - 125, 350))
    draw_text(surface, font, "Press ESC to Quit", (WIDTH // 2 - 115, 390))


def create_brick_row(y, row_index):
    """建立一整排方塊，並依列數循環使用方塊顏色。"""
    row_bricks = []
    color_index = row_index % len(BRICK_COLORS)

    for col in range(BRICK_COLS):
        x = BRICK_START_X + col * (BRICK_WIDTH + BRICK_PADDING)
        brick = Brick(x, y, BRICK_WIDTH, BRICK_HEIGHT, BRICK_COLORS[color_index])
        row_bricks.append(brick)

    return row_bricks


def create_bricks():
    """建立遊戲開始時的5排方塊。"""
    bricks = []

    for row in range(BRICK_ROWS):
        row_y = BRICK_START_Y + row * BRICK_ROW_STEP
        row_bricks = create_brick_row(row_y, row)
        for brick in row_bricks:
            bricks.append(brick)

    return bricks


def add_brick_row(bricks, row_index):
    """將活方塊向下移動一排，並在最上方加入新的一排。"""
    for brick in bricks:
        if brick.alive:
            brick.rect.y += BRICK_ROW_STEP

    new_bricks = create_brick_row(BRICK_START_Y, row_index)
    for brick in new_bricks:
        bricks.append(brick)


def bricks_reached_paddle(bricks, paddle):
    """檢查是否有活方塊到達底板高度。"""
    for brick in bricks:
        if brick.alive and brick.rect.bottom >= paddle.rect.top:
            return True
    return False


def bounce_from_rect(ball, target_rect):
    """找出重疊最少的一側，決定反轉水平或垂直速度。"""
    overlaps = {
        "left": ball.rect.right - target_rect.left,
        "right": target_rect.right - ball.rect.left,
        "top": ball.rect.bottom - target_rect.top,
        "bottom": target_rect.bottom - ball.rect.top,
    }
    collision_side = min(
        overlaps, key=overlaps.get
    )  # overlaps是要比較的東西(這裡是字典)，key=overlaps.get是要比較的方式(把值抓出，做比較)，這裡是比較overlaps這個字典裡的所有的值
    # 這行=min(overlaps.get(left), overlaps.get(right), overlaps.get(top), overlaps.get(bottom))，回傳最小的那個key
    if collision_side in ["left", "right"]:
        ball.velocity.x *= -1
    else:
        ball.velocity.y *= -1


def handle_collision(ball, paddle, bricks):
    # 碰撞處理三步驟:找到、改狀態、改方向。
    # 檢查底板碰撞
    if ball.velocity.y > 0 and ball.rect.colliderect(paddle.rect):
        ball.rect.bottom = paddle.rect.top
        ball.position.y = ball.rect.centery
        ball.velocity.y = -abs(ball.velocity.y)  # 這個=ball.velocity.y *= -1

        offset = (ball.rect.centerx - paddle.rect.centerx) / (paddle.rect.width / 2)
        ball.velocity.x = offset * 6

    brick_hit = False
    # 檢查磚塊碰撞
    for brick in bricks:
        if brick.alive and ball.rect.colliderect(brick.rect):
            brick.alive = False
            brick_hit = True
            bounce_from_rect(ball, brick.rect)
            break  # 只處理一個磚塊碰撞

    return brick_hit


#########################磚塊#########################
bricks = create_bricks()

#########################底板#########################
paddle = Paddle()

#########################球#########################
ball = Ball(paddle)

#########################遊戲狀態#########################
score = 0
lives = INITIAL_LIVES
game_state = "playing"
spawn_timer = 0
spawn_interval = INITIAL_SPAWN_INTERVAL
next_row_index = BRICK_ROWS
survival_started = False
survival_time = 0

#########################主程式#########################
#  遊戲主迴圈
running = True
while running:
    # 新用法：clock.tick回傳距離上一幀經過的毫秒數。
    elapsed_time = clock.tick(FPS)

    # 處理事件
    for event in pg.event.get():
        if event.type == pg.QUIT:  # 按螢幕上方按鈕就關閉
            running = False
        elif event.type == pg.KEYDOWN:  # 按下ESC鍵就關閉
            if event.key == pg.K_ESCAPE:
                running = False
            elif (
                event.key == pg.K_SPACE and game_state == "playing"
            ):  # 按下空白鍵就發射球
                ball.lounch()
                survival_started = True
            # 新指令：pg.K_r是鍵盤R鍵的代號。
            elif event.key == pg.K_r and game_state != "playing":
                bricks = create_bricks()
                paddle = Paddle()
                ball = Ball(paddle)
                score = 0
                lives = INITIAL_LIVES
                game_state = "playing"
                spawn_timer = 0
                spawn_interval = INITIAL_SPAWN_INTERVAL
                next_row_index = BRICK_ROWS
                survival_started = False
                survival_time = 0

    if game_state == "playing":
        # 只有球正在移動時，才累積生存時間與方塊下壓時間。
        if survival_started and ball.launched:
            spawn_timer += elapsed_time
            survival_time += elapsed_time

            if spawn_timer >= spawn_interval:
                add_brick_row(bricks, next_row_index)
                spawn_timer = 0
                spawn_interval = max(
                    MIN_SPAWN_INTERVAL,
                    spawn_interval - SPAWN_INTERVAL_DECREASE,
                )
                next_row_index += 1

        # 方塊碰到底板高度時，Game Over優先於其他勝利條件。
        if bricks_reached_paddle(bricks, paddle):
            game_state = "game_over"

        if game_state == "playing":
            # 取得按鍵狀態
            keys = pg.key.get_pressed()
            paddle.update(keys)
            missed = ball.update(paddle)

            if missed:
                lives -= 1

            if lives <= 0:
                game_state = "game_over"

        if game_state == "playing":
            if handle_collision(ball, paddle, bricks):
                score += BRICK_SCORE
                if all_bricks_destroyed(bricks):
                    game_state = "win"

        if game_state == "playing" and survival_time >= SURVIVAL_TIME:
            game_state = "win"

    # 清除畫面
    screen.fill(BACKGROUND_COLOR)

    # 繪製磚塊與底板
    for brick in bricks:
        brick.draw(screen)
    paddle.draw(screen)
    ball.draw(screen)

    # 新指令：f-string會把score、lives與時間數值嵌入文字中。
    survival_seconds = min(SURVIVAL_SECONDS, survival_time // 1000)
    draw_text(screen, font, f"Score: {score}", (20, 20))
    draw_text(screen, font, f"Lives: {lives}", (150, 20))
    draw_text(screen, font, f"Time: {survival_seconds}/{SURVIVAL_SECONDS}", (250, 20))

    if game_state != "playing":
        draw_end_screen(screen, game_state, score)

    # 更新畫面顯示
    pg.display.flip()

#########################遊戲結束設定#########################
# 退出 Pygame
pg.quit()
