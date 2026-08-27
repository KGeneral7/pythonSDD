# 資料模型：瞄準線、飛行物速度與角色戰鬥平衡

**功能**：`002-aim-balance-projectiles`

本設計延伸既有 `pvpve_escape/models.py` 的資料類別。資料只保存世界狀態與跨模組需要的值；輸入事件由 `controllers.py` 轉換，碰撞與傷害由 `world.py`／`rules.py` 更新，Pygame 繪製不直接修改資料。

## 1. 瞄準預覽

### `AimGuide`

短生命週期、只讀的世界座標幾何資料；每次繪製依目前玩家方向與按住中的技能重新建立，不保存到 `MatchState`。

| 欄位 | 型別 | 說明與限制 |
|---|---|---|
| `owner_id` | `int` | 預覽所屬玩家；本機首版為 0 |
| `ability_slot` | `str` | `primary`、`ultimate` 或 `tactical` |
| `shape` | `str` | `wedge`、`line`、`path`、`circle` 或 `beam` |
| `origin` | `Vector2` | 預覽起點，使用玩家或技能效果的世界座標 |
| `direction` | `Vector2` | 正規化瞄準方向；零向量使用玩家上一個有效方向 |
| `end` | `Vector2` | 線段、路徑或落點的終點；必須被限制在世界矩形內 |
| `range` | `float` | 最大距離；近戰／範圍效果可為 0 |
| `radius` | `float` | 圓形控制或爆發半徑；非圓形為 0 |
| `angle_degrees` | `float` | 扇形或弧形角度；非角度形狀為 0 |
| `path_points` | `tuple[Vector2, ...]` | 追獵者去回路徑或多段提示；一般線段可為空 |
| `valid` | `bool` | 資源／冷卻允許施放時為 `True`；無效時仍顯示固定的無效色弱化預覽，放開時不得施放 |

### 預覽幾何規則

- 破陣者：`shape=wedge`，射程 200、角度 60 度，`path_points` 保存五條散射方向的端點。
- 狙擊者：`shape=line`，射程 1000，`end = origin + direction × range`；不鎖定目標。
- 守衛者：`shape=wedge`，射程 125、角度 100 度，代表即時近戰弧形。
- 追獵者：`shape=path`，去程最遠 340；回程端點依施放後玩家位置更新。
- 控場者普攻：`shape=circle` 搭配投射方向，落點最遠 460、地雷落地控制半徑 100；大招半徑 190。
- 控場配件：`shape=circle`，控制圈中心為受世界邊界限制的預計落點、半徑 100；它是 `projectile_speed=0` 的即時範圍效果，放開時立即建立，不進入地雷飛行狀態。
- 吸能者：`shape=beam`，射程 280，表示按住期間持續引導，不表示飛行物。
- 大招與配件使用相同的 `AimGuide` 資料，依動作形狀顯示爆發圈、突進線、護盾圈或控制圈。
- 預覽是建議幾何，不建立命中事件，也不保證目標會留在路徑上。

## 2. 輸入狀態

### `InputState`

每幀由 `HumanController.collect` 產生，不保存到比賽；`HumanController` 另外保存上一幀按鍵狀態以計算邊緣。

| 欄位 | 型別 | 說明與限制 |
|---|---|---|
| `move_direction` | `Vector2` | WASD 正規化方向 |
| `aim_direction` | `Vector2` | 滑鼠換算的世界方向 |
| `primary_pressed` | `bool` | 非吸能者普攻按下邊緣或單元測試快速點按旗標；吸能者不得以此旗標建立引導 |
| `primary_held` | `bool` | 左鍵本幀持續按住 |
| `primary_released` | `bool` | 左鍵由按住轉為放開 |
| `ultimate_pressed` | `bool` | 右鍵按下邊緣或快速點按旗標 |
| `ultimate_held` | `bool` | 右鍵本幀持續按住 |
| `ultimate_released` | `bool` | 右鍵由按住轉為放開 |
| `tactical_pressed` | `bool` | Space 按下邊緣或快速點按旗標 |
| `tactical_held` | `bool` | Space 本幀持續按住 |
| `tactical_released` | `bool` | Space 由按住轉為放開 |
| `focus_lost` | `bool` | 視窗失去焦點；所有按住狀態視為結束 |

### 輸入狀態轉換

```text
IDLE ── pressed ──► HELD / PREVIEWING ── released ──► CAST ONCE ──► IDLE
  │                         │
  └──── focus_lost / death ┘
                 └──────────► CANCELLED ─────────────► IDLE

吸能者普攻：IDLE ── pressed/held（非快速點按）──► CHANNELING ── released ──► STOPPED ──► IDLE
```

- 非引導技能在 `released` 時才建立一次動作；若直接收到沒有持續按住的快速旗標，視為同一幀的按下／放開。
- 吸能者在 `CHANNELING` 每 0.15 秒作用；放開、死亡或失焦會立即停止，快速點按旗標不建立引導。
- 失焦不得在恢復焦點後補發攻擊；死亡／重生不得延續狙擊蓄力或其他預覽。

## 3. 角色定義

### `CharacterDefinition`

既有角色資料新增 `base_health` 與 `projectile_speed`，並將被動條件閾值與技能所需數值集中在 `parameters`。`projectile_speed=0` 只用於即時近戰、範圍效果或持續引導。

| 角色 | `base_health` | 普攻資料 | `primary_range` | `projectile_speed` | 被動／大招基準 |
|---|---:|---|---:|---:|---|
| 破陣者 | 110 | 每顆 7 傷害、5 顆、60 度散射；距離不超過 200 時 +20% | 200 | 900 | 半徑 190、傷害 55、擊退 |
| 狙擊者 | 80 | 50 傷害；距離至少 450 時 +20%；保留最多 0.6 秒蓄力 | 1000 | 1400 | 傷害 90、射程 1100、穿透 |
| 守衛者 | 115 | 30 傷害、100 度近戰弧形 | 125 | 0 | 生命被動有效 138；4 秒減傷 70% |
| 追獵者 | 95 | 24 傷害回旋飛刃 | 340 | 520 | 突進 360、路徑傷害 50 |
| 控場者 | 90 | 20 傷害地雷；落地半徑 100 | 460 | 650 | 半徑 190、減速 70%、定身 0.75 秒、持續 3 秒 |
| 吸能者 | 105 | 每 0.15 秒 6 傷害，最多引導 1.2 秒 | 280 | 0 | 半徑 220、傷害 60、治療比例 50% |

### 角色不變條件

- 普攻傷害先套用 `1 + 0.03 × upgrade_stacks`，再套用角色被動；有效傷害才增加大招能量。
- 守衛者 `max_health = 115 × 1.2 = 138`（未計死亡前怪物強化）；其他角色使用表中的基準生命。
- 破陣者近距離門檻 200；狙擊者遠距離門檻 450；控場者控制持續時間仍套用 +50%；吸能者對怪物能量仍為 +25%；追獵者移速仍為 +15%。
- 普攻彈匣容量、補彈間隔、戰術配件冷卻與中央撤離規則沿用原規格，除非後續規格另行變更。

## 4. 戰鬥動作

### `CombatAction`

既有一次施放的描述資料，新增 `projectile_speed`；由 `characters.py` 建立，交由 `world.py` 套用。

| 欄位 | 型別 | 說明與限制 |
|---|---|---|
| `kind` | `str` | `breach_cone`（一次扇形施放）、`sniper_line`、`boomerang`、`mine`、`tactical_control` 或既有即時效果類型；`breach_pellet` 僅用於展開後的 `AbilityEffect` |
| `owner_id` | `int` | 施放玩家 |
| `origin` | `Vector2` | 世界座標起點；地雷起點仍須由玩家位置與瞄準方向決定 |
| `direction` | `Vector2` | 施放時快照的正規化方向 |
| `damage` | `float` | 基準傷害，實際值由規則套用被動與強化 |
| `range` | `float` | 最大射程 |
| `radius` | `float` | 範圍效果半徑 |
| `duration` | `float` | 持續效果或地雷存活時間 |
| `max_distance` | `float` | 飛行或突進最大距離 |
| `projectile_speed` | `float` | 飛行物速度；非飛行效果為 0 |
| `metadata` | `dict` | 顆數、散射角、蓄力、擊退、穿透等動作專屬值 |

### 動作建立規則

- 非吸能者普攻、所有角色大招與戰術配件在有效放開時建立動作；`create_primary_action` 只在成功建立時消耗彈藥與啟動冷卻，吸能者普攻改由引導狀態處理。
- 破陣者以 `CombatAction.kind=breach_cone` 表示一次普攻，再展開為 5 個 `AbilityEffect.kind=breach_pellet` 的獨立飛行效果，而不是建立一個施放即傷害的扇形事件。
- 狙擊者使用施放時方向與蓄力值建立一顆速度 1400 的子彈；命中後不再重新尋找移動中的目標。
- 追獵者使用速度 520 的去回飛刃；去程與回程的路徑狀態分開維護。
- 控場者普攻使用速度 650 的地雷；到達落點前 `armed=False`，到達後 `armed=True`。
- 控場配件使用 `kind=tactical_control` 的即時範圍效果，`projectile_speed=0`，其中心直接取有效預覽落點；守衛者、吸能者、大招範圍、盾與突進依原本效果種類建立，不虛構飛行速度。

## 5. 飛行效果

### `AbilityEffect`

既有短生命週期效果新增或整理為顯式飛行狀態。非飛行效果仍可使用同一資料類別，並將 `projectile_speed` 保持為 0。

| 欄位 | 型別 | 說明與限制 |
|---|---|---|
| `effect_id` | `int` | 單局效果唯一識別字 |
| `kind` | `str` | `breach_pellet`、`sniper_line`、`boomerang`、`mine`、`tactical_control` 或既有效果種類 |
| `owner_id` | `int` | 來源玩家 |
| `position` | `Vector2` | 目前飛行頭端、效果中心或命中位置 |
| `previous_position` | `Vector2` | 本次更新前位置，供繪製與線段碰撞共用 |
| `direction` | `Vector2` | 當前移動或效果方向 |
| `damage` | `float` | 基準傷害 |
| `radius` | `float` | 投射物或範圍半徑 |
| `remaining` | `float` | 效果剩餘時間 |
| `max_distance` | `float` | 可飛行／返回的最大距離 |
| `projectile_speed` | `float` | 世界單位／秒；非飛行為 0 |
| `distance_travelled` | `float` | 去程累積距離 |
| `returning` | `bool` | 回旋飛刃是否進入回程 |
| `armed` | `bool` | 地雷是否已抵達落點並啟用 |
| `impact_position` | `Vector2 \| None` | 實際命中或阻擋位置；命中後固定 |
| `impact_status` | `str` | `命中`、`護盾`、`免傷`、`無效` 或空字串 |
| `hit_target_ids` | `set[tuple[str, int]]` | 避免同一飛行段重複命中 |
| `metadata` | `dict` | 對外繪製文字與效果專屬資料 |

**速度欄位遷移**：`projectile_speed` 是三個資料類別的唯一執行期速度來源；既有 `AbilityEffect.speed`、`metadata["speed"]` 或同義欄位必須在建立資料時轉換後移除，後續更新、碰撞、繪製與測試不得讀取舊欄位。

### 飛行效果狀態

```text
SPAWNED ── update(projectile_speed × dt) ──► FLYING ── path intersects target ──► IMPACTED
   │                                  │                                      │
   └──── max distance ───────────────┴──── remaining <= 0 ───────────────► EXPIRED

mine: FLYING ── reach landing point ──► ARMED ── target enters radius ──► TRIGGERED
boomerang: FLYING(outbound) ── reach max distance ──► FLYING(returning)
```

- 每次飛行更新先將 `previous_position = position`，再移動到 `position`；繪製的本幀線段與碰撞使用同一組座標。
- 碰撞候選依線段投影距離排序；狙擊者命中第一個候選後保存 `impact_position`、`impact_status` 與有效傷害，不再跟著目標位置更新。
- `target_radius + effect.radius` 是碰撞帶；高速物件跨過目標仍會命中。
- 護盾、免傷、目標死亡等狀態仍建立實際碰撞結果，但 `effective_damage` 可為 0；畫面提示必須使用 `impact_status`。
- 地雷 `armed=False` 時不得建立傷害、控制或能量事件；落地後的控制只對觸發當下仍存活的目標作用。

## 6. 怪物資料

### `MonsterState`

沿用原欄位，僅調整基準值：

| 欄位 | 新基準 | 驗證規則 |
|---|---:|---|
| `radius` | 16 | 位置夾制與玩家碰撞使用相同半徑 |
| `max_health`／`health` | 85 | 生命介於 0 與最大值；死亡後等待重生 |
| `move_speed` | 95 | 追擊速度再乘當前減速倍率 |
| `attack_timer` | 0.8 秒間隔 | 接觸玩家時造成 12 傷害 |
| `respawn_timer` | 6 秒 | 重生回原生成點並清除控制與最後傷害來源 |
| 每區數量 | 3 | 四個生成區共 12 隻 |

- 最後一筆有效玩家傷害仍決定怪物強化歸屬；怪物死亡後不保留控制、追擊與最後傷害狀態。
- 怪物受到控場時仍可顯示減速／定身狀態，這些狀態不改變本次新增的基準值。

## 7. 關係與資料流

```text
InputState ──► world.update_match ──► CombatAction ──► AbilityEffect
     │                                      │               │
     └────────► AimGuide（只讀預覽）         └───────────────┤
                                                             ▼
                                              DamageEvent ──► PlayerState / MonsterState
                                                             │
                                                             ▼
                                                   MatchState 勝負／撤離
```

- `PlayerState` 參照一個 `CharacterDefinition` 與一個 `TacticalDefinition`；定義資料不保存單局生命、彈藥或冷卻。
- `CombatAction` 是施放當下的快照；`AbilityEffect` 是需要跨幀更新的效果；`DamageEvent` 是唯一的傷害／能量／最後一擊輸入。
- `AimGuide` 不反向修改 `CombatAction` 或 `AbilityEffect`，但使用相同的角色射程、半徑、角度與速度資料建立預覽。
- `MatchState.effects` 保存本局所有效果；玩家死亡時由世界更新移除其持續效果，既有死亡重置規則清除強化、能量與撤離進度。

## 8. 不變條件

- 所有位置與方向使用世界座標；玩家、怪物、地雷落點、飛行物與瞄準端點不得超出世界矩形。
- `projectile_speed > 0` 只允許出現在可飛行效果；守衛者近戰與吸能者光束速度為 0。
- 非引導技能按住預覽不產生傷害／控制／位移／資源扣除；一次放開最多產生一次動作。吸能者普攻是唯一例外，按住期間依 0.15 秒引導作用，放開／死亡／失焦立即停止。
- 有效傷害、護盾吸收、免傷與無效碰撞均透過同一傷害事件回饋，不以單獨圖像座標宣告命中。
- 既有 `upgrade_stacks` 仍限制 0～10；死亡後生命強化、大招能量與撤離進度清除，5 秒後以角色基準生命重生。
- 撤離區仍於剩餘 30 秒啟用；每名玩家獨立連續累積 10 秒，多人同區仍繼續，離開者只清除自己的進度。
