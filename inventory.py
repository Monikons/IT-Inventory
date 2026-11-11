import json
import os
import re

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "inventory.json")

VALID_STATUSES = ("исправно", "требует ремонта", "списано")
REQUIRED_FIELDS = ("inv_number", "equipment_type", "name", "room", "status")
OPTIONAL_FIELDS = ("date_added", "responsible")

# Названия полей для сообщений пользователю
FIELD_LABELS = {
    "inv_number": "Инвентарный номер",
    "equipment_type": "Тип",
    "name": "Наименование",
    "room": "Кабинет",
    "status": "Состояние",
}

UNKNOWN = "неизвестно"   # что показываем, если данные не указаны
ID_PREFIX = "INV-"
ID_MIN_DIGITS = 4        # INV-0001; после INV-9999 число просто станет длиннее
_ID_RE = re.compile(rf"^{re.escape(ID_PREFIX)}(\d+)$", re.IGNORECASE)


# ======================================================================
#  Чистые функции (ничего не печатают, ничего не читают с диска)
# ======================================================================

def parse_inv_number(value) -> int | None:
    """'INV-0007' → 7. Если строка не похожа на инв. номер — None."""
    match = _ID_RE.match(str(value).strip())
    return int(match.group(1)) if match else None


def format_inv_number(number: int) -> str:
    """7 → 'INV-0007'."""
    return f"{ID_PREFIX}{number:0{ID_MIN_DIGITS}d}"


def next_inv_number(items: list[dict]) -> str:
    """Следующий свободный номер: максимальный существующий + 1.

    Записи с «чужими» номерами (не по шаблону INV-N) пропускаются.
    Для пустого списка вернёт INV-0001.
    """
    numbers = []
    for it in items:
        n = parse_inv_number(it.get("inv_number", ""))
        if n is not None:
            numbers.append(n)
    return format_inv_number(max(numbers, default=0) + 1)


def display_value(value) -> str:
    """Что показать пользователю: пустое значение → «неизвестно»."""
    text = "" if value is None else str(value).strip()
    return text if text and text != "—" else UNKNOWN


def normalize_item(raw: dict) -> dict:
    """Привести введённые данные к единому виду.

    - лишние пробелы убираются, не-строки превращаются в строки;
    - состояние приводится к нижнему регистру («Исправно» → «исправно»);
    - необязательные поля (дата, ответственный), если пусты, получают «неизвестно».
    """
    item = {}
    for field in REQUIRED_FIELDS:
        value = raw.get(field)
        item[field] = "" if value is None else str(value).strip()
    item["status"] = item["status"].lower()
    for field in OPTIONAL_FIELDS:
        item[field] = display_value(raw.get(field))
    return item


def validate_item(item: dict) -> tuple[bool, str]:
    """Проверить уже нормализованную запись. Возвращает (успех, сообщение)."""
    for field in REQUIRED_FIELDS:
        if not item.get(field):
            return False, f"Поле «{FIELD_LABELS[field]}» обязательно и не может быть пустым."
    if item["status"] not in VALID_STATUSES:
        return False, f"Состояние должно быть одним из: {', '.join(VALID_STATUSES)}."
    return True, ""


# ======================================================================
#  Хранилище и операции над записями
# ======================================================================

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

    def next_number(self) -> str:
        """Номер, который получит следующая добавленная запись."""
        return next_inv_number(self.items)

    def add(self, item: dict) -> tuple[bool, str]:
        """Добавить запись с готовым инв. номером. Возвращает (успех, сообщение).

        Проверяет обязательные поля, состояние и уникальность номера.
        Пустые необязательные поля заполняются значением «неизвестно».
        """
        item = normalize_item(item)
        ok, message = validate_item(item)
        if not ok:
            return False, message
        if self.find(item["inv_number"]):
            return False, f"Инвентарный номер {item['inv_number']} уже существует."
        self.items.append(item)
        self.save()
        return True, "Запись добавлена."

    def create(self, fields: dict) -> tuple[bool, str]:
        """Добавить запись, присвоив ей новый уникальный инв. номер автоматически.

        Номер в fields (если он там есть) игнорируется.
        """
        item = dict(fields)
        item["inv_number"] = self.next_number()
        ok, message = self.add(item)
        if not ok:
            return False, message
        return True, f"Запись добавлена. Присвоен номер {item['inv_number']}."

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
