from setuptools import setup, find_packages

setup(
    name="stock-strategies",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'backtrader',
        'pandas',
        'numpy',
        'matplotlib',
        'redis>=4.0.0',
    ],
)
