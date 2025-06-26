from importlib import util
from pathlib import Path

module_path = (
    Path(__file__).resolve().parents[2] / "backend/open_webui/test/util/mock_user.py"
)
spec = util.spec_from_file_location("mock_user", module_path)
module = util.module_from_spec(spec)
spec.loader.exec_module(module)  # type: ignore

globals().update(vars(module))
