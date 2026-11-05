"""scripts/gen-env.sh must generate a password that survives DATABASE_URL."""
import os
import re
import shutil
import subprocess
from urllib.parse import urlsplit

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.skipif(
    not (
        shutil.which("bash")
        and shutil.which("openssl")
        and os.path.exists(os.path.join(REPO, "scripts", "gen-env.sh"))
    ),
    reason="needs bash + openssl and the repo checkout (not just backend/)",
)


def _run_gen_env(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copy(os.path.join(REPO, "scripts", "gen-env.sh"), tmp_path / "scripts")
    shutil.copy(os.path.join(REPO, ".env.example"), tmp_path / ".env.example")
    subprocess.run(["bash", str(tmp_path / "scripts" / "gen-env.sh")], check=True,
                   capture_output=True)
    env = (tmp_path / ".env").read_text()
    return re.search(r"^ALPHA_DB_PASSWORD=(.*)$", env, re.M).group(1)


@pytest.mark.parametrize("attempt", range(8))
def test_generated_password_is_url_safe(tmp_path, attempt):
    password = _run_gen_env(tmp_path)
    assert len(password) >= 32
    # docker-compose.yml splices it into postgresql://alpha:<pw>@db:5432/alpha;
    # base64's "/" and "+" broke that URL roughly two runs in three.
    assert re.fullmatch(r"[A-Za-z0-9]+", password)
    url = urlsplit(f"postgresql://alpha:{password}@db:5432/alpha")
    assert (url.hostname, url.port, url.password) == ("db", 5432, password)


def test_rerun_keeps_the_existing_password(tmp_path):
    first = _run_gen_env(tmp_path)
    subprocess.run(["bash", str(tmp_path / "scripts" / "gen-env.sh")], check=True,
                   capture_output=True)
    env = (tmp_path / ".env").read_text()
    assert re.search(r"^ALPHA_DB_PASSWORD=(.*)$", env, re.M).group(1) == first
