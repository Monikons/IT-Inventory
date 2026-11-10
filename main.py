import os
import sys

from inventory import Inventory, VALID_STATUSES, display_value

# ─── цвета (ANSI) ───
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_DIM     = "\033[2m"
C_RED     = "\033[31m"
C_GREEN   = "\033[32m"
C_YELLOW  = "\033[33m"
C_BLUE    = "\033[34m"
C_CYAN    = "\033[36m"
C_WHITE   = "\033[37m"
C_BG_BLUE = "\033[44m"
C_BG_GRAY = "\033[47m"

STATUS_COLORS = {
    "исправно": C_GREEN,
    "требует ремонта": C_YELLOW,
    "списано": C_RED,
}

WIDTH = 98


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def header(title: str):
    """Красивый заголовок."""
    print()
    print(f"{C_CYAN}{C_BOLD}{'═' * WIDTH}{C_RESET}")
    pad = (WIDTH - len(title) - 4) // 2
    print(f"{C_CYAN}{C_BOLD}{' ' * pad}  {title}  {' ' * (WIDTH - pad - len(title) - 2)}{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}{'═' * WIDTH}{C_RESET}")
    print()


def fit(text, width: int) -> str:
    """Обрезать текст до ширины колонки (с многоточием), если он длиннее."""
    text = str(text)
    return text if len(text) <= width else text[:width - 1] + "…"


def show_table(items: list[dict]):
    """Вывести список оборудования в виде таблицы."""
    if not items:
        print(f"{C_YELLOW}  Список пуст.{C_RESET}\n")
        return

    headers = ["Инв. №", "Тип", "Наименование", "Кабинет", "Состояние",
               "Поступило", "Ответственный"]
    widths = [9, 9, 24, 8, 15, 10, 15]

    # шапка
    header_row = f"  {C_BG_BLUE}{C_BOLD}{C_WHITE}"
    for h, w in zip(headers, widths):
        header_row += h.ljust(w) + " "
    header_row += C_RESET
    print(header_row)

    sep = f"  {C_DIM}{'─' * (sum(widths) + len(widths) - 1)}{C_RESET}"
    print(sep)

    for it in items:
        status = it["status"]
        scolor = STATUS_COLORS.get(status, C_WHITE)
        row = "  "
        row += fit(it["inv_number"], widths[0]).ljust(widths[0]) + " "
        row += fit(it["equipment_type"], widths[1]).ljust(widths[1]) + " "
        row += fit(it["name"], widths[2]).ljust(widths[2]) + " "
        row += fit(it["room"], widths[3]).ljust(widths[3]) + " "
        row += f"{scolor}{fit(status, widths[4]).ljust(widths[4])}{C_RESET} "
        # необязательные поля: если не указаны — «неизвестно»
        row += fit(display_value(it.get("date_added")), widths[5]).ljust(widths[5]) + " "
        row += fit(display_value(it.get("responsible")), widths[6]).ljust(widths[6])
        print(row)

    print(sep)
    print(f"  {C_DIM}Всего записей: {len(items)}{C_RESET}\n")


def show_card(item: dict):
    """Карточка одной записи."""
    scolor = STATUS_COLORS.get(item["status"], C_WHITE)
    print(f"""
  {C_BOLD}{'─' * 40}{C_RESET}
  {C_CYAN}Инв. номер:{C_RESET}     {item['inv_number']}
  {C_CYAN}Тип:{C_RESET}            {item['equipment_type']}
  {C_CYAN}Наименование:{C_RESET}   {item['name']}
  {C_CYAN}Кабинет:{C_RESET}        {item['room']}
  {C_CYAN}Состояние:{C_RESET}      {scolor}{item['status']}{C_RESET}
  {C_CYAN}Дата поступления:{C_RESET} {display_value(item.get('date_added'))}
  {C_CYAN}Ответственный:{C_RESET}    {display_value(item.get('responsible'))}
  {C_BOLD}{'─' * 40}{C_RESET}
""")


def show_menu():
    """Главное меню."""
    print(f"""  {C_BOLD}{C_BLUE}┌──────────────────────────────────────────┐{C_RESET}
  {C_BOLD}{C_BLUE}│{C_RESET}  {C_BOLD}МЕНЮ{C_RESET}                                    {C_BOLD}{C_BLUE}│{C_RESET}
  {C_BOLD}{C_BLUE}├──────────────────────────────────────────┤{C_RESET}
  {C_BOLD}{C_BLUE}│{C_RESET}  {C_GREEN}1{C_RESET}  Показать всё оборудование              {C_BOLD}{C_BLUE}│{C_RESET}
  {C_BOLD}{C_BLUE}│{C_RESET}  {C_GREEN}2{C_RESET}  Добавить оборудование                  {C_BOLD}{C_BLUE}│{C_RESET}
  {C_BOLD}{C_BLUE}│{C_RESET}  {C_GREEN}3{C_RESET}  Найти по инв. номеру                   {C_BOLD}{C_BLUE}│{C_RESET}
  {C_BOLD}{C_BLUE}│{C_RESET}  {C_GREEN}4{C_RESET}  Показать кабинет                       {C_BOLD}{C_BLUE}│{C_RESET}
  {C_BOLD}{C_BLUE}│{C_RESET}  {C_GREEN}5{C_RESET}  Изменить запись                        {C_BOLD}{C_BLUE}│{C_RESET}
  {C_BOLD}{C_BLUE}│{C_RESET}  {C_GREEN}6{C_RESET}  Удалить запись                         {C_BOLD}{C_BLUE}│{C_RESET}
  {C_BOLD}{C_BLUE}│{C_RESET}  {C_RED}0{C_RESET}  Выход                                  {C_BOLD}{C_BLUE}│{C_RESET}
  {C_BOLD}{C_BLUE}└──────────────────────────────────────────┘{C_RESET}""")


def prompt(msg: str) -> str:
    return input(f"  {C_CYAN}▸ {msg}{C_RESET} ").strip()


def msg_ok(text: str):
    print(f"  {C_GREEN}✔ {text}{C_RESET}")


def msg_err(text: str):
    print(f"  {C_RED}✘ {text}{C_RESET}")


def msg_warn(text: str):
    print(f"  {C_YELLOW}⚠ {text}{C_RESET}")


# ─── действия ───

def action_show_all(inv):
    header("СПИСОК ОБОРУДОВАНИЯ")
    show_table(inv.list_all())


def action_add(inv):
    header("ДОБАВЛЕНИЕ ОБОРУДОВАНИЯ")
    print(f"  {C_DIM}Инвентарный номер будет присвоен автоматически: {inv.next_number()}{C_RESET}")
    print(f"  {C_DIM}Пустой ввод в обязательном поле (*) — отмена.{C_RESET}")
    print(f"  {C_DIM}Необязательные поля можно пропустить — будет «неизвестно».{C_RESET}\n")

    eq_type = prompt("Тип (ПК / Монитор / Принтер …) *:")
    if not eq_type:
        msg_warn("Отменено.")
        return
    name = prompt("Наименование *:")
    if not name:
        msg_warn("Отменено.")
        return
    room = prompt("Кабинет *:")
    if not room:
        msg_warn("Отменено.")
        return
    print(f"  {C_DIM}Состояние: {' / '.join(VALID_STATUSES)}{C_RESET}")
    while True:
        status = prompt("Состояние *:")
        if not status:
            msg_warn("Отменено.")
            return
        if status.lower() in VALID_STATUSES:
            break
        msg_err("Нет такого состояния, введите одно из списка выше.")

    date_added = prompt("Дата поступления (необязательно):")
    responsible = prompt("Ответственное лицо (необязательно):")

    ok, message = inv.create({
        "equipment_type": eq_type,
        "name": name,
        "room": room,
        "status": status,
        "date_added": date_added,
        "responsible": responsible,
    })
    if ok:
        msg_ok(message)
    else:
        msg_err(message)


def action_find(inv):
    header("ПОИСК ПО ИНВЕНТАРНОМУ НОМЕРУ")
    num = prompt("Введите инв. номер:")
    if not num:
        msg_warn("Пустой ввод.")
        return
    item = inv.find(num)
    if item:
        show_card(item)
    else:
        msg_err("Не найдено.")


def action_room(inv):
    header("ОБОРУДОВАНИЕ КАБИНЕТА")
    room = prompt("Введите номер кабинета:")
    if not room:
        msg_warn("Пустой ввод.")
        return
    items = inv.by_room(room)
    if items:
        show_table(items)
    else:
        msg_warn(f"В кабинете {room} нет оборудования.")


def action_update(inv):
    header("ИЗМЕНЕНИЕ ЗАПИСИ")
    num = prompt("Инв. номер записи:")
    if not num:
        msg_warn("Пустой ввод.")
        return
    item = inv.find(num)
    if not item:
        msg_err("Не найдено.")
        return

    show_card(item)
    print(f"  {C_DIM}Оставьте поле пустым, чтобы не менять.{C_RESET}\n")

    new_status = prompt("Новое состояние (исправно / требует ремонта / списано):")
    new_room = prompt("Новый кабинет:")

    changes = {}
    if new_status:
        changes["status"] = new_status
    if new_room:
        changes["room"] = new_room

    if not changes:
        msg_warn("Ничего не изменено.")
        return

    ok, message = inv.update(num, **changes)
    if ok:
        msg_ok(message)
        show_card(inv.find(num))
    else:
        msg_err(message)


def action_delete(inv):
    header("УДАЛЕНИЕ ЗАПИСИ")
    num = prompt("Инв. номер записи:")
    if not num:
        msg_warn("Пустой ввод.")
        return
    item = inv.find(num)
    if not item:
        msg_err("Не найдено.")
        return

    show_card(item)
    confirm = prompt("Точно удалить? (да/нет):")
    if confirm.lower() in ("да", "д", "yes", "y"):
        ok, message = inv.delete(num)
        if ok:
            msg_ok(message)
    else:
        msg_warn("Удаление отменено. Запись осталась.")


# ─── главный цикл ───

def main():
    inv = Inventory()

    while True:
        clear()
        header("УЧЁТ ОБОРУДОВАНИЯ · КОЛЛЕДЖ")
        show_menu()
        choice = prompt("Выберите пункт:")

        if choice == "1":
            action_show_all(inv)
        elif choice == "2":
            action_add(inv)
        elif choice == "3":
            action_find(inv)
        elif choice == "4":
            action_room(inv)
        elif choice == "5":
            action_update(inv)
        elif choice == "6":
            action_delete(inv)
        elif choice == "0":
            print(f"\n  {C_GREEN}До свидания!{C_RESET}\n")
            sys.exit(0)
        else:
            msg_err("Нет такого пункта меню.")

        input(f"\n  {C_DIM}Нажмите Enter, чтобы продолжить…{C_RESET}")


if __name__ == "__main__":
    main()
