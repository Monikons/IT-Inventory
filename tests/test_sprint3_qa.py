"""Спринт 3 (QA): поиск, изменение, удаление.

Номера T-xx совпадают с тест-кейсами в отчёте QA.
Тесты, помеченные xfail, фиксируют найденные дефекты (DEF-xx): пока дефект не
исправлен, они «ожидаемо падают» и не ломают общий прогон. Когда LD исправит
дефект, тест покажет XPASS — после этого пометку xfail нужно убрать.
"""

import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main
from inventory import Inventory

ANSI = re.compile(r"\x1b\[[0-9;]*m")

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
    {"inv_number": "INV-0006", "equipment_type": "Проектор", "name": "Epson EB-X06",
     "room": "310", "status": "исправно", "date_added": "2024-11-05", "responsible": "Козлов Д.М."},
]


def make_inv(tmp_path, items=None):
    fp = os.path.join(tmp_path, "inventory.json")
    if items is not None:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
    return Inventory(filepath=fp)


def ui(monkeypatch, capsys, action, inv, answers):
    """Запустить действие меню, подав «ответы пользователя»; вернуть вывод без цветов."""
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(it))
    action(inv)
    return ANSI.sub("", capsys.readouterr().out)


# ───────────── Поиск по номеру (US-3) ─────────────

def test_T01_find_existing_shows_card(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_find, inv, ["INV-0001"])
    assert "Dell OptiPlex 3080" in out and "101" in out


def test_T02_find_unknown_says_not_found(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_find, inv, ["INV-9999"])
    assert "Не найдено" in out


def test_T03_find_empty_input_no_crash(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_find, inv, ["   "])
    assert "Пустой ввод" in out


def test_T04_repeated_find_gives_same_result(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    first = ui(monkeypatch, capsys, main.action_find, inv, ["INV-0002"])
    second = ui(monkeypatch, capsys, main.action_find, inv, ["INV-0002"])
    assert first == second and "Samsung S24F350" in second


def test_T04b_find_after_update_shows_new_data(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    inv.update("INV-0002", room="310")
    out = ui(monkeypatch, capsys, main.action_find, inv, ["INV-0002"])
    assert "310" in out


@pytest.mark.xfail(reason="DEF-01: поиск чувствителен к регистру (inv-0001 не находится)")
def test_T05_find_lowercase_number(tmp_path):
    inv = make_inv(tmp_path, DEMO)
    assert inv.find("inv-0001") is not None


# ───────────── Оборудование кабинета (US-4) ─────────────

def test_T06_room_with_equipment(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_room, inv, ["101"])
    assert "INV-0001" in out and "INV-0002" in out and "INV-0003" not in out


def test_T07_room_without_equipment(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_room, inv, ["999"])
    assert "В кабинете 999 нет оборудования" in out


def test_T08_room_empty_input_no_crash(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_room, inv, [""])
    assert "Пустой ввод" in out


# ───────────── Изменение (US-5) ─────────────

def test_T09_update_status_visible_in_list(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    ui(monkeypatch, capsys, main.action_update, inv, ["INV-0001", "списано", ""])
    out = ui(monkeypatch, capsys, main.action_show_all, inv, [])
    row = next(line for line in out.splitlines() if "INV-0001" in line)
    assert "списано" in row


def test_T10_update_room(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    ui(monkeypatch, capsys, main.action_update, inv, ["INV-0001", "", "310"])
    assert inv.find("INV-0001")["room"] == "310"


def test_T11_update_unknown_number(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_update, inv, ["INV-9999"])
    assert "Не найдено" in out


def test_T12_update_invalid_status_rejected_and_unchanged(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_update, inv, ["INV-0001", "сломано", ""])
    assert "Состояние должно быть" in out
    assert inv.find("INV-0001")["status"] == "исправно"


@pytest.mark.xfail(reason="DEF-02: при изменении «Исправно» (с заглавной) отклоняется, а при добавлении принимается")
def test_T13_update_status_capital_letter(tmp_path):
    inv = make_inv(tmp_path, DEMO)
    ok, _ = inv.update("INV-0003", status="Исправно")
    assert ok


def test_T13b_update_nothing_entered(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_update, inv, ["INV-0001", "", ""])
    assert "Ничего не изменено" in out


# ───────────── Удаление (US-6) ─────────────

def test_T14_delete_with_confirmation(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_delete, inv, ["INV-0006", "да"])
    assert "Запись удалена" in out
    assert inv.find("INV-0006") is None and len(inv.list_all()) == 5


@pytest.mark.parametrize("answer", ["нет", "н", "no", "абв"])
def test_T15_delete_cancelled(tmp_path, monkeypatch, capsys, answer):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_delete, inv, ["INV-0006", answer])
    assert "Удаление отменено" in out
    assert inv.find("INV-0006") is not None


def test_T16_delete_empty_answer_cancels(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    ui(monkeypatch, capsys, main.action_delete, inv, ["INV-0006", ""])
    assert inv.find("INV-0006") is not None


def test_T17_delete_unknown_number(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    out = ui(monkeypatch, capsys, main.action_delete, inv, ["INV-9999"])
    assert "Не найдено" in out and len(inv.list_all()) == 6


def test_T18_delete_same_record_twice(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    ui(monkeypatch, capsys, main.action_delete, inv, ["INV-0006", "да"])
    out = ui(monkeypatch, capsys, main.action_delete, inv, ["INV-0006"])
    assert "Не найдено" in out


def test_T19_find_after_delete(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    ui(monkeypatch, capsys, main.action_delete, inv, ["INV-0006", "да"])
    out = ui(monkeypatch, capsys, main.action_find, inv, ["INV-0006"])
    assert "Не найдено" in out


# ───────────── Сохранение и устойчивость ─────────────

def test_T20_changes_survive_restart(tmp_path, monkeypatch, capsys):
    inv = make_inv(tmp_path, DEMO)
    ui(monkeypatch, capsys, main.action_update, inv, ["INV-0001", "списано", "310"])
    ui(monkeypatch, capsys, main.action_delete, inv, ["INV-0006", "да"])
    again = Inventory(filepath=inv.filepath)
    assert again.find("INV-0001")["status"] == "списано"
    assert again.find("INV-0001")["room"] == "310"
    assert again.find("INV-0006") is None


@pytest.mark.xfail(reason="DEF-05: запись без поля inv_number/room в JSON роняет поиск (KeyError)")
def test_T21_record_with_missing_field_does_not_crash(tmp_path):
    items = [{"name": "без номера"}, dict(DEMO[0])]
    inv = make_inv(tmp_path, items)
    assert inv.find("INV-0001") is not None
    inv.by_room("101")   # не должно падать


@pytest.mark.xfail(reason="DEF-06: номер последней удалённой записи выдаётся повторно")
def test_T22_number_not_reused_after_deleting_last(tmp_path):
    inv = make_inv(tmp_path, DEMO)
    inv.delete("INV-0006")
    inv.create({"equipment_type": "ПК", "name": "New", "room": "1", "status": "исправно"})
    assert inv.find("INV-0006") is None


@pytest.mark.xfail(reason="DEF-03: изменение без параметров сообщает «Запись обновлена»")
def test_T23_update_without_changes_reports_nothing_changed(tmp_path):
    inv = make_inv(tmp_path, DEMO)
    ok, _ = inv.update("INV-0001")
    assert not ok


@pytest.mark.xfail(reason="DEF-04: update(room=None) падает с AttributeError")
def test_T24_update_with_none_room_does_not_crash(tmp_path):
    inv = make_inv(tmp_path, DEMO)
    inv.update("INV-0001", room=None)
