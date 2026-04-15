from pathlib import Path


def test_generated_art_is_wired_into_firmware_sources():
    repo_root = Path(__file__).resolve().parents[2]

    cmake_text = (repo_root / "boards/shields/nice_view_custom/CMakeLists.txt").read_text()
    peripheral_text = (
        repo_root / "boards/shields/nice_view_custom/widgets/peripheral_status.c"
    ).read_text()
    art_path = repo_root / "boards/shields/nice_view_custom/widgets/generated_art.c"

    assert art_path.exists()
    assert "zephyr_library_sources(widgets/generated_art.c)" in cmake_text
    assert "LV_IMG_DECLARE(anime_portrait);" in peripheral_text
    assert "LV_IMG_DECLARE(anime_portrait_inverted);" in peripheral_text
    assert "IS_ENABLED(CONFIG_NICE_VIEW_WIDGET_INVERTED)" in peripheral_text
    assert "&anime_portrait_inverted" in peripheral_text
    assert "&anime_portrait" in peripheral_text
