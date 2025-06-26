import json
import types

from pipelines import loader


def test_manifest_loader_caches(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([{"id": "a"}]))
    monkeypatch.setattr(loader, "_MANIFEST_PATH", manifest)

    t = {"value": 0}

    def fake_time():
        return t["value"]

    monkeypatch.setattr(loader, "time", types.SimpleNamespace(time=fake_time))
    loader._cache = {"ts": 0.0, "data": []}

    data1 = loader.load_manifest()
    assert data1 == [{"id": "a"}]

    manifest.write_text(json.dumps([{"id": "b"}]))
    data2 = loader.load_manifest()
    assert data2 == [{"id": "a"}]

    t["value"] = 61
    data3 = loader.load_manifest()
    assert data3 == [{"id": "b"}]
