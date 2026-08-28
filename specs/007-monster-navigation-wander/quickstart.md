# 快速開始與驗證：小怪動態尋路與營地遊蕩

## 前置條件

- Windows 已安裝 Python 3.11 或更新版本。
- 目前工作目錄為專案根目錄 `C:\Users\Yun-Tse Kao\Desktop\pythonSDD`。
- 依專案既有方式準備虛擬環境；若尚未安裝 Pygame，在虛擬環境中執行 `python -m pip install -r pvpve_escape/requirements.txt`。

## 自動化驗證

在專案根目錄以 PowerShell 依序執行：

```powershell
python -m unittest discover -s pvpve_escape/tests -p "test_*.py"
python -m compileall -q pvpve_escape
git diff --check
```

預期結果：第一個指令全部測試通過且沒有失敗；第二個指令沒有輸出或錯誤；第三個指令沒有空白與 patch 格式錯誤。若要只驗證本功能，可先執行：

```powershell
python -m unittest pvpve_escape.tests.test_navigation
python -m unittest pvpve_escape.tests.test_game_features pvpve_escape.tests.test_terrain
```

量化驗收必須以全新 `MatchState` 重複執行 20 次：追擊測試每次都要在 10 秒內完成，遊蕩測試中每種怪物每次都要抵達至少兩個不同安全點；測試以 100% 通過作為 SC-001／SC-004 的完成條件。

## PR #13 原始驗證結果（2026-08-28，地圖素材整合前）

- `python -m unittest pvpve_escape.tests.test_navigation`：15 項通過；包含牆體簽章即時失效、厚牆阻擋、牆角掃掠一致性、無路徑重試與 520px／視線邊界。
- `python -m unittest pvpve_escape.tests.test_game_features pvpve_escape.tests.test_terrain`：47 項通過；包含 20 次三種類型繞牆追擊、20 次三種類型遊蕩、700px 候選範圍、返營、重生與戰鬥回歸。
- `python -m unittest discover -s pvpve_escape/tests -p "test_*.py"`：205 項通過；既有玩家、地形、技能、渲染與戰鬥測試沒有回歸。
- `python -m compileall -q pvpve_escape` 與 `git diff --check`：均無錯誤輸出。
- 以 `SDL_VIDEODRIVER=dummy` 啟動 `python -m pvpve_escape` 執行 3 秒 headless smoke run，主迴圈持續運作且無啟動例外；此結果作為補充，互動視覺情境已由使用者完成桌面人工驗證。
- 效能抽樣 120 幀：`update_monsters` 平均約 4.0ms、完整 `update_world` 平均約 4.3ms；已將導航起點搜尋改為鄰近擴張，並在單次 A* 快取格子安全判定。
- 平衡與出生點驗證：追獵獸為玩家基礎移速 90%，砲台蟲與重裝巨獸套用同一相對增幅；遊蕩候選可產生接近 700px 的安全半徑；玩家 0 號到所有營地中心與實際怪物出生點均至少 200px。

自動化量化結果：20 次獨立追擊案例中，`CHASER`、`SHOOTER`、`BRUTE` 均於 10 秒內到達互動距離，且每幀位移與牆體碰撞檢查全數通過；20 次獨立遊蕩案例中，三種類型每次均完成至少兩個不同遊蕩點，候選點均在營地中心 700px 內。

## 與 007 地圖素材整合後驗證（2026-08-28，砲台蟲修正前基線）

- 基準為 PR #13／`v0.4.0` 的 `main`；地圖整合後聚焦 `test_navigation`、`test_game_features` 與 `test_terrain` 共 71 項通過。
- 完整 `python -m unittest discover -s pvpve_escape/tests -p "test_*.py"`：226 項通過，怪物尋路、遊蕩、地形、技能與渲染沒有回歸。
- `python -m compileall -q pvpve_escape` 與 `git diff --check`：通過。
- 主迴圈上限仍為 120 FPS；地圖整合固定場景在 120 幀暖機後量測 600 幀，約 6.703 秒、89.51 FPS，量測期間沒有 PNG 載入。
- PR #13 的 20 次追擊、20 次遊蕩、破牆後改道、厚牆阻擋與三種怪物戰鬥差異仍以原驗證結果為準；本段只補充地圖整合後的回歸結果。

## 砲台蟲牆角修正驗證（2026-08-28）

- T027 回歸案例一：砲台蟲位於 `(820,540)`、目標位於 `(1200,600)`，偏好距離點落入 `(900,500,100,160)` 厚牆；200 次 `0.05` 秒更新後進入 300px 偏好距離容許帶，且每次位置都沒有與牆體重疊。
- T027 回歸案例二：砲台蟲沿 `(300,400,100,600)` 長牆上方轉角離開導航額外 4px clearance；200 次更新後仍能繼續繞行並進入偏好距離容許帶，沒有卡在 `(300,380)` 牆角。
- T027 回歸案例三：砲台蟲位於 `(460,470)`、目標位於 `(950,470)`，安全的偏好距離點被四面厚牆封閉；200 次更新後改走目標路線離開封閉區並進入偏好距離容許帶，且沒有牆體重疊。
- `python -m unittest pvpve_escape.tests.test_navigation pvpve_escape.tests.test_game_features pvpve_escape.tests.test_terrain`：74 項通過。
- `python -m unittest discover -s pvpve_escape/tests -p "test_*.py"`：229 項通過；包含新增的三個砲台蟲牆角／封閉區回歸案例。
- `python -m compileall -q pvpve_escape` 與 `git diff --check`：通過。
- 固定地圖抽樣 20 個偏好距離點落入牆體的案例，200 次更新後失敗數為 0；主迴圈上限仍為 120 FPS。
- 最新效能量測：120 幀暖機、600 幀、約 8.438 秒、71.11 FPS；量測期間沒有 PNG 載入，且高於 55 FPS 門檻。

## 純邏輯驗收情境

以下情境應由 `pvpve_escape/tests/test_navigation.py` 與怪物更新測試自動化：

1. 先讓 `CHASER`、`SHOOTER`、`BRUTE` 各自在 520px 內且無牆視線下取得同一名玩家，再把玩家移到牆體另一側；每種怪物更新至少 10 秒並重複 20 次，三種怪物都應沿安全節點繞過牆，進入各自原本的攻擊互動距離。
2. 在路徑中放置厚牆，確認 A* 不會穿越牆角；每次更新後以 `circle_intersects_rect` 確認小怪圓形邊界與牆體不重疊，且非重生單幀位移不超過 `move_speed * delta_time * slow_multiplier + config.TERRAIN_GEOMETRY_EPSILON`。無路徑時位置保持安全且之後會重試。
3. 以同一營地至少三隻分別處於 `WANDER`、`RETURN`、`CHASE` 的小怪先取得繞過薄牆的路徑，再將薄牆設為 `destroyed=True`；下一次 `update_monsters` 前後比較 `navigation_obstacle_signature` 與路徑，三隻怪物都應清除舊路徑並可使用原薄牆位置，而未摧毀厚牆仍不可通行。
4. 將玩家放在 520px 外、520px 內牆後、520px 內無牆三種位置，分別確認遊蕩、無新目標、追擊三種結果；剛好 520px 應可取得，超過 520px 才解除。
5. 讓追擊目標死亡或離開距離，確認小怪進入 `RETURN`、返營期間不攻擊，距營地中心 64px 內才轉回 `WANDER`，回到營地後選擇至少兩個不同安全遊蕩點；每個點距營地中心不超過 700px。
6. 檢查重生流程：殺死小怪並等待重生，確認位置回出生點、狀態為 `WANDER`、目標／路徑／遊蕩停留計時均清空，且沒有沿用死亡前的投射物或攻擊狀態。

## 手動遊戲驗證

以專案根目錄執行：

```powershell
python -m pvpve_escape
```

啟動後依序觀察：

1. 開場先不要靠近怪物，觀察各營地的小怪在中心 700px 範圍內移動，抵達點後短暫停留；遊蕩時不應跨圖追逐或攻擊玩家。
2. 讓玩家接近某營地的一隻小怪，在 520px 內且視線沒有牆時，小怪應鎖定最近玩家並追擊；若玩家在完整牆後且尚未被鎖定，小怪應維持營地行為。
3. 讓已鎖定的小怪和玩家分處牆體兩側，觀察小怪繞過牆角，不應連續一秒以上停在牆前，不應穿牆或瞬間跳位；返營完成以距營地中心 64px 為準。
4. 使用既有玩家技能破壞路徑上的薄牆；下一個畫面更新後，小怪應能把薄牆原位置視為可通行並修正方向。旁邊未破壞的厚牆仍應阻擋。
5. 將已鎖定玩家帶離 520px 或使其死亡，確認小怪停止攻擊並返營；回到營地後重新遊蕩。分別觀察追獵獸、砲台蟲與重裝巨獸，確認接觸攻擊、砲台蟲偏好距離與投射物外觀／速度沒有改變。

## 驗收紀錄格式

完成實作後，在 PR 或實作回報中記錄；PR #13 的原始結果與地圖整合後的回歸結果分開保存：

- 自動化測試的通過數與執行指令。
- 20 次獨立牆體兩側追擊測試中三種怪物是否都在 10 秒內達到攻擊距離，以及是否符合 SC-002 的位移上限。
- 破牆後下一次更新是否清除舊路徑，以及厚牆阻擋測試結果。
- 20 次獨立遊蕩測試中每種怪物完成的不同遊蕩點數、最大營地距離與 64px 返營完成判定。
- 手動遊戲中的卡牆觀察結果，及任何仍需追蹤的邊界案例。

使用者已於 2026-08-28 回報完成桌面人工驗證且沒有問題；本地 review 將此結果作為手動驗證證據，並以自動化測試補足速度比例、出生距離與 700px 候選範圍的可重複斷言。
