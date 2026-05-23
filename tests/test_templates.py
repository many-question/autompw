import site
import sysconfig
from pathlib import Path

from autompw.templates import template_candidates


def test_template_candidates_include_data_and_user_install_locations():
    candidates = template_candidates()

    assert Path(sysconfig.get_path("data")).resolve() / "templates" in candidates
    assert Path(site.getuserbase()).resolve() / "templates" in candidates
