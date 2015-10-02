from setuptools import setup, find_packages

setup(
    name="pymdb",
    version="1.0",
    packages=find_packages(),
    author="Aborilov Pavel",
    description="NRI Currenza RS232 MDB protocol python implimentation",
    install_requires=["Twisted", "pyserial"],
    )
