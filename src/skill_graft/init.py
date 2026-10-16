"""Creates `~/.apm/skill-graft/` and registers it with APM."""

from skill_graft import apm, paths
from skill_graft.errors import SkillGraftError

CONFIG_TEMPLATE = """\
# skill-graft.toml: the skills you want and where they come from.
#
# entries = ["own/chisel"]   # Skill IDs: <source alias>/<skill name>
#
# [sources.own]
# path = "~/skills"          # a folder; skills are found at any depth
"""

APM_YML = "name: skill-graft\nversion: 0.1.0\n"


def init() -> None:
    package = paths.package()
    try:
        package.mkdir(parents=True)
    except FileExistsError:
        raise SkillGraftError(f"{package} already exists; init does nothing") from None
    paths.config_file().write_text(CONFIG_TEMPLATE)
    (package / "apm.yml").write_text(APM_YML)
    try:
        apm.install()
    except SkillGraftError as error:
        retry = f"apm install -g {package.absolute()}"
        raise SkillGraftError(f"{error}\nto retry, run: {retry}") from None
