import os
import tempfile
from unittest.mock import patch

from rpm_lockfile.content_origin import load_system_repos


ENABLED_REPO = """\
[rhel-9-baseos]
name=RHEL 9 BaseOS
baseurl=https://cdn.redhat.com/content/dist/rhel9/9/$basearch/baseos/os
enabled=1
gpgcheck=1
"""

DISABLED_REPO = """\
[rhel-9-baseos-debug]
name=RHEL 9 BaseOS Debug
baseurl=https://cdn.redhat.com/content/dist/rhel9/9/$basearch/baseos/debug
enabled=0
gpgcheck=1
"""

MIXED_REPO = """\
[appstream]
name=AppStream
baseurl=https://cdn.redhat.com/content/dist/rhel9/9/$basearch/appstream/os
enabled=1

[appstream-debug]
name=AppStream Debug
baseurl=https://cdn.redhat.com/content/dist/rhel9/9/$basearch/appstream/debug
enabled=0
"""

NO_BASEURL_REPO = """\
[rhsm-katello]
name=Katello agent
enabled=1
"""

IMPLICIT_ENABLED_REPO = """\
[fast-datapath]
name=Fast Datapath
baseurl=https://cdn.redhat.com/content/dist/layered/rhel9/$basearch/fast-datapath/os
gpgcheck=1
"""


def _write_repo(tmpdir, filename, content):
    path = os.path.join(tmpdir, filename)
    with open(path, "w") as f:
        f.write(content)
    return path


class TestLoadSystemRepos:
    def test_loads_enabled_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_repo(tmpdir, "redhat.repo", ENABLED_REPO)
            with patch(
                "rpm_lockfile.content_origin.glob.glob",
                return_value=[os.path.join(tmpdir, "redhat.repo")],
            ):
                repos = load_system_repos()

        assert len(repos) == 1
        assert repos[0].repoid == "rhel-9-baseos"

    def test_skips_disabled_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_repo(tmpdir, "redhat.repo", DISABLED_REPO)
            with patch(
                "rpm_lockfile.content_origin.glob.glob",
                return_value=[os.path.join(tmpdir, "redhat.repo")],
            ):
                repos = load_system_repos()

        assert len(repos) == 0

    def test_mixed_enabled_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_repo(tmpdir, "redhat.repo", MIXED_REPO)
            with patch(
                "rpm_lockfile.content_origin.glob.glob",
                return_value=[os.path.join(tmpdir, "redhat.repo")],
            ):
                repos = load_system_repos()

        assert len(repos) == 1
        assert repos[0].repoid == "appstream"

    def test_skips_repo_without_baseurl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_repo(tmpdir, "redhat.repo", NO_BASEURL_REPO)
            with patch(
                "rpm_lockfile.content_origin.glob.glob",
                return_value=[os.path.join(tmpdir, "redhat.repo")],
            ):
                repos = load_system_repos()

        assert len(repos) == 0

    def test_implicit_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_repo(tmpdir, "redhat.repo", IMPLICIT_ENABLED_REPO)
            with patch(
                "rpm_lockfile.content_origin.glob.glob",
                return_value=[os.path.join(tmpdir, "redhat.repo")],
            ):
                repos = load_system_repos()

        assert len(repos) == 1
        assert repos[0].repoid == "fast-datapath"

    def test_no_repo_files(self):
        with patch(
            "rpm_lockfile.content_origin.glob.glob", return_value=[]
        ):
            repos = load_system_repos()

        assert len(repos) == 0

    def test_multiple_repo_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_repo(tmpdir, "redhat.repo", ENABLED_REPO)
            _write_repo(tmpdir, "cuda.repo", IMPLICIT_ENABLED_REPO)
            with patch(
                "rpm_lockfile.content_origin.glob.glob",
                return_value=sorted(
                    [
                        os.path.join(tmpdir, "cuda.repo"),
                        os.path.join(tmpdir, "redhat.repo"),
                    ]
                ),
            ):
                repos = load_system_repos()

        assert len(repos) == 2
        repoids = {r.repoid for r in repos}
        assert "rhel-9-baseos" in repoids
        assert "fast-datapath" in repoids
