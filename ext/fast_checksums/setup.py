from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "fast_checksums",
        ["fast_checksums.cpp"],
        language='c++',
    ),
]

setup(
    name='fast_checksums',
    version='0.1.0',
    description='Fast checksum utilities (pybind11 PoC)',
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
