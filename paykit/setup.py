from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="paykit",
    version="0.1.0",
    author="Abror Kodirov",
    author_email="splayerme@gmail.com",
    description="Payment provider integration toolkit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/abrorbekuz/paykit",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "paykit=paykit.cli:cli",
        ],
    },
)
