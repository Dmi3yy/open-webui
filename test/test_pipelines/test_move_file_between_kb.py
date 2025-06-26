import asyncio

from pipelines import move_file_between_kb as pipe


def test_follow_up_when_missing():
    result = asyncio.run(pipe.run({}))
    assert result["finish_reason"] == "follow_up"
    assert set(result["follow_up"]["missing_fields"]) == {
        "src_kb_id",
        "dst_kb_id",
        "file_id",
    }


def test_success():
    metadata = {"src_kb_id": "a", "dst_kb_id": "b", "file_id": "c"}
    result = asyncio.run(pipe.run(metadata))
    assert result["finish_reason"] == "stop"
    assert result["content"]["moved"] is True
