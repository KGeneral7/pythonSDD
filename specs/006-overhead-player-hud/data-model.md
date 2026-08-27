# 資料模型：玩家頭頂 HUD 與個人戰鬥資訊

**功能識別字**：`006-overhead-player-hud`
**模型策略**：沿用既有 `PlayerState`；新增的是渲染層的衍生投影，不是持久化或同步資料。

## 既有來源資料

| 來源 | 欄位 | 顯示用途 | 是否對其他玩家顯示 |
|---|---|---|---|
| `PlayerState` | `player_id`、角色名稱 | 玩家識別列 | 是 |
| `PlayerState` | `health`、`max_health` | 生命條與生命數值 | 是 |
| `PlayerState` | `ammo`、`ammo_capacity` | 彈藥分段與數值 | 否，僅本機玩家 |
| `PlayerState` | `tactical_cooldown`、配件定義 | 配件可用/冷卻圓圈 | 否，僅本機玩家 |
| `PlayerState` | `ultimate_energy` | 大招百分比 | 否，僅本機玩家 |
| `PlayerState` | `upgrade_stacks` | 強化層數 | 否，僅本機玩家 |
| `PlayerState` | `status`、`death_timer` | 死亡時的生命、配件冷卻生命週期與本機中央倒數 | 生命部分是；倒數與配件狀態否 |
| `PlayerState` | `position` | 將世界座標投影到玩家頭上 | 不適用 |

欄位的實際命名與型別以 `pvpve_escape/models.py` 為準；本文件只定義本功能如何消費這些欄位，不要求重新命名或搬移資料。

## 衍生顯示模型

實作上可使用區域變數或小型私有結構表達以下投影；不要求新增 `models.py` 的公開 dataclass。

### `OverheadDisplayState`

| 欄位 | 型別/範圍 | 來源或規則 | 不變量 |
|---|---|---|---|
| `screen_position` | Pygame 2D 座標 | `world_to_screen(player.position, camera.position)` | 每幀由最新位置計算，不保存舊螢幕座標 |
| `player_label` | 字串 | 玩家編號與角色名稱 | 對所有可見玩家存在 |
| `health` | 整數 | `clamp(player.health, 0, max_health)` | 不低於 0、不高於 `max_health` |
| `max_health` | 正整數 | `player.max_health` | 大於 0 |
| `show_private_info` | 布林值 | `player.player_id == viewer_id`（目前 `viewer_id=0`） | 只有目前觀察者自己的玩家為真 |
| `ammo` | 整數 | `clamp(player.ammo, 0, ammo_capacity)` | 只在 `show_private_info` 為真時消費 |
| `ammo_capacity` | 正整數 | 角色彈匣容量 | 分段數量固定，避免狀態更新時跳動布局 |
| `gadget_ready` | 布林值 | 配件冷卻完成且玩家存活 | 可用=藍色；否則=灰色 |
| `ultimate_percent` | 整數 0–100 | `clamp(player.ultimate_energy, 0, 100)` | 只在 `show_private_info` 為真時顯示 |
| `upgrade_stacks` | 整數 0 以上 | `player.upgrade_stacks` | 只在 `show_private_info` 為真時顯示 |
| `respawn_countdown` | 非負秒數 | 本機玩家死亡時的 `death_timer`；大於 0 才繪製中央倒數 | 只對目前觀看者自己的死亡狀態顯示，重生後消失 |

此投影不會複製或修改 `PlayerState`；繪製時讀取同一幀的狀態即可，避免顯示與戰鬥更新之間出現第二份可過期資料。

## 可見性規則

| 查看對象 | 顯示內容 | 明確隱藏內容 |
|---|---|---|
| 本機玩家（`player.player_id == viewer_id`；目前 `viewer_id=0`） | 名稱/編號、生命條/數值、彈藥、配件圓圈、大招百分比、強化層數；死亡時另顯示畫面中央倒數 | 無 |
| 其他存活玩家 | 名稱/編號、生命條/數值 | 彈藥、配件顏色、大招百分比、強化層數、死亡倒數 |
| 其他死亡玩家 | 名稱/編號、空生命條/0 生命 | 同上；不得因死亡而顯示私有資源 |
| 選角頁或結果頁 | 選角資訊/結果資訊 | 戰鬥中的頭頂資源；不建立玩家頭頂覆蓋層 |

玩家的「名稱與編號」沿用現有標籤組合；本功能不新增可編輯暱稱資料，也不把其他玩家的資源轉換成模糊或摘要資訊。`viewer_id` 沿用既有 `draw_world()`/`draw_hud()` 的參數，單機流程預設為 0。

## 狀態轉換與顯示結果

| 觸發事件 | 來源狀態變化 | 下一幀應顯示 |
|---|---|---|
| 發射主要攻擊 | `ammo` 減少、可能開始恢復計時 | 本機彈藥分段與數值立即減少；其他玩家仍不顯示彈藥 |
| 彈藥恢復 | `ammo` 增加至容量 | 本機分段依序填回，滿彈不超過容量 |
| 使用配件 | `tactical_cooldown` 進入冷卻 | 本機圓圈變灰；玩家死亡也維持灰色 |
| 配件冷卻完成 | `tactical_cooldown` 歸零 | 本機圓圈變藍 |
| 累積或消耗大招能量 | `ultimate_energy` 改變 | 本機顯示夾取後的整數百分比；不顯示給其他玩家 |
| 取得或消耗強化 | `upgrade_stacks` 改變 | 本機顯示最新層數；不顯示給其他玩家 |
| 使用配件後死亡 | `tactical_cooldown` 保留，死亡期間不倒數 | 本機圓圈維持灰色；重生後才繼續倒數，其他玩家仍不顯示配件狀態 |
| 受傷/死亡/復活 | `health`、`status`、`death_timer` 改變 | 所有人看到生命更新；只有本機看到自己的私有列與中央死亡倒數，重生後倒數消失 |
| 移動或鏡頭追蹤 | `position` 或 `camera.position` 改變 | 所有可見覆蓋層重新由世界座標投影，保持在對應玩家上方 |

## 排版不變量

- 頭頂資訊區塊的最大寬度為 240 像素，視窗左右至少保留 8 像素邊界。
- 身份文字超過區塊可用寬度時以省略號截斷；截斷不改變玩家編號與資訊區塊的所屬關係。
- 公開列與本機私有列採固定垂直順序；多名玩家靠近時不把任何區塊重新放到螢幕固定角落。

## 邊界條件

- `max_health`、`ammo_capacity` 為有效正值時才繪製比例與分段；異常值需以安全下限處理，不應使整個畫面繪製失敗。
- 生命、彈藥與大招百分比在顯示前夾取到合法範圍；顯示不得因暫時的更新順序出現負數或超過上限的文字。
- 玩家位於視窗邊緣時，顯示列可做螢幕範圍內的有限夾取，但仍須維持世界玩家與覆蓋層的一對一關係。
- 玩家死亡後不保留上一幀的配件藍色狀態；若死亡與冷卻資料同時存在，以灰色為準。
- 本機死亡倒數只在 `death_timer > 0` 時顯示，必須以大型字型置中；其他玩家死亡不會使本機畫面顯示倒數。
- 配件冷卻值在死亡時不得重設，死亡期間凍結，重生後恢復倒數。
