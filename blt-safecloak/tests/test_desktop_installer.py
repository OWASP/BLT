import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).parent.parent
INSTALLER = ROOT / 'public' / 'install.sh'


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_installer_builds_from_the_forge_monorepo():
    script = _read('public/install.sh')

    assert 'OS_NAME="$(uname -s)"' in script
    assert 'https://git.owaspblt.org/BLT.git' in script
    assert 'sparse-checkout set "$REPO_FOLDER/client"' in script
    assert 'REPO_FOLDER="blt-safecloak"' in script
    # The GitLab CI artifacts API is gone; nothing may download from it.
    assert '/-/jobs/artifacts' not in script
    assert 'gitlab' not in script.lower()


def _stub(path: Path, body: str) -> None:
    path.write_text('#!/usr/bin/env bash\n' + body, encoding='utf-8')
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_installer_builds_a_local_checkout(tmp_path):
    source = tmp_path / 'checkout' / 'client'
    source.mkdir(parents=True)
    (source / 'CMakeLists.txt').write_text('project(stub)\n', encoding='utf-8')
    tools = tmp_path / 'tools'
    tools.mkdir()
    # A fake cmake: "--build <dir>" drops an executable where the installer looks for it.
    _stub(tools / 'cmake', 'if [ "$1" = --build ]; then printf "#!/bin/sh\\n" > "$2/safecloak"; '
          'chmod +x "$2/safecloak"; fi\n')
    for tool in ('g++', 'clang++', 'make', 'openssl', 'brew'):
        _stub(tools / tool, 'exit 0\n')
    bin_dir = tmp_path / 'bin'
    env = {
        **os.environ,
        'PATH': f'{tools}:{os.environ["PATH"]}',
        'SAFECLOAK_SOURCE_DIR': str(tmp_path / 'checkout'),
        'SAFECLOAK_BIN_DIR': str(bin_dir),
        'SAFECLOAK_APP_DIR': str(tmp_path / 'apps'),
    }
    result = subprocess.run(['bash', str(INSTALLER)], env=env, capture_output=True, text=True, timeout=60)

    assert result.returncode == 0, result.stderr
    assert (bin_dir / 'safecloak').exists()


def test_installer_rejects_a_source_dir_without_the_client(tmp_path):
    env = {**os.environ, 'SAFECLOAK_SOURCE_DIR': str(tmp_path), 'SAFECLOAK_BIN_DIR': str(tmp_path / 'bin')}
    result = subprocess.run(['bash', str(INSTALLER)], env=env, capture_output=True, text=True, timeout=60)

    assert result.returncode != 0
    assert 'no SafeCloak client sources' in result.stderr
