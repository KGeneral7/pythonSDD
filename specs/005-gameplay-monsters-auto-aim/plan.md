# 實作計畫：玩法導覽、多種怪物、歷史位置自動瞄準與慢速投射物

**功能識別字**：`005-gameplay-monsters-auto-aim`

**預定功能分支**：`codex/005-gameplay-monsters-auto-aim`

**原始交付分支**：`codex/003-combat-vfx-cone-ammo`。本功能與 003、004 共用 `world.py`、`rendering.py` 與測試整合，已隨 [PR #3](https://github.com/KGeneral7/pythonSDD/pull/3) 與 `v0.1.0` 完成；目前的 004 地圖更新由 `codex/004-obstacles-breach-bushes` 另行交付。

## 技術決策

- 在 `config.py` 集中保存 `AUTO_AIM_LOOKBACK_SECONDS = 0.2` 與 `PROJECTILE_SPEED_SCALE = 0.60`；角色與射手怪物只讀取設定後的有效速度。
- 在 `MatchState.position_history` 保存玩家與怪物的時間／位置樣本，以線性插值取得回看時間的座標；資料不足時使用最早可用樣本，不捏造未來位置。
- `resolve_auto_aim()` 只回傳一次施放方向與目標資訊。`_apply_action()` 之後不再讀取目標位置，因此投射物不會追蹤，也不會由自瞄函式直接套用傷害。
- `resolve_auto_aim()` 在目前比賽有提供牆體時，會排除到達線段被尚未破壞牆體阻擋的目標；施放與預覽因此不會把牆後目標當成合法自瞄目標。
- 以 `MonsterType` 與 `MonsterDefinition` 分離追擊獸、砲台蟲、重裝巨獸的生命、速度、攻擊與投射物資料；每個怪物區固定配置三種各一隻。
- 新增 `AppScreen.INTRO`，介紹頁只負責說明玩法；Enter／Space 進入選角，選角頁按 I 可返回介紹頁。

## 資料與責任

- `models.py`：保存畫面狀態、怪物種類、怪物射擊投射物與位置歷史。
- `auto_aim.py`：記錄歷史位置、依手動瞄準扇形選擇最近目標、產生固定方向結果。
- `monsters.py`：集中怪物定義與建立函式。
- `world.py`：處理自瞄施放、慢速玩家／敵方投射物、怪物 AI、命中與重生。
- `rendering.py`：繪製介紹頁、怪物形狀、敵方子彈路徑、自瞄回看標記與 HUD 狀態。
- `controllers.py`／`main.py`：處理 Tab 開關與介紹／選角／比賽／結算的畫面流程。

## 驗證情境

1. 啟動遊戲先看到玩法介紹；按 Enter 或 Space 進入選角，按 I 可再次查看，按 Enter 開始比賽。
2. 建立新局後，四個怪物區各有追獵獸、砲台蟲與重裝巨獸。
3. 設定目標在兩個不同時間點的位置，確認自瞄方向指向 `AUTO_AIM_LOOKBACK_SECONDS` 秒前的位置；修改設定後測試新值生效，並確認牆後目標不會被選取。
4. 發射後移動目標，確認投射物維持原方向且不會在施放瞬間直接扣血；按 Tab 關閉後只使用手動方向。
5. 讓砲台蟲發射子彈，移動玩家離開路徑，確認子彈可被閃避。
6. 執行 `python -m unittest pvpve_escape.tests.test_game_features`、完整 `pvpve_escape/tests` 回歸、`python -m compileall -q pvpve_escape` 與 `git diff --check`；目前完整套件為 162/162 通過。
