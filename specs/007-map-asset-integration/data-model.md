# 資料模型：100×100 地圖素材接入遊戲

**功能識別字**：007-map-asset-integration
**範圍**：描述正式地圖布局、比賽內地形狀態、單格佔用與渲染投影；不新增持久化資料庫或對外資料格式。

## 模型概觀

目前布局以 config.py 的矩形清單描述，正式比賽不直接使用這些多格矩形，而是經由 terrain.py 正規化成單一格狀態：

~~~text
矩形布局輸入
    │ 向外對齊 100px、限制世界範圍
    ▼
100×100 格佔用鍵 (left, top)
    │ 同類型去重、厚牆 > 薄牆 > 草叢
    ▼
MatchState.obstacles / MatchState.bushes
    │ destroyed / active 局內變化
    ▼
rendering.py 以世界座標投影 tile Surface
~~~

地面是連續的視覺底層，不是可破壞的 MatchState 物件；牆與草叢才是有局內生命週期的地形狀態。

## 既有實體與本功能約束

### WorldRect

沿用 models.py 的 WorldRect 作為世界座標矩形，保存 left、top、width、height 及由此導出的 right、bottom、contains／colliderect 等幾何操作。

正式地圖地形的約束：

- left、top 為整數。
- left 與 top 都是 100 的倍數。
- width = 100、height = 100。
- 0≤left、0≤top、left+100≤2400、top+100≤1400。

既有幾何輔助函式仍可接受任意尺寸的手動 WorldRect fixture，以保留一般幾何測試的相容性；只有 config.py 產生的正式地形要求上述單格約束。

### TerrainCellKey

概念上的格佔用鍵為：

~~~text
(left, top)
~~~

它代表世界中左上角位於該座標的 100×100 格。正規化過程以此鍵做去重與跨類型衝突解決；不需要將此鍵持久化或加入 MatchState 公開欄位。

### ObstacleState

沿用 models.py 既有欄位：

| 欄位 | 型別／規則 | 本功能意義 |
|---|---|---|
| obstacle_id | int；同一局內唯一 | 單格牆的識別與破壞回傳值 |
| kind | ObstacleKind.THICK_WALL 或 THIN_WALL | 決定素材與互動規則 |
| bounds | 100×100 的 WorldRect（正式配置） | 單格世界位置 |
| destroyed | bool，預設 False | 薄牆是否已被移除；厚牆維持既有不可破壞規則 |

既有衍生規則維持：solid 由未 destroyed 決定，destructible 只對薄牆為真。每個格子各有自己的 destroyed，不與鄰格共享。

### BushState

沿用 models.py 既有欄位：

| 欄位 | 型別／規則 | 本功能意義 |
|---|---|---|
| bush_id | int；同一局內唯一 | 單格草叢的識別 |
| bounds | 100×100 的 WorldRect（正式配置） | 單格世界位置 |
| active | bool，預設 True | 草叢是否仍提供原有隱蔽效果 |

草叢不進入 solid obstacle 查詢；active 只影響草叢視覺與既有可見性判定。

### 地面素材狀態

ground_tile.png 是 rendering.py 的快取 Surface，不加入 MatchState，不參與碰撞、不被破壞，也不需要每格建立資料物件。draw_world 依世界網格位置重複鋪設，因此能覆蓋完整可遊玩範圍。

### 地形素材索引

rendering.py 內部維護四個視覺用途的對應關係：

| 用途 | 檔案 | 使用狀態 |
|---|---|---|
| 地面 | pvpve_escape/assets/map/ground_tile.png | draw_world 的連續底層 |
| 薄牆 | pvpve_escape/assets/map/thin_wall_tile.png | 有效薄牆 ObstacleState |
| 厚牆 | pvpve_escape/assets/map/thick_wall_tile.png | 有效厚牆 ObstacleState |
| 草叢 | pvpve_escape/assets/map/bush_tile.png | active BushState |

快取中可保存 Surface 或該類型的備援標記，但不可把 Surface 寫入 MatchState。

## 正規化演算法契約

### 輸入

- 牆布局：kind、left、top、width、height。
- 草叢布局：left、top、width、height。
- 世界尺寸：2400×1400。
- 格尺寸：TERRAIN_CELL_SIZE = 100。

### 輸出

- 每個輸出項目只佔一個 100×100 格。
- 每個格鍵最多有一個正式物件。
- 不存在越出世界範圍的 bounds。
- 物件 ID 在各自清單內唯一且按穩定順序建立。

### 建立入口責任

- build_terrain() 是正式地圖的唯一合併正規化入口：一次收集牆與草叢候選、套用同格優先級，再返回 obstacles 與 bushes 兩份清單。
- create_obstacles() 與 create_bushes() 為既有呼叫端保留的相容性入口；兩者都必須呼叫同一份合併正規化結果，再各自選取牆或草叢清單，不得各自建立只看單一類型的結果。
- create_terrain() 只委派給 build_terrain()，不另行正規化。如此任何正式建立方式都會得到相同的跨類型去重結果。
- 若建立入口各自被單獨呼叫，返回的該類型清單仍須反映另一類型的優先級排除結果；正式牆／草叢清單合併後不得共享格鍵。

### 順序與優先級

1. 將矩形界線轉成整數格界線：左／上向下取整，右／下向上取整，並 clamp 到世界邊界。
2. 依格界線逐格產生候選項目。
3. 以 (left, top) 去除同類型重複。
4. 若牆與草叢候選共用格鍵，保留優先級較高者：厚牆 3、薄牆 2、草叢 1。
5. 依布局來源順序、再依 top／left 穩定排序建立狀態 ID。

目前布局的驗證基準：

~~~text
厚牆：36 格
薄牆：22 格
草叢：92 格
總計：150 格
~~~

## 狀態轉移

### 比賽建立

~~~text
未建立
  └─ build_terrain() ─> 所有牆 destroyed=False、所有草叢 active=True
~~~

每次呼叫都由布局重新產生新的狀態清單；不複製上一局的可變狀態，不修改 config.py 的原始布局。

### 薄牆

~~~text
有效薄牆
  └─ destroy_thin_wall_on_path / destroy_terrain_in_radius / DASH ─> destroyed=True
~~~

destroyed=True 後：

- 不再是 solid，不再繪製薄牆圖片。
- 該格由地面底層顯示。
- 相鄰 ObstacleState 不受影響。
- 厚牆不進入此轉移。

### 草叢

~~~text
有效草叢 (active=True)
  └─ destroy_bushes_on_segment / destroy_terrain_in_radius ─> active=False
~~~

active=False 後不再繪製草叢，且不再把玩家判定為位於有效草叢；相鄰草叢各自維持原狀。

## 關係與不變條件

- MatchState.obstacles 只保存牆狀態；MatchState.bushes 只保存草叢狀態。
- 正式地形清單中，任兩個物件不可共用同一個 (left, top) 格鍵。
- 有效薄牆與厚牆使用同樣的單格幾何邊界；差別只在 destructible 與規則。
- 草叢可與角色、投射物路徑重疊，但不應被當作 solid obstacle。
- 破壞函式以狀態為單位更新，不能依原始布局矩形的 ID 或整段範圍刪除。
- 新局的狀態不應含有上一局的 destroyed=True 或 active=False。
- 素材尺寸與資料尺寸都固定為 100×100；相機只改變投影位置，不修改 bounds。

## 渲染投影

對每個有效狀態：

1. 讀取其 bounds.left、bounds.top 世界座標。
2. 以 world_to_screen(position, camera_position) 轉為螢幕左上角。
3. 將對應完整 100×100 Surface blit 到該目的位置。
4. 由 Pygame 顯示 Surface 自然裁切畫面外部分。

因此 destroyed 的格子只缺少自己的前景 Surface，底層地面仍存在；camera 平移不會改變格子的世界 bounds。

## 持久化與外部介面

本資料模型沒有新增資料庫、網路 API、CLI 協定或跨程序訊息。map_editor.py 的既有草稿可以繼續讀取；正規化後的新輸出以每筆 100×100 的布局項目保存。圖片檔案只作資產輸入，不是遊戲狀態持久化。

## 實作對照（2026-08-28）

- 目前正式 `MatchState` 的地形狀態為 36 個厚牆格、22 個薄牆格與 92 個草叢格，共 150 個單格物件。
- 每個正式 `ObstacleState`／`BushState` 的 `bounds` 都是 100×100，且左上角依 100px 網格對齊；同格重疊已在建立期依厚牆 > 薄牆 > 草叢移除。
- 單格 `destroyed`／`active` 狀態、新局重建與渲染快取行為已由目前測試套件覆蓋。
