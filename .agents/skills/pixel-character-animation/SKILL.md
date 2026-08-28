---
name: pixel-character-animation
description: 製作並檢查以角色功能為核心的 Q 版像素角色與怪物、透明 raster 預覽、方向幀與動畫；並在使用者明確要求套用時，提供與驗證遊戲程式整合方法。
---

# Pixel Character Animation

這是一個把角色功能轉譯成可在小尺寸辨識的 Q 版像素外觀、動畫資產與遊戲整合流程的工作區技能，適用於玩家角色、敵人、怪物與 NPC。預設先產出與檢查視覺資產；只有使用者明確要求套用時，才依專案現有架構提供程式修改與驗證。它不處理寵物互動、命名、打包或部署。

## 工作流程

1. 先讀取角色或怪物的功能、威脅類型、武器／道具、移動方式與陣營，再整理成一個穩定的視覺身份；若要套用到遊戲，也先盤點角色模型、輸入／更新／繪製接點、資產路徑與既有 fallback。
2. 建立單一主視覺：完整全身、緊湊輪廓、固定比例、固定材質與有限色盤。所有後續方向或動畫幀都以這個主視覺為參考。
3. 使用內建 `image_gen` 生成 raster 預覽或動畫素材。需要改造既有參考圖時，將每個本機參考檔放入 `referenced_image_paths`；每個獨立素材使用一次生成呼叫。不要使用 CLI、API 或自行撰寫的本機繪圖器。
4. 生成後檢查輪廓、角色身份、透明背景、像素邊緣、比例與幀間一致性；不合格的創意或畫面內容只針對問題素材重新生成。若只是不透明背景、畫布尺寸、透明 alpha 或置中等可明確判定的格式問題，才可用確定性的資產整理流程處理，不重畫角色像素。
5. 使用者要求套用時，依「資產索引／載入 → 動畫狀態 → 世界更新 → 共用繪製入口 → fallback」的責任邊界整合，先補回歸測試，再執行自動與人工驗收。

## 工作區參考流程

本專案的完整可重用流程（包含 72 張破陣者資產命名、透明與尺寸 QA、Pygame 程式改法、測試與人工驗收）位於 [references/pvpve_escape_breacher_workflow.md](references/pvpve_escape_breacher_workflow.md)。遇到本專案或相同 Pygame 結構的角色套用工作，先讀取該參考文件；其他引擎則只沿用責任邊界與 QA 原則，不照抄 Pygame API。

### 參考圖的分工

風格參考與配色參考必須分開處理。使用者只說「參考畫法」時，只吸收像素大小、輪廓簡化、比例、外框、明暗階與筆觸節奏；不要自動借用參考圖的色相、明度、材質色或背景色。配色應由角色身份、專案既有色盤或使用者明確指定決定。只有使用者明確要求「參考配色」時，才複製參考圖的色彩關係。

## Q 版像素視覺規則

- 頭身比約 2.5–3 頭身，頭部和主要武器／道具略微誇張，但四肢與裝備仍要清楚可辨。
- 使用硬邊、整齊像素塊、有限且一致的色盤、深色像素外框與清楚的明暗階。避免柔焦、照片感、漸層噪點與反鋸齒邊緣。
- 以功能塑造形狀語言：重裝／防禦使用寬肩、厚護甲、穩定下盤；遠程／狙擊使用細長輪廓、明確瞄具與長武器；近戰／突擊使用前傾姿勢、強烈斜線與破壞性道具；控場／支援使用模組、天線、束縛器或能量容器等集中識別物。
- 角色與怪物都必須是單一完整主體，動作與裝備要服務於身份辨識；不要讓特效比身體輪廓更醒目。
- 預覽圖不放文字、UI、標籤、logo、水印、背景場景、地面貼片或網格。

## 透明背景與特效

- 交付透明 PNG 時，主體外所有像素都要能乾淨移除；透明像素不能殘留 RGB 邊緣色或白／黑光暈。
- 不使用漂浮星星、煙霧、塵土、速度線、殘影、拖尾、外發光、光環、投影或接觸陰影。需要表現能量時，將它限制在角色身上或緊貼武器的可辨識像素區域。
- 檢查頭盔、武器、尾巴、觸手與其他外伸部位沒有被裁切，也沒有脫離主體的孤立像素。

## 動畫製作規則

- idle 只做微小呼吸、眨眼、輕微上下起伏或材質擺動；不要在 idle 中新增道具或做大幅度揮舞。
- 行走／奔跑幀只改變身體、四肢與攜帶道具的運動；左右腳或主要肢體要有交替節奏，朝向、武器手持側與臉部特徵要正確。
- 每一幀維持相同角色身份、基準位置、畫布尺寸、比例、材質與主色；避免尺寸跳動、姿勢漂移、臉部變形、道具消失或跨幀重疊。
- 本工作區若需要 sprite sheet，除非專案規格另訂方向，預設採 4 方向 × 4 幀：列為 down、right、up、left，幀格尺寸固定，使用 nearest-neighbor，不加入可見分隔線或標註；若專案要求八方向，必須依專案的方向索引與命名，不可套用四方向假設。預覽階段先以「每個角色／怪物一張完整主視覺」確認身份，再延伸成幀動畫。
- 動畫 QA 必須確認：每格有內容、方向正確、步伐有交替、循環不僵硬、沒有錯向／反向、沒有透明污染、沒有裁切與尺寸跳動。

## 程式套用原則

- 先從既有角色功能與資料流找出穩定的整合點，不把方向、動畫計時或圖片載入散落在輸入分支與各個 renderer 呼叫點。
- 資產載入器應集中處理固定路徑、尺寸／透明驗證、每張圖片的實際非透明區域、最近鄰縮放、快取與失敗診斷；缺圖時回退既有幾何外觀，不讓繪圖錯誤中斷遊戲。
- 動畫狀態應放在角色狀態資料中，與生命、碰撞、傷害和技能規則分離；用 `delta_time` 推進，並在死亡／重生時清除上一條命的動作進度。
- 方向由遊戲已有的有效瞄準或移動向量量化；不要在執行期旋轉或翻轉預繪槍盾，避免像素模糊、上下方向錯置或手持側錯誤。
- 若每張生成圖的透明留白或外框不同，逐張擷取實際非透明角色區域，再以固定顯示畫布直接重採樣；這是顯示格式標準化，不是重畫角色內容。
- 選角、玩家列表與對局應共用同一個角色繪製入口；其他角色與怪物維持原本路徑，除非需求明確擴大範圍。
- 只有在使用者要求「套用／整合／修改程式」時才修改程式；單純預覽或生成圖片要求不修改遊戲程式碼。

## 可重複驗收

- 資產：數量、命名、方向、幀數、畫布尺寸、四角透明、未貼邊、無透明 RGB 污染、角色中心與武器完整性。
- 顯示：固定顯示尺寸、最近鄰像素邊緣、八方向（包含上方與斜上方的正確背面）、idle／move／attack 優先序、沒有常駐底圈或意外外框。
- 程式：方向量化、動畫時間、持續技能不重置攻擊幀、死亡／重生重置、失敗資產只警告一次、fallback 與其他角色／怪物回歸。
- 驗證命令依專案而定；Pygame 專案至少執行針對性 `unittest`、完整 `unittest discover`、`compileall` 與 `git diff --check`，再完成選角、八方向、移動、攻擊、技能、死亡／重生與缺圖情境的人工測試。

## 生成提示詞模板

```text
Use case: stylized-concept (or style-transfer when a reference image is supplied).
Create one full-body chibi pixel-art game sprite for [character or monster identity].
Preserve these function cues: [role, threat, weapon, movement, signature prop].
Compact readable silhouette, about 2.5–3 heads tall, hard pixel edges, limited coherent palette,
dark pixel outline, clear highlights and shadows, centered on a clean transparent background.
No text, UI, logo, watermark, scene, floor patch, shadow, glow halo, smoke, dust, speed lines,
floating particles, detached effects, stray pixels, clipping, or extra subjects.
Keep the face, proportions, materials, palette, signature prop, and facing direction consistent
with the character identity reference or project palette. If an input is style-only, do not copy
its colors; preserve the role's own color identity instead.
```

## 使用邊界

這個技能可產出或檢查角色／怪物的像素繪圖、透明 raster 預覽與動畫幀規格，也可在使用者明確要求時協助把資產套入遊戲。程式修改只限於必要的資產索引、動畫狀態、渲染整合、fallback、測試與文件；不得藉此改變遊戲規則、傷害、碰撞、速度、技能效果或未納入範圍的角色／怪物行為。
