"""
Модель данных и логика учёта оборудования.
Хранение — SQLite (data/inventory.db).

Спринт 2: добавление с валидацией, генерация уникального инв. номера,
разделение логики и интерфейса (модуль импортируется без запуска меню).
"""

import os
import re
import sqlite3

DB_FILE = os.path.join(os.path.dirname(__file__), "data", "inventory.db")

VALID_STATUSES = ("исправно", "требует ремонта", "списано")
REQUIRED_FIELDS = ("inv_number", "equipment_type", "name", "room", "status")

SCHEMA = """
CREATE TABLE IF NOT EXISTS equipment (
    inv_number     TEXT PRIMARY KEY,
    equipment_type TEXT NOT NULL,
    name           TEXT NOT NULL,
    room           TEXT NOT NULL,
    status         TEXT NOT NULL CHECK(status IN ('исправно','требует ремонта','списано')),
    date_added     TEXT DEFAULT '—',
    responsible    TEXT DEFAULT '—'
)
"""


class Inventory:
    """Учёт оборудования колледжа. Хранение в SQLite."""

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(SCHEMA)

    # ---------- helpers ----------
    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return dict(row)

    # ---------- генерация инв. номера ----------
    def generate_inv_number(self) -> str:
        """Сгенерировать уникальный инвентарный номер вида INV-XXXX."""
        with self._connect() as conn:
            rows = conn.execute("SELECT inv_number FROM equipment").fetchall()
        numbers = [r["inv_number"] for r in rows]
        max_num = 0
        for n in numbers:
            m = re.match(r"INV-(\d+)", n)
            if m:
                max_num = max(max_num, int(m.group(1)))
        return f"INV-{max_num + 1:04d}"

    # ---------- валидация ----------
    def validate(self, item: dict) -> tuple[bool, str]:
        """Проверить корректность записи. Возвращает (успех, сообщение)."""
        for field in REQUIRED_FIELDS:
            if not item.get(field, "").strip():
                return False, f"Поле «{field}» обязательно и не может быть пустым."
        if item["status"] not in VALID_STATUSES:
            return False, (
                f"Недопустимое состояние «{item['status']}». "
                f"Допустимые: {', '.join(VALID_STATUSES)}."
            )
        if self.find(item["inv_number"]):
            return False, f"Инвентарный номер {item['inv_number']} уже существует."
        return True, "OK"

    # ---------- CRUD ----------
    def list_all(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM equipment ORDER BY inv_number").fetchall()
        return [self._row_to_dict(r) for r in rows]

    def find(self, inv_number: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM equipment WHERE inv_number = ?", (inv_number,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def add(self, item: dict) -> tuple[bool, str]:
        """Добавить запись с валидацией."""
        ok, msg = self.validate(item)
        if not ok:
            return False, msg
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO equipment VALUES (?,?,?,?,?,?,?)",
                    (item["inv_number"], item["equipment_type"], item["name"],
                     item["room"], item["status"],
                     item.get("date_added") or "—", item.get("responsible") or "—"),
                )
            return True, "Запись добавлена."
        except sqlite3.Error as e:
            return False, f"Ошибка базы данных: {e}"

    def update(self, inv_number: str, **changes) -> tuple[bool, str]:
        if not self.find(inv_number):
            return False, "Не найдено"
        sets, params = [], []
        if "status" in changes:
            if changes["status"] not in VALID_STATUSES:
                return False, (
                    f"Недопустимое состояние. "
                    f"Допустимые: {', '.join(VALID_STATUSES)}."
                )
            sets.append("status = ?")
            params.append(changes["status"])
        if "room" in changes and changes["room"].strip():
            sets.append("room = ?")
            params.append(changes["room"].strip())
        if not sets:
            return False, "Нет изменений."
        params.append(inv_number)
        try:
            with self._connect() as conn:
                conn.execute(
                    f"UPDATE equipment SET {', '.join(sets)} WHERE inv_number = ?",
                    params,
                )
            return True, "Запись обновлена."
        except sqlite3.Error as e:
            return False, f"Ошибка базы данных: {e}"

    def delete(self, inv_number: str) -> tuple[bool, str]:
        if not self.find(inv_number):
            return False, "Не найдено"
        with self._connect() as conn:
            conn.execute("DELETE FROM equipment WHERE inv_number = ?", (inv_number,))
        return True, "Запись удалена."

    def by_room(self, room: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM equipment WHERE room = ? ORDER BY inv_number", (room,)
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]
