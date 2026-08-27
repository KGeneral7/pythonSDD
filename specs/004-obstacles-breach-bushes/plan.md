# 實作計畫：地圖障礙物、破牆、草叢視線與戰鬥恢復

**功能識別字**：004-obstacles-breach-bushes
**預定功能分支**：codex/004-obstacles-breach-bushes（本次依使用者要求保留現行工作樹）
**實作工作樹**：codex/003-combat-vfx-cone-ammo
**本次交付分支**：codex/003-combat-vfx-cone-ammo（與 003、005 的已驗證變更整合交付）
**日期**：2026-08-27
**規格**：[spec.md](spec.md)
**輸入**：004 號功能規格、研究決策與既有 pvpve_escape 程式結構。

> 依使用者先前要求保留目前工作，本次規劃與實作均不切換 `codex/003-combat-vfx-cone-ammo` 工作分支，也不覆蓋其未提交內容；功能目錄與 SDD 文件仍使用 004 號功能識別字。使用者現在已明確授權 PR、發布與合併，因此本次以現有分支作為整合交付分支，完成後回填外部 Git 結果。

## 摘要

本功能會在現有 Pygame PvPvE 原型加入固定且經使用者確認的厚牆、薄牆與草叢配置。配置不要求幾何鏡像，正式座標以地圖配置編輯器送出的 JSON 為準；本次 18 個牆體與 16 個草叢的紅框重疊均保留，改以警示與路線驗收追蹤。牆體使用和地面不同的顏色，厚牆不可破壞，薄牆可由破陣者的主要/終極技能與 DASH 配件破壞；玩家與怪物不能穿牆，直線/光束/飛行技能在第一面牆前停止。破陣者的遠程破壞在移除薄牆後仍結束本次路徑，DASH 則破壞第一面薄牆並完成剩餘位移。

技術上會在純 Python 模型增加軸對齊矩形與地形狀態，新增小型 terrain.py 共用圓形碰撞、線段掃掠、路徑端點、破壞與草叢判定。world.py 使用同一套地形結果處理玩家、怪物與技能；rules.py 增加受擊/攻擊雙計時器和最大生命值 10%/秒的恢復；rendering.py 依 viewer_id 控制草叢內玩家的顯示，讓自己看見自己、其他觀看者看不見角色資訊。所有資料仍只存在單局記憶體，不新增依賴或外部服務。

## 技術上下文

**語言／版本**：Python 3.11.5

**主要依賴**：Pygame 2.6.1；Python unittest；既有無頭 SDL 測試設定

**儲存**：N/A；地形破壞、草叢有效狀態與戰鬥計時只保存在單局 MatchState

**測試**：unittest 純規則與世界整合測試、SDL_VIDEODRIVER=dummy 的 Pygame.Surface 冒煙測試、compileall、git diff --check，以及 quickstart 手動驗收

**目標平台**：Windows 桌面 Pygame，視窗 1280×720，世界 2400×1400

**專案類型**：既有單一 Pygame 2D 桌面遊戲套件 pvpve_escape

**效能目標**：在 1280×720 本地視窗、6 名玩家、最多 12 隻怪物與固定地形的正常場景中，先預熱後至少完成 600 個更新/繪製迴圈，以實際經過秒數計算平均值，結果維持至少 55 FPS；地形查詢成本維持為小型線性掃描，不在每幀重新建立固定配置

**限制**：不新增第三方套件、外部素材、網路服務、資料庫或持久化格式；保留既有角色、彈藥、技能、怪物、死亡、重生、撤離、勝負和 GUI 行為；保留工作區中使用者目前未提交的變更

**規模／範圍**：6 名玩家、6 種角色、3 種配件、4 個怪物區、每區 3 隻怪物、固定牆/草叢配置、單一人類觀看視角加可測試的 viewer_id 參數

## 憲章檢查

| 憲章原則 | 設計檢查 | 結果 |
|---|---|---|
| I. 小步驟、可執行的學習 | 依序拆成資料/幾何、移動/路徑、破壞、渲染、恢復、回歸六個階段；每階段先跑對應測試再進下一階段 | 通過 |
| II. 先理解再自動化 | 已產出 spec.md、research.md、data-model.md；計畫明確描述地形資料、碰撞邊界、破牆快照、恢復公式與更新順序 | 通過 |
| III. 用清楚的 Python 基礎承載功能 | 延伸既有 dataclass、enum、函式與集中設定；只新增一個不依賴 Pygame 的 terrain.py，避免物理引擎與過度抽象 | 通過 |
| IV. 以資料、狀態與邊界描述互動行為 | 以 WorldRect、ObstacleState、BushState、TerrainHitResult、TerrainInteraction、前後位置和雙戰鬥計時器明確表示輸入/更新/碰撞/繪製邊界 | 通過 |
| V. 每個功能都要被驗證 | 新增地形、恢復、可見性與渲染測試，並在 quickstart 提供牆角、牆後目標、破壞、多視角、5 秒門檻與重開手動驗證 | 通過 |
| VI. SDD 文件語言一致性 | 本功能的 spec.md、plan.md、research.md、data-model.md、quickstart.md 與 tasks.md 均使用繁體中文；程式識別字和命令保留原始拼寫 | 通過 |
| VII. 依 Spec Kit 管理分支與 PR 生命週期 | 功能目錄和文件使用 004-obstacles-breach-bushes；本次因跨功能變更已在現行 codex/003-combat-vfx-cone-ammo 整合，並由 T036 追蹤已授權的 PR、發布與合併結果 | 通過（整合例外與交付追蹤已記錄） |

### 設計門檻結論

設計門檻通過。為了不打斷當時進行中的工作，本次在現行 `codex/003-combat-vfx-cone-ammo` 工作樹完成實作；T002 已記錄分支例外與工作內容保留，T031～T035 已完成。現在已取得外部 Git 授權，T036 將以此現行分支完成整合 PR、發布與合併，不修改或重置其他未提交內容。

## 專案結構

### 本功能文件

    specs/004-obstacles-breach-bushes/
    ├── spec.md
    ├── plan.md
    ├── research.md
    ├── data-model.md
    ├── quickstart.md
    ├── map-layout-draft.json    # 使用者確認的配置 JSON 快照
    ├── checklists/
    │   └── requirements.md
    └── tasks.md                 # 由 speckit-tasks 產生，已完成任務拆解

本專案是內部桌面應用，沒有公開 API、CLI 協定或跨服務介面，因此不建立 contracts/ 目錄。

### 原始碼與測試

    pvpve_escape/
    ├── config.py                # 地圖配置、顏色、恢復常數
    ├── models.py                # 幾何、地形、玩家與動作資料類別
    ├── terrain.py               # 新增：地形建立與共用幾何/狀態輔助函式
    ├── characters.py            # 角色/配件的地形互動資格
    ├── aiming.py                # 使用地形端點的瞄準預覽
    ├── rules.py                 # 受擊/攻擊計時、恢復、死亡重置
    ├── world.py                 # 單局初始化、移動、技能路徑、破壞與更新順序
    ├── rendering.py             # 牆、草叢與觀看者特定的玩家顯示
    └── tests/
        ├── test_terrain.py      # 新增：資料、配置、碰撞、路徑與破壞
        ├── test_regeneration.py # 新增：恢復門檻、速率、重置與生命週期
        ├── test_visibility.py   # 新增：草叢可見性和不改變戰鬥規則
        ├── test_aiming.py       # 補充：瞄準端點不越牆
        ├── test_rendering.py    # 補充：地形層、顏色和隱藏玩家
        └── test_rules.py        # 補充：世界整合和既有回歸

**結構決策**：沿用現有單一 Pygame 模組分層。terrain.py 僅負責可在純數值環境驗證的地形資料與幾何；world.py 負責把地形結果套用至遊戲流程；rules.py 負責玩家生命與計時；rendering.py 只負責畫面和 viewer_id 顯示。main.py 與 controllers.py 不需新增輸入按鍵，因為重開已透過 create_match 建立新地形，觀看者預設為人類玩家 0。

## 實作設計

### 1. 地形資料與集中設定

在 models.py 增加：

- ObstacleKind enum：THICK_WALL、THIN_WALL。
- WorldRect dataclass：left、top、width、height，以及 right、bottom、center 導出屬性。
- ObstacleState dataclass：obstacle_id、kind、bounds、destroyed。
- BushState dataclass：bush_id、bounds、active。
- TerrainHitResult dataclass：第一面牆、距離、有效停止點、blocked、destroyed。
- TerrainInteraction enum：BLOCK、BREAK_THIN_ON_PATH、BREAK_THIN_IN_AREA、DASH_BREAK_FIRST_THIN。

在 MatchState 最後增加 obstacles 和 bushes 欄位，避免改變既有 positional 建構；在 PlayerState 最後增加 last_attack_time，保留 last_damage_time 的原有經過秒數語意。CombatAction 與 AbilityEffect 在既有欄位末端增加 terrain_interaction 預設值，讓目前直接以 positional 建構的角色動作保持相容。

在 config.py 增加：

- OBSTACLE_LAYOUT：依使用者確認 JSON 寫入的 18 個固定牆型和矩形資料 tuple。
- BUSH_LAYOUT：依使用者確認 JSON 寫入的 16 個固定草叢矩形資料 tuple。
- THICK_WALL_COLOR=(115, 93, 105)。
- THIN_WALL_COLOR=(212, 143, 62)。
- WALL_BORDER_COLOR=(235, 240, 242)。
- BUSH_COLOR=(74, 156, 91)、BUSH_HIGHLIGHT_COLOR=(144, 211, 116)。
- WALL_BORDER_WIDTH=2、THIN_WALL_CRACK_WIDTH=1、THIN_WALL_CRACK_COUNT=2。
- PLAYER_REGEN_DELAY=5.0、PLAYER_REGEN_RATE=0.10。
- TERRAIN_GEOMETRY_EPSILON、TERRAIN_SPAWN_SAFE_RADIUS=72.0、TERRAIN_CAMP_SAFE_RADIUS=94.0 與 TERRAIN_EXTRACTION_SAFE_PADDING=20.0。

固定配置不要求世界中心鏡像；terrain.py 建立每場的獨立 dataclass 物件。建立測試確認 34 個矩形完全落在世界內、牆型與草叢數量符合已確認配置，並將編輯器紅框重疊列為已核准的警示清單，而非建立失敗條件。重開由 main.py 既有的 create_match 路徑自動取得全新物件，不增加全域可變地圖。

### 2. terrain.py 的共用幾何介面

terrain.py 不匯入 Pygame，也不匯入 world.py，避免模型和世界更新循環依賴。預計提供下列單一責任函式：

| 函式責任 | 主要輸入 | 主要輸出 |
|---|---|---|
| create_obstacles | 固定配置 | 每場獨立的 ObstacleState 清單 |
| create_bushes | 固定配置 | 每場獨立的 BushState 清單 |
| circle_overlaps_rect | 圓心、半徑、WorldRect | 是否重疊 |
| move_circle_with_obstacles | 位置、位移、半徑、牆體 | 不穿牆的新位置 |
| first_obstacle_on_segment | 起點、終點、路徑半徑、牆體 | TerrainHitResult |
| resolve_path_endpoint | 起點、方向、距離、半徑、牆體 | 牆前端點與阻擋結果 |
| destroy_thin_wall_on_path | 路徑、破壞政策、牆體 | 是否移除薄牆與 TerrainHitResult |
| destroy_terrain_in_radius | 中心、半徑、破壞政策、牆/草叢 | 被移除的物件數量 |
| destroy_bushes_on_segment | 路徑、草叢 | 更新 active 並回傳移除數量 |
| is_player_in_bush | PlayerState、草叢 | 是否位於有效草叢 |
| is_player_visible_to_viewer | PlayerState、viewer_id、草叢 | 觀看者是否可見 |

線段與矩形交集使用 slab/軸向區間方法，先以路徑半徑膨脹矩形，再選取最小進入距離；移動使用 X 後 Y 的軸向分離修正，保持斜向接觸時停止或沿牆滑動。所有距離與比較使用既有 GEOMETRY_EPSILON，並在世界邊界最後套用 clamp_position。

草叢不進入固體碰撞清單。destroy_bushes_on_segment 只改變 active，不影響路徑端點；is_player_in_bush 使用存活玩家的中心點落入任一 active bounds 作為簡單、可測試的判定。

### 3. 玩家、怪物與技能的牆碰撞

create_match 建立 players/monsters 後呼叫 create_obstacles 和 create_bushes。update_player_movement 增加可選的牆體輸入，讓舊測試不傳牆時仍保持世界邊界行為；world.py 的人類移動傳入 match.obstacles。update_monsters 保留最近目標追擊，不新增尋路，只將預定位移交給 move_circle_with_obstacles。

將 _advance_projectile 改成能取得 match.obstacles，使用 effect.previous_position 到預定位置的連續線段。遇到牆時：

- sniper_line：位置停在牆前，保存地形阻擋狀態，像既有命中 marker 一樣短暫保留畫面提示。
- sniper_ultimate_line：施放時先解析牆前端點，再只對該線段內目標結算。
- boomerang：去程在牆前轉為回程；回程也再次檢查牆，不得穿越。
- mine：飛行段在牆前落地並進入 armed 狀態，不能穿到牆後落點。
- beam：每次 tick 重新解析從施放者到牆前的可見線段。
- hunter_dash：使用一般 BLOCK 政策，在牆前停止，路徑傷害只檢查牆前段。
- tactical_control、gravity_cage：投放端點在牆前，不讓飛行/直線段把控制區放到牆後。
- radial burst、shield 等不沿路徑移動的效果維持既有範圍規則；破陣者爆發另外執行薄牆/草叢範圍破壞。

_targets_in_segment、_targets_in_line 和立即結算的 sniper ultimate 需使用解析後端點或地形快照，先處理牆再處理目標。這確保牆後目標即使幾何上仍在技能射程內，也不會被牆前技能影響。

### 4. 破牆資格與動作流程

在 characters.py 建立角色動作時設定地形政策：

| 動作 | terrain_interaction | 行為 |
|---|---|---|
| 破陣者 breach_cone | BREAK_THIN_ON_PATH | 薄牆可破壞，遠程本次 effect 在牆前結束 |
| 破陣者 breach_burst | BREAK_THIN_IN_AREA | 爆發範圍內薄牆/草叢移除，厚牆保留 |
| DASH tactical_dash | DASH_BREAK_FIRST_THIN | 第一面薄牆移除後繼續剩餘位移 |
| 其他主要/終極/配件 | BLOCK | 牆前停止，不破壞 |
| hunter_dash | BLOCK | 牆前停止，不破壞 |

破陣者 breach_cone 建立 effect 時先複製所有尚未破壞牆的 obstacle_id、kind、bounds 到 terrain blocker snapshot。第一次地形處理依扇形/路徑找到符合的薄牆並設 destroyed=True；後續目標檢查仍使用 snapshot，所以本次施放不能因薄牆已消失而穿過缺口。五個 breach_pellet 僅負責視覺呈現，不直接改動地形或生命。

breach_burst 在既有圓形目標結算前，呼叫範圍破壞輔助函式；厚牆不會變更。DASH 則循環解析剩餘線段：無牆時走完、厚牆時停在牆前、第一面薄牆時移除並扣除到牆前的距離後繼續。DASH 路徑上的所有草叢可被移除但不阻擋；下一面仍存在的牆仍會停止衝刺。

### 5. 戰鬥恢復與更新順序

在 rules.py 增加：

- mark_player_hit(player)：存活玩家被有效攻擊命中時將 last_damage_time 歸零；有效命中包含敵方控場命中、傷害被護盾完全吸收、被減傷降為 0 或生命值沒有下降的情況，呼叫位置需在護盾吸收/減傷結果確定前。
- mark_player_attack(player)：只有成功建立攻擊 action/effect 或正在維持持續攻擊時才將 last_attack_time 歸零；冷卻或資源不足而未建立 action 時不得重置。
- regenerate_player_health(player, delta_time)：存活、未滿血、last_damage_time 和 last_attack_time 都至少 5 秒時，以 max_health * 0.10 * delta_time 加血並使用 min 截斷。

update_player_timers 每幀增加兩個計時器。apply_damage_to_player 保留既有實際扣血流程，並確保有效受擊事件在護盾吸收、減傷、免傷邊界仍有清楚的計時語意；handle_player_death、respawn_player 及 create_match 初始化歸零。死亡玩家不恢復，重生維持既有滿血規則。

world.py 的 update_world 順序調整為：

1. 更新 match 時間與玩家冷卻/短狀態計時。
2. 處理人類輸入、移動、建立 action；成功的攻擊和持續普攻標記 last_attack_time。
3. 更新 effect、投射物、地形命中、傷害、護盾與控場。
4. 更新怪物移動與接觸傷害；受擊時標記玩家。
5. 對所有玩家呼叫 regenerate_player_health。
6. 回復彈藥、移除死亡效果、更新撤離和勝負。
7. 更新鏡頭。

主要攻擊、傷害/控場終極技能、tactical_control 與具有傷害的 hunter_dash 算攻擊；普通 DASH、SHIELD、Guardian 防禦大招不算。吸能光束按住期間每幀維持攻擊標記，攻擊 action 因冷卻/資源不足沒有成立時不重置。恢復在所有本幀傷害後執行，因此同幀受擊不會額外回血。

### 6. 瞄準預覽與草叢觀看者渲染

aiming.py 的 build_aim_guide 增加可選 obstacles 參數，預設空集合以保持現有測試呼叫。rendering.py 的 draw_world 將 match.obstacles 傳入，讓線段/路徑/衝刺預覽使用和實際路徑相同的牆前端點；DASH 預覽以非變更模擬表示第一面薄牆可破壞、下一面牆會阻擋。草叢不會縮短任何預覽。

rendering.py 增加：

- draw_terrain：唯一負責牆和草叢幾何繪製的共用層，直接使用 config.py 的 18 個牆體與 16 個草叢矩形，確保每個已確認物件都會被正式遊戲畫面繪出；以 match.camera.position 做世界座標平移，依 `surface.get_rect()` 跳過完全在視窗外的物件並裁切跨越邊界的矩形，攝影機進入範圍即可看見物件。
- 地形層的實際順序為地面/網格 → 草叢 → 厚牆/薄牆 → 怪物/效果/角色 → HUD；草叢使用綠色幾何填充與葉片筆觸，厚牆使用深紫灰色加亮邊框，薄牆使用橘色加亮邊框與裂紋。牆放在草叢之後，避免重疊時牆的辨識被覆蓋；觀看者可見性不得在此重複繪製草叢。
- draw_world(..., viewer_id=0) 和 draw_match(..., viewer_id=0)：維持舊有位置參數，新增尾端預設。
- _draw_player_roster(..., viewer_id=0)：對非自身觀看者跳過草叢內玩家的玩家名單角色、編號與狀態。
- 玩家繪製迴圈在繪製死亡標記、角色形狀、瞄準線、生命條、控場/防禦狀態前呼叫 is_player_visible_to_viewer。被隱藏的玩家整段不畫；自己的玩家即使在草叢內仍完整畫出。
- 草叢本身所有 viewer 都畫出；離開 bounds 或 active=False 後下一次 draw 自動顯示玩家。

可見性只存在 rendering 分支，不傳入 _target_entries、apply_damage、update_monsters 或技能命中。這保證草叢不提供免傷、不可選取或碰撞例外。

### 7. 測試設計

| 測試位置 | 新增/修改內容 |
|---|---|
| tests/test_config.py | 已確認的 18 個牆體、16 個草叢、世界邊界、顏色/恢復常數與 9 筆紅框安全區警示 |
| tests/test_terrain.py | WorldRect 邊界、固定配置警示清單、玩家與怪物正面/斜向滑動、線段第一面牆、投射物半徑、薄/厚牆政策、DASH 多牆、草叢非阻擋與破壞、同場持續/新場重置 |
| tests/test_regeneration.py | 4.9 秒不回血、5.0 秒開始、1 秒 10%、最大值截斷、受擊/護盾/攻擊重置、普通 DASH/SHIELD 不重置、死亡/重生 |
| tests/test_visibility.py | 自己在草叢可見、他人視角隱藏角色資訊、離開/破壞後恢復、隱藏不改變目標/傷害結果 |
| tests/test_aiming.py | 線段/路徑端點受牆截斷，DASH 預覽與解析端點一致，舊版空 obstacles 仍維持原結果 |
| tests/test_rendering.py | 確認完整世界畫布上的 18 個牆體與 16 個草叢都有填色，並在實際 1280×720 視窗的不同相機位置確認牆/草叢可見；地形層先於角色/效果、viewer_id 下角色/玩家名單隱藏與自身顯示、既有技能效果仍可繪製 |
| tests/test_rules.py | create_match 地形欄位、技能整合的牆後不命中、破陣者/DASH 破壞資格、既有死亡/撤離回歸 |

所有對應 SC-001～SC-011 的新測試使用固定座標與固定 delta_time，實際情境至少重複 20 次；SC-009 另外檢查 4.9/5.0 秒門檻、完整 1 秒恢復量與既有數值精度容許範圍。純輔助函式測試不啟動視窗，渲染測試沿用 test_helpers.py 的 dummy video driver。保留既有函式的可選參數預設，避免現有測試因 API 擴充失效。

初始工作樹基線曾受未提交的 GUI、自動瞄準、投射物與戰鬥變更影響；本輪依使用者要求保留 `codex/003-combat-vfx-cone-ammo` 未提交內容，並讓地形無關的既有技能 fixture 使用空障礙物清單以維持測試責任邊界。完成整合後，完整套件實際為 159/159 通過；沒有以回復或重置使用者變更的方式消除基線差異。

## 實作階段與每階段檢查點

### 階段 A：模型、設定與純地形輔助函式

修改 models.py、config.py，新增 terrain.py 和 test_terrain.py 的資料/幾何部分。先驗證固定配置、WorldRect、圓形重疊、線段命中和移動滑動；此階段不改技能效果。

檢查：

    .\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_terrain -v
    .\.venv\Scripts\python.exe -m compileall -q pvpve_escape

### 階段 B：生物移動與技能路徑

把牆體傳入玩家/怪物移動，將路徑端點套入投射物、光束、地雷、回旋鏢、狙擊終極與其他飛行/直線效果；補上牆後目標整合測試。

檢查：

    .\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_terrain pvpve_escape.tests.test_rules pvpve_escape.tests.test_aiming -v

### 階段 C：破牆能力與同次施放邊界

在角色 action 設定 TerrainInteraction，完成 Breacher snapshot、Breacher burst 範圍破壞、DASH 第一面薄牆循環和草叢破壞；補測錯誤角色/配件與厚牆不可破壞。

檢查：

    .\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_terrain pvpve_escape.tests.test_rules -v

### 階段 D：地形與觀看者渲染

新增牆/草叢繪製、顏色/裂紋、viewer_id 和玩家名單隱藏，讓瞄準預覽使用地形端點；補上無頭 Pygame.Surface 與自身/他人視角測試。

檢查：

    .\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_visibility pvpve_escape.tests.test_rendering pvpve_escape.tests.test_aiming -v

### 階段 E：戰鬥恢復

增加 last_attack_time、受擊/攻擊標記和 regenerate_player_health，調整 update_world 的恢復位置，補上 4.9/5.0 秒、速率、護盾、攻擊、DASH/SHIELD、死亡/重生測試；每一類量化情境至少重複 20 次。

檢查：

    .\.venv\Scripts\python.exe -m unittest pvpve_escape.tests.test_regeneration pvpve_escape.tests.test_rules -v

### 階段 F：完整回歸與手動驗收

執行所有測試、compileall、git diff --check，啟動遊戲依 quickstart 驗證牆色、牆角、怪物阻擋、破牆、草叢自身/他人視角、恢復門檻與按 R 重置。

檢查：

    .\.venv\Scripts\python.exe -m unittest discover -s pvpve_escape\tests -p "test_*.py" -v
    .\.venv\Scripts\python.exe -m compileall -q pvpve_escape
    git diff --check
    .\.venv\Scripts\python.exe -m pvpve_escape

自動化驗證與入口煙霧驗收已完成；互動視覺情境列於 quickstart.md 供使用者開啟遊戲確認。T036 的功能分支推送、PR、發布與合併屬本次已授權的外部 Git 交付步驟，完成後回填實際結果。

## 風險與處理方式

- 牆體增加後，既有測試若使用固定座標剛好穿過新牆，優先調整測試夾具到明確的牆前/牆後位置，不放寬碰撞規則。
- 薄牆在遠程 action 中即時消失可能造成穿透，使用 effect 的 terrain blocker snapshot 解決；snapshot 只讀，不取代 MatchState 的實際 destroyed 狀態。
- Pygame 渲染若只跳過角色、不跳過玩家名單，仍會洩漏草叢玩家資訊；玩家本體與玩家名單必須共用可見性判定函式。
- 怪物沒有尋路時可能在牆前停住；這符合本規格的停止/滑動要求，不在本功能加入大範圍路徑尋找。
- 預覽與實際路徑若使用不同半徑或端點，會出現畫面誤導；兩者共用 terrain.py，且保留沒有 obstacles 參數時的舊行為。
- 完整測試目前為 159/159 通過；若後續其他工作樹再次出現 GUI 或既有功能基線差異，應獨立記錄，不覆蓋未提交 `config.py`。

## 第一階段產物

- research.md：完成所有技術未知與替代方案研究。
- data-model.md：完成地形、動作、玩家計時、狀態轉移與模組責任。
- quickstart.md：完成自動化命令、手動驗收與基線說明。
- plan.md：本文件，完成技術方案、憲章檢查、結構、階段與驗證策略。

## 複雜度追蹤

沒有需要豁免的憲章違反。terrain.py 是為了讓模型/規則/渲染共用同一套幾何且避免循環依賴而新增的單一責任模組；不引入物理引擎、服務層或新的持久化抽象。
