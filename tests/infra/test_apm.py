from pathlib import Path

from conftest import FakeApm

from skill_graft.infra import apm, paths


def project(tmp_path: Path) -> paths.Scope:
    scope = paths.Scope(tmp_path / "project")
    scope.package.mkdir(parents=True)
    return scope


def test_project_package_unregistered_before_install(
    tmp_path: Path, fake_apm: FakeApm
) -> None:
    assert not apm.registered(project(tmp_path))


def test_install_registers_a_project_package_in_its_root(
    tmp_path: Path, fake_apm: FakeApm
) -> None:
    scope = project(tmp_path)
    apm.install(scope)
    assert fake_apm.calls == [["install", "./.apm/skill-graft"]]
    assert fake_apm.working_folders == [str(scope.root)]
    assert apm.registered(scope)
