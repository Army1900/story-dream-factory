import pathlib

from app.persistence.image_store import ImageStore


def test_save_and_load_image(tmp_path):
    store = ImageStore(base_dir=str(tmp_path))
    data = b"\x89PNG fake image bytes"
    path = store.save(world_id="w1", image_id="img-1", data=data, ext="png")
    assert path.endswith("img-1.png")
    loaded = store.load(path)
    assert loaded == data


def test_save_uses_world_subdir(tmp_path):
    store = ImageStore(base_dir=str(tmp_path))
    path = store.save(world_id="w1", image_id="img-1", data=b"x", ext="png")
    assert "w1" in path


def test_delete_image(tmp_path):
    store = ImageStore(base_dir=str(tmp_path))
    path = store.save(world_id="w1", image_id="img-1", data=b"x", ext="png")
    store.delete(path)
    assert not pathlib.Path(path).exists()
