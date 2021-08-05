import os
import re

import setuptools


def read(filename):
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), filename)
    with open(path, 'r') as f:
        return f.read()


def find_version(text):
    match = re.search(r"^__version__\s*=\s*['\"](.*)['\"]\s*$", text,
                      re.MULTILINE)
    return match.group(1)


AUTHOR = "Conservation Technology Lab at the San Diego Zoo Wildlife Alliance"
DESC = ("Code for ScrubDash: Dashboard for organizing, visualizing, and "
        "analyzing images coming in from a ScrubCam(s).")

setuptools.setup(
    name="scrubdash",
    description=DESC,
    long_description=read('README.md'),
    license="MIT",
    version=find_version(read('scrubdash/__init__.py')),
    author=AUTHOR,
    packages=setuptools.find_packages('.'),
    install_requires=[
        'dash',
        'dash_html_components',
        'plotly',
        'pandas',
        'dash_core_components',
        'numpy',
        'dash_bootstrap_components',
        'Pillow',
        'PyYAML'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        'Development Status :: 2 - Pre-Alpha',
        'Topic :: Scientific/Engineering',
    ],
    python_requires=">=3.7",
    entry_points={'console_scripts': ["scrubdash=scrubdash.__main__:main"]},
    include_package_data=True
)
