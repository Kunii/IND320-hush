"""Shared pytest setup: repo root on the path and the notebook module fixture.

``Proj-P3.py`` carries the notebook's narrative cells as well as its helpers.
The run cells are tagged ``run`` in the source, so importing the file for its
helpers must not download data or draw figures. ``load_notebook_module``
executes only the untagged (definition) cells.
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

NOTEBOOK_SOURCE = REPO_ROOT / "notebooks" / "CA3" / "Proj-P3.py"
RUN_TAG = '"tags": ["run"]'


def load_notebook_module() -> types.ModuleType:
    """Load the definition cells of ``Proj-P3.py`` without running the notebook."""
    source = NOTEBOOK_SOURCE.read_text()
    cells = re.split(r"^# %%", source, flags=re.M)[1:]
    if not cells:
        raise ImportError(f"No percent-format cells found in {NOTEBOOK_SOURCE}")
    module = types.ModuleType("proj_p3")
    module.__file__ = str(NOTEBOOK_SOURCE)
    sys.modules["proj_p3"] = module
    executed = 0
    for cell in cells:
        lines = cell.splitlines()
        if lines and RUN_TAG in lines[0]:
            continue
        exec(
            compile("\n".join(lines[1:]), str(NOTEBOOK_SOURCE), "exec"),
            module.__dict__,
        )
        executed += 1
    if executed == 0:
        raise ImportError(f"Every cell of {NOTEBOOK_SOURCE} is tagged {RUN_TAG}")
    return module


@pytest.fixture(scope="session")
def p3() -> types.ModuleType:
    """The notebook's helper module, loaded once per test session."""
    return load_notebook_module()
