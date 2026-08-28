# 驗證快速開始：100×100 地圖素材接入遊戲

**功能識別字**：007-map-asset-integration
**適用分支**：codex/007-map-asset-integration
**目的**：在實作完成後確認四種地圖素材、100×100 單格資料、單格破壞、鏡頭裁切、備援載入與效能都符合規格。

## 前置條件

- Windows 工作環境。
- 專案根目錄為 C:\Users\Yun-Tse Kao\Desktop\pythonSDD。
- .venv\Scripts\python.exe 可執行，且已安裝 requirements.txt 的 Pygame。
- 正式遊戲視窗為 1280×720，遊戲主迴圈 FPS 上限為 120；效能驗收固定使用同一 Windows、Python 3.11、Pygame 執行環境與同一正常遊戲場景。
- 下列四個正式素材存在且各為 100×100px：
  - pvpve_escape/assets/map/ground_tile.png
  - pvpve_escape/assets/map/thin_wall_tile.png
  - pvpve_escape/assets/map/thick_wall_tile.png
  - pvpve_escape/assets/map/bush_tile.png
- 不需啟動網路服務或安裝新的第三方套件。

## 自動驗證

在專案根目錄執行：

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s pvpve_escape\tests -p "test_*.py" -v
.\.venv\Scripts\python.exe -m compileall -q pvpve_escape
git diff --check
~~~

本功能新增／更新的自動測試檔案如下：

- `pvpve_escape/tests/test_terrain.py`：150 格正規化、優先級、單格幾何破壞。
- `pvpve_escape/tests/test_map_editor.py`：舊矩形載入與 100×100 保存。
- `pvpve_escape/tests/test_map_assets.py`：素材尺寸、完整不透明像素、快取與缺圖備援。
- `pvpve_escape/tests/test_rendering.py`：正式素材像素、地面鋪設、破壞後畫面、鏡頭與裁切。
- `pvpve_escape/tests/test_game_features.py`、`test_breach_cone.py`：技能逐格整合回歸。
- `pvpve_escape/tests/test_main.py`：重新開局地形狀態重建。
- `pvpve_escape/tests/test_map_performance.py`：120 幀暖機、600 幀更新／繪製效能基準。

## 目前驗證結果（2026-08-28，rebase 後基線）

- `python -m unittest discover -s pvpve_escape/tests -p "test_*.py"`：226 項通過。
- `python -m unittest pvpve_escape.tests.test_navigation pvpve_escape.tests.test_game_features pvpve_escape.tests.test_terrain`：71 項通過。
- `python -m compileall -q pvpve_escape` 與 `git diff --check`：通過。
- 正式布局：36 個厚牆格、22 個薄牆格、92 個草叢格，共 150 個 100×100 格；四種素材與缺圖備援測試均通過。
- 效能測試：120 幀暖機後量測 600 幀，約 6.703 秒、89.51 FPS；量測期間沒有 PNG 載入。

## 後續砲台蟲牆角修正後驗證（2026-08-28）

- 地圖整合後新增三個砲台蟲牆角／封閉區回歸案例；完整 unittest 更新為 229 項通過，地圖素材與 150 個獨立地形格驗證仍通過。
- 固定效能測試：120 幀暖機後量測 600 幀，約 8.438 秒、71.11 FPS；量測期間沒有 PNG 載入，且低於 120 FPS 上限。

測試若需要清除模組級地圖素材快取，可在 Python 測試生命週期中呼叫：

~~~python
from pvpve_escape.tests.test_helpers import reset_rendering_test_state
reset_rendering_test_state()
~~~

該輔助會呼叫 `rendering.clear_map_asset_cache()`；快取清除後下一次繪製會重新載入素材。缺圖／錯誤素材測試只替換單一素材鍵，其他類型仍使用圖片，失敗類型則回到原本的程式繪製。

預期結果：

- unittest 全部通過。
- 正式布局為 36 個厚牆格、22 個薄牆格、92 個草叢格，共 150 格。
- 每個正式牆／草叢 bounds 都是 100×100，左上角座標都是 100 的倍數，且沒有重複格鍵或越界格。
- 四種素材可載入；如果以測試替身模擬缺圖，遊戲仍能建立畫面並顯示目前的程式繪製備援。
- compileall 與 git diff --check 沒有輸出錯誤。

若專案提供專門的素材測試檔，應確認其涵蓋：

- 圖片檔案尺寸、alpha／不透明像素與快取只載入一次。
- 地面在不同 camera_position 下仍按照世界 100px 網格排列。
- 牆與草叢完整填滿單格，不因 viewport 邊界而拉伸。
- 同格優先級為厚牆 > 薄牆 > 草叢。
- 一個薄牆／草叢格破壞後只顯示該格地面，鄰格仍存在。

## 執行期手動驗收

啟動正式遊戲：

~~~powershell
.\.venv\Scripts\python.exe -m pvpve_escape
~~~

依序檢查：

1. 開始一場比賽，確認地面連續覆蓋地圖，薄牆、厚牆、草叢能以目前確認的軍事廢墟 Q 版像素素材清楚區分。
2. 觀察相鄰的牆格與草叢格，確認每格都完整填滿 100×100 世界格，沒有不預期的空白邊緣、縮放或錯位。
3. 將鏡頭查看左上、中央、右下區域。確認同一世界座標附近的地形相對位置不變，進入畫面的邊界格只被裁切、不被拉伸。
4. 找到由多格組成的薄牆，使用既有可破壞技能命中其中一格；確認只有命中格消失，左右／上下鄰格仍顯示。
5. 讓路徑或範圍效果穿過多格草叢；確認只有實際幾何相交的草叢格失效，其他草叢仍可提供隱蔽效果。
6. 對厚牆施放同樣效果；確認厚牆仍存在並維持阻擋。
7. 重新開始一場比賽；確認所有 150 格回到初始有效狀態，上一局的破壞不會殘留。
8. 暫時將其中一張 tile 移出或讓測試替身回報載入錯誤，再啟動遊戲；確認仍可進入比賽並看見該類型的可辨識程式繪製。
9. 恢復素材後再次啟動，確認圖片路徑恢復且沒有因備援狀態污染後續場次。

每次手動驗收請將日期、素材狀態、三個鏡頭結果、單格破壞結果、缺圖備援與重新開局結果記錄在 `specs/007-map-asset-integration/manual-acceptance.md`；若只做自動驗證，也在該檔案註明未執行的手動項目。

## 效能驗收

在固定 Windows、Python 3.11、Pygame、1280×720 視窗環境與固定正常地圖、角色存在的場景中，先完成 120 幀暖機，再以單調時鐘量測接續的 600 次更新與繪製；平均 FPS 以 600 除以這段實際經過秒數計算，並記錄執行環境、經過秒數與平均 FPS：

- 平均畫面更新率至少 55 FPS。
- 正式遊戲主迴圈不會將 FPS 上限設為高於 120。
- 暖機前完成素材快取；量測的 600 次中不應再發生 PNG 檔案讀取。
- 首次素材讀取只發生在快取建立階段。
- 後續幀沒有反覆讀取 PNG 或建立大量重複 Surface。
- 沒有因素材繪製造成明顯卡頓、閃爍或地形跳動。

## 驗收對照

| 驗收內容 | 對應規格 |
|---|---|
| 四種素材在正式畫面正確顯示 | FR-001、FR-004、SC-002 |
| 每格完整 100×100 且對齊世界網格 | FR-002、FR-003、FR-005、SC-001 |
| 同格去重與厚牆／薄牆／草叢優先級 | FR-006 |
| 單格路徑／範圍破壞與厚牆不可破壞 | FR-007、FR-008、FR-009、SC-003 |
| 多個鏡頭位置與邊界裁切 | FR-010、SC-004 |
| 缺圖仍可啟動 | FR-012、SC-005 |
| 600 次更新與繪製 | SC-006 |
| 新局狀態重建 | FR-011、SC-007 |

## 問題排查

- 若四張圖片都沒有顯示，先確認從專案根目錄以 .venv\Scripts\python.exe 啟動，再檢查 pvpve_escape/assets/map/ 路徑；不要用修改遊戲規則的方式繞過素材錯誤。
- 若只有一類圖片失效，檢查該 PNG 是否為 100×100px、可由 Pygame 解碼且沒有被其他測試替身留在快取。
- 若單格破壞連帶影響鄰格，先檢查 create_obstacles()／create_bushes() 的正式輸出是否仍含有寬高大於 100 的布局物件。
- 若相機邊界出現拉伸，檢查渲染是否把 destination rect 先裁成 viewport 交集；正式格應以完整 Surface blit，再讓顯示 Surface 裁切。
