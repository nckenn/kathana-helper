"""Tests for virtual key mapping (self-target grave key, etc.)."""
import input_handler


def test_grave_key_maps_to_vk_oem3():
    assert input_handler.get_virtual_key_code('`') == 0xC0
    assert input_handler.get_virtual_key_code('grave') == 0xC0
    assert input_handler.get_virtual_key_code('backtick') == 0xC0


def test_grave_key_not_ascii_ord():
    assert input_handler.get_virtual_key_code('`') != ord('`')
