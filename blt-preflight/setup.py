#!/usr/bin/env python3
"""
Setup script for BLT-Preflight - installs the 'pf' command.
"""

from setuptools import setup, find_packages

setup(
    name="blt-preflight",
    version="1.0.0",
    description="BLT Preflight - pre-commit security advisory check",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="OWASP BLT",
    url="https://github.com/OWASP-BLT/BLT-Preflight",
    license="Apache-2.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "pf=blt_preflight:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Topic :: Security",
        "Topic :: Software Development :: Quality Assurance",
    ],
)
