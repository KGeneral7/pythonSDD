# 資料模型與狀態規則

本功能不新增持久化資料；所有牆、草叢、戰鬥計時與觀看者判定都存在單局 MatchState。模型層維持不依賴 Pygame，渲染層只把世界座標轉成 Pygame 圖形。

## 地形資料

### ObstacleKind

| 值 | 意義 | 碰撞 | 破壞 |
|---|---|---|---|
| THICK_WALL | 不可破壞厚牆 | 阻擋玩家、怪物與路徑型技能 | 永不移除 |
| THIN_WALL | 可破壞薄牆 | 尚未破壞時阻擋玩家、怪物與路徑型技能 | 具資格能力一次有效命中即移除 |

### WorldRect

| 欄位 | 型別 | 規則 |
|---|---|---|
| left | float | 世界座標左邊界 |
| top | float | 世界座標上邊界 |
| width | float | 必須大於 0 |
| height | float | 必須大於 0 |
| right | 導出 float | left + width |
| bottom | 導出 float | top + height |
| center | 導出 Vector2 | 矩形中心 |

WorldRect 只描述幾何，不保存 Pygame 物件。其邊界必須落在 0～WORLD_WIDTH、0～WORLD_HEIGHT 內；碰撞輔助函式會用物件半徑膨脹矩形，以處理圓形角色而非只有中心點。

### ObstacleState

| 欄位 | 型別 | 初始值 | 不變量 |
|---|---|---:|---|
| obstacle_id | int | 固定配置序號 | 同一場比賽內唯一且不重用 |
| kind | ObstacleKind | 固定 | 決定顏色、碰撞與是否可破壞 |
| bounds | WorldRect | 固定 | 同一場比賽內不移動 |
| destroyed | bool | False | 只有 THIN_WALL 可變為 True；厚牆保持 False |

導出狀態：

- solid = not destroyed。
- destructible = kind == THIN_WALL。
- 破壞只改變 destroyed，不從 MatchState.obstacles 移除物件，讓識別與同場狀態可追蹤。
- 已破壞薄牆不再阻擋移動、路徑或目標視線，也不會在同一場重新生成。

### BushState

| 欄位 | 型別 | 初始值 | 不變量 |
|---|---|---:|---|
| bush_id | int | 固定配置序號 | 同一場比賽內唯一且不重用 |
| bounds | WorldRect | 固定 | 同一場比賽內不移動 |
| active | bool | True | 被具資格能力破壞後維持 False |

草叢不屬於固體障礙物：不阻擋玩家、怪物或任何技能路徑。active 只控制畫面是否提供隱藏與是否繪製草叢。

### TerrainHitResult

| 欄位 | 型別 | 說明 |
|---|---|---|
| obstacle | ObstacleState 或 None | 路徑遇到的第一個尚未破壞牆體 |
| distance | float | 從路徑起點到牆前碰撞點的距離 |
| position | Vector2 | 牆前、已扣除移動物件半徑的有效停止點 |
| blocked | bool | 是否應停止/截斷路徑 |
| destroyed | bool | 此次解析是否移除了可破壞薄牆 |

TerrainHitResult 只描述一次查詢結果，不直接改變狀態；破壞輔助函式明確接收允許的 TerrainInteraction 後才修改 ObstacleState 或 BushState。

## 固定地圖配置

config.py 保存不可變的配置資料，terrain.py 負責轉成新物件：

- OBSTACLE_LAYOUT：由牆型、left、top、width、height 組成的 tuple。
- BUSH_LAYOUT：由 left、top、width、height 組成的 tuple。
- 配置採地圖編輯器送出的固定座標，位置固定且每場一致，不要求世界中心水平/垂直鏡像。
- 建立時必須驗證物件完全在世界內；與 SPAWN_POINTS、MONSTER_CAMP_POINTS 或中央 EXTRACTION_ZONE 安全判定區重疊時只產生警示，不得自動刪除已由使用者確認的配置。
- 測試檢查 18 個牆體（12 個厚牆、6 個薄牆）、27 個草叢、兩種牆型、世界邊界，以及 5 筆已確認保留的安全區警示。
- 正式畫面由 `rendering.draw_match` → `draw_world` → `draw_terrain` 逐一繪出這 45 個矩形；每個矩形先以 `match.camera.position` 轉成畫面座標，再依 Pygame surface 裁切，地面/網格之後先畫草叢，再畫牆，攝影機移入世界座標範圍時即可看到對應物件。

建議集中設定值：

| 設定 | 預設 | 用途 |
|---|---:|---|
| THICK_WALL_COLOR | (115, 93, 105) | 厚牆填色，和地面不同 |
| THIN_WALL_COLOR | (212, 143, 62) | 薄牆填色，和厚牆/地面不同 |
| WALL_BORDER_COLOR | (235, 240, 242) | 牆體邊界高亮 |
| WALL_BORDER_WIDTH | 2 | 牆體邊界寬度 |
| THIN_WALL_CRACK_WIDTH | 1 | 薄牆裂紋寬度 |
| THIN_WALL_CRACK_COUNT | 2 | 每面薄牆裂紋數量 |
| BUSH_COLOR | 綠色系 | 草叢填色 |
| BUSH_HIGHLIGHT_COLOR | (144, 211, 116) | 草叢葉片/高光 |
| PLAYER_REGEN_DELAY | 5.0 | 脫離戰鬥等待秒數 |
| PLAYER_REGEN_RATE | 0.10 | 每秒最大生命值比例 |
| TERRAIN_SPAWN_SAFE_RADIUS | 72.0 | 出生點警示判定半徑 |
| TERRAIN_CAMP_SAFE_RADIUS | 94.0 | 怪物區警示判定半徑 |
| TERRAIN_EXTRACTION_SAFE_PADDING | 20.0 | 撤離區警示額外 padding |

## MatchState 擴充

在既有 MatchState 欄位最後增加，避免影響既有 positional 建構：

| 欄位 | 型別 | 說明 |
|---|---|---|
| obstacles | list[ObstacleState] | 本場牆體與其破壞狀態 |
| bushes | list[BushState] | 本場草叢與其破壞狀態 |

create_match 的順序為建立玩家/怪物 → 建立全新障礙物與草叢複本 → 組合 MatchState。GameApplication.restart 仍以重新建立比賽恢復初始地形，不需要額外存檔或清理全域清單。

## PlayerState 擴充

### 戰鬥計時

| 欄位 | 型別 | 初始值 | 語意 |
|---|---|---:|---|
| last_damage_time | float | 0.0 | 距離最近一次有效受擊命中的經過秒數；既有欄位保留此語意 |
| last_attack_time | float | 0.0 | 距離最近一次攻擊動作/持續攻擊活動的經過秒數 |

不變量與操作：

- 兩個計時器不得小於 0。
- update_player_timers 每次以 max(0, delta_time) 增加兩者。
- mark_player_hit 在存活玩家被有效攻擊命中時將 last_damage_time 歸零；敵方控場命中、護盾完全吸收、減傷降為 0 或生命值沒有下降仍算命中。
- mark_player_attack 在攻擊動作成立時將 last_attack_time 歸零；長按吸能光束等持續攻擊每幀維持歸零。
- handle_player_death、respawn_player 與新比賽初始化都將兩者歸零。
- 死亡玩家不能恢復，即使計時器數值已超過 5 秒。

### 草叢位置

玩家是否在草叢內不保存為可變欄位，避免移動後產生過期狀態；由 is_player_in_bush(player, bushes) 以存活玩家中心點是否落入任一 active BushState.bounds 導出。

## CombatAction 與 AbilityEffect 的地形互動

新增 TerrainInteraction 明確描述 action 的地形行為：

| 值 | 適用動作 | 行為 |
|---|---|---|
| BLOCK | 一般移動/技能、破陣者 breach_cone / breach_pellet | 第一面尚未破壞的牆阻擋；草叢忽略 |
| BREAK_THIN_ON_PATH | 明確具備遠程破牆資格的路徑 action | 可移除路徑第一面薄牆，但本次 effect 仍在該牆位置停止；破陣者普攻不使用此政策 |
| BREAK_THIN_IN_AREA | 破陣者爆發 | 移除作用範圍內的薄牆與草叢；厚牆不變 |
| DASH_BREAK_FIRST_THIN | DASH | 移除衝刺路徑第一面薄牆，消耗到牆前的距離後繼續；下一面牆仍阻擋 |

CombatAction 增加 terrain_interaction 欄位，放在既有 metadata 之後並提供 BLOCK 預設，以保留目前 positional 建構相容性。由角色/配件建立動作時設定，不讓 world.py 依傷害大小猜測是否可以破壞。

AbilityEffect 複製 action 的地形互動狀態。只有明確使用遠程破牆政策時，才需要在 metadata 保存施放當下的地形阻擋快照，至少包含 obstacle_id、kind、bounds，以防止同次施放穿透；BLOCK 的破陣者普攻不建立此快照。快照只供該 effect 的目標路徑查詢，不回寫地形；實際 destroyed 狀態仍由 MatchState 保存。

## 移動狀態轉移

狀態流程：

    原位置
      → 依 move_direction 計算預定位置
      → 以半徑膨脹牆體並檢查 X 位移
      → 以已修正 X 的位置檢查 Y 位移
      → 套用世界邊界 clamp_position
      → 新位置

- root 或死亡玩家不進行移動。
- 怪物追擊邏輯保留；只有實際位移改由 move_circle_with_obstacles 解析。
- 撞牆時不尋路，不穿牆；若另一軸可行，沿牆滑動。
- 速度仍使用既有 slow_multiplier 和 delta_time。

### 一般路徑型效果

狀態流程：

    上一幀位置
      → 預定本幀位置
      → first_obstacle_on_segment
      ├─ 沒有牆：移動到預定位置
      └─ 有牆：截斷到牆前、標記 blocked、停止或按 effect 類型返程/落地

sniper_line、sniper_ultimate_line、boomerang、mine、beam、hunter_dash、tactical_control 與 gravity_cage 的直線/飛行段使用此流程。投射物仍使用 previous_position 與 position 的同一條線段，避免高速效果越過窄牆。

## 破牆狀態轉移

### 遠程技能與破牆

1. `breach_cone` 與 `breach_pellet` 使用 `BLOCK`，從施放位置到第一面牆截斷路徑；薄牆不設為 `destroyed=True`，草叢也不受影響。
2. 只有明確使用 `BREAK_THIN_ON_PATH` 的遠程 action 才在建立 effect 時保存尚未破壞牆體快照，移除第一面薄牆後仍以快照阻擋同次傷害，避免穿過新缺口。
3. `breach_burst` 使用 `BREAK_THIN_IN_AREA` 移除範圍內薄牆與草叢，厚牆保持存在；下一次施放讀取更新後的 MatchState。

### DASH

狀態流程：

    剩餘距離 = DASH 最大距離
    目前位置 = 施放位置
    只要剩餘距離 > 0：
        找目前路徑第一面牆
        若沒有牆：前進剩餘距離並結束
        若是厚牆：停在牆前並結束
        若是第一面薄牆：移除薄牆，前進到牆前，扣除已走距離，繼續

草叢在完整 DASH 路徑內移除但不扣除阻擋距離；衝刺特效保存實際移動距離，瞄準預覽使用同一個非變更狀態的解析結果。

## 生命恢復狀態轉移

狀態流程：

    受擊或攻擊
      → last_damage_time = 0 或 last_attack_time = 0
      → 等待
      → 兩個計時器都 >= PLAYER_REGEN_DELAY
      → 恢復中
      → health == max_health
      → 滿血

恢復函式：

    若玩家死亡或 health >= max_health：
        不恢復
    若 last_damage_time < 5 或 last_attack_time < 5：
        不恢復
    否則：
        health = min(max_health,
                     health + max_health * 0.10 * max(0, delta_time))

update_world 的本幀順序必須為：

1. 更新時間、冷卻與既有玩家生命週期。
2. 處理人類輸入、建立動作並標記攻擊活動。
3. 更新技能效果、投射物、傷害、護盾與控制。
4. 更新怪物移動與接觸傷害。
5. 呼叫 regenerate_player_health；因此同幀命中先重置計時，不會同幀回血。
6. 回復彈藥、移除死亡效果、更新撤離與勝負。
7. 更新鏡頭。

普通 DASH 與 SHIELD 不呼叫 mark_player_attack；其餘具傷害或敵方控場效果的 action 在成立時呼叫。攻擊失敗（冷卻、資源不足而沒有建立 action）不重置攻擊計時。

## 觀看者與草叢狀態

可見性是渲染時的導出值：

    hidden = player.alive AND is_player_in_bush(player, match.bushes)
    visible = NOT hidden OR viewer_id == player.player_id

當 visible=False 時，draw_world 與 _draw_player_roster 都不繪製該玩家的角色、編號、生命值、狀態或瞄準線；草叢仍照常繪製。viewer_id=0 是 draw_match 的相容預設，保證人類玩家在自己的畫面永遠可見。

可見性不傳入 _target_entries、apply_damage、update_monsters 或技能碰撞函式，因此不會改變目標、傷害、碰撞、撤離或怪物仇恨。玩家移動離開 bounds，或能力將 BushState.active 設為 False 後，下一次繪製立即恢復可見。

## 模組責任

| 模組 | 責任 |
|---|---|
| config.py | 固定地形 tuple、牆/草叢顏色、恢復常數 |
| models.py | WorldRect、ObstacleKind、ObstacleState、BushState、TerrainHitResult、玩家/動作欄位 |
| terrain.py | 地形建立、幾何查詢、移動/路徑解析、破壞與草叢判定 |
| characters.py | 為破陣者終極技能與 DASH 設定破壞型 TerrainInteraction；破陣者主要技能與其他能力使用 BLOCK |
| rules.py | 受擊/攻擊計時、恢復公式、死亡/重生重置 |
| world.py | 建立單局地形、套用生物/技能碰撞、處理破壞與更新順序 |
| aiming.py | 使用不修改狀態的地形端點預覽，保持瞄準線和實際路徑一致 |
| rendering.py | 依固定配置繪製全部牆/草叢、依 viewer_id 隱藏玩家與玩家名單資訊；地形層位於角色與技能效果之前 |
| tests/ | 純幾何、世界整合、恢復、可見性、渲染與既有功能回歸 |

## 主要不變量

- 所有活著的玩家/怪物位置都在世界邊界內，且不與尚未破壞牆體重疊。
- 厚牆永不 destroyed；薄牆/草叢在同場比賽中只從有效變為無效，不會自行恢復。
- health 維持在 0～max_health；恢復不會超過上限。
- 玩家死亡期間不產生技能傷害、移動或生命恢復。
- 草叢只改變畫面可見性，不改變目標選取、碰撞、傷害與控制。
- 既有玩家、怪物、技能 effect 與撤離狀態的識別字仍維持穩定。

## 實作核對結果

- `MatchState` 已在每場建立 18 個牆體與 27 個草叢的獨立狀態；新局會重新建立，破壞狀態不跨局保留。
- `draw_match` 已接入地形繪製與 `viewer_id` 過濾；牆體依相機座標繪製在正式畫面，草叢內玩家只對其他觀看者隱藏。
- `update_world` 已接入移動/技能地形解析與恢復順序；完整自動化測試為 162/162 通過。
