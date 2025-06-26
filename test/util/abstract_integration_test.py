from importlib import util
from pathlib import Path

module_path = (
    Path(__file__).resolve().parents[2]
    / "backend/open_webui/test/util/abstract_integration_test.py"
)
spec = util.spec_from_file_location("abstract_integration_test", module_path)
module = util.module_from_spec(spec)
spec.loader.exec_module(module)  # type: ignore

globals().update(vars(module))
