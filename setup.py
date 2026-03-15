"""Setup script for gitpull."""

from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gitpull",
    version="0.3.0",
    author="Project Gutenberg",
    description="Update a folder with the latest files from a Git repository",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gutenbergtools/gitpull",
    py_modules=["gitpull", "puller"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "gitpull=gitpull:main",
            "puller=puller:main",
        ],
    },
)
