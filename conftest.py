"""Ignore version-specific test files (mostly due to incompatible syntax).
"""

import sys
import os

tests_dir = "tests"

collect_ignore = []

major = sys.version_info[0]
other_major = {2: 3, 3: 2}[major]

for name in os.listdir(tests_dir):
    rel_path = "{0}/{1}".format(tests_dir, name)
    if (
        os.path.isfile(rel_path)
        and name.endswith("_py{0}.py".format(other_major))
    ):
        collect_ignore.append(rel_path)
