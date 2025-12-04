"""Setup script for flex-analyzer"""

from setuptools import setup, find_packages

setup(
    name="flex-analyzer",
    version="2.0.0",
    description="DSA (Distance Scoring Analysis) for protein flexibility",
    author="Research Lab",
    python_requires=">=3.12",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "biopython>=1.80",
        "requests>=2.28.0",
        "lxml>=4.9.0",
        "click>=8.0.0",
        "numba>=0.57.0",
        "pydantic>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "flex-analyze=flex_analyzer.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3.12",
    ],
)
