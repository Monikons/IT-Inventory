"""Тесты для модуля inventory."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inventory import Inventory, VALID_STATUSES


def make_inv(tmp_path, items=None):
    fp = os.path.join(tmp_path, "test_inventory.json")
    if items is not None:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
    return Inventory(filepath=fp)


DEMO = [
    {"inv_number": "INV-0001", "equipment_type": "ПК", "name": "Dell OptiPlex 3080",
     "room": "101", "status": "исправно", "date_added": "2024-09-01", "responsible": "Иванова А.П."},
    {"inv_number": "INV-0002", "equipment_type": "Монитор", "name": "Samsung S24F350",
     "room": "101", "status": "исправно", "date_added": "2024-09-01", "responsible": "Иванова А.П."},
    {"inv_number": "INV-0003", "equipment_type": "Принтер", "name": "HP LaserJet Pro M404",
     "room": "102", "status": "требует ремонта", "date_added": "2023-02-15", "responsible": "Петров Б.С."},
    {"inv_number": "INV-0004", "equipment_type": "ПК", "name": "Lenovo ThinkCentre M70",
     "room": "205", "status": "исправно", "date_added": "2025-01-20", "responsible": "Сидорова В.Н."},
    {"inv_number": "INV-0005", "equipment_type": "Монитор", "name": "LG 24MK430H",
     "room": "205", "status": "списано", "date_added": "2022-05-10", "responsible": "Сидорова В.Н."},
]


class TestList:
    """US-1: показать список."""

    def test_list_returns_items(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        assert len(inv.list_all()) == 5

    def test_list_empty(self, tmp_path):
        inv = make_inv(tmp_path, [])
        assert inv.list_all() == []

    def test_fields_present(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        for it in inv.list_all():
            for field in ("inv_number", "equipment_type", "name", "room", "status"):
                assert field in it


class TestAdd:
    """US-2: добавление."""

    def test_add_valid(self, tmp_path):
        inv = make_inv(tmp_path, [])
        ok, msg = inv.add({"inv_number": "INV-0100", "equipment_type": "ПК",
                           "name": "Test", "room": "999", "status": "исправно"})
        assert ok
        assert len(inv.list_all()) == 1

    def test_add_empty_field_rejected(self, tmp_path):
        inv = make_inv(tmp_path, [])
        ok, msg = inv.add({"inv_number": "", "equipment_type": "ПК",
                           "name": "Test", "room": "999", "status": "исправно"})
        assert not ok
        assert len(inv.list_all()) == 0

    def test_add_duplicate_rejected(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        ok, msg = inv.add({"inv_number": "INV-0001", "equipment_type": "ПК",
                           "name": "Dup", "room": "999", "status": "исправно"})
        assert not ok

    def test_add_invalid_status(self, tmp_path):
        inv = make_inv(tmp_path, [])
        ok, msg = inv.add({"inv_number": "INV-0101", "equipment_type": "ПК",
                           "name": "Test", "room": "999", "status": "сломано"})
        assert not ok


class TestFind:
    """US-3: поиск по номеру."""

    def test_find_existing(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        item = inv.find("INV-0001")
        assert item is not None
        assert item["name"] == "Dell OptiPlex 3080"

    def test_find_missing(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        assert inv.find("INV-9999") is None


class TestByRoom:
    """US-4: оборудование кабинета."""

    def test_room_found(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        items = inv.by_room("101")
        assert len(items) == 2

    def test_room_empty(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        assert inv.by_room("999") == []


class TestUpdate:
    """US-5: изменение."""

    def test_update_status(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        ok, msg = inv.update("INV-0001", status="требует ремонта")
        assert ok
        assert inv.find("INV-0001")["status"] == "требует ремонта"

    def test_update_room(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        ok, msg = inv.update("INV-0001", room="310")
        assert ok
        assert inv.find("INV-0001")["room"] == "310"

    def test_update_not_found(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        ok, msg = inv.update("INV-9999", status="списано")
        assert not ok
        assert msg == "Не найдено"

    def test_update_invalid_status(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        ok, msg = inv.update("INV-0001", status="утоплено")
        assert not ok


class TestDelete:
    """US-6: удаление."""

    def test_delete_existing(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        ok, msg = inv.delete("INV-0001")
        assert ok
        assert inv.find("INV-0001") is None
        assert len(inv.list_all()) == 4

    def test_delete_not_found(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        ok, msg = inv.delete("INV-9999")
        assert not ok
        assert msg == "Не найдено"


class TestPersistence:
    """US-7: сохранение."""

    def test_save_and_reload(self, tmp_path):
        inv = make_inv(tmp_path, DEMO)
        inv.add({"inv_number": "INV-0100", "equipment_type": "ПК",
                 "name": "New", "room": "999", "status": "исправно"})
        inv2 = Inventory(filepath=inv.filepath)
        assert len(inv2.list_all()) == 6

    def test_missing_file(self, tmp_path):
        inv = make_inv(tmp_path)
        assert inv.list_all() == []

    def test_corrupted_json(self, tmp_path):
        fp = os.path.join(tmp_path, "bad.json")
        with open(fp, "w") as f:
            f.write("NOT VALID JSON {{{")
        inv = Inventory(filepath=fp)
        assert inv.list_all() == []
