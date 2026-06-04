"""docker_manager SCSS-reference detection (auto-stub) — no docker needed."""

from app.docker_manager import _SCSS_REF_RE


def _refs(content: str) -> list[str]:
    return [m.group(1) for m in _SCSS_REF_RE.finditer(content)]


def test_scss_ref_matches_style_src():
    # SFC `<style scoped src="./X.scss">` must be detected so the stub is created
    assert _refs('<style scoped lang="scss" src="./CpmsFoo.scss"></style>') == ["./CpmsFoo.scss"]


def test_scss_ref_matches_import_and_from():
    assert _refs("@import './a.scss';") == ["./a.scss"]
    assert _refs("import styles from './b.scss'") == ["./b.scss"]


def test_scss_ref_ignores_non_scss():
    assert _refs('src="./CpmsFoo.vue"') == []
    assert _refs("import { x } from './util'") == []
