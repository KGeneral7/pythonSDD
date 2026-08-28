# 任務清單：100×100 地圖素材接入遊戲

**功能識別字**：007-map-asset-integration

**輸入文件**：

- [spec.md](spec.md)
- [plan.md](plan.md)
- [research.md](research.md)
- [data-model.md](data-model.md)
- [quickstart.md](quickstart.md)

**專案結構**：單一 Python／Pygame 桌面遊戲；原始碼位於 pvpve_escape/，測試位於 pvpve_escape/tests/，地圖素材位於 pvpve_escape/assets/map/。

**測試政策**：規格已提供每個使用者故事的獨立測試情境與可衡量成功標準，因此本任務清單包含先寫測試、再實作的測試任務。

**外部契約**：不建立 contracts/；本功能沒有 HTTP API、CLI 協定、跨服務訊息或其他外部介面。

## 任務格式

每項任務均使用格式：- [狀態] [TaskID] [P?] [Story?] 說明與明確檔案路徑。

- [P] 代表可在沒有依賴未完成任務的情況下平行處理。
- [US1]、[US2]、[US3] 分別對應規格中的三個使用者故事。
- Setup、Foundational 與 Polish 任務不加使用者故事標籤。

## Phase 1：設定與基線

**目的**：確認既有圖片、啟動點與測試環境，不新增依賴或改動遊戲規則。

- [X] T001 [P] 確認 pvpve_escape/assets/map/ground_tile.png、thin_wall_tile.png、thick_wall_tile.png、bush_tile.png 都存在且為 100×100px，並確認 pvpve_escape/__main__.py 可作為手動啟動入口
- [X] T002 [P] 在 pvpve_escape/tests/test_helpers.py 整理 SDL dummy display 初始化與 rendering 資產快取清理輔助，讓離屏渲染測試可重複執行

**完成檢查點**：資產路徑與測試啟動方式已確認；pvpve_escape/requirements.txt 不需新增套件。

---

## Phase 2：共同地形基礎

**目的**：建立所有使用者故事都需要的 100px 格尺寸、布局正規化與獨立比賽狀態。

**重要依賴**：本階段完成前，不開始正式使用者故事的實作。

- [X] T003 在 pvpve_escape/tests/test_terrain.py 先加入會失敗的正規化測試，驗證 36 個厚牆格、22 個薄牆格、92 個草叢格、總數 150、100×100 尺寸、100px 對齊、世界邊界、同格去重與厚牆 > 薄牆 > 草叢優先級
- [X] T004 [P] 在 pvpve_escape/config.py 新增 TERRAIN_CELL_SIZE = 100，並確認 WORLD_WIDTH、WORLD_HEIGHT 與既有 GRID_SIZE 的責任不被混用
- [X] T005 在 pvpve_escape/terrain.py 建立共用布局正規化函式，實作左／上向下取整、右／下向上取整、世界邊界限制、100×100 格展開與 (left, top) 格鍵
- [X] T006 在 pvpve_escape/terrain.py 讓 build_terrain() 單次執行合併正規化並完成同類型去重、跨類型優先級、穩定 ID 與新的可變狀態清單，再讓 create_obstacles()、create_bushes() 委派同一結果後各自選取清單，create_terrain() 委派 build_terrain()
- [X] T007 [P] 在 pvpve_escape/tests/test_map_editor.py 新增編輯器布局測試，驗證載入舊矩形後可正規化，儲存的新地形項目固定為 100×100 且座標對齊 100px 網格
- [X] T008 在 pvpve_escape/map_editor.py 將編輯器的格線、建立、移動與保存流程改為使用 config.TERRAIN_CELL_SIZE，並讓舊草稿載入與新草稿保存共用正規化規則

**完成檢查點**：正式地形清單只有單格牆／草叢；既有任意尺寸 WorldRect 的幾何 fixture 仍可被 terrain.py 輔助函式接受。

---

## Phase 3：使用者故事 1－在遊戲中看到一致的地圖素材（優先級：P1，MVP）

**目標**：在正式比賽畫面以目前確認的四種圖片顯示地面、薄牆、厚牆與草叢，每個正式格完整填滿 100×100px。

**獨立測試**：建立一場比賽並呼叫 draw_match，在左上、中央與右下可見區域檢查四種素材；確認相鄰格位置正確、素材沒有空白邊緣或不預期縮放，且移除單一素材後仍能啟動並顯示該類型的程式繪製備援。

### US1 測試任務

- [X] T009 [P] [US1] 在 pvpve_escape/tests/test_map_assets.py 新增四張 PNG 的存在、100×100 尺寸、可載入、完整像素範圍與快取只載入一次測試，並加入缺圖／錯誤素材的備援測試
- [X] T010 [P] [US1] 在 pvpve_escape/tests/test_rendering.py 擴充正式 MatchState 的地面、薄牆、厚牆與草叢繪製測試，改以素材像素與 100×100 格位置驗證，不再依賴舊的單色矩形中心點假設

### US1 實作任務

- [X] T011 [US1] 在 pvpve_escape/rendering.py 建立相對於模組路徑的地圖素材載入器與模組級快取，加入尺寸驗證、單類型錯誤狀態與既有程式繪製備援
- [X] T012 [US1] 在 pvpve_escape/rendering.py 實作以 camera_position 對應世界範圍的 ground_tile.png 100px 網格鋪設，保留既有地面清底與格線責任
- [X] T013 [US1] 在 pvpve_escape/rendering.py 更新 draw_terrain，使有效 BushState、未破壞 ObstacleState 分別使用 bush、thin wall、thick wall 素材，正式格以完整 Surface blit 到 100×100 世界格
- [X] T014 [US1] 在 pvpve_escape/rendering.py 整合 draw_world、draw_terrain、draw_match 的圖層順序與備援路徑，保持既有函式簽名、角色／營地／撤離區／特效圖層與 MatchState 不變

**完成檢查點**：US1 可單獨啟動與渲染；素材存在時顯示圖片，素材失效時仍顯示可辨識地形且不改變碰撞規則。

---

## Phase 4：使用者故事 2－分別破壞單一地形格（優先級：P1）

**目標**：讓薄牆與草叢的路徑／範圍效果逐格更新，命中格消失或失效，鄰格維持原狀；厚牆維持不可破壞。

**獨立測試**：建立含有相鄰薄牆與草叢格的 MatchState，重複執行至少 20 次單格路徑破壞與範圍破壞，確認每次只更新實際相交格；對厚牆執行相同效果後確認仍存在。

### US2 測試任務

- [X] T015 [P] [US2] 在 pvpve_escape/tests/test_terrain.py 新增單格薄牆路徑、DASH 首面薄牆、草叢線段、範圍交集、邊界接觸與厚牆不可破壞測試，確認相鄰狀態不變
- [X] T016 [P] [US2] 在 pvpve_escape/tests/test_game_features.py 與 pvpve_escape/tests/test_breach_cone.py 擴充技能整合測試，確認既有破牆／範圍技能面對多格狀態時不會整批移除原始矩形
- [X] T017 [US2] 在 pvpve_escape/tests/test_rendering.py 新增破壞後渲染測試，確認被破壞格露出地面素材、相鄰未破壞格仍顯示原素材，且厚牆素材仍存在

### US2 實作任務

- [X] T018 [US2] 在 pvpve_escape/terrain.py 逐一檢查單格 ObstacleState、BushState 的路徑與範圍相交結果，保留既有幾何 epsilon 與邊界政策，只更新命中格的 destroyed／active
- [X] T019 [US2] 在 pvpve_escape/rules.py 與 pvpve_escape/main.py 審核並調整所有地形破壞呼叫點，使其使用單格狀態清單與單格 ID，且不改變厚牆、草叢、技能與碰撞的既有規則

**完成檢查點**：US1 的畫面與 US2 的狀態更新可同時運作；單格破壞不會連帶隱藏相鄰格，也不會污染布局來源。

---

## Phase 5：使用者故事 3－在不同視角維持地圖位置（優先級：P1）

**目標**：鏡頭位於左上、中央、右下或格子部分進入視窗時，地形仍保持正確世界位置與尺寸；新局會重建完整狀態。

**獨立測試**：在三個鏡頭位置呼叫 draw_match，檢查同一世界格的投影座標與邊界裁切；先破壞一格再建立新局，確認所有正式地形恢復有效。

### US3 測試任務

- [X] T020 [P] [US3] 在 pvpve_escape/tests/test_rendering.py 新增左上、中央、右下 camera_position 與部分進入 viewport 的裁切測試，確認完整 tile 不被縮放或拉伸
- [X] T021 [P] [US3] 在 pvpve_escape/tests/test_main.py 新增新局重建測試，確認上一局的 ObstacleState.destroyed 與 BushState.active 變化不會出現在下一局

### US3 實作任務

- [X] T022 [US3] 在 pvpve_escape/rendering.py 完成可見世界範圍的地面／地形投影與自然 Surface clipping，並在 pvpve_escape/world.py 維持 world_to_screen 的 top-left camera 契約，不改變世界座標資料

**完成檢查點**：三個鏡頭位置與部分裁切情境都通過；新局狀態獨立且所有地形恢復初始有效狀態。

---

## Phase 6：收尾與跨功能驗證

**目的**：確認效能、文件、啟動與既有功能回歸，並保留可審查的完成證據。

- [X] T023 [P] 在 pvpve_escape/tests/test_map_performance.py 建立 Windows、Python 3.11、Pygame、1280×720 固定場景先暖機 120 幀、再以單調時鐘量測 600 次更新與繪製的基準，使用 600 除以實際經過秒數計算平均 FPS 至少 55，記錄環境／經過秒數／平均 FPS，並驗證量測期間沒有 PNG 磁碟讀取或重複建立 Surface
- [X] T024 [P] 更新 specs/007-map-asset-integration/quickstart.md，補上實際測試檔名、素材快取清理方式、缺圖備援驗證與手動驗收結果記錄位置
- [X] T025 在 pvpve_escape/tests/ 執行完整 unittest，在 pvpve_escape/ 執行 compileall，並依 specs/007-map-asset-integration/quickstart.md 核對所有自動驗證項目
- [X] T026 在 pvpve_escape/__main__.py 啟動正式遊戲，依 quickstart.md 完成三個鏡頭位置、相鄰格破壞、厚牆、缺圖備援與重新開始手動驗收
- [X] T027 [P] 檢查 pvpve_escape/config.py、terrain.py、rendering.py、map_editor.py、world.py、rules.py、main.py 與 specs/007-map-asset-integration/ 的差異，確認沒有無關重構、沒有新增外部依賴，並執行 git diff --check

**完成檢查點**：所有規格成功標準都有自動或手動證據，且程式可啟動、完整測試通過、效能達標。

## 依賴與執行順序

### 階段依賴

- Phase 1 設定：T001 與 T002 可平行，完成後進入共同基礎。
- Phase 2 共同基礎：T003／T004 可在基線完成後準備；T005 依賴 T004；T006 依賴 T005；T007 依賴 T005；T008 依賴 T006 與 T007，並阻擋所有使用者故事。
- Phase 3 US1：T009 與 T010 可平行；測試完成後依序執行 T011、T012、T013、T014。
- Phase 4 US2：T015、T016 可在 Phase 2 完成後先寫；T018、T019 依賴這些測試；T017 的渲染回歸依賴 T014 與 T018。
- Phase 5 US3：T020 與 T021 可平行準備；T022 依賴 T014、T020、T021。
- Phase 6 收尾：T023～T027 依賴要交付的使用者故事完成；T025～T027 必須在報告完成前執行。

### 使用者故事完成順序

- US1（P1）：依賴 Phase 2；是 MVP，提供四種素材在遊戲中可見的最小可交付版本。
- US2（P1）：核心狀態與幾何部分只依賴 Phase 2，可與 US1 的圖片載入工作平行；畫面回歸 T017 需等待 US1 的渲染層。
- US3（P1）：依賴 Phase 2 與 US1 的渲染層，因為鏡頭驗證必須檢查圖片投影；新局狀態測試可與鏡頭測試平行。
- Polish：依賴已選定的三個使用者故事完成。

### 每個使用者故事內的順序

1. 先建立或更新該故事的測試，確認測試能在功能完成前指出缺漏。
2. 再實作資料／載入／渲染／規則整合。
3. 在故事完成檢查點執行獨立測試，再進入下一個故事。
4. 不把故事的完成建立在未列出的跨故事隱性狀態上。

## 平行處理範例

### Phase 1

~~~text
工作 A：T001，確認 pvpve_escape/assets/map/ 下四張 tile 與 pvpve_escape/__main__.py
工作 B：T002，整理 pvpve_escape/tests/test_helpers.py 的離屏顯示與快取清理
~~~

### US1

~~~text
工作 A：T009，建立 pvpve_escape/tests/test_map_assets.py
工作 B：T010，擴充 pvpve_escape/tests/test_rendering.py
兩項測試完成後：
工作 C：T011，實作 pvpve_escape/rendering.py 的素材載入與快取
~~~

### US2

~~~text
工作 A：T015，擴充 pvpve_escape/tests/test_terrain.py
工作 B：T016，擴充 pvpve_escape/tests/test_game_features.py 與 test_breach_cone.py
測試準備完成後：
工作 C：T018，實作 pvpve_escape/terrain.py 的逐格破壞
工作 D：T019，審核 pvpve_escape/rules.py 與 pvpve_escape/main.py 的呼叫點
~~~

### US3

~~~text
工作 A：T020，建立 pvpve_escape/tests/test_rendering.py 的鏡頭與裁切測試
工作 B：T021，建立 pvpve_escape/tests/test_main.py 的新局重建測試
~~~

## 實作策略

### MVP：只交付使用者故事 1

1. 完成 Phase 1 設定。
2. 完成 Phase 2 共同地形基礎。
3. 完成 Phase 3 US1 的素材載入、地面鋪設、牆／草叢圖片與備援。
4. 在 US1 檢查點確認四種素材、100×100 填滿與可啟動備援。
5. 若只需要先展示圖片，可在此停下；不可宣稱 US2 的單格破壞或 US3 的完整鏡頭驗收已完成。

### 增量交付

1. Phase 1 + Phase 2：得到 150 個獨立且可測試的正式地形格。
2. 加入 US1：得到可看見四種素材的正式遊戲畫面。
3. 加入 US2：得到單格薄牆／草叢破壞與厚牆保護。
4. 加入 US3：得到相機位置、邊界裁切與新局重建驗收。
5. 執行 Phase 6：完成效能、啟動、文件與完整回歸。

## 完成定義

1. tasks.md 的所有必要任務已依序完成並勾選。
2. 36 厚牆、22 薄牆、92 草叢的正式狀態都為 100×100 且網格對齊。
3. 同格重疊已按厚牆 > 薄牆 > 草叢移除，沒有重複物件。
4. 單格路徑／範圍破壞、厚牆不可破壞與草叢可見性規則通過。
5. 地面、牆、草叢素材在三個鏡頭位置及部分裁切情境正確顯示。
6. 素材缺失時仍可啟動並使用程式繪製備援。
7. 遊戲主迴圈 FPS 上限為 120。
8. 固定環境暖機 120 幀後，600 次更新與繪製以實際經過時間計算平均至少 55 FPS，且已記錄環境與量測結果。
9. unittest、compileall、git diff --check 與 quickstart.md 手動驗收均有結果。

## 格式驗證

- 任務總數：27
- 使用者故事任務數：US1 6 項、US2 5 項、US3 3 項
- [P] 任務均標記為可在其依賴完成後與其他不同檔案任務平行處理。
- 每項任務均使用 checkbox 並包含連續 TaskID；使用者故事階段均含 [US1]、[US2] 或 [US3]；每項描述都含明確檔案路徑。
- MVP 範圍為 Phase 1、Phase 2 與 US1。

## 目前交付狀態

- 所有 T001 至 T027 均已完成；目前工作樹已以 `v0.4.0`／PR #13 的 `main` 為基準完成整合。
- 地圖功能尚未建立新的 PR；PR 前需只提交本功能的程式、素材、測試與 `specs/007-map-asset-integration/` 文件。
