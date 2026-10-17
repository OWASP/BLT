from pathlib import Path


ROOT = Path(__file__).parent.parent


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_installer_auto_detects_linux_and_macos_artifacts():
    script = _read('public/install.sh')

    assert 'OS_NAME="$(uname -s)"' in script
    assert 'Linux:x86_64|Linux:amd64' in script
    assert 'Darwin:arm64|Darwin:aarch64' in script
    assert 'client/build/safecloak?job=build-client' in script
    assert (
        'client/dist/safecloak-macos-arm64.zip?job=build-client-macos-arm64'
        in script
    )
    assert 'This installer currently supports Linux only' not in script


def test_gitlab_builds_macos_client_artifact():
    ci = _read('.gitlab-ci.yml')

    assert 'build-client-macos-arm64:' in ci
    assert 'saas-macos-medium-m1' in ci
    assert 'macos-15-xcode-16' in ci
    assert '-DCMAKE_OSX_ARCHITECTURES=arm64' in ci
    assert 'client/scripts/package-macos.sh client/build client/dist' in ci
    assert 'client/dist/safecloak-macos-arm64.zip' in ci
