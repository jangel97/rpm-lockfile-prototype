import configparser
import glob
import logging
import platform

from importlib.metadata import entry_points
from dataclasses import dataclass, field


@dataclass(frozen=True, order=True)
class Repo:
    repoid: str
    kwargs: dict() = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data):
        repoid = data.pop("repoid")
        if not isinstance(data.get("baseurl", []), list):
            # If baseurl is not a list already, convert it to a list by
            # splitting on whitespace. If there's only one URL, this will
            # produce a list with a single item. But there may be multiple
            # baseurls.
            data["baseurl"] = data["baseurl"].split()

        if (
            "baseurl" not in data
            and "metalink" not in data
            and "mirrorlist" not in data
        ):
            raise RuntimeError(
                f"Repo {repoid} must specify one of baseurl/metalink/mirrorlist"
            )

        return cls(repoid=repoid, kwargs=data)


def load():
    group = "rpm_lockfile.content_origins"
    try:
        # Python 3.10+
        eps = entry_points(group=group)
    except TypeError:
        # Python 3.9
        eps = entry_points()[group]
    return {c.name: c.load() for c in eps}


def _normalize_basearch(options):
    """Replace the host architecture with $basearch in repo URLs.

    subscription-manager writes baseurls with the host architecture
    hardcoded (e.g. /x86_64/).  Replacing it with $basearch lets DNF
    substitute the correct value for each target architecture, the same
    approach composes.py uses for compose paths.
    """
    host_arch = platform.machine()
    for key in ("baseurl", "metalink", "mirrorlist"):
        value = options.get(key)
        if value and isinstance(value, str) and f"/{host_arch}/" in value:
            options[key] = value.replace(f"/{host_arch}/", "/$basearch/")
    return options


def load_system_repos():
    """Load enabled repositories from /etc/yum.repos.d/."""
    repo_files = sorted(glob.glob("/etc/yum.repos.d/*.repo"))
    if not repo_files:
        logging.warning(
            "systemRepos: no .repo files found in /etc/yum.repos.d/"
        )
        return []

    repos = []
    for repo_file in repo_files:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(repo_file)
        for section in parser.sections():
            if parser.get(section, "enabled", fallback="1") == "0":
                continue
            options = {"repoid": section} | dict(parser.items(section))
            _normalize_basearch(options)
            options.setdefault("skip_if_unavailable", "1")
            try:
                repos.append(Repo.from_dict(options))
            except RuntimeError:
                logging.debug(
                    "Skipping repo %s: no baseurl/metalink/mirrorlist", section
                )

    if not repos:
        logging.warning(
            "systemRepos: no enabled repositories found in /etc/yum.repos.d/"
        )
    else:
        logging.info(
            "systemRepos: loaded %d repos: %s",
            len(repos),
            ", ".join(r.repoid for r in repos),
        )
    return repos
