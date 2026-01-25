import sys
from pathlib import Path
from typing import Literal

# Add parent directory to import from utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


Decision = Literal["allow", "block"]


def no_coding_guardrail(file_path: str, state_path: Path) -> Decision:
    if not file_path.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
        return "allow"

    return "block"
