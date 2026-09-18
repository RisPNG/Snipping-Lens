import json
import logging

from sniplens.settings import ALWAYS_ON, PAUSED, TRAY_ONLY, SettingsStore


def test_load_defaults_when_file_missing(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    values = store.load()
    assert values["tray_status"] == ALWAYS_ON
    assert values["startup"] == 0
    assert values["alternate_hotkey_bypass"] is True
    assert isinstance(values["alternate_hotkey"], str)


def test_round_trip_wrapped_format(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    store.save({"tray_status": TRAY_ONLY, "startup": 1})
    raw = json.loads(path.read_text())
    assert raw["tray_status"]["value"] == TRAY_ONLY
    assert raw["tray_status"]["description"]
    loaded = store.load()
    assert loaded["tray_status"] == TRAY_ONLY
    assert loaded["startup"] == 1


def test_load_accepts_plain_values_from_v4_files(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"tray_status": {"value": 1, "description": "x"}, "startup": 0}))
    values = SettingsStore(path).load()
    assert values["tray_status"] == TRAY_ONLY


def test_invalid_values_fall_back_to_defaults(tmp_path, caplog):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "tray_status": {"value": 9, "description": "x"},
                "startup": {"value": "banana", "description": "x"},
                "alternate_hotkey_bypass": {"value": False, "description": "x"},
            }
        )
    )
    with caplog.at_level(logging.WARNING):
        values = SettingsStore(path).load()
    assert values["tray_status"] == ALWAYS_ON
    assert values["startup"] == 0
    assert values["alternate_hotkey_bypass"] is False
    assert any("invalid" in r.message.lower() or "invalid setting" in r.message.lower() for r in caplog.records)


def test_string_bool_coercion(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"alternate_hotkey_bypass": {"value": "on", "description": "x"}}))
    values = SettingsStore(path).load()
    assert values["alternate_hotkey_bypass"] is True


def test_save_merges_and_keeps_unknown_keys(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"future_key": {"value": 42}, "tray_status": {"value": 0, "description": "old"}}))
    store = SettingsStore(path)
    store.save({"tray_status": PAUSED})
    raw = json.loads(path.read_text())
    assert raw["future_key"] == {"value": 42}
    assert raw["tray_status"]["value"] == PAUSED
