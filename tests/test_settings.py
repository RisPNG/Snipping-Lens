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


def test_load_accepts_both_plain_and_wrapped_values(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"tray_status": 1, "startup": {"value": 1, "description": "x"}})
    )
    values = SettingsStore(path).load()
    assert values["tray_status"] == TRAY_ONLY
    assert values["startup"] == 1


def test_load_ignores_keys_dropped_since_v4(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "tray_ui_enabled": {"value": True},
                "tray_snip_token": "abc",
                "last_litterbox_url": "https://files.catbox.moe/x.png",
                "tray_status": {"value": 1},
            }
        )
    )
    values = SettingsStore(path).load()
    assert values["tray_status"] == TRAY_ONLY
    assert "tray_ui_enabled" not in values and "tray_snip_token" not in values


def test_save_is_atomic_and_leaves_no_temporary_file(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    store.save({"tray_status": TRAY_ONLY})
    assert [p.name for p in tmp_path.iterdir()] == ["settings.json"]


def test_save_refuses_to_wipe_a_file_it_cannot_parse(tmp_path, caplog):
    """A truncated or hand-broken file must not be treated as empty: merging
    into {} would replace every other setting with the handed-in key alone."""
    path = tmp_path / "settings.json"
    path.write_text('{"tray_status": {"value": 1, "descr')
    with caplog.at_level(logging.ERROR):
        SettingsStore(path).save({"last_detected_image": "abc"})
    assert path.read_text() == '{"tray_status": {"value": 1, "descr'
    assert any("left unchanged" in r.message for r in caplog.records)


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
