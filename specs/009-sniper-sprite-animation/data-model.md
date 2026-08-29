# 資料模型：狙擊者 Q 版像素角色與八方向動畫

## 模型概覽

本功能只有可替換的視覺資產、玩家短期動畫狀態與載入器快取，不新增戰鬥資料、持久化資料或外部交換格式。`PlayerState` 保存動畫進度；資產目錄保存狙擊者圖片；繪製階段依動畫狀態選出單張圖片，失敗時使用既有幾何外觀。

## 實體定義

### `CharacterSpriteSpec`

由資產載入器使用的內部角色規格，將破陣者與狙擊者的共同圖片規則集中管理。

| 欄位 | 型別 | 狙擊者值／規則 |
|---|---|---|
| `character_id` | `CharacterId` | `CharacterId.SNIPER` |
| `asset_root` | 路徑 | `assets/characters/sniper` |
| `source_size` | `int` | `1024`，寬高相同 |
| `display_size` | `int` | 對局 `50` |
| `selection_size` | `int` | 選角 `54` |
| `roster_size` | `int` | 玩家列表 `24` |
| `preload_display_sizes` | 3 個 `int` | `(50, 54, 24)`；資產初始化時三種尺寸都要暖身。 |
| `direction_names` | 8 個字串 | 固定八方向順序 |
| `frame_count` | `int` | 移動與攻擊皆為 `4` |
| `move_frame_time` | `float` | `0.10` 秒 |
| `attack_frame_time` | `float` | `0.06` 秒 |
| `attack_duration` | `float` | `0.24` 秒 |
| `fit_mode` | `str` | `source_canvas`；狙擊者素材已依各方向全部動畫幀的身體核心聯合外框重新縮放，武器外伸不參與本體比例，顯示時保留固定來源畫布，讓走路幀與朝上方向不會重新決定角色大小。 |

### `PlayerAnimationState`

隸屬於 `PlayerState` 的短期視覺狀態。欄位已有預設值，不能改變既有 positional 建構相容性。

| 欄位 | 型別 | 預設值 | 規則 |
|---|---|---:|---|
| `facing_direction_index` | `int` | `0` | 只能是 0～7；順序為右、右下、下、左下、左、左上、上、右上。 |
| `moving` | `bool` | `False` | 玩家存活、未被定身且本幀有有效移動輸入時為真。 |
| `move_elapsed` | `float` | `0.0` | 非負數；以 0.10 秒為一格，四格循環。 |
| `attack_elapsed` | `float` | `0.0` | 非負數；以 0.06 秒為一格，超過最後一格固定在第四格。 |
| `attack_hold` | `float` | `0.0` | 非負數；大於零時攻擊動畫優先，連續動作只能延長維持時間。 |

**衍生狀態**：

- `attack_active`：`attack_hold > 0`。
- `move_frame`：`floor(move_elapsed / 0.10) % 4`。
- `attack_frame`：`min(3, floor(attack_elapsed / 0.06))`。
- 待機：`moving == False` 且 `attack_active == False`。

### `SpriteFrameRequest`

繪製層向資產載入器提出的短期查詢值。

| 欄位 | 型別 | 規則 |
|---|---|---|
| `character_id` | `CharacterId` | 目前支援破陣者與狙擊者；其他角色不查詢像素資產。 |
| `visual_state` | `str` | 只能是 `idle`、`move` 或 `attack`。 |
| `direction_index` | `int` | 0～7，對應固定方向名稱。 |
| `frame_index` | `int` | `idle` 固定為 0；`move`／`attack` 為 0～3。 |

不合法的查詢值不得組出越界路徑或拋出繪製例外，必須回傳不可用結果並由繪製層 fallback。

### `SniperSpriteAsset`

代表一張狙擊者來源圖片及其載入後狀態，不保存到遊戲對局資料。

| 欄位 | 型別 | 規則 |
|---|---|---|
| `visual_state` | `idle`、`move`、`attack` | `idle` 只有單張；其他狀態各方向四張。 |
| `direction_index` | `int` | 0～7。 |
| `frame_index` | `int` | 待機為 0，移動／攻擊為 0～3。 |
| `path` | 專案相對路徑 | 必須位於 `pvpve_escape/assets/characters/sniper/` 下。 |
| `source_surface` | 圖片或不可用 | 成功時維持來源畫布；驗證失敗時標記不可用。 |
| `visible_bounds` | 矩形 | 取 `alpha >= 64` 的實際角色、槍與瞄具區域；來源圖是否有內容與是否貼邊則以 `alpha > 0` 判斷。 |
| `display_surface` | 圖片或不可用 | 狙擊者使用已完成方向身體核心聯合外框標準化的固定來源畫布，以最近鄰縮放至需求尺寸；破陣者維持既有 `visible_extent` 流程。 |

### `SpriteFallback`

圖片不存在、讀取失敗、尺寸不符、透明度不合格、空白或查詢值不合法時的顯示結果。它不改變玩家位置、生命、戰鬥、技能或碰撞狀態，只讓 `draw_player_visual()` 改畫既有幾何狙擊者。

## 圖片資產關係

```text
PlayerState
└── PlayerAnimationState
    └── SpriteFrameRequest
        └── SniperSpriteAsset（成功時）
            或 SpriteFallback（失敗時）
```

狙擊者資產完整集合如下：

- 待機：8 張。
- 移動：8 個方向 × 4 張 = 32 張。
- 攻擊：8 個方向 × 4 張 = 32 張。
- 合計：72 張。

## 方向與動畫規則

| 索引 | 名稱 | 畫面座標方向 |
|---:|---|---|
| 0 | `right` | 右 |
| 1 | `down_right` | 右下 |
| 2 | `down` | 下 |
| 3 | `down_left` | 左下 |
| 4 | `left` | 左 |
| 5 | `up_left` | 左上 |
| 6 | `up` | 上 |
| 7 | `up_right` | 右上 |

- 在 Pygame 螢幕座標中令右方為 0 度、`y` 正方向向下，令 `angle = atan2(y, x)` 使用弧度，並以 `floor((angle + pi / 8) / (pi / 4)) % 8` 量化有效 `aim_direction`；正好落在 22.5 度分界時歸入順時針側，零向量沿用上一個有效方向，初始為索引 0。
- `idle` 只取第 0 幀；`move` 每 0.10 秒循環一格；`attack` 每 0.06 秒前進一格，總長 0.24 秒。
- 狙擊者蓄力中不改變攻擊動畫狀態；只有成功建立普攻、戰術配件或終極技能動作才啟動攻擊動畫。
- 攻擊未啟動時成功動作會將 `attack_elapsed` 設為 0；攻擊進行中再次成功不重設目前幀，只將 `attack_hold` 延長至至少 0.24 秒。每次更新先將 `attack_elapsed` 增加並限制在 0.24 秒，再將 `attack_hold` 扣減；`attack_hold <= 0` 時清除攻擊進度。
- 攻擊動畫期間優先於移動動畫；完成後回到玩家當下的移動或待機狀態。
- 死亡與重生清除移動／攻擊進度，面向通常保留以避免重生瞬間跳回右方。

## 狀態轉移

```text
待機 ──有效移動輸入──> 移動
  │                    │
  └──成功攻擊／技能──> 攻擊 <──成功攻擊／技能── 移動
                         │
               動畫完成 │
                         v
                   待機或移動
```

圖片載入失敗是繪製結果的旁路狀態，不會改寫上述動畫狀態；下一次查詢仍可依同一狀態嘗試或使用已記錄的 fallback。

## 驗證規則

- 每一個方向必須存在待機圖、四張移動圖與四張攻擊圖。
- 每張來源圖必須是 1024×1024 RGBA，四角 alpha 為 0，含可見角色像素，非透明像素不得貼住邊界。
- 同方向的動畫幀中心相對畫布中心偏移不得超過 16 個來源像素；槍、瞄具與角色本體不得被裁切或變成孤立像素。
- 狙擊者來源圖先以頭盔／面罩頭部錨點及方向身體核心聯合外框統一整套動畫比例；武器外伸不作為角色本體尺寸基準。對局、選角與玩家列表保留固定來源畫布並分別縮放到 50×50、54×54、24×24，確保同方向走路幀與八個角度的角色本體佔位一致。兩者均不得執行期旋轉或鏡像圖片。
- 圖片不存在、讀取失敗、透明度不合格或查詢值不合法時，結果必須是幾何 fallback，且同一資產鍵只產生一次診斷警告。
- 動畫時間不得為負數，更新使用的時間步長沿用既有上限；視覺狀態不得改寫生命、速度、傷害、碰撞、冷卻或彈藥。
- 預載入必須涵蓋兩個像素角色各 72 個來源幀，並為 50、54、24 三種顯示尺寸建立顯示快取；量測期間不得呼叫圖片讀取函式。

## 實作後覆核（2026-08-29）

- `pvpve_escape/sprites.py` 以 `CHARACTER_SPRITE_SPECS` 保存破陣者與狙擊者兩份 `CharacterSpriteSpec`；兩者使用同一套路徑、來源驗證、`alpha >= 64` 裁切、縮放與錯誤處理流程。
- 角色中立來源快取鍵為 `(character_id, visual_state, direction_index, frame_index)`，顯示快取鍵再加上 `display_size`；破陣者另外同步保留舊的四欄 `_SPRITE_CACHE` 檢視，確保既有 wrapper 與測試相容，狙擊者不會寫入該 legacy 檢視。
- `preload_character_sprites()` 先讀取每個角色 72 個來源幀，再暖身傳入的顯示尺寸；省略尺寸時使用 `CharacterSpriteSpec.preload_display_sizes` 的 `(50, 54, 24)`，兩個角色合計 144 次來源讀檔與最多 432 個顯示表面。
- `load_breacher_sprite()`、`preload_breacher_sprites()`、`breacher_sprite_error()` 的原始呼叫形式維持不變；狙擊者對應介面為 `load_sniper_sprite()`、`preload_sniper_sprites()` 與 `sniper_sprite_error()`。
- 狙擊者 72 張來源圖已依每方向待機頭部錨點及全部動畫幀的身體核心聯合外框重新縮放完整角色並重新置中；`CharacterSpriteSpec.fit_mode` 為 `source_canvas`，顯示快取保留固定來源畫布，避免武器外伸造成走路幀或朝上方向的角色本體大小跳動。
