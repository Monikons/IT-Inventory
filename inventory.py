"""
Модель данных и логика учёта оборудования.
Карточка оборудования: инв. номер, тип, наименование, кабинет, состояние,
дата поступления, ответственное лицо.
"""

import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "inventory.json")

VALID_STATUSES = ("исправно", "требует ремонта", "списано")
REQUIRED_FIELDS = ("inv_number", "equipment_type", "name", "room", "status")


class Inventory:
    """Учёт оборудования колледжа. Хранение в JSON-файле."""

    def __init__(self, filepath: str = DATA_FILE):
        self.filepath = filepath
        self.items: list[dict] = []
        self.load()

    # ---------- хранение ----------
    def load(self):
        """Загрузить данные из JSON. Пустой/отсутствующий файл → пустой список."""
        if not os.path.exists(self.filepath):
            self.items = []
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.items = data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            print("⚠ Файл данных повреждён или недоступен. Начинаем с пустого списка.")
            self.items = []

    def save(self):
        """Сохранить данные в JSON."""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)

    # ---------- CRUD ----------
    def list_all(self) -> list[dict]:
        return self.items

    def find(self, inv_number: str) -> dict | None:
        for it in self.items:
            if it["inv_number"] == inv_number:
                return it
        return None

    def add(self, item: dict) -> tuple[bool, str]:
        """Добавить запись. Возвращает (успех, сообщение)."""
        for field in REQUIRED_FIELDS:
            if not item.get(field, "").strip():
                return False, f"Поле «{field}» обязательно и не может быть пустым."
        if item["status"] not in VALID_STATUSES:
            return False, f"Состояние должно быть одним из: {', '.join(VALID_STATUSES)}."
        if self.find(item["inv_number"]):
            return False, f"Инвентарный номер {item['inv_number']} уже существует."
        self.items.append(item)
        self.save()
        return True, "Запись добавлена."

    def update(self, inv_number: str, **changes) -> tuple[bool, str]:
        """Изменить состояние и/или кабинет записи."""
        it = self.find(inv_number)
        if not it:
            return False, "Не найдено"
        if "status" in changes:
            if changes["status"] not in VALID_STATUSES:
                return False, f"Состояние должно быть одним из: {', '.join(VALID_STATUSES)}."
            it["status"] = changes["status"]
        if "room" in changes and changes["room"].strip():
            it["room"] = changes["room"].strip()
        self.save()
        return True, "Запись обновлена."

    def delete(self, inv_number: str) -> tuple[bool, str]:
        it = self.find(inv_number)
        if not it:
            return False, "Не найдено"
        self.items.remove(it)
        self.save()
        return True, "Запись удалена."

    def by_room(self, room: str) -> list[dict]:
        return [it for it in self.items if it["room"] == room]
