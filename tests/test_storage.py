"""Спринт 4: сохранение и загрузка JSON (формат версии 2)."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inventory import Inventory

NEW = {"equipment_type": "ПК", "name": "Test PC", "room": "1", "status": "исправно"}


def path(tmp_path):
    return os.path.join(tmp_path, "data", "inventory.json")


def read(fp):
    with open(fp, encoding="utf-8") as f:
        return json.load(f)


def test_first_run_no_file_empty_list_and_message(tmp_path):
    inv = Inventory(filepath=path(tmp_path))
    assert inv.list_all() == []
    assert "ещё не создан" in inv.load_message
    assert not os.path.exists(inv.filepath)          # файл появится при первом изменении


def test_first_change_creates_file_in_v2(tmp_path):
    inv = Inventory(filepath=path(tmp_path))
    inv.create(NEW)
    data = read(inv.filepath)
    assert data["version"] == 2 and data["last_number"] == 1
    assert data["items"][0]["inv_number"] == "INV-0001"


def test_empty_file_gives_empty_list(tmp_path):
    fp = path(tmp_path)
    os.makedirs(os.path.dirname(fp))
    open(fp, "w").close()
    inv = Inventory(filepath=fp)
    assert inv.list_all() == [] and "пуст" in inv.load_message


def test_corrupt_json_creates_backup_and_keeps_original_text(tmp_path):
    fp = path(tmp_path)
    os.makedirs(os.path.dirname(fp))
    with open(fp, "w", encoding="utf-8") as f:
        f.write("{ это не json")
    inv = Inventory(filepath=fp)
    assert inv.list_all() == []
    assert "повреждён" in inv.load_message
    backups = [n for n in os.listdir(os.path.dirname(fp)) if ".corrupt-" in n]
    assert len(backups) == 1
    with open(os.path.join(os.path.dirname(fp), backups[0]), encoding="utf-8") as f:
        assert f.read() == "{ это не json"


def test_wrong_structure_treated_as_corrupt(tmp_path):
    fp = path(tmp_path)
    os.makedirs(os.path.dirname(fp))
    with open(fp, "w") as f:
        f.write('{"hello": 1}')
    inv = Inventory(filepath=fp)
    assert inv.list_all() == [] and "повреждён" in inv.load_message


def test_old_list_format_is_read_and_upgraded_on_save(tmp_path):
    fp = path(tmp_path)
    os.makedirs(os.path.dirname(fp))
    old = [dict(NEW, inv_number="INV-0005", date_added="x", responsible="y")]
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(old, f)
    inv = Inventory(filepath=fp)
    assert inv.find("INV-0005") and inv.next_number() == "INV-0006"
    inv.create(NEW)
    assert read(fp)["version"] == 2


def test_last_number_never_reused_after_delete_and_restart(tmp_path):
    inv = Inventory(filepath=path(tmp_path))
    inv.create(NEW)
    inv.create(NEW)
    inv.delete("INV-0002")
    again = Inventory(filepath=inv.filepath)
    assert again.next_number() == "INV-0003"


def test_last_number_not_lower_than_existing_items(tmp_path):
    fp = path(tmp_path)
    os.makedirs(os.path.dirname(fp))
    with open(fp, "w", encoding="utf-8") as f:
        json.dump({"version": 2, "last_number": 1,
                   "items": [dict(NEW, inv_number="INV-0009")]}, f)
    assert Inventory(filepath=fp).next_number() == "INV-0010"


def test_write_error_rolls_back_and_reports(tmp_path, monkeypatch):
    inv = Inventory(filepath=path(tmp_path))
    inv.create(NEW)

    def boom(*a, **k):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr("inventory.os.replace", boom)
    ok, msg = inv.create(NEW)
    assert not ok and "Не удалось сохранить" in msg
    assert len(inv.list_all()) == 1 and inv.next_number() == "INV-0002"
    assert len(read(inv.filepath)["items"]) == 1       # файл остался прежним
    assert not os.path.exists(inv.filepath + ".tmp")


def test_write_error_on_update_restores_old_value(tmp_path, monkeypatch):
    inv = Inventory(filepath=path(tmp_path))
    inv.create(NEW)
    monkeypatch.setattr("inventory.os.replace", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    ok, _ = inv.update("INV-0001", status="списано")
    assert not ok and inv.find("INV-0001")["status"] == "исправно"


def test_corrupt_file_backup_not_duplicated_on_repeated_launch(tmp_path):
    fp = path(tmp_path)
    os.makedirs(os.path.dirname(fp))
    with open(fp, "w", encoding="utf-8") as f:
        f.write("{ повреждён")
    first = Inventory(filepath=fp)
    second = Inventory(filepath=fp)
    backups = [n for n in os.listdir(os.path.dirname(fp)) if ".corrupt-" in n]
    assert len(backups) == 1
    assert "повреждён" in first.load_message and "уже сохранён" in second.load_message


def test_changed_corrupt_file_gets_its_own_backup(tmp_path):
    import time
    fp = path(tmp_path)
    os.makedirs(os.path.dirname(fp))
    with open(fp, "w", encoding="utf-8") as f:
        f.write("{ первый вариант")
    Inventory(filepath=fp)
    with open(fp, "w", encoding="utf-8") as f:
        f.write("{ второй вариант")
    time.sleep(1.1)       # имя копии содержит время с точностью до секунды
    Inventory(filepath=fp)
    backups = [n for n in os.listdir(os.path.dirname(fp)) if ".corrupt-" in n]
    assert len(backups) == 2


def test_sample_inventory_has_at_least_10_valid_records():
    real = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "inventory.json")
    inv = Inventory(filepath=real)
    assert inv.load_message is None
    assert len(inv.list_all()) >= 10
    numbers = [it["inv_number"] for it in inv.list_all()]
    assert len(numbers) == len(set(numbers))
    assert {"исправно", "требует ремонта", "списано"} <= {it["status"] for it in inv.list_all()}
