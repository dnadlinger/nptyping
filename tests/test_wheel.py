import os
import subprocess
import sys
import venv
from contextlib import contextmanager
from glob import glob
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import TestCase, TestLoader
from zipfile import ZipFile

from nptyping.package_info import __version__

_PATH_TO_SETUP = str(Path(__file__).parent.parent / "setup.py")
_ROOT = Path(__file__).parent.parent.absolute()
_VENV_NAME = "test_venv"
_WHEEL_NAME = f"nptyping-{str(__version__)}-py3-none-any.whl"
_VENV_PYTHON = "bin/python"
_VENV_PIP = "bin/pip"
if os.name == "nt":
    _VENV_PYTHON = "Scripts\\python.exe"
    _VENV_PIP = "Scripts\\pip.exe"
_EXPECTED_FILES_IN_WHEEL = {
    "__init__.py",
    "assert_isinstance.py",
    "error.py",
    "ndarray.py",
    "ndarray.pyi",
    "nptyping_type.py",
    "package_info.py",
    "py.typed",
    "shape_expression.py",
    "shape_expression.pyi",
    "typing_.py",
    "typing_.pyi",
}


def determine_order(_: Any, x: str, __: str) -> int:
    if x == "test_wheel_is_built_correctly":
        return -1
    if x == "test_wheel_can_be_installed":
        return -1
    return 1


TestLoader.sortTestMethodsUsing = determine_order


@contextmanager
def working_dir(path: Path):
    origin = Path().absolute()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)


class WheelTest(TestCase):
    temp_dir: TemporaryDirectory
    py: str
    pip: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = TemporaryDirectory()
        venv_bin = Path(cls.temp_dir.name) / _VENV_NAME
        cls.py = str(venv_bin / _VENV_PYTHON)
        cls.pip = str(venv_bin / _VENV_PIP)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_wheel_is_built_correctly(self):
        with working_dir(_ROOT):
            subprocess.check_output(
                f"{sys.executable} setup.py bdist_wheel", shell=True
            )
            wheel_files = glob(f"dist/*{__version__}*")
            self.assertEqual(1, len(wheel_files))

        with ZipFile(_ROOT / Path(wheel_files[0]), "r") as zip_:
            files_in_wheel = set(
                f.filename[len("nptyping/") :]
                for f in zip_.filelist
                if f.filename.startswith("nptyping/")
            )

        self.assertSetEqual(_EXPECTED_FILES_IN_WHEEL, files_in_wheel)

    def test_wheel_can_be_installed(self):
        with working_dir(Path(self.temp_dir.name)):
            venv.create(_VENV_NAME, with_pip=False)
            # For some reason, with_pip=True fails, so we do it separately.
            subprocess.check_output(
                f"{self.py} -m ensurepip --upgrade --default-pip", shell=True
            )
            subprocess.check_output(
                f"{self.pip} install {_ROOT / 'dist' / _WHEEL_NAME}", shell=True
            )
            # No errors raised? Then the install succeeded.

    def test_basic_nptyping_code(self):
        code = (
            "from nptyping import NDArray, Shape, Int; "
            "import numpy as np; "
            "print(isinstance(np.array([[1, 2], [3, 4]]), NDArray[Shape['2, 2'], Int]))"
        )

        output = subprocess.check_output(f'{self.py} -c "{code}"', shell=True)

        self.assertIn("True", str(output))
