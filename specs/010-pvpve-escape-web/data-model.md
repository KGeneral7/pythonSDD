# 資料模型：PvPvE Escape 瀏覽器版

## 模型原則

- 瀏覽器版使用 TypeScript 的小寫字串 ID；每個 ID 都在下表明確對應既有 Python/Pygame 的 enum 與顯示名稱。
- 所有比賽狀態只存在瀏覽器記憶體；重新整理、按 `R` 或重新開始都建立新的 match。
- `input`、`update`、`render` 三層分離：DOM 事件產生語意化 `InputState`，遊戲核心更新 `MatchState`，renderer 只讀取狀態。
- 世界座標與螢幕／邏輯座標分開。遊戲世界為 `2400 × 1400`，Canvas 邏輯畫布為 `1280 × 720`；相機負責兩者轉換。
- 規則資料以既有 `pvpve_escape/models.py`、`config.py`、`rules.py`、`characters.py`、`controllers.py` 和 `world.py` 的已驗證行為為基準；網頁版可改用瀏覽器友善的實作，但不可改變這些語意。

## 資源載入狀態（App 外層）

初次開啟或重新整理時，App 先建立一次性的資源 loading gate；它位於 `GameState` 之外，不新增 `ScreenPhase`／`MatchPhase`，也不建立 `MatchState`。必要的地圖 manifest 與可玩角色動畫完成所有載入嘗試（失敗項目已轉為 `null` fallback）後，才解除 gate、顯示 `intro` 並允許既有輸入流程。

```ts
type LoadedAsset = HTMLImageElement | HTMLCanvasElement | null;

type LoadedGameAssets = {
  assets: Record<string, LoadedAsset>;
  failures: number;
};
```

`AssetLoader` 以 promise cache 共享這份結果；`CharacterSelect` 與 `PlayingScreen` 不各自重新載入。loading 期間不註冊外層啟動快捷鍵、遊戲不更新時間，且 `match` 維持 `null`；若個別資源失敗，仍在所有請求完成後以幾何／文字 fallback 進入可玩的原版流程。

## 列舉與 canonical 對照

| 型別 | 瀏覽器值 | Python 基準／顯示名稱 | 用途 |
|---|---|---|---|
| `ScreenPhase` | `intro`、`character-select`、`playing`、`result` | `AppScreen.INTRO`、`CHARACTER_SELECT`、`PLAYING`、`RESULT` | 網頁外層畫面 |
| `MatchPhase` | `character-select`、`playing`、`victory`、`no-winner` | `MatchPhase.CHARACTER_SELECT`、`PLAYING`、`VICTORY`、`NO_WINNER` | 一局內流程；撤離是 playing 內的條件，不是額外勝負 phase |
| `PlayerStatus` | `alive`、`dead` | `PlayerStatus.ALIVE`、`DEAD` | 玩家生命週期 |
| `ControllerType` | `human`、`dummy` | `ControllerType.HUMAN`、`DUMMY` | 玩家控制來源 |
| `CharacterId` | `breacher`（破陣者）、`sniper`（狙擊者）、`guardian`（守衛者）、`hunter`（追獵者）、`controller`（控場者）、`siphoner`（吸能者） | `CharacterId.BREACHER` 等六值 | 六種角色的穩定識別 |
| `TacticalId` | `dash`（短距離衝刺）、`shield`（短時間護盾）、`control`（範圍控場） | `TacticalId.DASH`、`SHIELD`、`CONTROL` | 三種戰術配件 |
| `ObstacleKind` | `thick-wall`、`thin-wall` | `ObstacleKind.THICK_WALL`、`THIN_WALL` | 牆體種類 |
| `TerrainInteraction` | `block`、`break-thin-on-path`、`break-thin-in-area`、`dash-break-first-thin` | `TerrainInteraction.BLOCK` 等四值 | 攻擊／衝刺與牆體的互動政策 |
| `MonsterType` | `chaser`（追獵獸）、`shooter`（砲台蟲）、`brute`（重裝巨獸） | `MonsterType.CHASER` 等三值 | 怪物種類 |
| `MonsterBehavior` | `wander`、`chase`、`return` | `MonsterBehavior.WANDER`、`CHASE`、`RETURN` | 怪物移動與攻擊狀態 |

## 基礎幾何與常數

```ts
type Vector2 = { x: number; y: number };
type WorldRect = { left: number; top: number; width: number; height: number };
type CircleZone = { center: Vector2; radius: number };
type Color = string;
```

固定常數：

| 常數 | 值 | 來源／用途 |
|---|---:|---|
| `WORLD_WIDTH` / `WORLD_HEIGHT` | 2400 / 1400 | 世界邊界 |
| `LOGICAL_WIDTH` / `LOGICAL_HEIGHT` | 1280 / 720 | Canvas 邏輯尺寸 |
| `PLAYER_COUNT` | 6 | 1 名人類加 5 名 dummy |
| `MONSTER_CAMP_COUNT` / `MONSTERS_PER_CAMP` | 4 / 3 | 四個營地，每營地三隻怪物 |
| `MATCH_DURATION_SECONDS` | 240 | 單局總時間 |
| `EXTRACTION_START_SECONDS` | 210 | 剩餘 30 秒開放撤離 |
| `EXTRACTION_REQUIRED_SECONDS` | 10 | 個別玩家連續停留時間 |
| `PLAYER_REGEN_DELAY_SECONDS` | 5 | 離開受傷／攻擊後才可回復 |
| `PLAYER_REGEN_RATE` | 0.10 | 每秒恢復最大生命的比例 |
| `PLAYER_RESPAWN_DELAY_SECONDS` | 5 | 玩家死亡後重生 |
| `MONSTER_RESPAWN_DELAY_SECONDS` | 6 | 怪物原生成區重生 |
| `MAX_UPGRADE_STACKS` | 10 | 強化上限 |
| `UPGRADE_PER_STACK` | 0.03 | 每層攻擊與生命倍率 |
| `MAX_ULTIMATE_ENERGY` | 100 | 大招能量上限 |
| `AUTO_AIM_LOOKBACK_SECONDS` | 0.20 | 施放時取回看位置 |
| `AUTO_AIM_HALF_ANGLE_DEGREES` | 45 | 有效瞄準半角 |
| `MAX_UPDATE_DELTA_SECONDS` | 0.05 | 背景分頁／低幀率的 dt 上限 |
| `TERRAIN_CELL_SIZE` | 100 | 牆體／草叢正規化後的單格尺寸 |
| `EXTRACTION_CENTER` / `EXTRACTION_RADIUS` | `(1200, 700)` / `140` | 中央撤離區 |

## 原版 parity 固定資料

瀏覽器版不得從 UI 重新推導或改寫下列基準；`src/game/config.ts` 的值必須能直接由 parity test 核對：

| 類別 | 固定資料 |
|---|---|
| 玩家出生點（0～5） | `(300,180)`、`(1200,120)`、`(2230,170)`、`(170,1230)`、`(1200,1280)`、`(2230,1230)` |
| 怪物營地中心（0～3） | `(560,350)`、`(1840,350)`、`(560,1050)`、`(1840,1050)` |
| 原始障礙矩形 | 18 筆，保留 `kind/left/top/width/height` 順序與尺寸；正規化為 36 厚牆格、22 薄牆格 |
| 草叢 | 原始 27 筆配置，正規化為 92 格；活躍草叢只隱藏其他活玩家，觀看者在同一草叢不會因此看見目標 |
| 初始 roster | 6 名玩家、12 隻怪物；玩家 0 為 human，玩家 1～5 為 dummy；dummy 建立後不自主移動／攻擊 |
| 邏輯畫面 | `1280×720`；Canvas、DOM overlay 與選單／結果固定座標皆以此 surface 為基準，再由瀏覽器等比例縮放 |

原版 `rendering.py` 的 intro、選角、對局 HUD、developer 提示與 result 是可見呈現契約：Canvas 負責世界、角色、怪物、效果、瞄準與玩家頭頂資訊；DOM overlay 只承載原版固定右上倒數／撤離文字、右下 roster 與可及性語意。DOM 的 aria／focus 輔助可以存在，但不得加入原版沒有的可見 HUD panel、Toast、撤離進度圓環或結果摘要卡。

## 靜態定義

### `CharacterDefinition`

欄位必須直接對應既有 Python `CharacterDefinition`，避免選角、戰鬥和 HUD 各自保存一套數值：

```ts
type CharacterDefinition = {
  characterId: CharacterId;
  displayName: string;
  primaryKind: string;
  ammoCapacity: number;
  ammoRecoveryInterval: number;
  primaryCooldown: number;
  primaryDamage: number;
  primaryRange: number;
  passiveText: string;
  ultimateText: string;
  baseHealth: number;
  projectileSpeed: number;
  passiveMultiplier: number;
  passiveCondition: string;
  parameters: Record<string, number>;
};
```

六個 canonical 對照與普攻為：破陣者／`breacher`（60° 扇形散射，3 發，0.45 秒）、狙擊者／`sniper`（0.6 秒蓄力直線，2 發，0.80 秒）、守衛者／`guardian`（前方弧形盾牌衝擊，2 發，0.60 秒）、追獵者／`hunter`（往返回旋飛刃，3 發，0.35 秒）、控場者／`controller`（重力地雷，2 發，0.55 秒）、吸能者／`siphoner`（持續吸能光束，4 發，0.20 秒）。容量必須為 2–4，恢復間隔必須為 0.20–0.80 秒。

### `TacticalDefinition`

```ts
type TacticalDefinition = {
  tacticalId: TacticalId;
  displayName: string;
  cooldown: number;
  description: string;
  parameters: Record<string, number>;
};
```

三個配件都使用 12 秒冷卻：`dash` 位移 220 並免傷 0.2 秒、`shield` 吸收最多 60 點傷害並持續 2 秒、`control` 半徑 100、減速 60% 並持續 1.5 秒。

## 玩家模型

### `PlayerAnimationState`

```ts
type PlayerAnimationState = {
  facingDirectionIndex: number;
  moving: boolean;
  moveElapsed: number;
  attackElapsed: number;
  attackHold: number;
};
```

### `PlayerState`

| 欄位 | 型別／範圍 | 說明 |
|---|---|---|
| `playerId` | `0..5` | 穩定索引；0 為人類，1–5 為 dummy |
| `controllerType` | `ControllerType` | `human` 或 `dummy` |
| `characterId` / `tacticalId` | 對應 enum | 角色與戰術選擇 |
| `position` / `spawnPosition` | `Vector2` | 當前／出生世界座標 |
| `radius` | 正數 | 圓形碰撞半徑 |
| `baseMaxHealth` / `healthPassiveMultiplier` | 正數 | 未計強化的生命基準與角色被動 |
| `maxHealth` / `health` | `0..maxHealth` | 當前／最大生命 |
| `moveSpeed` | 正數 | 由角色、強化和控制效果修正得到 |
| `upgradeStacks` | `0..10` | 怪物擊殺強化層數 |
| `ultimateEnergy` | `0..100` | 有效傷害累積的大招能量 |
| `ammo` / `ammoCapacity` | `0..ammoCapacity` | 當前彈藥／彈匣上限 |
| `ammoRecoveryTimer` | 非負秒數 | 自動逐發補彈計時；沒有手動換彈動作 |
| `tacticalCooldown` / `primaryCooldown` | 非負秒數 | 戰術／普攻冷卻 |
| `deathTimer` | 非負秒數 | 死亡至重生倒數 |
| `extractionProgress` | `0..10` | 每名玩家獨立的撤離進度 |
| `developerPlaced` | boolean | 是否被 M 測試控制移入撤離區 |
| `status` | `alive`／`dead` | 玩家生命週期；勝負由 match `winnerId` 表示 |
| `aimDirection` | `Vector2` | 最近一次有效瞄準方向 |
| `invulnerabilityTimer` | 非負秒數 | 位移／大招免傷剩餘時間 |
| `damageReductionTimer` / `damageReduction` | 秒數／比例 | 減傷效果 |
| `shieldRemaining` / `shieldTimer` | 數值／秒數 | 護盾量與剩餘時間 |
| `slowTimer` / `slowMultiplier` / `rootTimer` | 秒數／比例／秒數 | 控制效果 |
| `primaryCharge` | 非負秒數 | 蓄力或引導時間 |
| `abilityInputBlocked` | boolean | 持續攻擊、受控或死亡時阻擋輸入 |
| `lastDamageTime` / `lastAttackTime` | 遊戲秒數 | 回復規則的受傷／攻擊間隔 |
| `autoAimEnabled` | boolean | 預設 true；由 `Tab` 切換 |
| `animationState` | `PlayerAnimationState` | 僅供視覺，不參與規則 |

強化倍率固定為 `1 + 0.03 × upgradeStacks`，同時套用攻擊和最大生命；取得生命強化時須依既有規則維持滿血或受傷比例。

## 怪物模型

```ts
type MonsterState = {
  monsterId: number;
  spawnZoneId: number;
  position: Vector2;
  spawnPosition: Vector2;
  radius: number;
  maxHealth: number;
  health: number;
  moveSpeed: number;
  targetPlayerId: number | null;
  attackTimer: number;
  respawnTimer: number;
  lastDamagePlayerId: number | null;
  slowTimer: number;
  slowMultiplier: number;
  rootTimer: number;
  alive: boolean;
  monsterType: MonsterType;
  aimDirection: Vector2;
  behavior: MonsterBehavior;
  navigationPath: Vector2[];
  navigationGoal: Vector2 | null;
  wanderTarget: Vector2 | null;
  wanderIndex: number;
  wanderPauseTimer: number;
};
```

遊戲建立四個 `spawnZoneId`；每個營地恰有 `chaser`、`shooter`、`brute` 各一隻，共 12 隻。有效傷害發生時更新 `lastDamagePlayerId`；怪物死亡時只將一層強化給該玩家，六秒後於 `spawnPosition` 重生並清除上一輪歸屬。

### `MonsterProjectileState`

```ts
type MonsterProjectileState = {
  projectileId: number;
  sourceMonsterId: number;
  position: Vector2;
  direction: Vector2;
  damage: number;
  projectileSpeed: number;
  radius: number;
  maxDistance: number;
  previousPosition: Vector2;
  distanceTravelled: number;
  remaining: number;
  impactPosition: Vector2 | null;
  impactStatus: string;
  impactTargetId: number | null;
};
```

## 地形模型

```ts
type ObstacleState = {
  obstacleId: number;
  kind: ObstacleKind;
  bounds: WorldRect;
  destroyed: boolean;
};

type BushState = {
  bushId: number;
  bounds: WorldRect;
  active: boolean;
};

type TerrainState = {
  worldBounds: WorldRect;
  obstacles: ObstacleState[];
  bushes: BushState[];
  extractionZone: CircleZone;
  monsterSpawnZones: Array<{ spawnZoneId: number; position: Vector2 }>;
};
```

厚牆永遠不可破壞，薄牆只在實際命中的單一路徑／範圍格被破壞；草叢以 `active` 狀態影響其他玩家可見資訊。新 match 必須建立全新的障礙與草叢集合。

## 戰鬥、瞄準與效果

```ts
type CombatAction = {
  kind: string;
  ownerId: number;
  origin: Vector2;
  direction: Vector2;
  damage: number;
  range: number;
  radius: number;
  duration: number;
  maxDistance: number;
  projectileSpeed: number;
  metadata: Record<string, unknown>;
  terrainInteraction: TerrainInteraction;
};

type AbilityEffect = {
  effectId: number;
  kind: string;
  ownerId: number;
  position: Vector2;
  previousPosition: Vector2;
  direction: Vector2;
  damage: number;
  radius: number;
  remaining: number;
  maxDistance: number;
  projectileSpeed: number;
  distanceTravelled: number;
  tickTimer: number;
  returning: boolean;
  armed: boolean;
  impactPosition: Vector2 | null;
  impactStatus: string;
  hitTargetIds: Set<string>;
  metadata: Record<string, unknown>;
  origin: Vector2;
  terrainInteraction: TerrainInteraction;
};

type DamageEvent = {
  sequence: number;
  sourcePlayerId: number | null;
  targetId: number;
  rawDamage: number;
  effectiveDamage: number;
  createdAt: number;
  targetKind: "player" | "monster";
};

type AimGuide = {
  ownerId: number;
  abilitySlot: "primary" | "ultimate" | "tactical";
  shape: string;
  origin: Vector2;
  direction: Vector2;
  end: Vector2;
  range: number;
  radius: number;
  angleDegrees: number;
  pathPoints: Vector2[];
  valid: boolean;
  targetPosition?: Vector2 | null;
  lookbackSeconds?: number;
  hasTarget?: boolean;
};
```

`AimGuide` 每幀由輸入產生，只供 renderer；不能被傷害或自動瞄準規則當成命中結果。auto-aim 只在施放時從 position history 取 0.20 秒前、有效角度內最近目標的位置，投射物建立後固定方向。

## 輸入模型

```ts
type InputState = {
  moveDirection: Vector2;
  aimDirection: Vector2;
  primaryPressed: boolean;
  primaryHeld: boolean;
  primaryReleased: boolean;
  ultimatePressed: boolean;
  ultimateHeld: boolean;
  ultimateReleased: boolean;
  tacticalPressed: boolean;
  tacticalHeld: boolean;
  tacticalReleased: boolean;
  focusLost: boolean;
  quitRequested: boolean;
  restartRequested: boolean;
  startRequested: boolean;
  introContinueRequested: boolean;
  introBackRequested: boolean;
  introRequested: boolean;
  autoAimTogglePressed: boolean;
  selectedCharacterIndex: number | null;
  selectedTacticalIndex: number | null;
  developerToggle: boolean;
  developerDummyId: number | null;
  developerPlace: boolean;
  developerReturn: boolean;
  mouseLogicalPosition: Vector2;
  mouseWorldPosition: Vector2;
  hasFocus: boolean;
};
```

DOM event 只更新此語意化狀態；`R` 設定 `restartRequested`、`Tab` 設定 `autoAimTogglePressed`、右鍵設定 ultimate 欄位、Space 設定 tactical 欄位。`blur`、`visibilitychange` 或 `hasFocus: false` 時清除所有 held／mouse held 欄位，並等待真正放開後才允許再次施放。

## 相機、開發者模式與頂層狀態

```ts
type CameraState = {
  position: Vector2;
  viewportSize: Vector2;
  worldSize: Vector2;
};

type FrameSamplerState = {
  sampleWindowSeconds: number;
  elapsedSeconds: number;
  frameCount: number;
  averageFps: number;
  complete: boolean;
};

type DeveloperModeState = {
  enabled: boolean;
  selectedDummyId: number;
  showOverlay: boolean;
};

type MatchState = {
  phase: MatchPhase;
  seed: number;
  rngState: number;
  elapsedTime: number;
  duration: number;
  extractionStartTime: number;
  extractionRequiredTime: number;
  extractionZone: CircleZone;
  players: PlayerState[];
  monsters: MonsterState[];
  winnerId: number | null;
  developerMode: DeveloperModeState;
  camera: CameraState;
  effects: AbilityEffect[];
  messages: Array<[string, number]>;
  nextEffectId: number;
  nextEventSequence: number;
  monsterProjectiles: MonsterProjectileState[];
  nextMonsterProjectileId: number;
  positionHistory: Record<string, Array<[number, Vector2]>>;
  obstacles: ObstacleState[];
  bushes: BushState[];
  navigationCache: Record<string, unknown>;
  navigationCacheObstacleSignature: Array<[number, ObstacleKind, WorldRect]>;
};

type GameState = {
  screen: ScreenPhase;
  selectedCharacter: CharacterId | null;
  selectedTactical: TacticalId | null;
  match: MatchState | null;
  frameSampler: FrameSamplerState;
  lastResultMessage: string | null;
};

type PublicPlayerView = {
  playerId: number;
  characterId: CharacterId;
  position: Vector2;
  health: number;
  maxHealth: number;
  status: PlayerStatus;
  visible: boolean;
};

type PrivatePlayerView = PublicPlayerView & {
  tacticalId: TacticalId;
  ammo: number;
  ammoCapacity: number;
  ultimateEnergy: number;
  upgradeStacks: number;
  primaryCooldown: number;
  tacticalCooldown: number;
  extractionProgress: number;
  deathTimer: number;
};
```

`winnerId` 只有玩家 ID 或 `null`；無固定隊伍勝利型別。正常 HUD 只能取得自己的 `PrivatePlayerView` 和其他玩家的 `PublicPlayerView`，不可透過 selector／Tab 面板取得其他玩家私有資源。自己的配件在可見 HUD 中以原版就緒圓點呈現，不顯示額外數值冷卻卡片。

`FrameSamplerState` 是瀏覽器效能儀表，不參與遊戲規則：playing 開始時以 `requestAnimationFrame` 每次回呼增加 `frameCount`，以 `performance.now()` 計算 `elapsedSeconds`；達到 60 秒後以 `averageFps = frameCount / elapsedSeconds` 完成量測，並由 developer overlay 保留可及性結果，不新增原版沒有的可見 HUD。重新開始或重新載入時重設 sampler。

## 狀態轉換

```text
INTRO
  └─ Enter / Space / 開始 ─> CHARACTER_SELECT
                              └─ 1–6、Q/W/E、Enter ─> PLAYING
                                                          ├─ winnerId != null ─> VICTORY
                                                          └─ 240 秒到期 ──────> NO_WINNER
任何畫面
  └─ R ─> 清除當前 match，回到 CHARACTER_SELECT
PLAYING / RESULT
  └─ Esc ─> INTRO（網頁版導覽）
RESULT
  └─ Enter / 再玩一次 ─> CHARACTER_SELECT
```

`MatchPhase` 的 `character-select`、`playing`、`victory`、`no-winner` 對應既有 Python phase；撤離區在 `playing` 且 elapsed time 達到 210 秒後啟用。進入 victory／no-winner 後停止上一局 update loop，外層 `ScreenPhase` 顯示 result。

## 玩家生命週期、強化與撤離

1. `alive` 人類玩家可移動、瞄準、攻擊、使用大招與戰術；`dead` 玩家停止輸入，`deathTimer` 倒數 5 秒後於安全外圍重生。dummy 不自主移動／攻擊，但仍接受一般生命週期與開發者測試控制。
2. 玩家死亡時清除強化、大招能量、撤離進度與不應延續的效果；重生時重設生命、彈藥、冷卻和安全位置。
3. 有效傷害讓攻擊者累積大招能量；怪物死亡讀取 `lastDamagePlayerId`，只給該玩家一層強化，並將 `upgradeStacks` 限制在 0–10。
4. 生命低於上限且 `lastDamageTime >= 5` 且 `lastAttackTime >= 5` 時，依 `PLAYER_REGEN_RATE` 回復；任何有效攻擊或受擊都重新計時。
5. elapsed time 達 210 秒時啟用撤離；每名仍在 `extractionZone` 且 alive 的玩家獨立累積 10 秒，離開或死亡只清除自己的進度。
6. 同一 update 週期多人達標時按遞增 `playerId` 選出唯一 `winnerId`；victory 優先於同一週期的 no-winner，240 秒仍無勝者才進入 no-winner。

## 不變量與更新順序

- `players.length === 6`；玩家 0 是 human，玩家 1–5 是 dummy，dummy 使用其餘五種不同角色與有效戰術。
- 每個新 match 有四個營地、每營地 chaser／shooter／brute 各一隻；死亡怪物可保留於集合以供重生計時，但不能造成傷害。
- 生命、能量、彈藥、升級、撤離進度、倒數和 cooldown 不低於 0；能量不超過 100，升級不超過 10，撤離進度不超過 10。
- 世界位置由同一套地形碰撞與世界邊界限制；相機不改變實體世界座標。
- 只有 alive 玩家、alive 怪物或仍有效的投射物／效果能建立攻擊；視覺效果和 `AimGuide` 不得單獨產生傷害。
- 私人 view 只可由玩家 0 的 match state 產生；其他玩家只能經 public view 進入正常 HUD。

```text
消費 pressed input（dummy 僅更新 lifecycle/timer，不進入人類輸入動作）
  → 更新人類玩家輸入、移動與瞄準
  → 更新玩家普攻／大招／戰術／彈藥／冷卻
  → 更新怪物遊蕩、追擊、繞行與攻擊
  → 更新效果與怪物投射物
  → 解析地形、實體、投射物碰撞與薄牆破壞
  → 套用傷害、最後傷害歸屬、能量、強化、回復、死亡與重生
  → 更新撤離進度與 match phase
  → 更新 position history、相機與 developer view；`requestAnimationFrame` 在核心更新完成後另行記錄 FPS sampler，動畫狀態在玩家輸入／生命週期步驟中更新
  → 判定 winnerId／no-winner、停止結果局並清理一次性事件
```
