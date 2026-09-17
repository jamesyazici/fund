from setuptools import setup, find_packages

setup(
    name="rqfc",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        # Only needed inside a strategy sandbox (rqfc._runtime).
        "runtime": ["nats-py>=2.6.0"],
    },
    entry_points={
        "console_scripts": ["rqfc=rqfc.cli:main"],
    },
    python_requires=">=3.9",
    description="Thin client for the RQFC fund trading backend",
    author="RQFC",
)
