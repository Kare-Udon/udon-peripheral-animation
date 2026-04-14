from pathlib import Path


def test_pipeline_package_layout_exists():
    assert Path("tools/pipeline").is_dir()
    assert Path("tools/pipeline/stages").is_dir()
    assert Path("tests/pipeline").is_dir()
