import heapq
import math
import random

from apps.game_core.resources.game_data.world_config import (
    BIOME_DEFINITIONS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
)


class PathFinder:
    """
    Универсальный навигатор.
    Используется и Генератором (для дорог), и Геймплеем (для автопилота).
    """

    def __init__(self, zone_biome_map: dict[str, str], zone_id_map: dict[tuple[int, int], str]):
        """
        :param zone_biome_map: {zone_id: biome_id} (карта биомов)
        :param zone_id_map: {(x, y): zone_id} (карта зон)
        """
        self.zone_biome_map = zone_biome_map
        self.zone_id_map = zone_id_map

        # Кэш стоимостей биомов, чтобы не парсить конфиг на каждом шаге A*
        self._biome_cost_cache = self._precompute_biome_costs()

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def get_path(self, start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
        """
        [Для Автопилота] Ищет оптимальный путь A* из точки А в Б.
        Огибает сложные биомы.
        """
        return self._find_path_a_star(start, end)

    def build_road_network(self, key_points: list[tuple[int, int]]) -> set[tuple[int, int]]:
        """
        [Для Генератора] Принимает список точек (POI), строит MST-граф
        и возвращает набор клеток, которые нужно залить асфальтом.
        """
        # 1. Строим логические связи (Кто с кем?)
        connections = self._build_mst_topology(key_points)

        road_cells = set()
        print(f"PathFinder: Routing {len(connections)} connections...")

        # 2. Прокладываем физические пути
        for p1, p2 in connections:
            path = self._find_path_a_star(p1, p2)
            for cell in path:
                road_cells.add(cell)

        return road_cells

    # =========================================================================
    # INTERNAL LOGIC
    # =========================================================================

    def _precompute_biome_costs(self) -> dict[str, float]:
        """
        Превращает сложный конфиг BIOME_DEFINITIONS в плоский словарь {biome_id: cost}.
        Берем дефолтный (самый частый) тип местности в биоме как базовую стоимость.
        """
        costs = {}
        for biome_id, terrains in BIOME_DEFINITIONS.items():
            # Пытаемся найти репрезентативный тип.
            # Обычно это тот, у кого самый большой spawn_weight, но для упрощения
            # берем 'thicket' для леса, 'flat' для пустоши, или просто первый попавшийся.

            # Эвристика: ищем ключи, похожие на дефолт
            default_key = next(iter(terrains))  # Берем первый как фолбэк

            if "thicket" in terrains:
                default_key = "thicket"
            elif "flat" in terrains:
                default_key = "flat"
            elif "shallow" in terrains:
                default_key = "shallow"

            costs[biome_id] = terrains[default_key]["travel_cost"]

        # Добавляем дефолт на случай ошибки
        costs["unknown"] = 1.0
        return costs

    def _get_cell_cost(self, x: int, y: int) -> float:
        """
        O(1) получение стоимости. Никаких IF.
        """
        if not (0 <= x < WORLD_WIDTH and 0 <= y < WORLD_HEIGHT):
            return 999.0

        z_id = self.zone_id_map.get((x, y))
        if not z_id:
            return 1.0

        biome_id = self.zone_biome_map.get(z_id, "unknown")

        # Мгновенный лукап в кэше вместо 14 if-ов
        return self._biome_cost_cache.get(biome_id, 1.0)

    def _build_mst_topology(self, nodes: list[tuple[int, int]]) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        """
        Строит Граф (MST + Loops). Чистая математика, не ходит по карте.
        """
        if not nodes or len(nodes) < 2:
            return []

        # 1. Все возможные ребра
        edges = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                p1, p2 = nodes[i], nodes[j]
                # Евклидово расстояние (просто по прямой)
                dist = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
                edges.append((dist, p1, p2))

        edges.sort(key=lambda x: x[0])

        # 2. Краскал (Union-Find)
        parent = {node: node for node in nodes}

        def find(n):
            if parent[n] != n:
                parent[n] = find(parent[n])
            return parent[n]

        def union(n1, n2):
            r1, r2 = find(n1), find(n2)
            if r1 != r2:
                parent[r1] = r2
                return True
            return False

        mst_conns = []
        rejected = []

        for dist, p1, p2 in edges:
            if union(p1, p2):
                mst_conns.append((p1, p2))
            elif dist < 40:  # Если точки близко, но уже соединены в обход - запоминаем
                rejected.append((p1, p2))

        # 3. Петли (для интересности)
        num_cycles = int(len(rejected) * 0.15)  # 15% петель
        random.shuffle(rejected)

        return mst_conns + rejected[:num_cycles]

    def _find_path_a_star(self, start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
        """Классический A*."""
        if start == end:
            return [start]

        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        frontier: list[tuple[float, tuple[int, int]]] = []
        heapq.heappush(frontier, (0, start))
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        cost_so_far = {start: 0.0}

        while frontier:
            _, current = heapq.heappop(frontier)

            if current == end:
                break

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_node = (current[0] + dx, current[1] + dy)

                cell_cost = self._get_cell_cost(*next_node)
                if cell_cost >= 999.0:
                    continue

                new_cost = cost_so_far[current] + cell_cost

                if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                    cost_so_far[next_node] = new_cost
                    priority = new_cost + heuristic(end, next_node)
                    heapq.heappush(frontier, (priority, next_node))
                    came_from[next_node] = current

        # Восстановление пути
        if end not in came_from:
            return []  # Пути нет

        path = []
        curr: tuple[int, int] | None = end
        while curr:
            path.append(curr)
            curr = came_from[curr]
        return path[::-1]  # Разворачиваем (от старта к концу)
