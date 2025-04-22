"""
Setup script for the GetVerbrauch package.
"""
from setuptools import setup, find_packages

setup(
    name="GetVerbrauch",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "python-dotenv==1.0.0",
    ],
    python_requires=">=3.8",
) 