from setuptools import setup
import re

version = ""
with open("dbouncer/__init__.py") as f:
    version = re.search(r"^__version__\s*=\s*[\"\']([^\"\']*)[\"\']", f.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError("Version is missing")

with open("README.md", encoding="utf-8") as f:
    readme = f.read()

setup(
    name="dbouncer",
    author="RocketRace",
    url="https://github.com/RocketRace/dbouncer",
    version=version,
    packages=["dbouncer"],
    license="MIT",
    description="A discord.py extension module to easily manage a bot's guild count.",
    long_description=readme,
    python_requires=">=3.5.3"
)