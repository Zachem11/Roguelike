"""
ПЕПЕЛ ЦИВИЛИЗАЦИИ - Постапокалиптический рогалик
После ядерной войны мир изменился. Радиация пробудила в людях магию.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
import math

# ========================= КОНСТАНТЫ =========================

MAP_WIDTH = 80
MAP_HEIGHT = 40
FOV_RADIUS = 8

# Символы для отрисовки
TILES = {
    'wall': '█',
    'floor': '·',
    'door': '+',
    'stairs_down': '>',
    'stairs_up': '<',
    'water': '~',
    'radiation': '☢',
    'rubble': '%',
    'terminal': '□',
    'chest': '◘',
}

# ========================= ПЕРЕЧИСЛЕНИЯ =========================

class DamageType(Enum):
    PHYSICAL = "физический"
    FIRE = "огонь"
    RADIATION = "радиация"
    ELECTRIC = "электричество"
    COLD = "холод"
    PSYCHIC = "пси"

class CharacterClass(Enum):
    PYROMANCER = "Пиромант"
    STALKER = "Сталкер"
    TECHNOPRIEST = "Технопріст"
    MUTANT = "Мутант"
    PSI_OPERATIVE = "Пси-оперативник"

class ItemType(Enum):
    WEAPON = "оружие"
    ARMOR = "броня"
    CONSUMABLE = "расходник"
    AMMO = "боеприпасы"
    ARTIFACT = "артефакт"
    IMPLANT = "имплант"

# ========================= БАЗОВЫЕ КЛАССЫ =========================

@dataclass
class Point:
    x: int
    y: int

    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def __eq__(self, other):
        if isinstance(other, Point):
            return self.x == other.x and self.y == other.y
        return False

    def __hash__(self):
        return hash((self.x, self.y))

@dataclass
class Spell:
    name: str
    mana_cost: int
    damage: int
    damage_type: DamageType
    range: int
    area: int = 0  # 0 = одиночная цель
    description: str = ""
    cooldown: int = 0
    current_cooldown: int = 0

@dataclass
class Item:
    name: str
    item_type: ItemType
    symbol: str = '?'
    color: str = '#ffffff'
    damage: int = 0
    armor: int = 0
    heal: int = 0
    mana_restore: int = 0
    description: str = ""
    equipped: bool = False
    charges: int = -1  # -1 = бесконечно

@dataclass
class StatusEffect:
    name: str
    duration: int
    damage_per_turn: int = 0
    damage_type: DamageType = DamageType.PHYSICAL
    stat_modifier: dict = field(default_factory=dict)

# ========================= СУЩЕСТВА =========================

@dataclass
class Entity:
    x: int
    y: int
    symbol: str
    name: str
    color: str = '#ffffff'
    blocks: bool = True

    hp: int = 10
    max_hp: int = 10
    mana: int = 0
    max_mana: int = 0

    strength: int = 5
    agility: int = 5
    intellect: int = 5
    endurance: int = 5

    armor: int = 0
    damage: int = 1

    xp: int = 0
    xp_value: int = 10
    level: int = 1

    character_class: Optional[CharacterClass] = None
    spells: list = field(default_factory=list)
    inventory: list = field(default_factory=list)
    effects: list = field(default_factory=list)

    is_player: bool = False
    ai_type: str = "basic"

    fire_resistance: int = 0
    radiation_resistance: int = 0

    @property
    def pos(self) -> Point:
        return Point(self.x, self.y)

    def take_damage(self, amount: int, damage_type: DamageType = DamageType.PHYSICAL) -> int:
        """Получить урон. Возвращает фактический урон."""
        actual = amount

        # Применяем сопротивления
        if damage_type == DamageType.FIRE:
            actual = int(actual * (100 - self.fire_resistance) / 100)
        elif damage_type == DamageType.RADIATION:
            actual = int(actual * (100 - self.radiation_resistance) / 100)

        # Броня снижает физический урон
        if damage_type == DamageType.PHYSICAL:
            actual = max(1, actual - self.armor)

        self.hp -= actual
        return actual

    def heal(self, amount: int) -> int:
        """Исцелиться. Возвращает количество восстановленного HP."""
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - old_hp

    def is_alive(self) -> bool:
        return self.hp > 0

    def get_attack_damage(self) -> int:
        """Получить урон атаки с учётом снаряжения."""
        base = self.damage + self.strength // 2
        for item in self.inventory:
            if item.equipped and item.item_type == ItemType.WEAPON:
                base += item.damage
        return base

# ========================= КАРТА =========================

@dataclass
class Tile:
    walkable: bool = False
    transparent: bool = False
    symbol: str = '█'
    color: str = '#444444'
    explored: bool = False
    visible: bool = False
    name: str = "стена"

class GameMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles = [[Tile() for _ in range(height)] for _ in range(width)]
        self.entities: list[Entity] = []
        self.items: list[tuple[int, int, Item]] = []
        self.depth = 1

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        if not self.in_bounds(x, y):
            return False
        return self.tiles[x][y].walkable

    def is_blocked(self, x: int, y: int) -> bool:
        """Проверка на блокировку (стена или существо)."""
        if not self.is_walkable(x, y):
            return True
        for entity in self.entities:
            if entity.x == x and entity.y == y and entity.blocks:
                return True
        return False

    def get_entity_at(self, x: int, y: int) -> Optional[Entity]:
        for entity in self.entities:
            if entity.x == x and entity.y == y:
                return entity
        return None

    def get_items_at(self, x: int, y: int) -> list[Item]:
        return [item for ix, iy, item in self.items if ix == x and iy == y]

    def remove_item(self, x: int, y: int, item: Item):
        self.items = [(ix, iy, i) for ix, iy, i in self.items
                      if not (ix == x and iy == y and i == item)]

# ========================= ГЕНЕРАЦИЯ КАРТЫ =========================

class MapGenerator:
    """Генератор постапокалиптических локаций."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    def generate_ruins(self, depth: int = 1) -> GameMap:
        """Генерация руин города."""
        game_map = GameMap(self.width, self.height)
        game_map.depth = depth

        # Заполняем стенами
        for x in range(self.width):
            for y in range(self.height):
                game_map.tiles[x][y] = Tile(
                    walkable=False, transparent=False,
                    symbol=TILES['wall'], color='#444444', name="бетонная стена"
                )

        # Генерируем комнаты (разрушенные здания)
        rooms = []
        for _ in range(15 + depth * 2):
            w = random.randint(5, 12)
            h = random.randint(4, 10)
            x = random.randint(1, self.width - w - 1)
            y = random.randint(1, self.height - h - 1)

            # Проверяем пересечение
            new_room = (x, y, w, h)
            if not any(self._rooms_intersect(new_room, r) for r in rooms):
                self._carve_room(game_map, x, y, w, h, depth)

                # Соединяем с предыдущей комнатой
                if rooms:
                    prev = rooms[-1]
                    self._create_corridor(game_map,
                        x + w // 2, y + h // 2,
                        prev[0] + prev[2] // 2, prev[1] + prev[3] // 2
                    )

                rooms.append(new_room)

        # Добавляем лестницы
        if rooms:
            # Лестница вниз в последней комнате
            last = rooms[-1]
            sx, sy = last[0] + last[2] // 2, last[1] + last[3] // 2
            game_map.tiles[sx][sy] = Tile(
                walkable=True, transparent=True,
                symbol=TILES['stairs_down'], color='#ffff00', name="спуск вниз"
            )

            # Лестница вверх в первой комнате (если не первый уровень)
            if depth > 1:
                first = rooms[0]
                ux, uy = first[0] + 1, first[1] + 1
                game_map.tiles[ux][uy] = Tile(
                    walkable=True, transparent=True,
                    symbol=TILES['stairs_up'], color='#00ffff', name="подъём вверх"
                )

        # Добавляем опасности и интересности
        self._add_hazards(game_map, rooms, depth)
        self._add_loot(game_map, rooms, depth)

        return game_map

    def _rooms_intersect(self, r1, r2) -> bool:
        return (r1[0] <= r2[0] + r2[2] + 1 and r1[0] + r1[2] + 1 >= r2[0] and
                r1[1] <= r2[1] + r2[3] + 1 and r1[1] + r1[3] + 1 >= r2[1])

    def _carve_room(self, game_map: GameMap, x: int, y: int, w: int, h: int, depth: int):
        """Вырезаем комнату с постапокалиптическим декором."""
        for rx in range(x, x + w):
            for ry in range(y, y + h):
                # Случайный мусор в комнатах
                if random.random() < 0.05:
                    game_map.tiles[rx][ry] = Tile(
                        walkable=True, transparent=True,
                        symbol=TILES['rubble'], color='#888888', name="обломки"
                    )
                else:
                    game_map.tiles[rx][ry] = Tile(
                        walkable=True, transparent=True,
                        symbol=TILES['floor'], color='#666666', name="потрескавшийся пол"
                    )

    def _create_corridor(self, game_map: GameMap, x1: int, y1: int, x2: int, y2: int):
        """Создаём коридор между точками."""
        x, y = x1, y1

        while x != x2:
            if game_map.in_bounds(x, y):
                game_map.tiles[x][y] = Tile(
                    walkable=True, transparent=True,
                    symbol=TILES['floor'], color='#555555', name="коридор"
                )
            x += 1 if x2 > x else -1

        while y != y2:
            if game_map.in_bounds(x, y):
                game_map.tiles[x][y] = Tile(
                    walkable=True, transparent=True,
                    symbol=TILES['floor'], color='#555555', name="коридор"
                )
            y += 1 if y2 > y else -1

    def _add_hazards(self, game_map: GameMap, rooms: list, depth: int):
        """Добавляем радиоактивные зоны и другие опасности."""
        for room in rooms:
            if random.random() < 0.2 + depth * 0.05:
                rx = random.randint(room[0], room[0] + room[2] - 1)
                ry = random.randint(room[1], room[1] + room[3] - 1)
                if game_map.tiles[rx][ry].walkable:
                    game_map.tiles[rx][ry] = Tile(
                        walkable=True, transparent=True,
                        symbol=TILES['radiation'], color='#00ff00',
                        name="радиоактивная лужа"
                    )

    def _add_loot(self, game_map: GameMap, rooms: list, depth: int):
        """Добавляем контейнеры с лутом."""
        for room in rooms:
            if random.random() < 0.3:
                rx = random.randint(room[0], room[0] + room[2] - 1)
                ry = random.randint(room[1], room[1] + room[3] - 1)
                if game_map.tiles[rx][ry].walkable and game_map.tiles[rx][ry].symbol == TILES['floor']:
                    item = self._generate_random_item(depth)
                    game_map.items.append((rx, ry, item))

    def _generate_random_item(self, depth: int) -> Item:
        """Генерация случайного предмета."""
        item_templates = [
            Item("Ржавый пистолет", ItemType.WEAPON, '/', '#aaaaaa', damage=3+depth,
                 description="Старый полуавтоматический пистолет"),
            Item("Аптечка", ItemType.CONSUMABLE, '!', '#ff0000', heal=20+depth*5,
                 description="Армейская аптечка первой помощи"),
            Item("Антирад", ItemType.CONSUMABLE, '!', '#00ff00', heal=0,
                 description="Снижает радиационное заражение"),
            Item("Бронежилет", ItemType.ARMOR, '[', '#5555ff', armor=2+depth//2,
                 description="Кевларовый бронежилет"),
            Item("Обрез", ItemType.WEAPON, '/', '#884422', damage=6+depth,
                 description="Двуствольный обрез"),
            Item("Энергонапиток", ItemType.CONSUMABLE, '!', '#ffff00', mana_restore=15+depth*3,
                 description="Восстанавливает ментальную энергию"),
            Item("Термоядерная батарея", ItemType.ARTIFACT, '*', '#ff00ff',
                 description="Излучает слабое тепло. Ценный артефакт."),
        ]
        return random.choice(item_templates)

    def get_player_start(self, game_map: GameMap) -> tuple[int, int]:
        """Найти стартовую позицию для игрока."""
        for x in range(self.width):
            for y in range(self.height):
                if game_map.tiles[x][y].walkable:
                    return x, y
        return self.width // 2, self.height // 2

# ========================= ЗАКЛИНАНИЯ =========================

PYROMANCER_SPELLS = [
    Spell("Огненный шар", 15, 25, DamageType.FIRE, 6, area=2,
          description="Взрыв пламени, наносящий урон всем в радиусе. Мощность крематория!"),
    Spell("Поток пламени", 8, 12, DamageType.FIRE, 4, area=0,
          description="Направленная струя огня"),
    Spell("Огненная стена", 20, 8, DamageType.FIRE, 5, area=3,
          description="Создаёт стену огня, наносящую урон проходящим"),
    Spell("Испепеление", 35, 50, DamageType.FIRE, 3, area=0, cooldown=5,
          description="Мгновенно испепеляет цель. Температура солнечной короны!"),
    Spell("Взрыв сверхновой", 50, 40, DamageType.FIRE, 0, area=5, cooldown=10,
          description="Опустошающий взрыв вокруг мага. Выжигает всё живое!"),
]

STALKER_SPELLS = [
    Spell("Меткий выстрел", 5, 15, DamageType.PHYSICAL, 10,
          description="Точный выстрел в уязвимое место"),
    Spell("Аура невидимости", 10, 0, DamageType.PHYSICAL, 0,
          description="Временная невидимость"),
]

TECHNOPRIEST_SPELLS = [
    Spell("Электрошок", 8, 10, DamageType.ELECTRIC, 5,
          description="Разряд электричества"),
    Spell("Взлом дрона", 15, 0, DamageType.PSYCHIC, 6,
          description="Перехват контроля над роботом"),
    Spell("EMP-импульс", 25, 15, DamageType.ELECTRIC, 0, area=4,
          description="Электромагнитный импульс - особенно эффективен против роботов"),
]

PSI_OPERATIVE_SPELLS = [
    Spell("Ментальный удар", 10, 12, DamageType.PSYCHIC, 6,
          description="Атака разума"),
    Spell("Контроль разума", 20, 0, DamageType.PSYCHIC, 5,
          description="Временный контроль над врагом"),
    Spell("Пси-щит", 15, 0, DamageType.PSYCHIC, 0,
          description="Защитный ментальный барьер"),
]

MUTANT_SPELLS = [
    Spell("Регенерация", 10, -20, DamageType.RADIATION, 0,
          description="Мутировавшие клетки быстро восстанавливаются"),
    Spell("Кислотный плевок", 8, 10, DamageType.RADIATION, 4,
          description="Плевок едкой слизью"),
    Spell("Радиоактивный взрыв", 20, 18, DamageType.RADIATION, 0, area=3,
          description="Выброс накопленной радиации"),
]

# ========================= ВРАГИ =========================

def create_enemy(enemy_type: str, x: int, y: int, depth: int = 1) -> Entity:
    """Фабрика врагов."""

    templates = {
        "raider": Entity(
            x=x, y=y, symbol='r', name="Рейдер", color='#ff4444',
            hp=15 + depth * 3, max_hp=15 + depth * 3,
            strength=4 + depth, damage=3 + depth, armor=depth // 2,
            xp_value=15 + depth * 5, ai_type="aggressive"
        ),
        "mutant_dog": Entity(
            x=x, y=y, symbol='d', name="Пёс-мутант", color='#884400',
            hp=10 + depth * 2, max_hp=10 + depth * 2,
            strength=3 + depth, agility=7, damage=4 + depth,
            xp_value=10 + depth * 3, ai_type="aggressive",
            radiation_resistance=50
        ),
        "ghoul": Entity(
            x=x, y=y, symbol='g', name="Гуль", color='#00aa00',
            hp=20 + depth * 4, max_hp=20 + depth * 4,
            strength=5 + depth, damage=5 + depth,
            xp_value=20 + depth * 5, ai_type="aggressive",
            radiation_resistance=100
        ),
        "robot_sentry": Entity(
            x=x, y=y, symbol='R', name="Робот-охранник", color='#4444ff',
            hp=25 + depth * 5, max_hp=25 + depth * 5,
            strength=6 + depth, damage=8 + depth, armor=3 + depth,
            xp_value=30 + depth * 8, ai_type="patrol",
            fire_resistance=30
        ),
        "wild_pyromancer": Entity(
            x=x, y=y, symbol='P', name="Дикий пиромант", color='#ff8800',
            hp=18 + depth * 3, max_hp=18 + depth * 3,
            mana=50, max_mana=50, intellect=8,
            damage=2, xp_value=40 + depth * 10, ai_type="caster",
            fire_resistance=75,
            spells=[PYROMANCER_SPELLS[0], PYROMANCER_SPELLS[1]]
        ),
        "deathclaw": Entity(
            x=x, y=y, symbol='D', name="Коготь смерти", color='#660000',
            hp=50 + depth * 10, max_hp=50 + depth * 10,
            strength=12 + depth * 2, agility=8, damage=15 + depth * 2,
            armor=5, xp_value=100 + depth * 20, ai_type="aggressive",
            radiation_resistance=80
        ),
    }

    if enemy_type in templates:
        enemy = templates[enemy_type]
        enemy.level = depth
        return enemy

    # Дефолтный враг
    return templates["raider"]

def spawn_enemies(game_map: GameMap, count: int = None) -> list[Entity]:
    """Размещение врагов на карте."""
    if count is None:
        count = 3 + game_map.depth * 2

    enemies = []
    enemy_types = ["raider", "mutant_dog", "ghoul", "robot_sentry"]

    # Добавляем более сильных врагов на глубоких уровнях
    if game_map.depth >= 3:
        enemy_types.append("wild_pyromancer")
    if game_map.depth >= 5:
        enemy_types.append("deathclaw")

    attempts = 0
    while len(enemies) < count and attempts < 100:
        x = random.randint(1, game_map.width - 2)
        y = random.randint(1, game_map.height - 2)

        if (game_map.is_walkable(x, y) and
            not game_map.get_entity_at(x, y) and
            game_map.tiles[x][y].symbol == TILES['floor']):

            enemy_type = random.choice(enemy_types)
            enemy = create_enemy(enemy_type, x, y, game_map.depth)
            enemies.append(enemy)
            game_map.entities.append(enemy)

        attempts += 1

    return enemies

# ========================= ПОЛЕ ЗРЕНИЯ =========================

def compute_fov(game_map: GameMap, x: int, y: int, radius: int):
    """Расчёт поля зрения с помощью raycasting."""
    # Сбрасываем видимость
    for tx in range(game_map.width):
        for ty in range(game_map.height):
            game_map.tiles[tx][ty].visible = False

    # Точка игрока всегда видима
    game_map.tiles[x][y].visible = True
    game_map.tiles[x][y].explored = True

    # Бросаем лучи во все стороны
    for angle in range(360):
        rad = angle * math.pi / 180
        dx = math.cos(rad)
        dy = math.sin(rad)

        px, py = float(x) + 0.5, float(y) + 0.5

        for _ in range(radius):
            px += dx
            py += dy

            tx, ty = int(px), int(py)

            if not game_map.in_bounds(tx, ty):
                break

            game_map.tiles[tx][ty].visible = True
            game_map.tiles[tx][ty].explored = True

            if not game_map.tiles[tx][ty].transparent:
                break

# ========================= ИИ ВРАГОВ =========================

def enemy_ai_turn(enemy: Entity, player: Entity, game_map: GameMap, log_callback: Callable):
    """Ход ИИ врага."""
    if not enemy.is_alive():
        return

    distance = enemy.pos.distance_to(player.pos)

    # Проверяем, видит ли враг игрока
    if not game_map.tiles[enemy.x][enemy.y].visible:
        # Враг не в поле зрения - случайное блуждание
        if random.random() < 0.3:
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            new_x, new_y = enemy.x + dx, enemy.y + dy
            if game_map.is_walkable(new_x, new_y) and not game_map.get_entity_at(new_x, new_y):
                enemy.x, enemy.y = new_x, new_y
        return

    # Кастеры пытаются использовать заклинания
    if enemy.ai_type == "caster" and enemy.spells and enemy.mana >= enemy.spells[0].mana_cost:
        if distance <= enemy.spells[0].range:
            spell = enemy.spells[0]
            enemy.mana -= spell.mana_cost
            damage = player.take_damage(spell.damage, spell.damage_type)
            log_callback(f"{enemy.name} использует {spell.name}! Урон: {damage}")
            return

    # Агрессивные враги идут к игроку
    if enemy.ai_type in ["aggressive", "caster"]:
        if distance <= 1.5:
            # Атака в ближнем бою
            damage = enemy.get_attack_damage()
            actual = player.take_damage(damage)
            log_callback(f"{enemy.name} атакует! Урон: {actual}")
        else:
            # Движение к игроку
            dx = 0 if player.x == enemy.x else (1 if player.x > enemy.x else -1)
            dy = 0 if player.y == enemy.y else (1 if player.y > enemy.y else -1)

            new_x, new_y = enemy.x + dx, enemy.y + dy
            if not game_map.is_blocked(new_x, new_y):
                enemy.x, enemy.y = new_x, new_y
            elif not game_map.is_blocked(enemy.x + dx, enemy.y):
                enemy.x += dx
            elif not game_map.is_blocked(enemy.x, enemy.y + dy):
                enemy.y += dy

# ========================= СОЗДАНИЕ ПЕРСОНАЖА =========================

def create_player(char_class: CharacterClass, x: int, y: int) -> Entity:
    """Создание игрока выбранного класса."""

    base_stats = {
        CharacterClass.PYROMANCER: {
            "hp": 80, "mana": 100, "str": 4, "agi": 5, "int": 10, "end": 5,
            "spells": PYROMANCER_SPELLS.copy(),
            "fire_res": 50, "rad_res": 0,
            "description": "Повелитель огня. Способен испепелять врагов потоками пламени."
        },
        CharacterClass.STALKER: {
            "hp": 100, "mana": 40, "str": 6, "agi": 8, "int": 5, "end": 7,
            "spells": STALKER_SPELLS.copy(),
            "fire_res": 10, "rad_res": 30,
            "description": "Выживальщик пустошей. Мастер скрытности и дальнего боя."
        },
        CharacterClass.TECHNOPRIEST: {
            "hp": 85, "mana": 70, "str": 4, "agi": 5, "int": 9, "end": 6,
            "spells": TECHNOPRIEST_SPELLS.copy(),
            "fire_res": 20, "rad_res": 20,
            "description": "Жрец машинного культа. Повелевает электричеством и техникой."
        },
        CharacterClass.PSI_OPERATIVE: {
            "hp": 70, "mana": 90, "str": 3, "agi": 6, "int": 10, "end": 4,
            "spells": PSI_OPERATIVE_SPELLS.copy(),
            "fire_res": 0, "rad_res": 10,
            "description": "Псионик. Атакует и защищается силой разума."
        },
        CharacterClass.MUTANT: {
            "hp": 120, "mana": 50, "str": 9, "agi": 4, "int": 4, "end": 10,
            "spells": MUTANT_SPELLS.copy(),
            "fire_res": 20, "rad_res": 80,
            "description": "Мутировавший от радиации. Невероятно живуч."
        },
    }

    stats = base_stats[char_class]

    player = Entity(
        x=x, y=y,
        symbol='@', name="Выживший", color='#ffffff',
        hp=stats["hp"], max_hp=stats["hp"],
        mana=stats["mana"], max_mana=stats["mana"],
        strength=stats["str"], agility=stats["agi"],
        intellect=stats["int"], endurance=stats["end"],
        damage=2, armor=0,
        character_class=char_class,
        spells=stats["spells"],
        fire_resistance=stats["fire_res"],
        radiation_resistance=stats["rad_res"],
        is_player=True
    )

    # Стартовое снаряжение
    if char_class == CharacterClass.STALKER:
        player.inventory.append(Item("Охотничий нож", ItemType.WEAPON, '/', '#aaaaaa', damage=4))
        player.inventory.append(Item("Кожаная куртка", ItemType.ARMOR, '[', '#884422', armor=2))
    elif char_class == CharacterClass.PYROMANCER:
        player.inventory.append(Item("Посох пламени", ItemType.WEAPON, '/', '#ff4400', damage=2))
    elif char_class == CharacterClass.TECHNOPRIEST:
        player.inventory.append(Item("Электрошокер", ItemType.WEAPON, '/', '#4444ff', damage=3))

    player.inventory.append(Item("Аптечка", ItemType.CONSUMABLE, '!', '#ff0000', heal=25))

    return player

# ========================= ИГРА =========================

class Game:
    """Основной класс игры."""

    def __init__(self):
        self.game_map: Optional[GameMap] = None
        self.player: Optional[Entity] = None
        self.log: list[str] = []
        self.state: str = "class_select"  # class_select, playing, dead, inventory, spells, targeting
        self.turn: int = 0
        self.selected_spell: Optional[Spell] = None
        self.target_x: int = 0
        self.target_y: int = 0

    def add_log(self, message: str):
        """Добавить сообщение в журнал."""
        self.log.append(message)
        if len(self.log) > 100:
            self.log = self.log[-50:]

    def select_class(self, char_class: CharacterClass):
        """Выбор класса и начало игры."""
        generator = MapGenerator(MAP_WIDTH, MAP_HEIGHT)
        self.game_map = generator.generate_ruins(depth=1)

        start_x, start_y = generator.get_player_start(self.game_map)
        self.player = create_player(char_class, start_x, start_y)
        self.game_map.entities.append(self.player)

        spawn_enemies(self.game_map)
        compute_fov(self.game_map, self.player.x, self.player.y, FOV_RADIUS)

        self.state = "playing"
        self.add_log(f"Вы - {char_class.value}. Добро пожаловать в пустошь!")
        self.add_log("Управление: WASD/стрелки - движение, SPACE - ждать")
        self.add_log("C - заклинания, I - инвентарь, G - подобрать предмет")

    def move_player(self, dx: int, dy: int) -> bool:
        """Передвижение игрока. Возвращает True если ход совершён."""
        if self.state != "playing" or not self.player:
            return False

        new_x = self.player.x + dx
        new_y = self.player.y + dy

        # Проверяем на врага
        target = self.game_map.get_entity_at(new_x, new_y)
        if target and target != self.player:
            return self.attack(target)

        # Проверяем проходимость
        if self.game_map.is_walkable(new_x, new_y):
            self.player.x = new_x
            self.player.y = new_y

            # Проверяем тайл под игроком
            tile = self.game_map.tiles[new_x][new_y]
            if tile.symbol == TILES['radiation']:
                damage = self.player.take_damage(3, DamageType.RADIATION)
                self.add_log(f"Радиация! Получено {damage} урона.")
            elif tile.symbol == TILES['stairs_down']:
                self.add_log("Вы видите спуск вниз. Нажмите > чтобы спуститься.")

            # Проверяем предметы
            items = self.game_map.get_items_at(new_x, new_y)
            if items:
                self.add_log(f"Здесь лежит: {', '.join(i.name for i in items)}")

            self.end_turn()
            return True

        return False

    def attack(self, target: Entity) -> bool:
        """Атака цели."""
        damage = self.player.get_attack_damage()

        # Бонус от ловкости
        if random.random() < self.player.agility / 20:
            damage = int(damage * 1.5)
            self.add_log("Критический удар!")

        actual = target.take_damage(damage)
        self.add_log(f"Вы атакуете {target.name}. Урон: {actual}")

        if not target.is_alive():
            self.add_log(f"{target.name} повержен!")
            self.player.xp += target.xp_value
            self.check_level_up()
            self.game_map.entities.remove(target)

        self.end_turn()
        return True

    def cast_spell(self, spell: Spell, target_x: int, target_y: int) -> bool:
        """Использование заклинания."""
        if self.player.mana < spell.mana_cost:
            self.add_log("Недостаточно маны!")
            return False

        if spell.current_cooldown > 0:
            self.add_log(f"{spell.name} перезаряжается ещё {spell.current_cooldown} ходов")
            return False

        distance = self.player.pos.distance_to(Point(target_x, target_y))
        if spell.range > 0 and distance > spell.range:
            self.add_log("Цель слишком далеко!")
            return False

        self.player.mana -= spell.mana_cost
        spell.current_cooldown = spell.cooldown

        # Область поражения
        if spell.area > 0:
            targets_hit = 0
            for entity in self.game_map.entities:
                if entity == self.player:
                    continue
                dist = entity.pos.distance_to(Point(target_x, target_y))
                if dist <= spell.area:
                    actual = entity.take_damage(spell.damage, spell.damage_type)
                    self.add_log(f"{spell.name} поражает {entity.name}! Урон: {actual}")
                    targets_hit += 1

                    if not entity.is_alive():
                        self.add_log(f"{entity.name} испепелён!")
                        self.player.xp += entity.xp_value
                        self.game_map.entities.remove(entity)

            if targets_hit == 0:
                self.add_log(f"{spell.name} никого не задел.")
        else:
            # Одиночная цель
            target = self.game_map.get_entity_at(target_x, target_y)
            if target and target != self.player:
                # Отрицательный урон = лечение
                if spell.damage < 0:
                    healed = target.heal(-spell.damage)
                    self.add_log(f"{spell.name}: восстановлено {healed} HP")
                else:
                    actual = target.take_damage(spell.damage, spell.damage_type)
                    self.add_log(f"{spell.name} поражает {target.name}! Урон: {actual}")

                    if not target.is_alive():
                        self.add_log(f"{target.name} повержен!")
                        self.player.xp += target.xp_value
                        self.game_map.entities.remove(target)
            elif spell.damage < 0:
                # Самолечение
                healed = self.player.heal(-spell.damage)
                self.add_log(f"{spell.name}: восстановлено {healed} HP")
            else:
                self.add_log(f"{spell.name} - промах!")

        self.state = "playing"
        self.selected_spell = None
        self.end_turn()
        return True

    def use_item(self, item: Item) -> bool:
        """Использование предмета."""
        if item.item_type == ItemType.CONSUMABLE:
            if item.heal > 0:
                healed = self.player.heal(item.heal)
                self.add_log(f"Использована {item.name}. Восстановлено {healed} HP.")
            if item.mana_restore > 0:
                old_mana = self.player.mana
                self.player.mana = min(self.player.max_mana, self.player.mana + item.mana_restore)
                restored = self.player.mana - old_mana
                self.add_log(f"Использован {item.name}. Восстановлено {restored} маны.")

            self.player.inventory.remove(item)
            self.end_turn()
            return True

        elif item.item_type in [ItemType.WEAPON, ItemType.ARMOR]:
            # Экипировка
            item.equipped = not item.equipped
            status = "экипировано" if item.equipped else "снято"
            self.add_log(f"{item.name} {status}.")
            return True

        return False

    def pickup_item(self) -> bool:
        """Подобрать предмет под игроком."""
        items = self.game_map.get_items_at(self.player.x, self.player.y)
        if items:
            item = items[0]
            self.player.inventory.append(item)
            self.game_map.remove_item(self.player.x, self.player.y, item)
            self.add_log(f"Подобрано: {item.name}")
            self.end_turn()
            return True
        else:
            self.add_log("Здесь ничего нет.")
            return False

    def descend(self) -> bool:
        """Спуск на следующий уровень."""
        tile = self.game_map.tiles[self.player.x][self.player.y]
        if tile.symbol != TILES['stairs_down']:
            self.add_log("Здесь нет спуска.")
            return False

        new_depth = self.game_map.depth + 1
        generator = MapGenerator(MAP_WIDTH, MAP_HEIGHT)

        # Сохраняем игрока
        player = self.player
        self.game_map.entities.remove(player)

        # Генерируем новый уровень
        self.game_map = generator.generate_ruins(new_depth)

        # Размещаем игрока
        start_x, start_y = generator.get_player_start(self.game_map)
        player.x, player.y = start_x, start_y
        self.game_map.entities.append(player)
        self.player = player

        spawn_enemies(self.game_map)
        compute_fov(self.game_map, self.player.x, self.player.y, FOV_RADIUS)

        self.add_log(f"Вы спустились на уровень {new_depth}. Враги сильнее...")
        return True

    def check_level_up(self):
        """Проверка повышения уровня."""
        xp_needed = self.player.level * 100
        while self.player.xp >= xp_needed:
            self.player.xp -= xp_needed
            self.player.level += 1

            # Бонусы за уровень
            self.player.max_hp += 10
            self.player.hp += 10
            self.player.max_mana += 5
            self.player.mana += 5
            self.player.strength += 1
            self.player.intellect += 1

            self.add_log(f"УРОВЕНЬ {self.player.level}! HP и Мана увеличены!")
            xp_needed = self.player.level * 100

    def end_turn(self):
        """Завершение хода игрока - ход врагов."""
        self.turn += 1

        # Обновляем кулдауны заклинаний
        for spell in self.player.spells:
            if spell.current_cooldown > 0:
                spell.current_cooldown -= 1

        # Регенерация маны
        if self.turn % 3 == 0:
            self.player.mana = min(self.player.max_mana, self.player.mana + 1)

        # Ходы врагов
        for entity in list(self.game_map.entities):
            if entity != self.player and entity.is_alive():
                enemy_ai_turn(entity, self.player, self.game_map, self.add_log)

        # Проверка смерти игрока
        if not self.player.is_alive():
            self.state = "dead"
            self.add_log("ВЫ ПОГИБЛИ! Пустошь забрала ещё одну жизнь...")

        # Обновляем поле зрения
        compute_fov(self.game_map, self.player.x, self.player.y, FOV_RADIUS)

    def wait(self):
        """Пропуск хода."""
        self.add_log("Вы ждёте...")
        self.end_turn()

    def get_visible_entities(self) -> list[Entity]:
        """Получить список видимых существ."""
        visible = []
        for entity in self.game_map.entities:
            if entity != self.player:
                if self.game_map.tiles[entity.x][entity.y].visible:
                    visible.append(entity)
        return visible

    def render_map(self) -> list[list[tuple[str, str]]]:
        """Рендер карты в виде матрицы (символ, цвет)."""
        result = []

        for y in range(self.game_map.height):
            row = []
            for x in range(self.game_map.width):
                tile = self.game_map.tiles[x][y]

                if tile.visible:
                    # Проверяем сущности
                    entity = self.game_map.get_entity_at(x, y)
                    if entity:
                        row.append((entity.symbol, entity.color))
                    else:
                        # Проверяем предметы
                        items = self.game_map.get_items_at(x, y)
                        if items:
                            row.append((items[0].symbol, items[0].color))
                        else:
                            row.append((tile.symbol, tile.color))
                elif tile.explored:
                    # Исследованные, но не видимые тайлы - затемнённые
                    row.append((tile.symbol, '#222222'))
                else:
                    row.append((' ', '#000000'))

            result.append(row)

        return result
