# 資料模型：小怪動態尋路與營地遊蕩

## 模型範圍

本功能只增加小怪在單場 `MatchState` 中的運行狀態，不新增存檔或網路資料。既有 `MonsterState.target_player_id` 仍是目標玩家的唯一引用；新增欄位保存行為、路徑快取、牆體版本與遊蕩進度。

## 新增列舉

### `MonsterBehavior`

位於 `pvpve_escape/models.py`，值固定為：

| 值 | 意義 | 可移動目的地 | 可攻擊 |
|---|---|---|---|
| `WANDER` | 小怪在所屬營地附近警戒與遊蕩 | 營地內安全遊蕩點 | 否 |
| `CHASE` | 小怪保有合法的存活玩家目標 | 目標位置或砲台蟲的安全偏好距離 | 是，依既有怪物類型規則 |
| `RETURN` | 目標失效後回到所屬營地 | `MONSTER_CAMP_POINTS[spawn_zone_id]` | 否 |

## `MonsterState` 新增欄位

現有欄位保持原意；以下欄位加入 `MonsterState`。預設值要讓新建立的存活小怪從 `WANDER` 開始，不得帶有目標或舊路徑。

| 欄位 | 型別／預設 | 用途與不變條件 |
|---|---|---|
| `behavior` | `MonsterBehavior`／`WANDER` | 當前行為狀態。非 `CHASE` 時 `target_player_id` 必須為 `None`。 |
| `navigation_path` | `list[Vector2]`／空清單 | 由目前位置前往當前目的地的有序安全節點；只保存通過目前牆體檢查的節點。 |
| `navigation_goal` | `Vector2 | None`／`None` | 建立 `navigation_path` 時的目的地；目的地格改變時路徑失效。使用副本，避免引用玩家向量後無法判斷變化。 |
| `navigation_obstacle_signature` | `tuple[tuple[int, ObstacleKind, WorldRect], ...]`／空 tuple | 最近一次尋路使用的固體牆快照。快照不同時必須清除路徑並立即重算。 |
| `navigation_repath_timer` | `float`／`0.0` | 距離下一次允許的一般路徑重算剩餘時間；牆體簽章改變時直接歸零。 |
| `wander_target` | `Vector2 | None`／`None` | 目前選定的營地遊蕩點；只在 `WANDER` 使用，抵達後清除並開始停留。 |
| `wander_index` | `int`／`0` | 產生可重現候選點的序號；每次選擇下一個遊蕩點遞增，不因短暫找不到路而重置。 |
| `wander_pause_timer` | `float`／`0.0` | 抵達遊蕩點後的停留時間；倒數期間不建立下一段遊蕩移動。 |

`spawn_position` 和 `spawn_zone_id` 仍是返營與重生的來源資料。營地中心由 `spawn_zone_id` 索引設定，不另存一份可能過期的座標。

## 導航資料

### 網格節點

- 世界尺寸由 `config.WORLD_WIDTH`、`config.WORLD_HEIGHT` 決定，格寬由 `config.MONSTER_NAVIGATION_CELL_SIZE` 決定，目前為 40px。
- 節點以整數 `(column, row)` 識別，計算和測試使用格中心 `Vector2`；世界邊界必須扣除目前小怪半徑與 `config.MONSTER_NAVIGATION_CLEARANCE`。
- 佔用判斷只讀取 `obstacle.solid` 的牆體，並以牆矩形膨脹 `monster.radius + clearance` 後檢查格中心；此矩形安全區與既有軸向移動碰撞一致，草叢不是阻擋物。
- 路徑鄰接使用上下左右與四個斜角。斜角移動除了檢查終點格，還要檢查兩個正交格，避免貼牆切角；不對每條格點鄰接邊重複做完整線段掃掠，以避免多怪物同時尋路造成更新卡頓。

### 路徑節點

`navigation_path` 的第一個節點是怪物下一個應接近的安全點，而不是已經走過的起點。每幀最多前進 `move_speed * delta_time * slow_multiplier`；若距離小於 `config.MONSTER_NAVIGATION_NODE_ARRIVAL_TOLERANCE`（8px）則移除該節點。實際位移仍交給 `move_circle_with_obstacles`，因此 A* 計算錯誤也不會授權穿牆。

精確線段安全檢查只放在實際起點到第一節點、必要的起點格中心備援，以及精確安全目標的最後一段；其餘中間節點由膨脹牆體的安全格與 no-corner-cut 規則限制，逐幀碰撞函式仍是最後一道保護。

### 速度與出生點配置

- `MonsterDefinition.move_speed` 保存三類怪物的最終移速：追獵獸為玩家基礎移速的 90%，砲台蟲與重裝巨獸以各自原始移速乘上追獵獸的相對增幅。
- `config.MONSTER_WANDER_RADIUS=700` 是遊蕩候選點的最大營地半徑；候選仍須通過世界邊界與牆體安全檢查。
- 玩家 0 號出生來源是 `config.SPAWN_POINTS[0]`；建立比賽時需驗證它距每個營地中心與 `create_monsters()` 的實際怪物出生點至少 200px。

## 目標資料與合法性

`target_player_id` 指向 `MatchState.players` 中的玩家 ID，不保存玩家物件引用。目標選擇規則如下：

1. 只考慮 `alive is True` 的玩家。
2. 新取得目標須滿足 `monster.position.distance_to(player.position) <= MONSTER_AGGRO_RADIUS`，目前常數為 520px。
3. 新取得目標的 `first_obstacle_on_segment(monster.position, player.position, match.obstacles, 0.0)` 不得回報未摧毀牆體；這個視線檢查只影響「取得」，不會讓已鎖定目標因短暫被牆遮住而立即消失。
4. 多個合法玩家依 `(distance, player_id)` 排序，確定選最近者且結果可重現。
5. 已鎖定目標死亡或距離嚴格大於 520px 時，清除目標和追擊路徑並轉為 `RETURN`；在 `WANDER`／`RETURN` 不保留失效目標。

規格所稱的「取得目標時距離／視線」是第 2、3 項的判定條件，不是需要保存的歷史欄位；鎖定後只保存 `target_player_id`，並在每次更新重新驗證存活與距離。

## 行為狀態轉換

| 目前狀態 | 條件 | 下一狀態 | 必須執行的清理／建立 |
|---|---|---|---|
| 任一存活狀態 | 重生完成 | `WANDER` | 位置回 `spawn_position`；清除目標、路徑、遊蕩點、停留計時與舊牆體簽章；攻擊計時器歸零。 |
| `WANDER` | 存活玩家符合 520px 且無牆視線 | `CHASE` | 設定最近玩家 ID；清除 `wander_target`、`wander_pause_timer` 與舊遊蕩路徑。 |
| `WANDER` | 沒有合法目標且位置不在營地 700px 遊蕩範圍內 | `RETURN` | 清除遊蕩點和停留計時；目的地改為所屬營地中心。 |
| `WANDER` | 沒有合法目標且位於營地範圍 | `WANDER` | 保留／產生安全遊蕩點；不攻擊。 |
| `CHASE` | 目標仍存活且距離 `<= 520px` | `CHASE` | 目標保留；牆體遮住時改用 A*，不重置為遊蕩。 |
| `CHASE` | 目標死亡或距離 `> 520px` | `RETURN` | `target_player_id=None`；清除追擊路徑與目標副本；不攻擊。 |
| `RETURN` | 追途中有新的合法玩家 | `CHASE` | 設定最近合法玩家；清除返營目的地和遊蕩狀態。 |
| `RETURN` | 到達營地中心的 `MONSTER_CAMP_ARRIVAL_RADIUS`（64px）範圍 | `WANDER` | 清除返營路徑；產生下一個安全遊蕩點；不攻擊。 |
| 任一移動狀態 | `snapshot_obstacles` 與保存簽章不同 | 原行為狀態 | 先清除路徑／目的地並令重算計時器為 0，再使用最新牆體重新尋路。 |

在一次 `update_monsters` 呼叫中，每隻怪物最多執行一次狀態轉換；距離邊界使用明確的 `<=` 取得／保留和 `>` 解除規則，避免同一幀往返切換。

## 更新交易順序

每隻小怪的更新依下列順序，確保輸入、狀態與輸出可追蹤：

1. 更新慢速、定身、攻擊與重生計時器；死亡中的小怪不尋路。
2. 若完成重生，執行完整狀態重設並進入下一隻。
3. 取得本次更新共用的固體牆快照；比對並先使舊路徑失效。
4. 依目標合法性決定 `WANDER`、`CHASE` 或 `RETURN`，設定本次目的地。
5. 若目的地存在且路徑空、目的地格改變、牆體變動或重算計時器到期，呼叫 `find_grid_path`；若回傳 `None`，保持目前安全位置，將重試計時器設為 `config.MONSTER_NAVIGATION_RETRY_INTERVAL`（0.25 秒）後重試。砲台蟲的偏好距離點若落在牆體或導航 clearance，或偏好點安全但目前沒有可達路徑，先改用目標位置作暫時終點；若首段起點只在額外 clearance 內，允許經實體半徑掃掠確認後朝外離開。
6. 沿下一個安全節點移動，經 `move_circle_with_obstacles` 與 `clamp_position`；更新 `aim_direction` 只反映實際移動方向。
7. 只有 `CHASE` 使用既有的攻擊距離與攻擊計時器；`WANDER` 和 `RETURN` 不造成傷害、不發射投射物。

## 驗證不變量

- 活著的小怪位置始終位於世界邊界內縮區，且不與任何 `solid` 牆體重疊。
- 路徑中的每個節點與相鄰段落都符合目前小怪半徑和 clearance；沒有路徑時不得以直接向量強行移動。
- `WANDER` 的目標點距營地中心不超過 700px；`RETURN` 的目的地永遠由 `spawn_zone_id` 取得，距中心 64px 內才轉為 `WANDER`。
- 非重生單次更新的位移不得超過 `move_speed * delta_time * slow_multiplier + config.TERRAIN_GEOMETRY_EPSILON`；重生回出生點的位移不列入跳躍判定。
- `CHASE` 以外 `target_player_id` 為 `None`，且不會呼叫接觸傷害或 `_spawn_monster_projectile`。
- 牆體簽章包含所有目前固體牆；薄牆摧毀後簽章必定改變，厚牆未摧毀時仍出現在簽章和佔用網格中。
- 玩家、怪物或牆體資料被測試修改後，下一次更新只讀取目前 `MatchState`，不使用建立比賽時的靜態障礙副本。

## 砲台蟲牆角修正對照（2026-08-28）

- `MonsterState` 不新增欄位；偏好位置是否可用由每次 `CHASE` 更新讀取目前 `match.obstacles` 判定。
- 偏好位置安全且有路徑時維持原本 300px 距離策略；偏好位置落入牆體、`radius + clearance` 安全區，或 A* 找不到可達路徑時，使用目標位置觸發 A* 繞牆／離開封閉區，避免最近安全格成為永久終點。
- 導航 clearance 是規劃用保守邊界，不等於實際碰撞邊界。怪物若已由 `move_circle_with_obstacles` 合法停在 clearance 內，首段只能向外離開，且必須通過實體半徑的 `first_obstacle_on_segment` 檢查。
- 回歸測試覆蓋厚牆內偏好點、多格長牆轉角，以及安全偏好點被四面厚牆封閉；三種情況都不允許牆體重疊或超過 1 秒沒有有效位移。
