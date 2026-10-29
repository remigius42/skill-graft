from pathlib import Path

from skill_graft.infra import paths


def test_home_root_is_user_scope(home: Path) -> None:
    assert paths.Scope(home).user


def test_any_other_root_is_project_scope(tmp_path: Path) -> None:
    assert not paths.Scope(tmp_path / "project").user


def test_symlink_to_home_is_user_scope(home: Path, tmp_path: Path) -> None:
    link = tmp_path / "link"
    link.symlink_to(home)
    assert paths.Scope(link).user


def test_paths_under_the_package(tmp_path: Path) -> None:
    scope = paths.Scope(tmp_path)
    package = tmp_path / ".apm" / "skill-graft"
    assert scope.package == package
    assert scope.lock_file == package / "skill-graft.lock"
    assert scope.skills == package / ".apm" / "skills"


def test_config_file_in_the_package(home: Path, tmp_path: Path) -> None:
    for root in (home, tmp_path / "project"):
        assert paths.Scope(root).config_file == (
            root / ".apm" / "skill-graft" / "skill-graft.toml"
        )


def test_user_manifest_in_the_apm_folder(home: Path) -> None:
    assert paths.Scope(home).manifest == home / ".apm" / "apm.yml"


def test_project_manifest_at_the_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    assert paths.Scope(project).manifest == project / "apm.yml"


def test_user_deploy_folders(home: Path) -> None:
    assert paths.Scope(home).deploy_folders == [
        home / folder for folder in paths.DEPLOY_FOLDERS
    ]


def test_project_deploy_folders_include_the_user_scopes(
    home: Path, tmp_path: Path
) -> None:
    project = tmp_path / "project"
    assert paths.Scope(project).deploy_folders == [
        *(home / folder for folder in paths.DEPLOY_FOLDERS),
        project / ".agents/skills",
        project / ".claude/skills",
        project / ".grok/skills",
        project / ".kiro/skills",
    ]


def test_user_packages(home: Path) -> None:
    assert paths.Scope(home).packages == [home / ".apm" / "skill-graft"]


def test_project_packages_include_the_user_scopes(home: Path, tmp_path: Path) -> None:
    project = tmp_path / "project"
    assert paths.Scope(project).packages == [
        project / ".apm" / "skill-graft",
        home / ".apm" / "skill-graft",
    ]
