"""Creates a package, `~/.apm/skill-graft/` or a project's, and registers it with APM."""

import shutil
from pathlib import Path

from skill_graft.infra import apm, paths
from skill_graft.infra.errors import SkillGraftError, notice

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
# subdirectory = "skills"    # optional; read only this folder of the repository
# prefix = "mp-"             # optional; each skill deploys as mp-<name> unless [rename] says otherwise
#
# graft-check, a skill that reviews how skill-graft read your skills (run /graft-check):
# [sources.skill-graft]
# git = "https://github.com/remigius42/skill-graft.git"
# subdirectory = "skills"
# then run `skill-graft update skill-graft`, `skill-graft add skill-graft/graft-check` and `skill-graft build`.
# Until that update sets its ref, every `build` fails, not only graft-check's.
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
    if package.exists() or package.is_symlink():
        raise _exists(package)
    try:
        apm.require()
    except SkillGraftError as error:
        retry = "skill-graft init --project" if project else "skill-graft init"
        raise SkillGraftError(f"{error}\ninstall APM, then run: {retry}") from None
    try:
        package.mkdir(parents=True)
    except FileExistsError:
        raise _exists(package) from None
    try:
        paths.config_file().write_text(CONFIG_TEMPLATE)
        (package / "apm.yml").write_text(APM_YML)
        apm.install(paths.in_use())
    except (SkillGraftError, OSError) as error:
        if not project:
            retry = apm.command_line(paths.in_use())
            raise SkillGraftError(f"{error}\nto retry, run: {retry}") from None
        if _listed():
            raise SkillGraftError(
                f"{error}\nfix that, then run: skill-graft build"
            ) from None
        # A package left behind would be found by every command below it.
        try:
            shutil.rmtree(made)
        except OSError as failure:
            error = SkillGraftError(
                f"{error}\ncannot remove {made}: {failure.strerror}"
            )
        retry = "skill-graft init --project"
        raise SkillGraftError(f"{error}\nfix that, then run: {retry}") from None


def _exists(package: Path) -> SkillGraftError:
    """The refusal of an existing folder, with the command that registers it when APM
    does not list it and it holds the `apm.yml` APM needs."""
    message = f"{package} already exists; init does nothing"
    if (package / "apm.yml").exists() and not _listed():
        where = f" in {paths.root()}" if paths.scope() == "project" else ""
        message += f"\nto register it, run{where}: {apm.command_line(paths.in_use())}"
    return SkillGraftError(message)


def _listed() -> bool:
    """Whether the scope's `apm.yml` lists the package; not when unreadable."""
    try:
        return apm.registered(paths.in_use())
    except (SkillGraftError, OSError):
        return False
