from setuptools import setup, find_packages

setup(
    name="traptrace-cli",
    version="0.3.0",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        "console_scripts": [
            "soroban-explain=traptrace_cli.cli:main",
            "traptrace=traptrace_cli.cli:main",
        ],
    },
    author="TrapTrace Team",
    description="CLI error lookup and diagnostic tool for Stellar Soroban developers",
    license="MIT",
    keywords="stellar soroban cli error debugging",
)
