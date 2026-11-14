import copy
import json
import shutil
from datetime import datetime
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
    """Учёт оборудования колледжа. Хранение в JSON-файле (формат версии 2)."""

    FORMAT_VERSION = 2

    def __init__(self, filepath: str = DATA_FILE):
        self.filepath = filepath
        self.items: list[dict] = []
        self.last_number = 0
        self.load_message: str | None = None   # что сообщить пользователю при старте
        self.load()

    # ---------- хранение ----------
    def load(self):
        """Загрузить данные. Любая проблема с файлом даёт пустой список, а не аварию."""
        self.items, self.last_number, self.load_message = [], 0, None
        if not os.path.exists(self.filepath):
            self.load_message = ("Файл данных ещё не создан — программа начнёт "
                                 "с пустого списка.")
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as exc:
            self._handle_corrupt(f"не удалось прочитать ({exc})")
            return
        if not text.strip():
            self.load_message = "Файл данных пуст — программа начнёт с пустого списка."
            return
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            self._handle_corrupt(str(exc))
            return

        stored_last = 0
        if isinstance(data, list):                       # старый формат
            items = data
        elif isinstance(data, dict) and isinstance(data.get("items"), list):
            items = data["items"]
            stored_last = data.get("last_number")
            stored_last = stored_last if isinstance(stored_last, int) and stored_last > 0 else 0
        else:
            self._handle_corrupt("неожиданная структура файла")
            return
        self.items = [it for it in items if isinstance(it, dict)]
        numbers = [parse_inv_number(it.get("inv_number")) for it in self.items]
        self.last_number = max([stored_last] + [n for n in numbers if n])

    def _handle_corrupt(self, reason: str):
        """Сохранить копию испорченного файла и продолжить с пустого списка."""
        try:
            existing = self._find_same_backup()
            if existing:       # такая копия уже есть: не плодим новые при каждом запуске
                saved = f" Исходный файл уже сохранён как «{os.path.basename(existing)}»."
            else:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup = f"{self.filepath}.corrupt-{stamp}"
                shutil.copy2(self.filepath, backup)
                saved = f" Исходный файл сохранён как «{os.path.basename(backup)}»."
        except OSError:
            saved = " Резервную копию создать не удалось."
        self.items, self.last_number = [], 0
        self.load_message = f"Файл данных повреждён: {reason}.{saved}"

    def _find_same_backup(self) -> str | None:
        """Путь к уже существующей копии с тем же содержимым, если она есть."""
        folder = os.path.dirname(self.filepath) or "."
        prefix = os.path.basename(self.filepath) + ".corrupt-"
        with open(self.filepath, "rb") as f:
            content = f.read()
        for name in sorted(os.listdir(folder)):
            if name.startswith(prefix):
                path = os.path.join(folder, name)
                with open(path, "rb") as f:
                    if f.read() == content:
                        return path
        return None

    def save(self):
        """Атомарная запись: во временный файл, затем os.replace. Ошибка → OSError."""
        folder = os.path.dirname(self.filepath) or "."
        os.makedirs(folder, exist_ok=True)
        payload = {"version": self.FORMAT_VERSION, "last_number": self.last_number,
                   "items": self.items}
        tmp = self.filepath + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.filepath)
        except OSError:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            raise

    def _commit(self, snapshot, ok_message: str) -> tuple[bool, str]:
        """Сохранить; при ошибке записи вернуть данные в прежнее состояние."""
        try:
            self.save()
        except OSError as exc:
            self.items, self.last_number = snapshot
            return False, f"Не удалось сохранить данные ({exc.strerror or exc}). Изменение отменено."
        return True, ok_message

    def _snapshot(self):
        return copy.deepcopy(self.items), self.last_number

    # ---------- CRUD ----------
    def list_all(self) -> list[dict]:
        return self.items

    def find(self, inv_number: str) -> dict | None:
        """Поиск по номеру без учёта регистра и лишних пробелов."""
        wanted = str(inv_number or "").strip().upper()
        for it in self.items:
            if str(it.get("inv_number", "")).strip().upper() == wanted:
                return it
        return None

    def next_number(self) -> str:
        """Номер, который получит следующая запись: last_number + 1."""
        return format_inv_number(max(self.last_number, 0) + 1)

    def add(self, item: dict) -> tuple[bool, str]:
        """Добавить запись с готовым инв. номером. Возвращает (успех, сообщение)."""
        item = normalize_item(item)
        ok, message = validate_item(item)
        if not ok:
            return False, message
        if self.find(item["inv_number"]):
            return False, f"Инвентарный номер {item['inv_number']} уже существует."
        snapshot = self._snapshot()
        self.items.append(item)
        number = parse_inv_number(item["inv_number"])
        if number and number > self.last_number:
            self.last_number = number
        return self._commit(snapshot, "Запись добавлена.")

    def create(self, fields: dict) -> tuple[bool, str]:
        """Добавить запись с автоматическим номером (номер из fields игнорируется)."""
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
        new_status = str(changes.get("status") or "").strip().lower()
        new_room = str(changes.get("room") or "").strip()
        if not new_status and not new_room:
            return False, "Ничего не изменено."
        if new_status and new_status not in VALID_STATUSES:
            return False, f"Состояние должно быть одним из: {', '.join(VALID_STATUSES)}."
        snapshot = self._snapshot()
        if new_status:
            it["status"] = new_status
        if new_room:
            it["room"] = new_room
        return self._commit(snapshot, "Запись обновлена.")

    def delete(self, inv_number: str) -> tuple[bool, str]:
        it = self.find(inv_number)
        if not it:
            return False, "Не найдено"
        snapshot = self._snapshot()
        self.items.remove(it)
        return self._commit(snapshot, "Запись удалена.")

    def by_room(self, room: str) -> list[dict]:
        wanted = str(room or "").strip()
        return [it for it in self.items if str(it.get("room", "")).strip() == wanted]

    def by_status(self, status: str) -> list[dict]:
        """Фильтр по состоянию. Регистр и пробелы не важны."""
        wanted = str(status or "").strip().lower()
        return [it for it in self.items if str(it.get("status", "")).strip().lower() == wanted]
