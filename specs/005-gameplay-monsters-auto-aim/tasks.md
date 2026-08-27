---

description: "玩法導覽、多種怪物、歷史位置自動瞄準與慢速投射物"
---

# 任務：玩法導覽、多種怪物、歷史位置自動瞄準與慢速投射物

**輸入**：`spec.md` 與目前 `pvpve_escape` 遊戲工作樹。

## 已完成任務

- [x] T001 建立 `AppScreen` 與介紹頁／選角／比賽／結算的畫面流程。
- [x] T002 建立 `MonsterType`、怪物定義、每區三種怪物配置與種類化繪製。
- [x] T003 建立玩家與怪物位置歷史，支援回看秒數的線性插值。
- [x] T004 建立 Tab 自動瞄準開關，施放與預覽共用同一個歷史位置解析結果，並排除目前牆體阻擋的牆後目標。
- [x] T005 將所有玩家飛行物與射手怪物子彈接上 60% 速度倍率，並加入可閃避的敵方投射物。
- [x] T006 將回看秒數集中在 `pvpve_escape/config.py` 的 `AUTO_AIM_LOOKBACK_SECONDS`，預設 `0.2`。
- [x] T007 新增介紹頁、歷史位置、怪物配置與投射物行為的自動化測試。

## 驗證

- `python -m compileall -q pvpve_escape` 通過。
- 新增功能測試 `python -m unittest pvpve_escape.tests.test_game_features` 通過。
- `git diff --check` 通過。
