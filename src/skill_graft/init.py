"""Creates a package, `~/.apm/skill-graft/` or a project's, and registers it with APM."""

import shutil

from skill_graft import apm, paths
from skill_graft.errors import SkillGraftError, notice

CONFIG_TEMPLATE = """\
# skill-graft.toml: the skills you want and where they come from.
#
# entries = ["own/chisel", "mp/tdd"]   # Skill IDs: <source alias>/<skill name>
#
# [sources.own]
# path = "~/skills"          # a folder; skills are found at any depth
#
# [sources.mp]
# git = "https://example.com/skills.git"   # a URL, user@host:path, or an absolute path
# branch = "main"            # optional; defaults to the remote's default branch
# ref = "<sha>"              # the commit build reads; `skill-graft update` sets it
"""

APM_YML = "name: skill-graft\nversion: 0.1.0\n"


def init(project: bool = False) -> None:
    """Creates and registers the user scope's package, or with `project` the one in
    the root `cli` set: the working folder."""
    if project and paths.scope() == "user":
        raise SkillGraftError(
            "the home folder is user scope: `skill-graft init` creates its package"
        )
    if project and ".apm" in paths.root().resolve().parts:
        # APM's or a package's own folder: its apm.yml is not a project's.
        raise SkillGraftError(
            f"{paths.root()} is inside an .apm folder; run init --project in a project"
        )
    package = paths.package()
    notice(f"package: {package.absolute()}")
    made = package.parent if not package.parent.exists() else package
    try:
        package.mkdir(parents=True)
    except FileExistsError:
        raise SkillGraftError(f"{package} already exists; init does nothing") from None
    paths.config_file().write_text(CONFIG_TEMPLATE)
    (package / "apm.yml").write_text(APM_YML)
    try:
        apm.install()
    except SkillGraftError as error:
        if not project:
            retry = f"apm install -g {package.absolute()}"
            raise SkillGraftError(f"{error}\nto retry, run: {retry}") from None
        if apm.registered():
            raise SkillGraftError(
                f"{error}\nfix that, then run: skill-graft build"
            ) from None
        # A package left behind would be found by every command below it.
        shutil.rmtree(made)
        retry = "skill-graft init --project"
        raise SkillGraftError(f"{error}\nfix that, then run: {retry}") from None
