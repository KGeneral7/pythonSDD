# 實作計畫：100×100 地圖素材接入遊戲

**功能識別字**：007-map-asset-integration
**原實作分支**：codex/007-map-asset-integration（已於 PR #14 合併後刪除）
**目前發布分支**：main
**日期**：2026-08-28
**基準版本**：`v0.4.0`（PR #13 合併後的 `main`）
**規格**：[spec.md](spec.md)
**輸入**：目前已確認的地面、薄牆、厚牆與草叢圖片，以及將正式地圖拆成互不連帶破壞的 100×100px 地形格之需求。

## 摘要

本功能將現有地圖素材接入 Pygame 正式比賽畫面，並在建立比賽時把既有矩形布局正規化成固定 100×100px 的獨立牆格與草叢格。正規化流程會向外對齊 100px 網格、移除同格重複資料，並以厚牆高於薄牆、薄牆高於草叢的優先級解決跨類型重疊。遊戲狀態仍沿用既有的 ObstacleState、BushState 與碰撞／破壞函式，因此單格更新不會改變角色、技能或規則。

繪製層會快取四種 100×100 圖片，將地面素材依世界網格連續鋪滿，再把有效草叢與牆格以完整尺寸 blit 到世界座標；鏡頭邊界只交由 Pygame 的 surface clipping 處理。素材缺失時沿用目前的程式繪製作為備援。完整戰術總覽圖只保留為預覽與設計確認資產，不作為動態遊戲背景。

## 技術上下文

**語言／版本**：Python 3.11

**主要依賴**：Pygame 2.5 以上且小於 3；標準函式庫 unittest、pathlib、dataclasses；不新增第三方依賴

**儲存**：無執行期資料庫；固定布局仍來自 pvpve_escape/config.py，局內地形狀態只存在記憶體

**測試**：pvpve_escape/tests/ 下的 unittest，搭配 SDL dummy video driver 的離屏 Surface 測試；另加 compileall、git diff --check 與手動啟動驗收

**目標平台**：Windows 桌面環境，使用現有 .venv 與 Pygame 視窗

**專案類型**：單一 Python／Pygame 桌面遊戲

**效能目標**：在 Windows、Python 3.11、Pygame、1280×720 遊戲視窗的固定正常場景先暖機 120 幀，再以單調時鐘量測 600 次更新與繪製；600 是量測樣本數，不是 FPS 設定。以 600 除以實際經過秒數計算平均至少 55 FPS，且圖片檔案不可在量測幀重複讀取

**限制**：世界固定為 2400×1400px，地形格固定為 100×100px，遊戲主迴圈與地圖編輯器 FPS 上限為 120；效能測試的 600 只代表量測次數；不得改變既有碰撞、傷害、撤離、怪物與技能規則；素材載入失敗仍須能啟動並顯示可辨識地形

**規模／範圍**：目前布局正規化後實際為 150 格：36 個厚牆格、22 個薄牆格、92 個草叢格；本功能涵蓋地形資料建立、地圖繪製、單格破壞回歸與素材驗證，不涵蓋角色或關卡規則重設

## 憲章檢查

本節為 Phase 0 研究前的設計閘門。依 .specify/memory/constitution.md 逐條檢查，所有原則均通過。

| 原則 | 計畫符合方式 | 狀態 |
|---|---|---|
| I. 小步驟、可執行的實作 | 依資料正規化、素材載入、繪製、破壞回歸、效能與手動驗收分成小步驟；每步都有可驗證結果 | 通過 |
| II. 規格與設計優先 | 先完成 spec.md、research.md、data-model.md、quickstart.md，再由 tasks.md 產生實作工作 | 通過 |
| III. 簡單、可維護的技術 | 沿用現有 Python／Pygame 狀態與幾何函式，只新增一個小型正規化流程和圖片快取，不引入框架或服務 | 通過 |
| IV. 明確的輸入、更新、渲染邊界 | 地形建立在比賽初始化，破壞在既有規則更新階段，圖片只在 rendering.py 投影；世界座標與螢幕座標保持分離 | 通過 |
| V. 自動與手動驗證 | 新增格數、重疊、單格破壞、素材尺寸、相機裁切、備援載入與效能測試，並以實機操作確認視覺結果 | 通過 |
| VI. 文件語言一致 | 本功能 SDD 文件使用繁體中文；程式識別字、既有英文檔名與命令列保留原樣 | 通過 |
| VII. 分支與規格識別字一致 | 分支 codex/007-map-asset-integration 與 specs/007-map-asset-integration 使用相同功能識別字 | 通過 |

結論：可進行 Phase 0 研究與 Phase 1 設計，沒有需要額外豁免的憲章違反。

## 專案結構

### 本功能文件

~~~text
specs/007-map-asset-integration/
├── spec.md             # 功能需求與驗收情境
├── plan.md             # 本實作計畫
├── research.md         # Phase 0 研究決策
├── data-model.md       # Phase 1 地形資料模型與不變條件
├── quickstart.md       # Phase 1 驗證與手動驗收步驟
├── checklists/
│   └── requirements.md # 規格完整性檢查表
└── tasks.md            # 由 $speckit-tasks 產生；本次不建立
~~~

本功能不建立 contracts/。這是本機 Pygame 桌面程式，沒有對外 HTTP API、CLI 協定、跨服務訊息或需版本化的外部介面；既有 Python 函式的相容性會在「介面與相容性」及測試中明確驗證。

### 原始碼與資產

~~~text
pvpve_escape/
├── config.py              # 世界尺寸、100px 網格與布局輸入
├── models.py              # ObstacleState、BushState、WorldRect
├── terrain.py             # 布局正規化、地形建立、碰撞與破壞
├── rendering.py           # 地面鋪設、素材快取、牆／草叢繪製與備援
├── map_editor.py          # 100px 格編輯與布局草稿輸出
├── world.py               # 世界座標與鏡頭換算
├── main.py、__main__.py   # 比賽啟動與主迴圈
├── requirements.txt       # 既有 Pygame 依賴宣告
├── assets/map/
│   ├── ground_tile.png
│   ├── thin_wall_tile.png
│   ├── thick_wall_tile.png
│   ├── bush_tile.png
│   └── map_overview_tactical.png
└── tests/
    ├── test_helpers.py         # 既有測試環境輔助
    ├── test_terrain.py         # 正規化、格狀態與破壞回歸
    ├── test_rendering.py       # 地圖層、鏡頭與繪製回歸
    ├── test_game_features.py   # 既有技能整合回歸
    ├── test_breach_cone.py     # 既有破牆效果回歸
    ├── test_main.py            # 既有啟動與新局回歸
    ├── test_map_assets.py      # 新增素材尺寸、快取與備援測試
    ├── test_map_editor.py      # 新增編輯器格資料測試
    └── test_map_performance.py # 新增地圖繪製效能測試
~~~

**結構決策**：維持現有單一 Pygame 專案分層。地形的資料粒度改在 terrain.py 統一處理，素材的檔案解析與視覺投影留在 rendering.py；不為本功能新增服務層、資料庫或獨立套件。

## 實作設計

### 1. 地形布局正規化與獨立狀態

1. 在 config.py 增加明確的 TERRAIN_CELL_SIZE = 100，並讓正式地形正規化使用此常數；既有 GRID_SIZE 維持目前地面網格用途。
2. 在 terrain.py 建立內部布局正規化流程，輸入既有矩形布局，輸出具備單一格座標的牆／草叢資料。既有矩形只作為布局輸入，不直接成為局內可破壞狀態。
3. 對每個矩形以左上角向下取整、右下角向上取整，並限制在世界範圍內；再依每個 100×100 格展開。這會把非 100px 的舊布局向外取整，符合規格中的既有布局假設。
4. 以 (left, top) 作為格佔用鍵。同類型重複只保留一筆；跨類型衝突套用厚牆 > 薄牆 > 草叢，最後每個佔用鍵最多只對應一個正式物件。
5. 由 build_terrain() 單次呼叫合併正規化流程，統一完成牆與草叢的同格優先級，再依穩定的布局順序與格內列舉順序分配 ID；create_obstacles() 與 create_bushes() 只作相容性包裝，呼叫同一合併流程後選取對應清單，create_terrain() 委派給 build_terrain()。如此任何正式建立入口都不會繞過跨類型去重。預期結果為厚牆 36 格、薄牆 22 格、草叢 92 格。
6. 更新 map_editor.py 的格線與新增／移動限制，使編輯器的新輸出以 100×100 為最小且固定的單格；讀取舊草稿時仍走同一套正規化規則，儲存時寫出單格物件，避免再產生一筆涵蓋多格的正式布局。

### 2. 素材解析、快取與地面鋪設

1. 在 rendering.py 以目前模組檔案位置為基準解析 pvpve_escape/assets/map/，不依賴工作目錄；素材鍵固定對應地面、薄牆、厚牆、草叢四種用途。
2. 採延遲載入與模組級快取：第一次繪製時讀取並轉為可 blit 的 Pygame Surface，後續幀重用同一份 Surface；不得在每幀呼叫檔案讀取。
3. 載入後驗證每個正式地形素材為 100×100px；若檔案不存在、格式錯誤、顯示器轉換失敗或尺寸不符，記錄可診斷的狀態並標記該素材使用程式繪製備援。
4. draw_world 先以地面顏色清底，再依相機可見世界範圍按 100px 世界網格鋪設 ground_tile.png，之後保留現有細網格線作為格界提示。地面起點必須由世界座標計算，不得由螢幕左上角重新開始。
5. map_overview_tactical.png 僅供預覽與設計確認，不進入每幀動態背景；動態場景一律由地面格與地形格組合。

### 3. 牆／草叢繪製與鏡頭裁切

1. draw_terrain 逐一取出有效的 BushState 與未被破壞的 ObstacleState，以其 WorldRect 左上角轉成螢幕位置，選擇對應 100×100 素材。
2. 正式 100×100 格以原始完整 Surface blit 到完整的世界格矩形，不先把 destination rect clip 成可見片段；視窗邊界由 Pygame surface 自然裁切，避免相機邊緣把素材拉伸或縮放。
3. 先繪製草叢，再繪製牆體，並依狀態有效性決定是否繪製；由正規化流程保證正式地圖不會留下需要靠繪製順序解決的同格重疊。
4. 非正式 100×100 的手動測試 fixture 或既有外部呼叫若仍傳入任意 WorldRect，保留目前的程式繪製路徑，避免破壞既有幾何測試；正式配置的 100×100 格則以圖片為主。
5. 單一素材失敗時只對該類型使用目前的顏色、邊框與裂紋／葉片繪製，不改 MatchState、碰撞或破壞結果，符合 FR-012。

### 4. 破壞流程與比賽生命週期

1. 保留 destroy_thin_wall_on_path、destroy_terrain_in_radius、destroy_bushes_on_segment、resolve_dash_path 的既有公開簽名與幾何判定；這些函式改為自然接收單格狀態清單，不再遇到一筆多格矩形。
2. 路徑命中只把實際命中的薄牆 ObstacleState 標記 destroyed；範圍效果逐一檢查每格相交關係；草叢逐一將相交格標記 inactive；厚牆仍不可破壞。
3. 破壞後 draw_terrain 不再繪製該格，draw_world 已經存在的地面層會露出；相鄰格仍由各自狀態控制，不共用 destroyed／active 欄位。
4. create_match 或等效的比賽建立流程每次呼叫 build_terrain 建立新清單；不得把上一局的狀態物件或可變布局資料快取到下一局。
5. 不修改草叢不阻擋移動／投射物、厚牆碰撞與薄牆破壞資格等既有規則，只調整狀態粒度與視覺輸出。

### 5. 測試、效能與文件

1. 在 test_terrain.py 驗證正規化數量、100×100 尺寸、網格對齊、世界邊界、同格去重與三類優先級。
2. 在 test_terrain.py 驗證多格薄牆、草叢路徑與範圍效果的單格狀態變更，以及厚牆不受破壞；同時保留既有任意矩形 fixture 的幾何回歸。
3. 在 test_rendering.py 或新增 test_map_assets.py 驗證圖片尺寸、地面連續鋪設、素材快取、正式格的素材像素、毀損格顯示地面、鄰格不被影響，以及左上／中央／右下相機和部分進入視窗的裁切。
4. 模擬缺失或無法載入圖片，確認遊戲畫面仍能建立且使用原有可辨識繪製；測試結束後還原快取／測試替身，避免污染其他測試。
5. 在 Windows、Python 3.11、Pygame、1280×720 遊戲視窗的固定驗收環境與固定正常遊戲場景先暖機 120 幀，再用單調時鐘量測連續 600 次更新與繪製（600 不是 FPS），以 600 除以實際經過秒數計算平均 FPS，確認至少 55 FPS；記錄環境、經過秒數與平均 FPS，並以載入計數或測試替身確認沒有每幀磁碟 I/O。
6. 更新 quickstart.md 與必要的功能文件，記錄資產位置、正規化數量、測試命令、手動破壞案例與備援行為；不在本階段產生 tasks.md。

## 介面與相容性

### 對內設定與資料介面

- 新增 config.TERRAIN_CELL_SIZE，值固定為 100；世界尺寸與既有 config.GRID_SIZE 不改。
- create_obstacles()、create_bushes()、build_terrain()、create_terrain() 的呼叫方式不變；其正式返回值改為每格一個狀態，並維持 ObstacleState、BushState 欄位名稱。
- build_terrain() 是跨類型布局正規化的唯一權威入口；create_obstacles() 與 create_bushes() 必須委派同一合併正規化結果後各自返回牆／草叢清單，不能各自獨立正規化而留下牆草重疊。
- 正式返回的每個牆與草叢 bounds 必須是整數座標且寬高皆為 100；既有手動建立的任意 WorldRect 仍可供幾何輔助函式使用。
- ObstacleState.obstacle_id 與 BushState.bush_id 在每次新局內唯一且穩定；不承諾跨局或跨版本的數值固定。

### 渲染介面

- draw_world(surface, match, ...)、draw_terrain(surface, match, ...) 與 draw_match(...) 的既有簽名保持不變，呼叫端不需知道圖片路徑。
- 新增的素材載入器為 rendering.py 內部實作，不形成外部 API；其責任只有路徑解析、Surface 快取、尺寸驗證與單類型備援選擇。
- 地圖圖片與地形狀態的連結只透過地形類型與 100px WorldRect 完成；不把 Surface 放入 MatchState，避免遊戲狀態依賴顯示器或圖片物件。

### 布局編輯相容性

- map_editor.py 的現有保存檔格式可讀；舊的多格矩形載入後先正規化。
- 編輯器後續寫出的地形物件採 100×100 單格資料，且以 100px 網格定位；出生點、怪物區與撤離區仍是警示標記，不加入可破壞地形狀態。

## 驗證計畫

| 驗證層級 | 覆蓋內容 | 通過條件 |
|---|---|---|
| 單元測試 | 正規化、格鍵、優先級、邊界、狀態獨立與幾何函式 | 150 格計數正確；無重疊；單格破壞與既有規則測試全通過 |
| 素材／渲染測試 | 四個 tile 尺寸、快取、地面鋪設、四類圖片、備援與毀損後底層 | 圖片完整填滿 100×100；相機三位置與部分裁切位置正確 |
| 整合測試 | create_match、draw_match、技能破壞、新局重建 | 破壞狀態只在當局且不污染下一局 |
| 靜態／啟動檢查 | compileall、完整 unittest、git diff --check、python -m pvpve_escape | 無語法錯誤、測試通過、無空白錯誤、可啟動 |
| 效能測試 | Windows、Python 3.11、Pygame、1280×720 視窗的固定場景暖機 120 幀後，以單調時鐘量測 600 次更新與繪製（600 不是 FPS） | 記錄環境、經過秒數與平均 FPS；600 除以實際經過秒數至少 55 FPS，無每幀素材讀取 |
| 手動驗收 | 左上／中央／右下鏡頭、相鄰格破壞、厚牆、缺圖備援 | 視覺與規格三個使用者故事的驗收情境一致 |

## Phase 1 設計後憲章再檢查

完成研究與資料模型後再次檢查，結果仍全部通過：

| 原則 | 設計後證據 | 狀態 |
|---|---|---|
| I. 小步驟、可執行的實作 | 正規化、快取／地面、地形渲染、生命週期回歸、驗證各自可獨立測試 | 通過 |
| II. 規格與設計優先 | research.md 記錄決策，data-model.md 定義狀態與不變條件，quickstart.md 定義驗證 | 通過 |
| III. 簡單、可維護的技術 | 只增加常數、正規化流程與小型快取；不新增第三方依賴、服務或過度抽象 | 通過 |
| IV. 明確的輸入、更新、渲染邊界 | 布局在建立期轉換、狀態在規則期改變、Surface 只在渲染期使用 | 通過 |
| V. 自動與手動驗證 | 測試矩陣與手動操作涵蓋功能、邊界、備援、效能與啟動 | 通過 |
| VI. 文件語言一致 | 四份新增 SDD 文件與本計畫均為繁體中文 | 通過 |
| VII. 分支與規格識別字一致 | 計畫、規格、分支與資料夾均為 007-map-asset-integration | 通過 |

設計閘門結論（規劃階段）：無新增違反，不需要架構豁免；依賴排序的實作任務已完成，結果記錄於 `tasks.md`。

## 複雜度與治理追蹤

本計畫沒有憲章違反，因此不新增複雜度豁免。特別維持以下簡化決策：

- 不把完整總覽圖作為執行期背景，避免相機、地形狀態與動態角色被迫整合到一張不可變圖片。
- 不新增空間索引；正式牆／草叢總量只有 150 格，沿用既有線性幾何查詢即可先達成需求，效能以 600 次更新／繪製量測確認（600 不是 FPS）。
- 不把 Pygame Surface 放進模型或序列化布局，保持資料、規則與渲染責任分離。
- 不建立 contracts/，因為本功能沒有外部介面。

## 實作後狀態（2026-08-28）

- 007 地圖素材功能已在目前工作樹完成，正式地形為 36 個厚牆格、22 個薄牆格與 92 個草叢格，共 150 個 100×100 格。
- 完整 unittest 共 229 項通過；`compileall` 與 `git diff --check` 通過，包含後續砲台蟲牆角／封閉區回歸測試。
- 固定場景在 120 幀暖機後量測 600 次更新／繪製，約 6.578 秒完成，平均 91.21 FPS；量測期間沒有 PNG 磁碟讀取，且執行期上限為 120 FPS。
- 非 draft [PR #14](https://github.com/KGeneral7/pythonSDD/pull/14) 已 squash merge 至 `main`，合併提交為 `0f4d7afe47895a97268fcd32b3d785a35ee2a5aa`，並發布 [v0.5.0](https://github.com/KGeneral7/pythonSDD/releases/tag/v0.5.0)；本文件、素材與測試均已納入，工作樹中的無關檔案已排除。
- 後續程式將執行期上限集中為 `config.MAX_FPS = 120`，並由 [PR #15](https://github.com/KGeneral7/pythonSDD/pull/15) 合併、以 [v0.5.1](https://github.com/KGeneral7/pythonSDD/releases/tag/v0.5.1) 發布；600 僅為效能量測次數。
