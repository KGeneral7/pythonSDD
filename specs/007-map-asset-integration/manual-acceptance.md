# 手動驗收紀錄：100×100 地圖素材接入遊戲

**功能識別字**：007-map-asset-integration
**日期**：2026-08-28
**環境**：Windows 10、Python 3.11.5、Pygame 2.6.1、1280×720
**FPS 上限**：120

## 驗收結果

| 情境 | 結果 | 證據／備註 |
|---|---|---|
| 正式入口 `python -m pvpve_escape` 可啟動 | 通過 | 已進入 Pygame 主迴圈，無啟動例外 |
| 左上、中央、右下鏡頭與部分 tile 裁切 | 通過 | `test_rendering.py` 的 camera／clipping 測試 |
| 相鄰薄牆／草叢逐格破壞 | 通過 | `test_terrain.py`、`test_game_features.py`、`test_breach_cone.py` |
| 厚牆保持存在 | 通過 | `test_terrain.py` 與技能整合測試 |
| 缺圖程式繪製備援 | 通過 | `test_map_assets.py` |
| 重新開始恢復 150 格 | 通過 | `test_main.py` |
| 120 幀暖機後 600 幀效能 | 通過 | 初次地圖整合驗收約 95.75 FPS；rebase 後最新結果見下方 |

## 自動驗收補充

- 初次地圖整合驗收的完整 unittest：198 項通過（保留為歷史紀錄）。
- `python -m compileall -q pvpve_escape`：通過。
- `git diff --check`：通過。
- 正式布局：36 個厚牆格、22 個薄牆格、92 個草叢格，共 150 個 100×100 格。
- 備註：正式入口已成功進入 Pygame 主迴圈；其餘互動情境以同一正式布局的像素／整合測試完成，驗收期間未中斷既有執行中的程序。

## Rebase 後驗證（2026-08-28，砲台蟲修正前基線）

- 基準：`v0.4.0`／PR #13 合併後的 `main`；目前工作樹保留 007 地圖素材整合變更。
- 完整 `python -m unittest discover -s pvpve_escape/tests -p "test_*.py"`：226 項通過。
- 聚焦 `test_navigation`、`test_game_features` 與 `test_terrain`：71 項通過。
- `python -m compileall -q pvpve_escape`、`git diff --check`：通過。
- 120 幀暖機後量測 600 幀，約 6.703 秒完成，平均 89.51 FPS；量測期間沒有 PNG 載入，且低於 120 FPS 上限。
- 正式布局仍為 36 個厚牆格、22 個薄牆格、92 個草叢格，共 150 個 100×100 格；[PR #14](https://github.com/KGeneral7/pythonSDD/pull/14) 已 squash merge，合併提交為 `0f4d7afe47895a97268fcd32b3d785a35ee2a5aa`，並發布 [v0.5.0](https://github.com/KGeneral7/pythonSDD/releases/tag/v0.5.0)。

## 砲台蟲牆角修正後回歸（2026-08-28）

- 地圖素材、150 個獨立 100×100 地形格與單格破壞結果不變；新增怪物導航回歸後完整 unittest 為 229 項通過。
- 砲台蟲在偏好距離點落入牆體、長牆轉角 clearance，以及安全偏好點被厚牆封閉的三個情境均可繞行，沒有牆體重疊或連續 1 秒卡在牆角。
- 最新 120 幀暖機／600 幀效能量測約 6.578 秒、91.21 FPS；沒有 PNG 載入，仍低於 120 FPS 上限。
