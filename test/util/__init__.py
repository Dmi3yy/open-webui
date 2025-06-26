from importlib import util
from pathlib import Path

module_dir = Path(__file__).resolve().parents[2] / "backend/open_webui/test/util"
for name in ("abstract_integration_test.py", "mock_user.py"):
    path = module_dir / name
    spec = util.spec_from_file_location(f"test.util.{path.stem}", path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    globals()[path.stem] = module
