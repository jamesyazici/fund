from setuptools import setup, find_packages

setup(
    name="rqfc",
    version="0.3.0",
    packages=find_packages(),
    install_requires=[
        "alpaca-py>=0.13.0",
        "pandas>=1.5.0",
        "numpy>=1.23.0",
        "supabase>=2.0.0",
    ],
    python_requires=">=3.9",
    description="Alpaca trading wrapper for the RQFC student quant fund",
    author="RQFC",
)
