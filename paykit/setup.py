from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="paykit",
    version="0.1.0",
    author="Abror Qodirov",
    author_email="splayerme@gmail.com",
    description="Payment provider integration toolkit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/abrorbekuz/paykit",
    packages=["paykit", "paykit.commands", "paykit.core", "paykit.utils"],
    package_dir={"": ".."},
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
