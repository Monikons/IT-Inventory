"""Тесты консольного ввода: подставляем «ответы пользователя» вместо input()."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main
from inventory import Inventory, UNKNOWN


def run_add(monkeypatch, inv, answers):
    """Запустить action_add, подав ответы по очереди."""
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(it))
    main.action_add(inv)


def test_add_via_terminal_skipping_optional(tmp_path, monkeypatch, capsys):
    inv = Inventory(filepath=str(tmp_path / "inv.json"))
    run_add(monkeypatch, inv, ["Принтер", "Canon LBP", "102", "исправно", "", ""])
    item = inv.list_all()[0]
    assert item["inv_number"] == "INV-0001"
    assert item["date_added"] == UNKNOWN
    assert item["responsible"] == UNKNOWN
    assert "INV-0001" in capsys.readouterr().out


def test_empty_required_field_cancels(tmp_path, monkeypatch):
    inv = Inventory(filepath=str(tmp_path / "inv.json"))
    run_add(monkeypatch, inv, ["ПК", ""])          # пустое наименование
    assert inv.list_all() == []


def test_wrong_status_is_asked_again(tmp_path, monkeypatch):
    inv = Inventory(filepath=str(tmp_path / "inv.json"))
    run_add(monkeypatch, inv, ["ПК", "Dell", "101", "сломано", "Исправно", "", ""])
    assert inv.list_all()[0]["status"] == "исправно"


def test_table_shows_unknown(tmp_path, capsys):
    inv = Inventory(filepath=str(tmp_path / "inv.json"))
    inv.create({"equipment_type": "ПК", "name": "Dell", "room": "101", "status": "исправно"})
    main.show_table(inv.list_all())
    assert UNKNOWN in capsys.readouterr().out
