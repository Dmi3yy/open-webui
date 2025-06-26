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


def test_patch_payload_injection(monkeypatch):
    import sys
    import types

    payload_mod = types.ModuleType("payload")

    def original(system, form_data, metadata=None, user=None):
        form_data["messages"] = [{"role": "system", "content": system}]
        return form_data

    payload_mod.apply_model_system_prompt_to_body = original
    sys.modules["backend.open_webui.utils.payload"] = payload_mod

    import importlib

    importlib.reload(prompt)
    if "open_webui.utils.task" not in sys.modules:
        package_stub = types.ModuleType("open_webui")
        utils_package = types.ModuleType("open_webui.utils")
        task_package = types.ModuleType("open_webui.utils.task")
        misc_package = types.ModuleType("open_webui.utils.misc")
        task_package.prompt_template = lambda t, **k: t
        task_package.prompt_variables_template = lambda t, v: t
        misc_package.deep_update = lambda a, b: {**a, **b}

        def add_or_update_system_message(content, messages, append=False):
            messages.insert(0, {"role": "system", "content": content})
            return messages

        misc_package.add_or_update_system_message = add_or_update_system_message
        utils_package.task = task_package
        utils_package.misc = misc_package
        utils_package.payload = payload_mod
        package_stub.utils = utils_package
        sys.modules["open_webui"] = package_stub
        sys.modules["open_webui.utils"] = utils_package
        sys.modules["open_webui.utils.payload"] = payload_mod
        sys.modules["open_webui.utils.task"] = task_package
        sys.modules["open_webui.utils.misc"] = misc_package
        sys.modules["backend.open_webui.utils"] = utils_package
        sys.modules["backend.open_webui.utils.task"] = task_package
        sys.modules["backend.open_webui.utils.misc"] = misc_package
        sys.modules["backend.open_webui.utils.payload"] = payload_mod
    monkeypatch.setattr(
        prompt,
        "PIPELINE_PROMPT_SNIPPET",
        "## Available Pipelines\n- id: x\n  call_via: run_pipeline",
    )
    prompt.patch_payload_injection()

    form = {"messages": []}
    result = payload_mod.apply_model_system_prompt_to_body("hello", form)
    assert "Available Pipelines" in result["messages"][0]["content"]
