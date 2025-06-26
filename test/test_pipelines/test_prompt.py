from pipelines import prompt
from pipelines import loader


def test_build_pipeline_prompt():
    manifest = [
        {"id": "pipe1", "name": "Pipe One"},
        {"id": "pipe2"},
    ]
    snippet = prompt.build_pipeline_prompt(manifest)
    expected = (
        "## Available Pipelines\n"
        "- id: pipe1\n"
        "  name: Pipe One\n"
        "  call_via: run_pipeline\n"
        "- id: pipe2\n"
        "  call_via: run_pipeline"
    )
    assert snippet == expected


def test_init_pipeline_prompt(monkeypatch):
    manifest = [{"id": "a"}]
    monkeypatch.setattr(loader, "load_manifest", lambda: manifest)
    prompt.init_pipeline_prompt()
    assert prompt.PIPELINE_PROMPT_SNIPPET.startswith("## Available Pipelines")
