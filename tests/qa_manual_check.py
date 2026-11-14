"""QA, 12.11.2026 — ручная проверка постоянного хранения данных.

Прогоняет сценарии QA-задания дня на временных файлах и на копии
реального data/inventory.json. Ничего в проекте не изменяет.

Запуск: python tests/qa_manual_check.py
"""

import json
import os
import shutil
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from inventory import Inventory, DATA_FILE  # noqa: E402


def line(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def copier(work):
    def copy_real():
        target = os.path.join(work, "inventory.json")
        shutil.copyfile(DATA_FILE, target)
        return target
    return copy_real


def main():
    work = tempfile.mkdtemp(prefix="qa-12-11-")
    copy_real = copier(work)
    passed = failed = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [ПРОШЁЛ] {name}  {detail}")
        else:
            failed += 1
            print(f"  [ПРОВАЛ] {name}  {detail}")

    try:
        line("Q-01…Q-04. Сохранение между запусками (копия реальных данных)")
        fp = copy_real()
        inv = Inventory(filepath=fp)
        start = len(inv.list_all())
        ok, msg = inv.create({"equipment_type": "Принтер", "name": "QA тест",
                              "room": "404", "status": "исправно"})
        new_num = msg.split()[-1].rstrip(".")
        inv.update("INV-0001", status="списано")
        inv.delete("INV-0002")

        again = Inventory(filepath=fp)
        check("Q-01 добавленная запись после перезапуска",
              again.find(new_num) is not None, new_num)
        check("Q-02 изменённая запись после перезапуска",
              again.find("INV-0001")["status"] == "списано")
        check("Q-03 удалённая запись осталась удалённой",
              again.find("INV-0002") is None)
        check("Q-04 количество записей согласовано",
              len(again.list_all()) == start + 1 - 1, f"{len(again.list_all())}")

        line("Q-05…Q-07. Первый запуск (файла нет)")
        fp_first = os.path.join(work, "first.json")
        inv = Inventory(filepath=fp_first)
        check("Q-05 пустой список", inv.list_all() == [])
        check("Q-06 сообщение о первом запуске", "не создан" in inv.load_message)
        check("Q-07 файл не создан до первого изменения", not os.path.exists(fp_first))
        inv.create({"equipment_type": "ПК", "name": "Первый", "room": "1",
                    "status": "исправно"})
        check("Q-07 файл создан после изменения", os.path.exists(fp_first))

        line("Q-08…Q-10. Пустой файл")
        fp_empty = os.path.join(work, "empty.json")
        open(fp_empty, "w", encoding="utf-8").close()
        inv = Inventory(filepath=fp_empty)
        check("Q-08 пустой файл → пустой список, без падения", inv.list_all() == [])
        check("Q-08 сообщение о пустом файле", "пуст" in inv.load_message)
        check("Q-09 размер файла не изменился", os.path.getsize(fp_empty) == 0)
        ok, msg = inv.create({"equipment_type": "Монитор", "name": "После пустого",
                              "room": "2", "status": "исправно"})
        check("Q-10 работа продолжается", ok, msg)

        line("Q-11…Q-14. Повреждённый JSON")
        fp_bad = os.path.join(work, "bad.json")
        broken = '{"version": 2, "items": [}'
        with open(fp_bad, "w", encoding="utf-8") as f:
            f.write(broken)
        inv = Inventory(filepath=fp_bad)
        check("Q-11 пустой список, без падения", inv.list_all() == [])
        backups = [n for n in os.listdir(work) if n.startswith("bad.json.corrupt-")]
        check("Q-12 резервная копия создана", len(backups) == 1, backups[0] if backups else "")
        with open(fp_bad, encoding="utf-8") as f:
            check("Q-13 оригинал не перезаписан", f.read() == broken)
        print("       сообщение:", inv.load_message)
        ok, _ = inv.create({"equipment_type": "ПК", "name": "После повреждения",
                            "room": "3", "status": "исправно"})
        check("Q-14 после повреждения можно работать", ok)

        line("Q-15…Q-17. Повторный запуск и нумерация")
        fp_rep = copy_real()
        inv = Inventory(filepath=fp_rep)
        for _ in range(5):
            inv = Inventory(filepath=fp_rep)
        check("Q-15 пятикратный перезапуск без дублей",
              len(inv.list_all()) == len(json.load(open(fp_rep, encoding="utf-8"))["items"]))
        removed = inv.list_all()[-1]["inv_number"]
        inv.delete(removed)
        inv = Inventory(filepath=fp_rep)
        ok, msg = inv.create({"equipment_type": "ПК", "name": "После удаления",
                              "room": "5", "status": "исправно"})
        new_num = msg.split()[-1].rstrip(".")
        check("Q-16 номер удалённой записи не повторён",
              new_num != removed, f"удалён {removed}, выдан {new_num}")
        check("Q-17 next_number после перезапуска",
              Inventory(filepath=fp_rep).next_number() != new_num)

        line("Q-18…Q-20. Повторная проверка дефектов спринта 3")
        fp_def = os.path.join(work, "defects.json")
        with open(fp_def, "w", encoding="utf-8") as f:
            json.dump([{"name": "без полей"},
                       {"inv_number": "inv-0001", "equipment_type": "ПК",
                        "name": "Dell", "room": "101", "status": "списано"}],
                      f, ensure_ascii=False)
        inv = Inventory(filepath=fp_def)
        check("DEF-01 поиск без учёта регистра", inv.find("INV-0001") is not None)
        check("DEF-05 запись без полей не роняет кабинет", inv.by_room("101") != [])
        ok, msg = inv.update("INV-0001", status="Исправно")
        check("DEF-02 состояние с заглавной принято", ok,
              inv.find("INV-0001")["status"])
        ok, msg = inv.update("INV-0001")
        check("DEF-03 пустое изменение отклонено", not ok, msg)
        try:
            inv.update("INV-0001", room=None)
            check("DEF-04 update(room=None) без исключения", True)
        except Exception as exc:                     # noqa: BLE001
            check("DEF-04 update(room=None) без исключения", False, repr(exc))

        line("ИТОГ")
        print(f"  проверок: {passed + failed}, прошло: {passed}, провалилось: {failed}")
        return 0 if failed == 0 else 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
