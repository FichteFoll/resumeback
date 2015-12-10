import io
import re
import os

from setuptools import setup


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

setup(
    name='resumeback',
    packages=['resumeback'],
    version=find_version('resumeback', '__init__.py'),
    description="Library for using callbacks to resume your code.",
    long_description=read('README.rst'),
    author='FichteFoll',
    author_email='fichtefoll2@googlemail.com',
    url='http://fichtefoll.github.io/resumeback/',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords=['generator', 'resume', 'callback'],
    zip_safe=True,
)
