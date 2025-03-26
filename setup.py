from setuptools import setup, find_packages

setup(
    name="watchdb",
    version="1.1.0",
    description="Watch database application",
    author="Mateusz Kadula",
    packages=find_packages(exclude=["tests*", "*/tests*"]),
    entry_points={
        "console_scripts": [
            "watchdb=watch.main:main",
        ],
    },
    install_requires=["prettytable"],
)
