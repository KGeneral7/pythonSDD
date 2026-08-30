# 實作計畫：PvPvE Escape 瀏覽器版

**功能分支**：`010-pvpve-escape-web`
**日期**：2026-08-29
**規格**：[spec.md](spec.md)

**輸入**：`specs/010-pvpve-escape-web/spec.md` 的功能規格，以及既有 `pvpve_escape/` Python/Pygame 實作作為行為基準。

## 摘要

新增一個獨立的 `pvpve_escape_web/` Sites 網站，將目前 PvPvE Escape 的單機桌面遊戲逐項重建成桌面瀏覽器可玩的 1:1 parity 版本。瀏覽器版使用 TypeScript、React、Vinext（以 Vite 與 Cloudflare Workers 為基礎）和 Canvas；React/DOM 負責固定邏輯座標的 intro、選角、HUD、結果、說明及可及性，純 TypeScript 遊戲核心負責狀態、輸入轉換、規則、AI、碰撞、撤離與動畫。角色、戰術、怪物、地形、PNG 資源、固定 UI 文案與繪製順序以既有 Python/Pygame 版本為唯一基準，但不改動 001–009 的桌面版來源。

網站不建立後端、帳號、資料庫、持久化或多人網路同步；全部比賽狀態留在瀏覽器記憶體。先以本機 preview 驗證一個有意義的可玩流程，再以 Sites private production slug `pvpve-escape-web` 發布，project id 記在新網站自己的 `.openai/hosting.json`。

## 技術背景

**語言／版本**：TypeScript（瀏覽器版）；React + Vinext（以 Vite／Cloudflare Workers 建置）；Node.js `v24.16.0`、npm `11.13.0`（規劃時環境版本）。既有 Python 3.11/Pygame 桌面版維持原設定，不在本功能中升級或改寫。

**主要依賴**：Sites starter、`@openai/sites@0.3.0`、`@openai/sites-vite-plugin`、Vinext、React、Vite、TypeScript、shadcn/ui、`lucide-react`、Vitest。遊戲核心不得依賴 React 或 DOM。

**儲存**：N/A；`GameState`、資源快取和 session seed 僅存在瀏覽器記憶體，不使用 API、資料庫、D1、R2、localStorage、帳號或 WebSocket。

**測試**：Vitest 純核心單元測試；`npm run build` 靜態建置檢查；本機 dev/preview 的桌面瀏覽器人工情境；Sites private production URL 的部署後 smoke test。父專案 Python 測試維持原有流程。

**目標平台**：支援鍵盤／滑鼠的桌面瀏覽器；Sites／Cloudflare Workers 相容的靜態前端。手機、觸控和線上多人服務不在本功能範圍。

**專案類型**：單一路由的前端 web app／Canvas 2D 遊戲。

**效能目標**：一般桌面瀏覽器在 1280×720 邏輯畫布維持目標 60 FPS，60 秒代表性遊玩期間不因資源重複解碼或未界定集合成長而明顯降速；每次更新的 `deltaTime` 上限為 0.05 秒，並以 55 FPS 作為可接受的人工觀察下限。

**限制**：不能在瀏覽器直接執行 Python/Pygame；不可要求父專案 Python 或本機 server；不引入後端、遊戲帳號、持久化、觸控、map editor 或線上同步。必須保留既有桌面版、既有 specs 001–009，以及使用者現有未追蹤的 `day3/` 和 `sample.png`。比賽固定有 4 個 `MatchPhase`（character-select、playing、victory、no-winner）、6 players（1 human + 5 dummy）、4 camps × 3 monster types、現有 PNG 資源；實作計畫的階段數由任務文件細分。固定 parity 基準為世界 `2400×1400`、邏輯 surface `1280×720`、原始 18 個地形矩形（正規化 36 厚牆／22 薄牆／92 草叢）、六個玩家出生點與四個營地座標，且 dummy 不自主移動或攻擊。

**規模／範圍**：一個遊戲入口、五個使用者故事、37 項功能需求；約 10 個遊戲核心模組、Canvas renderer、React shell、資源 manifest/cache/loading gate、Vitest 規則測試及部署 smoke test。

## 憲章檢查

| 原則 | 結果 | 計畫中的落實 |
|---|---|---|
| I. 增量式開發 | 通過 | 先建立新 feature 目錄，再按核心、可玩切片、完整內容、資源／部署階段逐步交付；每階段都可測試。 |
| II. SDD 先行與可追溯性 | 通過 | `spec.md`、`research.md`、`data-model.md`、`contracts/web-game-ui.md`、`quickstart.md` 和本計畫互相連結；實作任務將由後續 `$speckit-tasks` 產生。 |
| III. 技術選型與相容性 | 有記錄的例外 | 新網站改用 TypeScript／React／Vite／Canvas，因瀏覽器不能直接提供 Pygame 顯示與事件迴圈；既有 Python/Pygame 桌面版仍是行為基準且不受改動。替代方案與邊界記錄於 `research.md`，例外影響與補償測試記於 Complexity Tracking。 |
| IV. 模組化與邊界 | 通過 | `src/game` 不依賴 React／DOM；input、update、render 分離；世界／邏輯座標、資源、UI 和 Sites 設定有明確邊界。 |
| V. 測試與可驗證性 | 通過 | 以 Vitest 覆蓋數值和生命週期，build 驗證部署產物，quickstart 定義 resize、輸入、資源、撤離和結果情境。 |
| VI. 文件與語言 | 通過 | 本 feature 的規格、研究、模型、契約、quickstart 和計畫以繁體中文記錄；程式 API 可使用英文命名以符合 TypeScript 慣例。 |
| VII. 分支與發行流程 | 通過 | 分支、feature directory 和 plan 使用同一識別 `010-pvpve-escape-web`；實作後仍需遵循 project-release 的 review、驗證和發布流程。 |

### 實作前再檢查

- 研究已決定以原生瀏覽器 TypeScript 重建，而不是以 Pyodide、iframe 或遠端 Pygame 執行。
- 資料模型已定義玩家、怪物、投射物、地形、輸入、相機、developer mode、比賽階段和不變量。
- UI 契約已定義畫面階段、鍵鼠映射、HUD 隱私、resize、資源 fallback 和 private Sites 邊界。
- 除上述瀏覽器平台例外外，沒有其他需要憲章豁免的設計。

## 原版 parity 基準與邊界

`pvpve_escape/__main__.py → main.py` 是遊戲入口；`config.py`、`models.py`、`characters.py`、`rules.py`、`monsters.py`、`terrain.py`、`navigation.py`、`aiming.py`、`auto_aim.py`、`world.py` 與 `rendering.py` 是行為與畫面的基準來源。實作不能只維持「看起來相似」：初始資料、更新順序、技能預設地形互動、dummy 行為、Canvas 繪製層級、固定繁體中文文案與 UI 的邏輯座標都要有 parity fixture 或明確的對照測試。

| 基準項目 | 必須保留的結果 |
|---|---|
| 時間與更新 | 120 FPS 目標、`0.05s` 單次 dt cap、240 秒比賽、210 秒開放撤離、10 秒撤離、玩家 5 秒重生、怪物 6 秒重生 |
| 初始實體 | 6 名玩家、12 隻怪物、4 個營地；玩家 0 人類、玩家 1～5 dummy；dummy 不自主移動／攻擊 |
| 地形 | 18 個原始矩形不可合併／改位；36 厚牆、22 薄牆、92 草叢；厚牆阻擋、薄牆依原版動作破壞 |
| 畫面 | 1280×720 邏輯 surface；intro、選角、對局 HUD、developer、結果沿用原版座標、文案與繪製層級；瀏覽器只做等比例縮放 |
| 必要平台差異 | 瀏覽器 `Esc` 返回導覽而非關閉分頁；其餘 WASD、滑鼠、Space、Tab、R、F1、1～5、M/N、Q/W/E、Enter 流程不變 |

`map_editor.py` 仍是桌面開發工具，不搬進網站；DOM 只提供可聚焦／可及性語意與必要 click 入口，不能另加可見的現代化 HUD、Toast 或撤離圓環。

## 專案結構

新增網站的範圍限定在一個獨立目錄；父專案維持既有結構。

```text
pvpve_escape_web/
├── .openai/
│   └── hosting.json              # Sites project id 與 hosting 設定
├── public/
│   ├── assets/                   # 從 pvpve_escape/assets 複製的 PNG
│   ├── og.png                    # 首次有意義預覽後產生
│   └── ...                       # favicon／靜態 metadata 資源
├── src/
│   ├── app/                      # 畫面階段、session、React app 樣式
│   ├── components/               # React shell、選角、HUD、結果、GameCanvas
│   ├── game/
│   │   ├── types.ts              # GameState、PlayerState、MonsterState 等
│   │   ├── config.ts             # 世界、時間、角色和技能常數
│   │   ├── geometry.ts           # rect/circle/碰撞與座標轉換
│   │   ├── vector.ts             # Vector2 純函式
│   │   ├── rules.ts              # 傷害、生命、能量、彈藥、撤離規則
│   │   ├── characters.ts         # 六種角色定義和角色行為
│   │   ├── monsters.ts           # 三種怪物、AI 和攻擊定義
│   │   ├── terrain.ts             # 障礙、草叢、撤離區與生成區
│   │   ├── navigation.ts         # 營地／障礙導航與路徑
│   │   ├── aiming.ts              # 角度、射線、投射物和命中
│   │   ├── autoAim.ts             # 0.20 秒 lookback 預測
│   │   ├── input.ts               # DOM 事件到 InputState 的轉接
│   │   ├── world.ts               # createMatch/updateMatch 的協調器
│   │   └── renderer.ts            # Canvas world/overhead/aim/debug renderer
│   └── assets/                   # manifest、載入器、fallback
├── app/
│   ├── layout.tsx                # Vinext route layout 與頁面 metadata
│   ├── page.tsx                  # 單一路由入口
│   └── globals.css               # route-level global CSS import
├── tests/
│   ├── rules.test.ts
│   ├── combat.test.ts
│   ├── world.test.ts
│   ├── aiming.test.ts
│   └── input.test.ts
├── next.config.ts
├── package.json
├── tsconfig.json
├── vite.config.ts
└── vitest.config.ts
```

不新增或修改 `pvpve_escape/`、`specs/001-*` 到 `specs/009-*` 的程式內容；若需要比對數值，只讀取它們作為基準。

## 設計與實作細節

### 核心邊界與資料流

1. `src/game/types.ts` 定義 `GameState`、`MatchState`、`PlayerState`、`MonsterState`、`TerrainState`、`InputState`、`FrameSamplerState`、`PublicPlayerView`、`PrivatePlayerView`、`AimGuide` 和 renderer 所需的唯讀型別；canonical ID 對應既有 Python enum。
2. `src/game/config.ts`、`characters.ts`、`monsters.ts` 和 `terrain.ts` 提供單一靜態定義來源；UI 的選項卡片也由這些定義產生，不複製數值。
3. `src/game/input.ts` 只處理 DOM 事件、focus／blur、client-to-logical-to-world 座標轉換，輸出 `InputState`；右鍵產生 ultimate、Tab 切換 auto-aim、R 產生 restart、playing／result 的 Esc 返回 intro，且不直接呼叫傷害、移動或 React state 更新。
4. `src/game/world.ts` 暴露下列純核心邊界：

   ```ts
   createMatch(characterId: CharacterId, tacticalId: TacticalId, seed?: number): MatchState;
   updateMatch(match: MatchState, deltaTime: number, input: InputState): MatchState;
   getPublicPlayerViews(match: MatchState): PublicPlayerView[];
   getPrivatePlayerView(match: MatchState, playerId: number): PrivatePlayerView | null;
   ```

   `updateMatch` 內部先限制 `deltaTime`，再依 `data-model.md` 的固定順序更新玩家、技能、怪物、投射物、碰撞、傷害歸屬、生命週期、撤離、動畫和結果；`winnerId` 只保存玩家 ID 或 null。
5. `src/components/GameCanvas.tsx` 建立 Canvas 和 animation frame；每幀讀取 input snapshot、呼叫 `updateMatch`，再把狀態交給 renderer。React 不在每幀重新建立整個遊戲物件。
6. `src/game/renderer.ts` 只讀狀態和資產 cache，先畫世界／地形，再畫角色／怪物／投射物／效果與玩家頭頂資訊；React 的 `Hud`／`DeveloperOverlay` 在同一個 1280×720 surface 上補上原版固定右上文字、右下 roster 與 developer 文字。正常 HUD 只接受 private/public view，不直接讀其他玩家完整 state。

### 畫面與 Sites 邊界

- `src/app` 先以獨立的資源 loading gate 預載資料，完成後才管理 `intro → character-select → playing → result`，並提供重新開始時清除舊狀態的單一入口；loading gate 不增加 `ScreenPhase` 或建立 `MatchState`。
- 選角元件使用 `characters.ts` 和 tactical definitions；開始前確認所有選擇有效，將它們傳給 `createMatch`。
- 遊戲中 DOM 只顯示固定座標的原版文字／roster、可及性說明與焦點語意；Canvas 維持 1280×720 邏輯尺寸並繪製世界、角色、怪物、投射物、效果、玩家頭頂資訊與瞄準提示，CSS 以 16:9 contain 縮放。DOM overlay 不得增加現代化 HUD。
- `GameCanvas` 掛載時將 Canvas 設為焦點目標；`InputManager` 的視窗鍵盤事件只在 Canvas 為 `document.activeElement` 時轉成遊戲輸入，並以視窗 `pointerup`／`pointercancel` 清除 Canvas 外或被取消的滑鼠持續狀態。
- `src/assets` 建立 manifest、promise cache 與一次性 `loadGameAssets` 預載流程；圖片失敗時回傳 fallback descriptor，不讓 renderer 取得 undefined image 而崩潰。
- `LoadingScreen` 在預載完成前顯示固定 loading 頁並阻止外層快捷鍵；`CharacterSelect` 與 `PlayingScreen` 共用已完成的資源集合，不在開始比賽後重複載入。
- `public/assets/` 從既有 PNG 複製，不在核心中使用父目錄相對路徑。確認本機 preview 可玩後再加入 `og.png`、title 和 metadata。
- `.openai/hosting.json` 由 Sites hosting 流程寫入實際 project id；核心程式不載入此檔案，部署工具設定和遊戲邏輯保持分離。

## 實作階段

本計畫以七個交付階段描述整體路線；`tasks.md` 為了讓五個 User Story 可獨立交付，並容納後續的 parity、loading gate、本地 code review 與發布同步，會再細分成十一個可執行階段，並不代表有兩套不同的產品生命週期。

### Phase 1：SDD 與網站骨架

- 建立 Sites starter 的 `pvpve_escape_web/`、TypeScript／React／Vite 設定、基本 route 和 package scripts。
- 建立空的 intro、選角、playing shell、result shell、Canvas 容器和可及性焦點樣式。
- 先建立 `types.ts`、`config.ts` 與測試設定，使後續核心可以獨立於 UI 編譯。
- 複製並盤點 PNG 資源的來源與目標 URL，但把完整 fallback 與 loading gate 行為留到 Phase 5。

**完成條件**：`npm install`、`npm run build` 可執行；本機可看到 intro 到選角的 DOM 流程，未改動父專案。

### Phase 2：核心模型與規則

- 實作 geometry/vector、角色／戰術定義、玩家初始化、地形資料、怪物／營地初始化和固定常數。
- 實作生命、能量、自動補彈、升級、傷害歸屬、護盾、減傷、控制效果、死亡／重生和五秒離戰回復規則。
- 實作既有四值 `MatchPhase`（character-select、playing、victory、no-winner）、`ScreenPhase` 對接所需的結果條件、240 秒計時與 210 秒撤離開放條件。
- 建立 Vitest 規則測試，鎖定資料模型中的範圍不變量和固定 update 順序。

**完成條件**：核心可在無 Canvas、React、DOM 的測試環境建立一局，6 名玩家、12 隻怪物、4 個營地和所有數值邊界成立。

### Phase 3：第一個可玩切片

- 實作 input manager、WASD、滑鼠瞄準／左鍵普攻／右鍵大招、Space 戰術、R 重新開始、Tab auto-aim、playing／result 的 Esc 回 intro、Enter 流程和失焦清除。
- 實作 requestAnimationFrame、`performance.now()`、0.05 秒 dt 上限、玩家移動、相機跟隨、以 `frameCount / elapsedSeconds` 計算的 60 秒 frame sampler 和最小 Canvas renderer。
- 串起 intro／選角／playing／result，先以色塊／幾何圖形確認核心可玩，再加入完整資源。
- 實作 private/public HUD view，確認其他玩家的完整私有數值不進正常 HUD。

**完成條件**：使用者可以從 intro 選擇角色／戰術、在一局中移動瞄準射擊、使用技能並以重新開始回到初始流程。

### Phase 4：完整戰鬥、PvE、地形與撤離

- 實作三種怪物行為、四個營地的導航、怪物投射物、牆體碰撞、草叢可見性和地形破壞效果；角色技能造成的 slow／root 由角色規則處理。
- 實作六種角色的差異化武器／被動、三種戰術、自動瞄準 0.20 秒 lookback、動畫方向／幀和效果生命週期；怪物保存最後有效傷害玩家，強化倍率依每層 3% 計算。
- 實作完整世界／相機／HUD、生命回復、死亡／重生、撤離進度、結果頁和 240 秒終止。
- 實作 F1 開關、1–5 選取假玩家、M 放入中央撤離區、N 返回出生點與 developer overlay，並限制 debug 資訊不洩漏到正常玩家 HUD。

**完成條件**：六角色、三戰術、三怪物、四營地、地形、撤離和結果情境均可由自動測試及代表性人工遊玩驗證。

### Phase 5：資源、responsive 與 fallback

- 完成 `public/assets/` 資源 manifest、快取、角色／地圖 PNG 對應；初始資料載入期間顯示 loading 頁，完成所有載入嘗試後才解除 gate，並保留幾何 fallback。
- 完成 16:9 Canvas resize、1024×576、1280×720 與寬視窗驗證；修正高 DPI 與滑鼠座標換算。
- 完成 DOM 選角／結果可及性、鍵盤 focus、錯誤訊息、無障礙名稱和必要 metadata。
- 在有意義的本機預覽確認後產生 `og.png`，更新頁面 title、description 和 favicon 等靜態資源。

**完成條件**：資源遺失不造成白屏；資料載入期間不顯示可開始遊戲或建立比賽，載入完成後才進入 intro；resize 後遊戲仍可操作；intro、選角和結果可只用鍵盤使用。

### Phase 6：驗證與私人 Sites 發布

- 執行 `npm run test`、`npm run build` 和本機 preview；必要時修正測試或文件。
- 以 Sites 建立／確認專案，將 project id 保存到 `.openai/hosting.json`，使用 `pvpve-escape-web` 建立 private production。
- 在 production URL 以已授權擁有者與未授權瀏覽器 session 執行 quickstart 的代表性情境，確認 owner-only/private access policy、靜態資源路徑、直接開啟入口、重新整理、Canvas、metadata 和 fallback。
- 進行本地 code review、變更文件同步、發行紀錄；將功能分支推送至遠端並建立指向 `specs/010-pvpve-escape-web/` 的 PR，只有遠端確認合併後才依 project-release 流程清理分支。

**完成條件**：私人 URL 能載入並完成代表性流程，且沒有父專案 Python／Pygame／本機服務依賴；發布資訊和驗證結果可追溯。

### Phase 7：原版 parity closure

- 逐項比對原始常數、18 個矩形地形展開結果、spawn／camp、六角色 action 預設與 dummy 更新行為；以 deterministic parity fixture 鎖定結果。
- 逐項比對 `rendering.py` 的 intro、選角、世界、玩家／怪物、HUD、developer 與 result 的邏輯座標、固定文案、繪製順序和資訊隱私；移除瀏覽器版額外可見 UI。
- 重新執行 typecheck、lint、完整 Vitest、production build，推送同一 Sites source repository 後只更新既有 private project 的 saved version／deployment。

**完成條件**：SC-012／SC-013 的 parity fixture 與自動檢查通過；尚待本機長時間效能量測及已授權／未授權 production session smoke test。

## 驗證策略

### 自動測試分組

- **模型與邊界**：6 名玩家、12 隻怪物、4 個營地、canonical enum 對照、世界／邏輯座標、所有數值上下限。
- **角色與戰鬥**：六角色／三戰術定義、左鍵普攻、右鍵大招、Space 戰術、自動補彈、能量、升級、最後傷害歸屬、護盾、傷害、效果和冷卻。
- **世界與地形**：玩家移動、障礙阻擋、薄牆／草叢破壞、草叢可見性、怪物導航、投射物邊界和碰撞。
- **瞄準與動畫**：滑鼠座標轉換、方向角、auto-aim 0.20 秒 lookback、動畫幀／效果時間，以及 frame sampler 的 60 秒平均 FPS。
- **資源與啟動閘門**：地圖／角色預載、loading 畫面、載入期間快捷鍵阻擋、完成後才顯示 intro／建立 match，以及失敗資源 fallback。
- **生命週期與撤離**：五秒離戰回復、死亡／重生、210 秒開放、10 秒進度、離區中斷、240 秒結果；撤離測試至少 20 個 deterministic cases。
- **輸入與隱私**：pressed／held 一次性消費、Canvas focus 邊界、Canvas 外 pointerup／pointercancel 清除、失焦清除、Esc/Enter 流程、private/public HUD view。

### 人工與建置檢查

- 本機 dev／preview：依 `quickstart.md` 六組情境走完至少一次，並記錄瀏覽器與 viewport；SC-004～SC-006 各自記錄至少 20 個 deterministic cases。
- Build：確認產物只含網站自己的靜態檔案和依賴，無父目錄相對路徑或未處理 import。
- Visual：確認 Canvas 世界、角色、怪物、地形、HUD、結果頁在 16:9 中不裁切，圖片 fallback 可辨識；以 frame sampler 在固定環境量測至少 60 秒且平均至少 55 FPS。
- Sites：分別用已授權與未授權 session 確認 private production URL 的存取邊界；授權 session 可直接開啟、重新整理不 404、`/assets/` 可取得、標題／metadata 正確，並完成一次從 intro 到結果／重新開始的流程。

## 複雜度追蹤

| 例外／增加的複雜度 | 為何必要 | 取代方案與控制措施 |
|---|---|---|
| 新增 TypeScript／React／Vite／Canvas，而非沿用 Python/Pygame | 瀏覽器不能直接執行 Pygame 視窗和事件迴圈；必須產出可部署的靜態網站 | Pyodide、iframe 和遠端 Pygame 會增加執行與部署依賴；以 `src/game` 純核心、Vitest、既有 Python 行為對照和人工 parity 情境控制差異。 |
| 建立獨立 `pvpve_escape_web/` 與 Sites hosting 設定 | 要保留已發布桌面版，並讓網站有獨立 Node/build/assets 邊界 | 若把網站混入父專案，會污染 Python 依賴與發行邊界；新目錄、共享資源的明確複製來源、獨立 build 和 `.openai/hosting.json` 限制影響面。 |
| 初始載入新增一次性資源 loading gate | 避免資料尚未可用時顯示可開始入口或建立比賽，同時讓選角與對局共用同一份已載入資源 | 不在 `PlayingScreen` 內延遲載入；以 `App` 外層 gate、不可互動的 loading 畫面、promise cache 與 fallback 控制啟動邊界。 |
