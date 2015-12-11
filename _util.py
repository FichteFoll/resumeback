import io
import re
import os

__all__ = (
    'read',
    'find_version'
)


def read(*names, **kwargs):
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8")
    ) as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = (['\"])(.*?)\1",
                              version_file, re.M)
    if version_match:
        return version_match.group(2)
    raise RuntimeError("Unable to find version string.")
