"""Спринт 4 (QA): сохранение между запусками и ошибки файла (US-7)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main
from inventory import Inventory

NEW = {"equipment_type": "Монитор", "name": "LG", "room": "7", "status": "исправно"}


def fp_in(tmp_path):
    return os.path.join(tmp_path, "inventory.json")


def test_US7_1_records_survive_restart(tmp_path):
    inv = Inventory(filepath=fp_in(tmp_path))
    inv.create(NEW)
    assert Inventory(filepath=inv.filepath).find("INV-0001")["name"] == "LG"


def test_US7_2_missing_file_no_crash(tmp_path):
    assert Inventory(filepath=fp_in(tmp_path)).list_all() == []


def test_US7_3_corrupt_json_not_silent(tmp_path):
    fp = fp_in(tmp_path)
    open(fp, "w").write("[[[")
    inv = Inventory(filepath=fp)
    assert inv.load_message
    assert any(".corrupt-" in n for n in os.listdir(tmp_path))


def test_US7_4_record_with_missing_fields_no_crash(tmp_path, capsys, monkeypatch):
    fp = fp_in(tmp_path)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump([{"name": "без номера"}, {"inv_number": "INV-0001"}], f)
    inv = Inventory(filepath=fp)
    assert inv.find("INV-0001") is not None
    assert inv.by_room("101") == []
    main.show_table(inv.list_all())
    main.show_card(inv.list_all()[0])
    assert "неизвестно" in capsys.readouterr().out


def test_US7_5_zero_byte_file(tmp_path):
    fp = fp_in(tmp_path)
    open(fp, "w").close()
    assert Inventory(filepath=fp).list_all() == []


def test_US7_6_add_update_delete_then_restart(tmp_path):
    inv = Inventory(filepath=fp_in(tmp_path))
    inv.create(NEW)
    inv.create(NEW)
    inv.update("INV-0001", status="списано", room="9")
    inv.delete("INV-0002")
    again = Inventory(filepath=inv.filepath)
    assert [i["inv_number"] for i in again.list_all()] == ["INV-0001"]
    assert again.find("INV-0001")["status"] == "списано"
    assert again.find("INV-0001")["room"] == "9"
