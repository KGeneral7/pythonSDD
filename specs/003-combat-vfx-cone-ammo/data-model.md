# 資料模型與狀態規則

本功能不新增持久化資料；以下模型均為單局記憶體狀態，欄位名稱以既有 Python dataclass 為基礎。數值以規格與現有角色平衡資料為準，避免在渲染層重複定義。

## 角色與配件定義

### `CharacterDefinition`

| 欄位 | 型別 | 規則 |
|---|---|---|
| `character_id` | `CharacterId` | 六種角色的穩定識別碼 |
| `display_name` | `str` | 選角與 HUD 顯示名稱 |
| `primary_kind` | `str` | 規則與 VFX 的普攻識別碼 |
| `ammo_capacity` | `int` | 普攻彈匣容量 |
| `ammo_recovery_interval` | `float` | 非攻擊狀態下逐發恢復間隔 |
| `primary_cooldown` | `float` | 普攻後搖／發射間隔 |
| `primary_damage` | `float` | 普攻單一傷害單位 |
| `primary_range` | `float` | 普攻有效距離 |
| `projectile_speed` | `float` | 移動型普攻的世界單位／秒 |
| `passive_text` | `str` | HUD 與選角頁顯示的被動說明 |
| `ultimate_text` | `str` | HUD 與選角頁顯示的大招說明 |
| `base_health` | `float` | 未套用角色被動前的基礎生命 |
| `passive_multiplier` | `float` | 條件被動使用的倍率 |
| `passive_condition` | `str` | 條件被動的規則識別字 |
| `parameters` | `dict[str, float]` | 角色專屬的角度、範圍、持續時間等數值 |

六角色的初始平衡與既有規格一致：破陣者（近距離高生命／扇形）、狙擊者（遠距離高傷害／高速明確子彈）、守衛者（防禦／盾弧）、追獵者（位移與近戰殘影）、控場者（地雷／控制區）、吸能者（持續吸取／生命轉換）。每種角色的 `primary_kind` 與 `create_ultimate_action` 產生的效果 kind 必須唯一，不能只換顏色。

角色特效顏色由 `config.py` 的集中設定提供，不在 `CharacterDefinition` 重複保存；大招的規則識別字由 `create_ultimate_action` 依 `character_id` 產生。

### `TacticalDefinition`

| 欄位 | 型別 | 規則 |
|---|---|---|
| `tactical_id` | `TacticalId` | 三種配件的穩定識別碼 |
| `display_name` | `str` | HUD 與選角頁顯示名稱 |
| `cooldown` | `float` | 10～15 秒固定冷卻值 |
| `description` | `str` | 配件規則與操作說明 |
| `parameters` | `dict[str, float]` | 位移、吸收、半徑、減速與持續時間等數值 |

三種配件的規則與視覺語彙如下：

| 配件 | 規則效果 | 視覺語彙 |
|---|---|---|
| `TacticalId.DASH` | 短距離位移並受世界邊界限制 | 起點／終點殘影與閃光線 |
| `TacticalId.SHIELD` | 短時間減傷／防禦 | 角色外圍盾形弧線與脈衝 |
| `TacticalId.CONTROL` | 在指定位置形成短暫控場區 | 圓形牢籠、網格與向內脈衝 |

配件開局即可用；規則效果與 `tactical_*` effect 同幀建立，不能只顯示冷卻圖示而沒有實際控制／防禦／位移。

## 玩家狀態

### `PlayerState` 相關欄位

| 欄位 | 型別 | 不變量／用途 |
|---|---|---|
| `status`／`alive` | `PlayerStatus`／導出 `bool` | 死亡時不能攻擊、回彈或觸發技能傷害 |
| `health` / `max_health` | `float` | `health` 維持在 0～`max_health` |
| `ammo` / `ammo_capacity` | `int` | `ammo` 維持在 0～容量 |
| `ammo_recovery_timer` | `float` | 只在非阻擋、未滿彈時累積 |
| `primary_cooldown` | `float` | 普攻後搖／間隔，非負數 |
| `primary_charge` | `float` | 蓄力或持續普攻的目前進度 |
| `ultimate_energy` | `float` | 造成怪物／玩家傷害時累積，施放後歸零 |
| `tactical_cooldown` | `float` | 配件冷卻，開局為零 |
| `death_timer` | `float` | 死亡後 5 秒重生流程 |
| `upgrade_stacks` | `int` | 擊殺怪物獲得的層數，最多 10；死亡清零 |

### 普攻狀態導出

```text
primary_attack_active(player, input) =
    player.alive AND (
        input.primary_held
        OR player.primary_charge > 0
        OR player.primary_cooldown > 0
    )
```

這個導出值只描述角色自身普攻，不把大招、配件或已發射後仍在場上的回旋鏢／地雷納入阻擋條件。

### 彈藥狀態轉移

```text
若 primary_attack_active 為真：
    ammo 不變
    ammo_recovery_timer = 0

否則若 player.alive 且 ammo < ammo_capacity：
    ammo_recovery_timer += delta_time
    當 timer >= recovery_interval：
        ammo += 1
        timer -= recovery_interval

否則若 ammo == ammo_capacity：
    ammo_recovery_timer = 0
```

攻擊解除的第一幀不立即補彈；必須再經過完整 `recovery_interval`。死亡／重生重置彈藥與恢復計時器的行為依既有死亡規則，且不允許死亡狀態在背景回彈。

## 戰鬥動作

### `CombatAction`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `kind` | `str` | `primary_*`、`ultimate_*` 或 `tactical_*` |
| `owner_id` | `int` | 建立動作的玩家 |
| `origin` | `Vector2` | 施放當下位置 |
| `direction` | `Vector2` | 正規化瞄準方向；零向量使用安全預設 |
| `damage` | `int/float` | 單一傷害事件數值 |
| `range` | `float` | 有效距離 |
| `radius` | `float` | 圓形／範圍效果半徑 |
| `duration` | `float` | 效果持續時間 |
| `max_distance` | `float` | 移動效果的最大距離 |
| `projectile_speed` | `float` | 移動效果速度 |
| `metadata` | `dict[str, float \| int \| str]` | `angle`、`pellets`、控制類型等規則資料 |

### 破陣者 action metadata

```text
{
    "angle": 60,
    "pellets": 5,
    "visual_pellets": 5,
    "authoritative_shape": "sector_sweep",
}
```

`pellets` 是每個目標在一次施放中可接受的獨立傷害事件上限，不代表要建立五個可傷害的 projectile。

## 能力效果

### `AbilityEffect`

既有欄位維持原意，新增／明確化下列欄位：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `effect_id` | `int` | 單局唯一識別碼 |
| `kind` | `str` | 規則與渲染的效果類型 |
| `owner_id` | `int` | 效果擁有者 |
| `origin` | `Vector2` | 移動、扇形或脈衝的固定起點 |
| `position` | `Vector2` | 當前位置／掃掠前端 |
| `previous_position` | `Vector2` | 上一幀位置／前端 |
| `direction` | `Vector2` | 移動／扇形方向 |
| `damage` | `int/float` | 單一事件傷害 |
| `radius` | `float` | 範圍或碰撞半徑 |
| `remaining` | `float` | 剩餘壽命 |
| `max_distance` | `float` | 最大作用距離 |
| `projectile_speed` | `float` | 前端移動速度 |
| `distance_travelled` | `float` | 從 origin 起算的距離 |
| `hit_target_ids` | `set[tuple[str, int]]` | 該獨立 projectile／效果已命中的 `(target_kind, target_id)` |
| `metadata` | `dict[str, Any]` | `visual_only`、`pellet_index`、`angle` 等 |

### 效果分類

- **權威傷害／控制**：由 `world.py` 更新並呼叫規則套用生命、控制、護盾或位移。
- **視覺-only**：`metadata["visual_only"] is True`，只更新壽命與位置，絕不呼叫傷害／控制函式。
- **HUD／瞬時 marker**：短壽命且不參與世界碰撞，用於提示蓄力、命中或撤離狀態。

### 破陣者效果集合

一次普攻建立：

1. 一個 `breach_cone` 權威效果：`origin` 固定、`position` 為掃掠前端、60°、200 距離、`pellets=5`。
2. 五個 `breach_pellet` 視覺-only 效果：各自有 `pellet_index`、方向偏移與獨立軌跡；不可產生傷害。

`breach_cone.hit_target_ids` 維持目標識別的集合；每個目標已處理的 pellet index 另以 `metadata["pellet_hits"]` 保存，型別為 `dict[tuple[str, int], set[int]]`。這兩層資料不可混用：前者防止同一個移動效果重複處理目標，後者確保同一目標每次施放最多五顆散射彈事件。

## 扇形命中模型

給定扇形原點 `O`、方向單位向量 `D`、目標中心 `P`、目標半徑 `r`、最大距離 `R`、半角 `a=30°`：

```text
v = P - O
d = |v|
target_angle = acos(clamp(dot(D, normalize(v)), -1, 1))
angle_margin = asin(clamp(r / max(d, epsilon), 0, 1))

inside_range = d <= R + r
inside_angle = d <= epsilon OR target_angle <= a + angle_margin
```

若 `inside_range AND inside_angle` 成立，再以目前掃掠前端 `front` 與上一幀前端 `previous_front` 檢查：

```text
d - r <= front AND d + r >= previous_front
```

通過後，對尚未處理的 pellet index 產生最多五個傷害事件。順序固定、結果可重現；不因渲染幀率或同幀重複 update 而增加事件。

## GUI 設定

| 設定 | 型別 | 預設 | 合法範圍 | 套用位置 |
|---|---|---:|---:|---|
| `GUI_OPACITY_PERCENT` | `int` | 78 | 50～90（含端點） | 選角卡、配件卡、HUD、名單、結果面板、血條背景 |

實際 alpha 為 `round(255 * GUI_OPACITY_PERCENT / 100)`。面板 surface 使用 `pygame.SRCALPHA`；文字、角色、怪物、瞄準線、技能前景與血條填色不共用該 alpha。

## 狀態轉移與不變量

### 破陣者攻擊

```text
ready -> cone_sweeping -> cone_expired
              ├─ each target: 0..5 pellet damage events
              └─ five visual pellet trails expire independently
```

- `origin` 與施放位置固定，不隨玩家後續移動。
- 扇形範圍是唯一傷害來源；視覺-only pellet 不可改變生命。
- 目標進入扇形邊界時依圓形半徑判定，死亡後不再接受有效傷害。

### 普攻與彈藥

```text
idle/recovering -> primary_active -> waiting_full_interval -> recovering
                         └─ ammo count/timer frozen and timer reset
```

- `ammo` 永不超過容量，也不低於零。
- 普攻按住、蓄力或普攻冷卻中的每一幀都不回彈。
- 大招／配件單獨使用不改變 `primary_attack_active`。
- 死亡清除戰鬥優勢；重生後不可沿用死亡前的彈藥恢復計時。
