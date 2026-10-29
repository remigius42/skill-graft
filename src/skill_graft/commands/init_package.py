"""Creates a package, `~/.apm/skill-graft/` or a project's, and registers it with APM."""

import shutil

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


def init(scope: paths.Scope, project: bool = False) -> None:
    """Creates and registers the user scope's package, or with `project` the one in
    the scope's root: the working folder."""
    if project and scope.user:
        raise SkillGraftError(
            "the home folder is user scope: `skill-graft init` creates its package"
        )
    if project and ".apm" in scope.root.resolve().parts:
        # APM's or a package's own folder: its apm.yml is not a project's.
        raise SkillGraftError(
            f"{scope.root} is inside an .apm folder; run init --project in a project"
        )
    package = scope.package
    notice(f"package: {package.absolute()}")
    made = package.parent if not package.parent.exists() else package
    if package.exists() or package.is_symlink():
        raise _exists(scope)
    try:
        apm.require()
    except SkillGraftError as error:
        retry = "skill-graft init --project" if project else "skill-graft init"
        raise SkillGraftError(f"{error}\ninstall APM, then run: {retry}") from None
    try:
        package.mkdir(parents=True)
    except FileExistsError:
        raise _exists(scope) from None
    try:
        scope.config_file.write_text(CONFIG_TEMPLATE)
        (package / "apm.yml").write_text(APM_YML)
        apm.install(scope)
    except (SkillGraftError, OSError) as error:
        if not project:
            retry = apm.command_line(scope)
            raise SkillGraftError(f"{error}\nto retry, run: {retry}") from None
        if _listed(scope):
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


def _exists(scope: paths.Scope) -> SkillGraftError:
    """The refusal of an existing folder, with the command that registers it when APM
    does not list it and it holds the `apm.yml` APM needs."""
    package = scope.package
    message = f"{package} already exists; init does nothing"
    if (package / "apm.yml").exists() and not _listed(scope):
        where = f" in {scope.root}" if not scope.user else ""
        message += f"\nto register it, run{where}: {apm.command_line(scope)}"
    return SkillGraftError(message)


def _listed(scope: paths.Scope) -> bool:
    """Whether the scope's `apm.yml` lists the package; not when unreadable."""
    try:
        return apm.registered(scope)
    except (SkillGraftError, OSError):
        return False
