import os
from pathlib import Path

import pytest


def test_unmarked_chmod_names_the_code_under_test_too(tmp_path: Path) -> None:
    file = tmp_path / "f"
    file.write_text("x")

    with pytest.raises(
        pytest.fail.Exception, match="by the test or by the code it runs"
    ):
        os.chmod(file, 0)
