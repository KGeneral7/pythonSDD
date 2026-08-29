# 資料模型：破陣者 Q 版像素角色與八方向動畫

## 模型概覽

本功能只有視覺資料與玩家動畫狀態，不新增戰鬥資料、持久化資料或外部交換格式。`PlayerState` 保存目前動畫進度；圖片資產目錄保存可替換的角色外觀；繪製階段依狀態選出單張圖片，失敗時使用既有幾何外觀。

## 實體定義

### `PlayerAnimationState`

隸屬於 `PlayerState` 的短期視覺狀態，所有欄位都有預設值，避免影響既有測試與 positional 建構。

| 欄位 | 型別 | 預設值 | 規則 |
|---|---|---:|---|
| `facing_direction_index` | `int` | `0` | 只能是 0～7；順序為右、右下、下、左下、左、左上、上、右上。 |
| `moving` | `bool` | `False` | 只有玩家存活、未被定身，且本幀有有效移動輸入時為真。 |
| `move_elapsed` | `float` | `0.0` | 非負數；移動時累加，用於計算四格循環索引。 |
| `attack_elapsed` | `float` | `0.0` | 非負數；攻擊狀態啟動後累加，超過最後一格時固定在第四格。 |
| `attack_hold` | `float` | `0.0` | 非負數；大於零表示攻擊動畫仍優先，連續技能可延長但不可重置 `attack_elapsed`。 |

**衍生狀態**：

- `attack_active`：`attack_hold > 0`。
- `move_frame`：`floor(move_elapsed / 0.10) % 4`。
- `attack_frame`：`min(3, floor(attack_elapsed / 0.06))`。
- 待機狀態：`moving == False` 且 `attack_active == False`。

### `BreacherSpriteAsset`

代表一張可供繪製的破陣者圖片，不保存到遊戲狀態，只由資產載入器依需要快取。

| 欄位 | 型別 | 規則 |
|---|---|---|
| `visual_state` | `idle`、`move` 或 `attack` | `idle` 只有待機圖；`move` 與 `attack` 必須有四格。 |
| `direction_index` | 8 方向索引 | 必須對應固定方向名稱與既有圖片目錄。 |
| `frame_index` | `0`～`3` 或待機索引 | 移動／攻擊不可超過 3；待機固定取單張圖片。 |
| `path` | 專案相對路徑 | 必須位於 `pvpve_escape/assets/characters/breacher/` 下。 |
| `surface` | Pygame 圖片或不可用 | 成功載入後快取；驗證失敗時標記不可用並走幾何 fallback。 |

### `SpriteFrameRequest`

繪製層向資產載入器提出的短期查詢值，包含 `visual_state`、`direction_index` 與 `frame_index`。查詢值必須經過範圍驗證；任何不合法值都回傳不可用結果，不得產生越界路徑或例外。

## 圖片資產關係

```text
PlayerState
└── PlayerAnimationState
    └── SpriteFrameRequest
        └── BreacherSpriteAsset（成功時）
            或既有幾何角色（失敗時）
```

破陣者資產完整集合如下：

- 待機：8 張。
- 移動：8 個方向 × 4 張 = 32 張。
- 攻擊：8 個方向 × 4 張 = 32 張。
- 合計：72 張。

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

- 方向更新發生在收到新的有效瞄準向量時，並寫入 `facing_direction_index`；零向量不覆蓋原方向。
- `start_or_refresh_attack_animation()` 在非攻擊狀態時將 `attack_elapsed` 歸零並啟動維持時間；已在攻擊狀態時只延長 `attack_hold`。
- 玩家死亡時清除 `moving`、`attack_elapsed` 與 `attack_hold`；死亡標記由原有流程繪製。
- 玩家重生後以初始待機狀態重新開始，面向沿用有效面向或回到右方預設。
- 怪物不持有此模型，其他角色也不載入破陣者資產。

## 驗證規則

- 每一個方向必須存在待機圖、四張移動圖與四張攻擊圖。
- 所有圖片畫布必須一致為 1024×1024，四個角落必須為真正透明像素，角色本體與武器不得貼住或超出畫布邊界，且同一方向動畫幀的非透明內容中心相對畫布中心偏移不得超過 16 個來源像素。
- 角色本體、槍與盾不得被畫布邊界裁切；各動畫幀的畫布與錨點必須一致。
- 圖片不存在、讀取失敗、透明度不合格或查詢值不合法時，輸出必須是幾何 fallback。
- `PlayerAnimationState` 的時間欄位不得為負數；世界更新使用的時間步長已受既有上限保護。
- 動畫狀態不得改寫生命、移動速度、技能冷卻、傷害、碰撞或彈藥欄位。
