import json
from pipelines import acl


def test_allowed_groups(tmp_path, monkeypatch):
    acl_file = tmp_path / "acl.json"
    acl_file.write_text(json.dumps({"group1": {"user_ids": ["1"], "roles": ["admin"]}}))
    monkeypatch.setattr(acl, "ACL_PATH", acl_file)
    acl._cache = {"ts": 0.0, "data": {}}
    user = {"id": "1", "role": "user"}
    assert acl.allowed_groups_for_user(user) == ["group1"]


def test_is_pipe_allowed(tmp_path, monkeypatch):
    acl_file = tmp_path / "acl.json"
    acl_file.write_text(json.dumps({"groupA": {"roles": ["admin"]}}))
    monkeypatch.setattr(acl, "ACL_PATH", acl_file)
    acl._cache = {"ts": 0.0, "data": {}}
    manifest = [{"id": "pipe1", "group": "groupA"}]
    user = {"id": "99", "role": "admin"}
    assert acl.is_pipe_allowed("pipe1", user, manifest)
