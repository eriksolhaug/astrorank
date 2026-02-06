from setuptools import setup, find_packages
import os

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="astrorank",
    version="0.1.0",
    author="Erik Solhaug",
    description="A GUI application for ranking astronomical images",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/eriksolhaug/astrorank",
    packages=find_packages(),
    package_data={
        "astrorank": ["../logo/*.png", "../config.json"],
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyQt5>=5.15.0",
        "Pillow>=8.0.0",
        "requests>=2.20.0",
        "astropy>=5.0.0",
        "numpy>=1.20.0",
    ],
    entry_points={
        "console_scripts": [
            "astrorank=astrorank.astrorank:main",
        ],
    },
)
