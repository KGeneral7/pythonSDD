"""遊戲狀態資料類別與幾何資料。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any


class MatchPhase(str, Enum):
    CHARACTER_SELECT = "CHARACTER_SELECT"
    PLAYING = "PLAYING"
    VICTORY = "VICTORY"
    NO_WINNER = "NO_WINNER"


class AppScreen(str, Enum):
    """應用程式畫面；與單局內的 MatchPhase 分開保存。"""

    INTRO = "INTRO"
    CHARACTER_SELECT = "CHARACTER_SELECT"
    PLAYING = "PLAYING"
    RESULT = "RESULT"


class PlayerStatus(str, Enum):
    ALIVE = "ALIVE"
    DEAD = "DEAD"


class ControllerType(str, Enum):
    HUMAN = "HUMAN"
    DUMMY = "DUMMY"


class CharacterId(str, Enum):
    BREACHER = "BREACHER"
    SNIPER = "SNIPER"
    GUARDIAN = "GUARDIAN"
    HUNTER = "HUNTER"
    CONTROLLER = "CONTROLLER"
    SIPHONER = "SIPHONER"


class TacticalId(str, Enum):
    DASH = "DASH"
    SHIELD = "SHIELD"
    CONTROL = "CONTROL"


class ObstacleKind(str, Enum):
    """地圖牆體種類；薄牆可破壞，厚牆整場固定存在。"""

    THICK_WALL = "thick_wall"
    THIN_WALL = "thin_wall"


class TerrainInteraction(str, Enum):
    """動作和牆、草叢互動時採用的明確政策。"""

    BLOCK = "BLOCK"
    BREAK_THIN_ON_PATH = "BREAK_THIN_ON_PATH"
    BREAK_THIN_IN_AREA = "BREAK_THIN_IN_AREA"
    DASH_BREAK_FIRST_THIN = "DASH_BREAK_FIRST_THIN"


class MonsterType(str, Enum):
    CHASER = "CHASER"
    SHOOTER = "SHOOTER"
    BRUTE = "BRUTE"


@dataclass
class Vector2:
    """不依賴畫面的二維向量；所有位置都以世界座標保存。"""

    x: float = 0.0
    y: float = 0.0

    def copy(self) -> "Vector2":
        return Vector2(self.x, self.y)

    def __add__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2":
        return Vector2(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> "Vector2":
        if scalar == 0:
            return Vector2()
        return Vector2(self.x / scalar, self.y / scalar)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> "Vector2":
        length = self.length()
        return self / length if length else Vector2()

    def distance_to(self, other: "Vector2") -> float:
        return (self - other).length()

    def dot(self, other: "Vector2") -> float:
        return self.x * other.x + self.y * other.y

    def tuple(self) -> tuple[float, float]:
        return self.x, self.y


@dataclass(frozen=True)
class WorldRect:
    """不依賴 Pygame 的軸對齊世界矩形。"""

    left: float
    top: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("WorldRect width and height must be positive")

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height

    @property
    def center(self) -> Vector2:
        return Vector2(self.left + self.width / 2, self.top + self.height / 2)

    def contains(self, point: Vector2) -> bool:
        return (
            self.left <= point.x <= self.right
            and self.top <= point.y <= self.bottom
        )


@dataclass
class ObstacleState:
    """單局牆體狀態；destroyed 只允許薄牆變成 True。"""

    obstacle_id: int
    kind: ObstacleKind
    bounds: WorldRect
    destroyed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ObstacleKind):
            self.kind = ObstacleKind(self.kind)
        if self.kind == ObstacleKind.THICK_WALL:
            self.destroyed = False

    @property
    def solid(self) -> bool:
        return not self.destroyed

    @property
    def destructible(self) -> bool:
        return self.kind == ObstacleKind.THIN_WALL


@dataclass
class BushState:
    """單局草叢狀態；active=False 後不再提供隱藏或繪製。"""

    bush_id: int
    bounds: WorldRect
    active: bool = True


@dataclass
class TerrainHitResult:
    """一次牆體路徑查詢的結果與可用端點。"""

    obstacle: ObstacleState | None = None
    distance: float = 0.0
    position: Vector2 = field(default_factory=Vector2)
    blocked: bool = False
    destroyed: bool = False


@dataclass
class CircleZone:
    """以圓形邊界描述的世界區域。"""

    center: Vector2
    radius: float

    def contains(self, point: Vector2) -> bool:
        return self.center.distance_to(point) <= self.radius


@dataclass
class AimGuide:
    """每幀依輸入建立的世界座標瞄準預覽，不保存比賽狀態。"""

    owner_id: int
    ability_slot: str
    shape: str
    origin: Vector2
    direction: Vector2
    end: Vector2
    range: float = 0.0
    radius: float = 0.0
    angle_degrees: float = 0.0
    # path_points 只描述提示線，不會被世界更新拿來鎖定目標。
    path_points: tuple[Vector2, ...] = field(default_factory=tuple)
    valid: bool = True


@dataclass
class CharacterDefinition:
    character_id: CharacterId
    display_name: str
    primary_kind: str
    ammo_capacity: int
    ammo_recovery_interval: float
    primary_cooldown: float
    primary_damage: float
    primary_range: float
    passive_text: str
    ultimate_text: str
    base_health: float = 100.0
    projectile_speed: float = 0.0
    passive_multiplier: float = 1.0
    passive_condition: str = ""
    parameters: dict[str, float] = field(default_factory=dict)


@dataclass
class TacticalDefinition:
    tactical_id: TacticalId
    display_name: str
    cooldown: float
    description: str
    parameters: dict[str, float] = field(default_factory=dict)


@dataclass
class CombatAction:
    """角色或戰術產生的動作；世界模組負責把動作套用到目標。"""

    kind: str
    owner_id: int
    origin: Vector2
    direction: Vector2 = field(default_factory=lambda: Vector2(1.0, 0.0))
    damage: float = 0.0
    range: float = 0.0
    radius: float = 0.0
    duration: float = 0.0
    max_distance: float = 0.0
    projectile_speed: float = 0.0
    metadata: dict[str, float | int | str] = field(default_factory=dict)
    terrain_interaction: TerrainInteraction = TerrainInteraction.BLOCK


@dataclass
class AbilityEffect:
    """技能或投射物的短生命週期狀態，交由世界更新模組處理。"""

    effect_id: int
    kind: str
    owner_id: int
    position: Vector2
    # 前後位置由同一幀的移動與碰撞共用，避免圖像與命中各算一條路徑。
    previous_position: Vector2 = field(default_factory=Vector2)
    direction: Vector2 = field(default_factory=lambda: Vector2(1.0, 0.0))
    damage: float = 0.0
    radius: float = 0.0
    remaining: float = 0.0
    max_distance: float = 0.0
    projectile_speed: float = 0.0
    distance_travelled: float = 0.0
    tick_timer: float = 0.0
    returning: bool = False
    # 控場地雷未落地前為 False；其他效果維持預設 True。
    armed: bool = True
    # 命中結果固定保存，讓目標移動後提示仍停留在實際碰撞位置。
    impact_position: Vector2 | None = None
    impact_status: str = ""
    hit_target_ids: set[tuple[str, int]] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
    # 固定的施放原點；position 只表示目前前端或範圍中心。
    # 放在既有預設欄位之後，保留舊版 positional dataclass 建構相容性。
    origin: Vector2 = field(default_factory=Vector2)
    terrain_interaction: TerrainInteraction = TerrainInteraction.BLOCK
    terrain_blocker_snapshot: tuple[tuple[int, ObstacleKind, WorldRect], ...] = field(default_factory=tuple)


@dataclass
class DamageEvent:
    sequence: int
    source_player_id: int | None
    target_id: int
    raw_damage: float
    effective_damage: float
    created_at: float
    target_kind: str = "player"


@dataclass
class PlayerState:
    player_id: int
    controller_type: ControllerType
    character_id: CharacterId
    tactical_id: TacticalId
    position: Vector2
    spawn_position: Vector2
    radius: float = 18.0
    base_max_health: float = 100.0
    health_passive_multiplier: float = 1.0
    max_health: float = 100.0
    health: float = 100.0
    move_speed: float = 220.0
    upgrade_stacks: int = 0
    ultimate_energy: float = 0.0
    ammo: int = 0
    ammo_capacity: int = 3
    ammo_recovery_timer: float = 0.0
    tactical_cooldown: float = 0.0
    primary_cooldown: float = 0.0
    death_timer: float = 0.0
    extraction_progress: float = 0.0
    developer_placed: bool = False
    status: PlayerStatus = PlayerStatus.ALIVE
    aim_direction: Vector2 = field(default_factory=lambda: Vector2(1.0, 0.0))
    invulnerability_timer: float = 0.0
    damage_reduction_timer: float = 0.0
    damage_reduction: float = 0.0
    shield_remaining: float = 0.0
    shield_timer: float = 0.0
    slow_timer: float = 0.0
    slow_multiplier: float = 1.0
    root_timer: float = 0.0
    primary_charge: float = 0.0
    ability_input_blocked: bool = False
    last_damage_time: float = 0.0
    auto_aim_enabled: bool = True
    # 本功能欄位追加在現有工作樹欄位之後，保留 positional 建構順序。
    last_attack_time: float = 0.0

    @property
    def alive(self) -> bool:
        return self.status == PlayerStatus.ALIVE

    @alive.setter
    def alive(self, value: bool) -> None:
        self.status = PlayerStatus.ALIVE if value else PlayerStatus.DEAD


@dataclass(frozen=True)
class MonsterDefinition:
    """怪物種類的固定資料；單隻怪物在建立時快照這些戰鬥數值。"""

    monster_type: MonsterType
    display_name: str
    max_health: float
    move_speed: float
    radius: float
    attack_kind: str
    attack_damage: float
    attack_interval: float
    attack_range: float = 0.0
    preferred_range: float = 0.0
    projectile_speed: float = 0.0
    projectile_radius: float = 0.0
    projectile_range: float = 0.0


@dataclass
class MonsterProjectileState:
    """怪物射手的可閃避投射物；以實際前後位置線段判定碰撞。"""

    projectile_id: int
    source_monster_id: int
    position: Vector2
    direction: Vector2
    damage: float
    projectile_speed: float
    radius: float
    max_distance: float
    previous_position: Vector2 = field(default_factory=Vector2)
    distance_travelled: float = 0.0
    remaining: float = 0.0
    impact_position: Vector2 | None = None
    impact_status: str = ""
    impact_target_id: int | None = None


@dataclass
class MonsterState:
    monster_id: int
    spawn_zone_id: int
    position: Vector2
    spawn_position: Vector2
    radius: float = 16.0
    max_health: float = 50.0
    health: float = 50.0
    move_speed: float = 80.0
    target_player_id: int | None = None
    attack_timer: float = 0.0
    respawn_timer: float = 0.0
    last_damage_player_id: int | None = None
    slow_timer: float = 0.0
    slow_multiplier: float = 1.0
    root_timer: float = 0.0
    alive: bool = True
    monster_type: MonsterType = MonsterType.CHASER
    aim_direction: Vector2 = field(default_factory=lambda: Vector2(1.0, 0.0))


@dataclass
class Camera:
    position: Vector2 = field(default_factory=Vector2)
    viewport_size: Vector2 = field(default_factory=lambda: Vector2(1280, 720))
    world_size: Vector2 = field(default_factory=lambda: Vector2(2400, 1400))

    def clamp(self) -> None:
        # 鏡頭左上角的上限必須扣除視窗大小，避免看到世界外的有效區域。
        self.position.x = max(0.0, min(self.position.x, self.world_size.x - self.viewport_size.x))
        self.position.y = max(0.0, min(self.position.y, self.world_size.y - self.viewport_size.y))

    def follow(self, target: Vector2) -> None:
        self.position = target - self.viewport_size / 2
        self.clamp()


@dataclass
class DeveloperModeState:
    enabled: bool = False
    selected_dummy_id: int = 1
    show_overlay: bool = False


@dataclass
class MatchState:
    phase: MatchPhase = MatchPhase.CHARACTER_SELECT
    elapsed_time: float = 0.0
    duration: float = 240.0
    extraction_start_time: float = 210.0
    extraction_required_time: float = 10.0
    extraction_zone: CircleZone = field(
        default_factory=lambda: CircleZone(Vector2(1200, 700), 140.0)
    )
    players: list[PlayerState] = field(default_factory=list)
    monsters: list[MonsterState] = field(default_factory=list)
    winner_id: int | None = None
    developer_mode: DeveloperModeState = field(default_factory=DeveloperModeState)
    camera: Camera = field(default_factory=Camera)
    effects: list[AbilityEffect] = field(default_factory=list)
    messages: list[tuple[str, float]] = field(default_factory=list)
    next_effect_id: int = 1
    next_event_sequence: int = 1
    monster_projectiles: list[MonsterProjectileState] = field(default_factory=list)
    next_monster_projectile_id: int = 1
    # 每個實體保存帶時間戳的位置，供自動瞄準取 lookback 秒前的座標。
    position_history: dict[tuple[str, int], list[tuple[float, Vector2]]] = field(default_factory=dict)
    # 本功能欄位追加在現有工作樹欄位之後，保留 positional 建構順序。
    obstacles: list[ObstacleState] = field(default_factory=list)
    bushes: list[BushState] = field(default_factory=list)
