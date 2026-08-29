# Pygame 角色外觀製作與套用流程

本文件把「根據角色功能製作 Q 版像素角色 → 生成與驗收圖片 → 套用到 Pygame → 回歸驗證」整理成可重複流程。它以 `pvpve_escape` 的破陣者八方向動畫為範例；其他角色或怪物應替換身份、功能線索與資產根目錄，不要直接複製不適用的數值。

## 1. 先把角色功能翻成視覺規格

先讀取角色定義、主要攻擊、戰術技能、終極技能、移動方式與陣營，再寫出一段主視覺規格。破陣者的穩定線索是：重裝、防禦、攻堅、槍與盾、厚重下盤、Q 版像素、遊戲俯視角。這些線索應決定輪廓、材質、姿勢和裝備關係；參考圖只在使用者指定時提供畫法、角度或比例，不自動帶入顏色。

主視覺規格至少明確寫出：

- 角色功能與一眼可辨識的形狀語言。
- 頭身比例、主要裝備、左右手接點與俯視角可見範圍。
- 方向清單與命名順序。
- idle、move、attack 的動作差異。
- 透明背景、無文字／UI／陰影／光環／場景，以及輸出畫布規格。

### 角色本體與外伸裝備的比例基準

角色本體尺寸與整張圖片的尺寸不是同一件事。頭部、軀幹與四肢是本體基準；長槍、盾牌、尾巴、觸手或特效的外伸距離不可直接決定本體比例。若要統一動畫大小，應以同方向 idle／move／attack 的身體核心聯合外框決定共同比例，再縮放並保留完整圖片與裝備。身體核心可用 `alpha >= 64` 遮罩搭配細長外伸部位排除或連通元件判定；這只用於量測與格式整理，不重畫角色。若裝備本身凸出過多，另做美術修正，不以縮小整個角色代替。

## 2. 用 image generation 產出圖片

使用內建 `image_gen` 工具，不使用 CLI、外部 API 或自行撰寫的繪圖器生成角色內容。每個獨立角色、方向或動畫批次都要保留清楚的提示詞與輸出對應；如果需要修改本機參考圖，將實際檔案放入 `referenced_image_paths`。

提示詞應同時包含：

```text
Create a full-body chibi pixel-art game sprite for a heavy breach defender.
Use a strict top-down game angle and preserve the role cues: heavy armor,
separate gun touching one hand, separate shield touching the other hand.
The shield is seen mainly from its top edge; the gun has no visible grip.
Use hard pixel blocks, a compact readable silhouette, and consistent proportions.
Transparent background, no checkerboard baked into the image, no text, UI,
logo, watermark, ground patch, shadow, glow, smoke, particles, or detached effects.
Preserve the character's own palette; a style-only reference must not donate colors.
For an upper-facing direction, show the rear of the character rather than a
down-facing front view. Keep the head footprint and body anchor consistent.
```

生成後先做視覺檢查，再做格式檢查。下列問題屬於創意或畫面內容問題，應重新生成該張：角色方向錯、上方仍是正面、頭部比例錯、槍盾合併／不碰手、盾牌看到錯誤面、槍出現握把、姿勢或像素風格不一致。只有在問題明確屬於格式時，才可進入下一節的確定性整理。

## 3. 資產命名與格式整理

`pvpve_escape` 的破陣者採用每格獨立 PNG：

```text
pvpve_escape/assets/characters/breacher/
├── idle/<direction>.png
├── move/<direction>/frame_01.png ... frame_04.png
└── attack/<direction>/frame_01.png ... frame_04.png
```

方向固定為：

```text
0 right, 1 down_right, 2 down, 3 down_left,
4 left, 5 up_left, 6 up, 7 up_right
```

本範例共有 8 張 idle、32 張 move、32 張 attack，共 72 張。每張正式來源圖應符合：

- 1024×1024 RGBA 畫布；四角 alpha 為 0。
- 角色、槍、盾與其他必要裝備完整，不貼住畫布邊界。
- 透明像素沒有殘留白／黑邊或非零 RGB 污染。
- 同方向動畫幀的非透明內容中心相對畫布中心偏移不超過 16 個來源像素。
- 若需求是角色本體大小一致，另以每方向所有動畫幀的身體核心聯合外框檢查共同比例；完整武器外框只檢查是否完整與是否意外裁切，不拿來決定本體大小。
- 逐張人工確認俯視角、八方向語意、頭部大小、槍盾分離、手部連接與無多餘特效。

可以使用確定性的資產整理處理「可判定的格式問題」：移除生成器棋盤格背景、建立 alpha、放入固定畫布、清除透明像素 RGB、依 alpha 外框置中。這些步驟不得重畫、修形、換色、移動槍盾或改寫角色像素內容；只要無法確定是格式問題，就重新生成。整理後仍需完整重跑驗證。

## 4. Pygame 程式套用方式

套用前先檢查現有程式分層，將修改限制在下列責任：

1. `config.py`：集中資產根目錄、來源畫布、固定顯示尺寸、方向數、幀數與動畫時間。
2. `models.py`：在玩家狀態追加有預設值的動畫狀態，保存面向、移動經過時間、攻擊經過時間與攻擊維持時間；不要重用生命或戰鬥計時欄位。
3. `sprites.py`：集中方向量化、路徑組合、來源圖片驗證、每張 alpha 外框擷取、最近鄰縮放、來源／裁切／顯示快取與錯誤診斷。載入失敗回傳 `None`，同一資產鍵在快取生命週期內只警告一次。
4. 世界更新：用有效瞄準向量量化面向；用 `delta_time` 推進移動與攻擊動畫；在共同動作套用點觸發普攻／戰術／終極技能的攻擊動畫；持續技能延長狀態但不重設目前攻擊幀。
5. `rules.py`：死亡與重生清除移動／攻擊進度，通常保留有效面向，避免上一條命的攻擊幀殘留。
6. `rendering.py`：建立一個圖片優先、幾何 fallback 的共用角色繪製入口，讓對局、選角與玩家列表共用；其他角色與怪物保留原本繪製路徑。狀態標記、血條、名稱與瞄準線要繼續由原本資訊層繪製。
7. 進入對局前可清除並 preload 全部必要幀，避免第一個畫面讀檔卡頓；不得每幀重新讀取圖片。

若每張生成圖有不同透明留白，先依角色需求選擇顯示策略：破陣者這類需要完整可見外框一致時，可擷取該張實際非透明區域，再以最近鄰重採樣到固定顯示畫布；若角色需要本體大小跨幀／跨方向一致，必須先以身體核心聯合外框固定來源比例，再保留完整來源畫布（`source_canvas`）縮放。這是顯示格式標準化，不是旋轉、翻轉、拼接或重畫槍盾。

## 5. 測試與人工驗收

至少建立下列自動測試：

- 72 張檔案存在、路徑與索引正確，畫布／四角透明／alpha 外框檢查通過。
- 八方向純函式量化，包含上、左上、右上的向量。
- 角色本體尺寸需以身體核心聯合外框檢查；若含長武器，確認武器不會改變本體比例或讓朝上／走路幀跳大小。
- idle／move／attack 的幀範圍、移動循環、攻擊優先與持續技能不重置。
- 每張圖裁切後固定顯示尺寸與置中；快取命中、清快取後重新讀取。
- 缺檔、讀取錯誤、尺寸錯誤、不透明背景與無效查詢回傳不可用結果，且同一錯誤只發出一次警告。
- 死亡／重生重置動畫；共用繪製入口 fallback；其他角色與怪物回歸。

Pygame 專案的基本命令：

```powershell
python -m unittest <targeted-tests> -q
python -m unittest discover -s pvpve_escape/tests -p 'test_*.py' -q
python -m compileall -q pvpve_escape
git diff --check
```

人工驗收依序確認：選角待機、八方向（上方與斜上方為背面）、每方向四格移動、每方向四格攻擊、移動中攻擊優先、普攻／戰術／終極技能、50×50 大小一致、槍盾分離並碰手、死亡／重生、狀態標記、缺圖 fallback，以及其他角色／怪物未改變。通過後才將資產視為正式套用結果。

## 6. 變更邊界與交付紀錄

單純「生成預覽」不修改遊戲程式。使用者明確說「套用」時，才依上述分層修改程式，並補測試、同步 SDD 文件與記錄驗證結果。交付前檢查 `git status` 與 `git diff`，只納入本功能要求的資產、程式、測試、文件與技能；既有不相關的使用者檔案要保留且不納入交付。
