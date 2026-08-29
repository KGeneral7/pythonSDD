# 實作計畫：狙擊者 Q 版像素外觀與八方向動畫

**分支**：`009-sniper-sprite-animation` | **日期**：2026-08-29 | **規格**：`specs/009-sniper-sprite-animation/spec.md`

**輸入**：`specs/009-sniper-sprite-animation/spec.md` 中的偵察狙擊兵視覺身份、八方向待機／移動／攻擊動畫、選角／對局／玩家列表整合、幾何 fallback 與不改變遊戲規則需求。

## 摘要

將狙擊者的幾何外觀替換為專案一致的 Q 版像素圖片：八個面向各一張待機圖、四張移動圖與四張攻擊圖，共 72 張獨立 PNG。素材先以 `pixel-character-animation` 技能與內建 `image_gen` 產生並逐張驗收；`sample.png` 只作為畫法參考，不帶入其背景或配色。來源圖再以角色身體核心而非武器外伸作固定比例基準。

程式部分把目前破陣者專用的圖片載入、驗證、裁切、縮放、快取與錯誤診斷抽成小型角色資產規格映射，保留既有破陣者介面並加入狙擊者介面。狙擊者素材以頭部錨點及每方向動畫的身體核心聯合外框統一整套來源圖比例，武器外伸不參與本體縮放，顯示時保留固定來源畫布，確保走路幀與所有角度的角色本體佔位一致。玩家動畫狀態、攻擊優先級與共同繪製入口維持單一責任邊界；狙擊者圖片不可用時回到既有幾何外觀，不改變任何戰鬥規則。

## 技術背景

**語言／版本**：Python 3.11（目前虛擬環境為 Python 3.11.5）

**主要依賴**：`pygame>=2.5,<3`（目前為 Pygame 2.6.1）；不新增第三方套件

**儲存**：版本控制內的 PNG 圖片，位於 `pvpve_escape/assets/characters/sniper/`；無資料庫、遠端服務或持久化動畫資料

**測試**：既有 `unittest`、headless Pygame 繪製測試、資產完整性測試與可重複的手動遊戲驗證

**目標平台**：Windows 桌面 Pygame 應用程式

**專案類型**：單一桌面遊戲專案

**效能目標**：在選角畫面或對局開始前預載入破陣者與狙擊者的 144 個來源幀，並暖身 50×50、54×54、24×24 三種顯示快取（最多 432 個顯示表面）；預載入完成後繪製期間不重新讀檔；連續遊玩 10 秒平均至少 60 FPS，任一單幀間隔不超過 100 毫秒

**限制**：來源圖片固定 1024×1024 RGBA；四角透明、角色不貼邊或裁切；對局固定 50×50 顯示；不執行期旋轉或鏡像圖片；圖片失效必須幾何 fallback；不得改變傷害、碰撞、速度、蓄力、彈藥、技能、死亡重生、地圖、其他角色或怪物行為

**規模／範圍**：1 個新角色、8 個方向、3 種視覺狀態、72 張狙擊者圖片；修改共用像素載入／繪製管線以保護既有 72 張破陣者圖片；新增或調整必要的動畫、繪製與回歸測試

## 憲章檢查

### Phase 0 前檢查

| 原則 | 結果 | 依據 |
|---|---|---|
| I. 小步驟、可執行的學習 | 通過 | 資產製作、載入器、動畫狀態、對局繪製、UI 整合與回歸測試分成可獨立驗證的階段。 |
| II. 先理解再自動化 | 通過 | 已盤點 `characters.py`、`models.py`、`sprites.py`、`world.py`、`rendering.py`、`main.py` 與既有 008 流程，研究結論記錄於 `research.md`。 |
| III. 用清楚的 Python 基礎承載功能 | 通過 | 沿用既有函式與資料類別，以小型角色規格映射消除重複載入邏輯，不引入大型框架或新套件。 |
| IV. 以資料、狀態與邊界描述互動行為 | 通過 | 面向、移動／攻擊時間、資產查詢、顯示尺寸、透明驗證與 fallback 均有明確欄位與邊界。 |
| V. 每個功能都要被驗證 | 通過 | `quickstart.md` 定義資產、方向、動畫、技能、死亡／重生、fallback、回歸與效能的自動及手動驗證。 |
| VI. SDD 文件語言一致性 | 通過 | 本功能 SDD 文件以繁體中文撰寫，程式識別字、路徑、Pygame 與 `unittest` 等技術字串保留正確原文。 |
| VII. 依 Spec Kit 管理分支與 PR 生命週期 | 通過 | 已建立 `009-sniper-sprite-animation` 分支與同名 `specs/` 功能目錄；完成後依憲章保留至 PR 合併。 |

## 設計決策

### 素材目錄與品質閘門

使用每格獨立 PNG，不製作 sprite sheet：

```text
pvpve_escape/assets/characters/sniper/
├── idle/<direction>.png
├── move/<direction>/frame_01.png ... frame_04.png
└── attack/<direction>/frame_01.png ... frame_04.png
```

方向固定為 `right`、`down_right`、`down`、`down_left`、`left`、`up_left`、`up`、`up_right`，順序索引為 0～7。所有 72 張圖片必須為 1024×1024 RGBA，四角 alpha 為 0，非透明像素不貼邊，同方向幀的非透明內容中心偏移不超過 16 個來源像素；每個方向以待機頭盔／面罩高度與 idle／move／attack 的身體核心聯合外框作比例錨點，武器外伸不納入角色本體尺寸，整張角色（含武器）保持完整且動畫比例一致。

角色身份固定為深藍／藍灰偵察服、低矮細長輪廓、長槍、瞄具與既有青藍狙擊者識別色。`sample.png` 僅吸收像素邊緣、比例與簡化節奏；不要複製其背景、文字或色彩。創意、方向、比例、持槍接點或像素內容錯誤必須重新生成；只有 alpha、畫布與置中等格式問題可作確定性整理。

### 資產載入與快取

在 `pvpve_escape/sprites.py` 內建立角色資產規格映射，至少包含角色 ID、資產根目錄、來源尺寸、對局／選角／列表尺寸、預載入尺寸、方向名稱、幀數、動畫時間與 `fit_mode`。共用載入流程依序處理：查詢值驗證 → 固定路徑 → 檔案存在與圖片可讀取 → 尺寸與四角透明驗證 → 以 `alpha > 0` 檢查可見內容與邊界 → 來源快取 → `alpha >= 64` 可見像素品質閘門 → 依角色規格選擇固定來源畫布或可見外框 → 最近鄰縮放與顯示快取；狙擊者來源圖必須先以每方向全部動畫幀的身體核心聯合外框完成標準化，不能讓武器外伸決定比例。

快取鍵必須包含角色 ID、視覺狀態、方向、幀與顯示尺寸，避免破陣者與狙擊者互相覆蓋。圖片錯誤回傳 `None`，由繪製層 fallback；同一資產鍵在快取生命週期內只產生一次警告。資產初始化時清除兩個像素角色的快取，對每個角色預載入 72 個來源幀，兩個角色合計 144 個來源幀，並暖身 50、54、24 三種顯示尺寸；如此選角、玩家列表與對局都不會在繪製期間重新讀檔。這裡的 144 是兩個角色的來源圖片總數，三種尺寸的顯示快取最多為 432 個表面。

### 動畫狀態與方向

沿用 `PlayerState.animation_state` 與既有 `PlayerAnimationState`，不新增戰鬥欄位，也不重用 `last_attack_time`。在 Pygame 螢幕座標中令右方為 0 度、`y` 正方向向下，令 `angle = atan2(y, x)` 使用弧度，並以 `floor((angle + pi / 8) / (pi / 4)) % 8` 量化；正好落在 22.5 度分界時歸入順時針側，零向量不改變狀態中的面向，初始面向為右。移動每格 0.10 秒循環四格；攻擊每格 0.06 秒、總長 0.24 秒。

狙擊者蓄力期間只更新既有蓄力欄位，不啟動攻擊動畫；成功建立普攻、戰術配件或終極技能時，在共同 `_apply_action()` 邊界啟動攻擊動畫。若攻擊尚未生效，啟動時將 `attack_elapsed` 設為 0；若已在攻擊中，重新成功動作不重設目前幀，只將 `attack_hold` 設為 `max(目前值, 0.24)`。每次更新以非負時間增加 `attack_elapsed` 並上限於 0.24，再扣減 `attack_hold`；`attack_hold <= 0` 時清除攻擊進度。攻擊期間優先於移動，完成後依當下移動狀態回到移動或待機；死亡與重生清除移動／攻擊進度並保留既有面向。

### 繪製責任邊界

- `config.py`：新增狙擊者資產根目錄、來源尺寸、`source_canvas` 顯示模式、50×50 對局尺寸、54×54 選角尺寸、24×24 玩家列表尺寸；來源圖先完成每方向 idle／move／attack 身體核心聯合外框標準化，共用動畫時間與方向／幀常數，保留既有 `BREACHER_*` 相容常數。
- `models.py`：將 `PlayerAnimationState` 說明改為角色中立；維持欄位、預設值與 positional 建構相容性。
- `sprites.py`：新增角色資產規格、狙擊者載入／預載入／錯誤查詢介面，保留破陣者介面；集中處理方向、驗證、依 `fit_mode` 選擇固定來源畫布或可見外框、縮放、快取與一次性診斷，讓狙擊者使用固定身體核心比例且不受單幀武器外框影響。
- `world.py`：讓破陣者與狙擊者在成功動作套用時啟動共同攻擊動畫；移動更新仍只負責動畫狀態與既有位置流程，不改速度與碰撞。
- `rendering.py`：`draw_player_visual()` 依角色選擇像素資產或幾何 fallback；選角與玩家列表傳入狙擊者尺寸；血條、名稱、瞄準線、死亡、護盾與控場標記維持原資訊層。
- `main.py`：資產初始化時清除並透過角色中立預載入介面暖身破陣者與狙擊者的三種顯示尺寸；其他角色不載入像素圖片。

### 模組介面

保留既有介面並新增角色中立／狙擊者介面：

```text
load_character_sprite(character_id, visual_state, direction_index, frame_index, display_size=None)
load_breacher_sprite(visual_state, direction_index, frame_index, display_size=None)
load_sniper_sprite(visual_state, direction_index, frame_index, display_size=None)
preload_character_sprites(character_id, display_sizes=None)
preload_breacher_sprites(display_size=50)
preload_sniper_sprites(display_sizes=None)
clear_character_sprite_cache(character_id=None)
character_sprite_error(character_id, visual_state, direction_index, frame_index)
```

`display_sizes=None` 時由該角色的 `CharacterSpriteSpec.preload_display_sizes` 提供預載入尺寸；只有呼叫端需要特殊暖身範圍時才傳入明確尺寸。

既有 `quantize_sprite_direction()`、`current_sprite_request()`、`update_player_animation()`、`start_or_refresh_attack_animation()` 與 `draw_player_visual()` 保持呼叫責任與行為；它們改為角色中立，不增加對外 HTTP、RPC 或資料交換契約。

### Fallback 與相容性

圖片不存在、讀取失敗、尺寸錯誤、四角不透明、空白、裁切或無效查詢都只影響視覺結果。`draw_player_visual()` 轉回目前的幾何狙擊者／破陣者外觀；世界更新、戰鬥結果、角色狀態與其他角色／怪物流程不因資產錯誤改變。破陣者的原有函式與 72 張資產測試必須持續通過。

## 公開／模組介面與資料流

本專案沒有外部服務契約；上述介面是本地模組介面。完整資料流如下：

```text
aim_direction + move input
        │
        ▼
PlayerAnimationState ── successful action ──> attack state
        │                                      │
        ▼                                      ▼
current_sprite_request ──> character sprite loader/cache
                                      │
                           valid image │ invalid image
                                      ▼             ▼
                              pixel sprite     geometry fallback
                                      │
                                      ▼
                         selection / roster / match renderer
```

## 測試策略

- `pvpve_escape/tests/test_sprite_animation.py`：參數化驗證破陣者與狙擊者各 72 張圖片、路徑、方向、分界角、幀範圍、透明度門檻、非透明邊界、中心偏移、狙擊者頭部錨點與各方向 idle／move／attack 身體核心聯合外框標準化、武器不參與本體縮放、狙擊者固定來源畫布與破陣者可見外框顯示模式、快取、三種尺寸預載入與錯誤一次性警告；驗證狙擊者成功普攻／戰術／終極技能會進入攻擊狀態，蓄力、無彈藥、冷卻中或其他失敗條件不會誤觸發，並驗證攻擊刷新與 0.24 秒結束邊界。
- `pvpve_escape/tests/test_rendering.py`：驗證狙擊者在對局、選角與玩家列表使用像素圖，攻擊優先於移動，素材失效時使用幾何 fallback，文字與狀態資訊仍可見；驗證存活角色沒有常駐底圈、死亡／護盾／控場標記仍繪製，其他角色與怪物仍走原本繪製路徑。
- 既有 `pvpve_escape/tests/` 全套回歸：保護角色數值、戰鬥、碰撞、地圖、可見性、怪物與輸入流程。
- `pvpve_escape/tests/test_sprite_performance.py`：在 headless surface 上先完成兩個像素角色三種尺寸預載入，再量測 10 秒繪製；記錄平均 FPS、最大單幀間隔與 `pygame.image.load` 呼叫次數，要求平均至少 60 FPS、最大單幀間隔不超過 100ms，量測區間讀檔次數為 0。

## 實作順序與檢查點

1. 先生成並驗收狙擊者 72 張圖片；資產數量、格式與人工視覺 QA 通過後才接入程式。
2. 建立角色中立資產載入／快取介面，保留破陣者相容性，完成狙擊者資產與 loader 測試。
3. 接入共用動畫狀態與 `_apply_action()`，確認狙擊者移動、成功攻擊與死亡／重生狀態不改變遊戲規則。
4. 接入對局、選角、玩家列表與資產初始化預載入，完成像素／幾何 fallback 測試。
5. 執行 quickstart 的完整自動、效能與人工驗收，更新文件紀錄。
6. 所有驗證通過後依憲章將功能分支推送至遠端並建立 PR，保留分支至 PR 合併後再清理。

## Phase 1 設計後覆核

| 原則 | 結果 | 依據 |
|---|---|---|
| I. 小步驟、可執行的學習 | 通過 | 依序拆分資產 QA、載入器、狀態、繪製與回歸檢查點，每一步都有可執行測試。 |
| II. 先理解再自動化 | 通過 | 研究已釐清既有破陣者流程、狙擊者動作接點與跨畫面繪製責任，沒有未解技術問題。 |
| III. 用清楚的 Python 基礎承載功能 | 通過 | 使用有限的資料映射與共用函式，保留既有介面，沒有引入不必要的抽象或套件。 |
| IV. 以資料、狀態與邊界描述互動行為 | 通過 | `PlayerAnimationState`、資產查詢、快取鍵、alpha／邊界驗證、固定顯示尺寸與 fallback 均已定義。 |
| V. 每個功能都要被驗證 | 通過 | `data-model.md`、`quickstart.md` 與測試策略涵蓋正常、邊界、失敗、死亡／重生及效能情境。 |
| VI. SDD 文件語言一致性 | 通過 | `research.md`、`data-model.md`、`quickstart.md` 與本計畫均使用繁體中文。 |
| VII. 依 Spec Kit 管理分支與 PR 生命週期 | 通過 | 分支、功能目錄與計畫欄位均使用 `009-sniper-sprite-animation`，並納入 PR 與分支保留規則。 |
