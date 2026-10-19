"""Static checks on the Docker build inputs (no Docker daemon needed)."""
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND = os.path.join(REPO, "frontend")

pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.join(FRONTEND, "Dockerfile")),
    reason="needs the repo checkout (not just backend/)",
)


def _lines(path):
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def test_frontend_image_never_copies_host_node_modules():
    # `COPY . .` used to drag a host node_modules (e.g. macOS esbuild/rollup
    # binaries from a local `npm install`) over the image's Linux install, and
    # compose seeds the /app/node_modules volume from that image layer.
    ignored = _lines(os.path.join(FRONTEND, ".dockerignore"))
    assert "node_modules" in ignored


def test_frontend_image_installs_from_the_lockfile():
    steps = _lines(os.path.join(FRONTEND, "Dockerfile"))
    copy = next(s for s in steps if s.startswith("COPY package"))
    assert "package-lock.json" in copy
    assert "RUN npm ci" in steps
