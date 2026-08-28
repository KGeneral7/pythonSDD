# 快速驗證：玩家頭頂 HUD 與個人戰鬥資訊

## 實作後驗證紀錄（2026-08-27）

- `.\.venv\Scripts\python.exe -m unittest discover -s pvpve_escape\tests -p "test_*.py" -q`：177 項測試全數通過；包含頭頂 HUD、其他玩家 viewport 離屏/回屏、選角與死亡倒數聚焦測試，另含配件死亡冷卻生命週期回歸測試。
- `.\.venv\Scripts\python.exe -m compileall -q pvpve_escape` 與 `git diff --check`：通過。
- 使用 headless Pygame surface 與合成鍵盤事件完成一次完整流程檢查：繪製角色索引 1–6、Q/W/E 更新 `selected_tactical_index`、開始比賽、移動、普攻耗彈、死亡/重生、中央撤離達成勝利與結果頁繪製，輸出 `FLOW_OK`。
- UI 行為檢查確認戰鬥左上固定玩家面板與底部普攻/大招/配件提示已移除；本機頭頂顯示完整私人列，其他玩家只顯示編號/名稱與生命公開列。
- 配件冷卻驗證確認：施放後死亡會保留原冷卻值，死亡等待期間不倒數，復活後才恢復倒數；死亡中的頭頂配件圓圈仍為灰色。
- 本機死亡時會在螢幕中央以大型 Pygame 字型顯示重生倒數；其他玩家死亡不會在本機畫面顯示其倒數。
- viewport 回歸測試確認：其他玩家錨點從左、右、上、下離開畫面時，角色與頭頂血量條/公開資訊不會殘留在邊緣；回到 viewport 內後恢復，且本機玩家仍維持繪製。

## 前置條件

- Windows 工作區位於 `C:\Users\Yun-Tse Kao\Desktop\pythonSDD`。
- Python 3.11 或相容版本。
- 專案既有虛擬環境可用：`.venv\Scripts\python.exe`。
- Pygame 已由專案環境安裝；本功能不新增套件或外部資產。

## 自動化驗證

在專案根目錄執行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s pvpve_escape\tests -p "test_*.py" -v
.\.venv\Scripts\python.exe -m compileall -q pvpve_escape
git diff --check
```

預期結果：所有既有測試與新增的渲染測試通過，Python 編譯沒有輸出錯誤，差異沒有空白字元錯誤。

## 手動遊玩驗證

啟動遊戲：

```powershell
.\.venv\Scripts\python.exe -m pvpve_escape
```

依序確認：

1. 在選角頁查看多個角色卡片，確認每張卡片有主要攻擊種類、傷害/效果、射程或距離、攻擊節奏與操作提示；特別查看狙擊型與生命汲取型角色。
2. 按 `1`–`6` 選擇角色，再按 `Q/W/E` 切換配件，確認 `selected_tactical_index` 隨選擇更新，最後按 `Enter` 開始比賽。
3. 確認戰鬥畫面左上角不再有原本的本機玩家固定戰鬥面板；右上角倒數/撤離、玩家名單與底部的移動/Tab/F1 等非攻擊提示仍存在，底部不再顯示左鍵普攻、右鍵大招或 Space 配件提示。
4. 確認自己的角色頭上有名稱/編號、生命條/數值、彈藥、配件圓圈、大招百分比與強化層數。
5. 使用 `W/A/S/D` 移動並觀察鏡頭至少 20 次，確認整組本機資訊每次都跟著角色，不會留在螢幕角落；靠近畫面邊緣時資訊區塊最大寬度不超過 240 像素、左右至少保留 8 像素，上下也不會被裁切，超長身份文字會截斷。
6. 用滑鼠左鍵攻擊，確認自己的彈藥分段和數值更新；等待恢復後確認分段填回。
7. 按 `Space` 使用配件，確認圓圈由藍色變灰色；冷卻結束後恢復藍色。
8. 以滑鼠右鍵使用大招或累積能量，確認頭上的百分比即時更新。
9. 觀察 viewport 內的其他玩家至少 20 種資源狀態組合：只應看到玩家編號/名稱與生命條/數值，不應看到彈藥、配件圓圈、大招百分比、強化層數或死亡倒數。
10. 讓其他玩家由 viewport 四邊離開再返回，確認其頭頂身份與生命條都會移除，回到視野內才恢復；確認角色圖形仍依既有 viewport 裁切，公開資訊不會被邊界夾取而留在畫面邊緣。
11. 讓自己或其他玩家受傷、死亡，再確認公開生命資訊更新；本機死亡時中央以大型字型顯示死亡倒數、配件圓圈為灰色，死亡期間配件冷卻不倒數且重生後繼續；對方死亡不會因此顯示私有資料或中央倒數。
12. 完成撤離或死亡流程，確認結果頁沒有殘留戰鬥頭頂覆蓋層，且既有結果流程正常。

## 測試重點

渲染單元測試應使用可控的 `PlayerState` 與最小 Pygame surface，至少驗證：

- 本機與其他玩家的可見元素集合不同。
- 至少 20 次玩家位置/鏡頭變更都維持頭頂資訊附著，且資訊區塊符合 240 像素最大寬度與 8 像素邊界。
- 生命、彈藥與大招百分比的上下限各重複至少 20 次，不會產生非法文字或繪製錯誤。
- 配件可用、冷卻中、死亡時的顏色狀態正確。
- 本機死亡倒數以大型 Pygame 字型置中顯示，隨剩餘時間更新並在重生後消失；其他玩家死亡不會顯示中央倒數。
- 強化顯示目前層數與 `MAX_UPGRADE_STACKS` 上限；配件冷卻死亡期間凍結且重生後繼續倒數。
- 同一名玩家的世界座標變更會帶動覆蓋層螢幕座標變更。
- 其他玩家的螢幕錨點離開 viewport 時，`draw_world()` 不會再呼叫其頭頂 overlay；錨點回到 viewport 內後恢復繪製。
- 選角頁提示使用既有角色資料，並涵蓋狙擊與汲取型特殊提示。
- Q/W/E 能切換配件選擇，且戰鬥底部不含普攻、大招或配件提示。

## 分支狀態

Spec Kit 規格資料夾與原始功能分支均使用 `006-overhead-player-hud` 識別字；原始功能已由 [PR #9](https://github.com/KGeneral7/pythonSDD/pull/9) squash merge 至 `main`，並發布 [v0.3.0](https://github.com/KGeneral7/pythonSDD/releases/tag/v0.3.0)。本次 viewport 邊界修正使用由 `main` 建立的 `codex/fix-offscreen-player-hud` 分支，已由 [PR #10](https://github.com/KGeneral7/pythonSDD/pull/10) squash merge 至 `main`（合併 commit `e9aa3b466ef197bba312d30c11b23dd7703b31fc`），並發布為 [v0.3.1](https://github.com/KGeneral7/pythonSDD/releases/tag/v0.3.1)；視野離開/返回情境已由使用者完成人工確認，結果無問題。

## 發布紀錄（2026-08-28）

- PR：[PR #10](https://github.com/KGeneral7/pythonSDD/pull/10) 已 squash merge。
- 合併 commit：`e9aa3b466ef197bba312d30c11b23dd7703b31fc`。
- Release：[v0.3.1](https://github.com/KGeneral7/pythonSDD/releases/tag/v0.3.1)。
