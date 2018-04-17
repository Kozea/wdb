import os
import sys
from distutils.sysconfig import get_python_lib

from setuptools import setup

site_packages_path = get_python_lib().replace(sys.prefix + os.path.sep, '')

setup(
    name="flask-wdb-hook",
    version='0.2.0',
    author="Florian Mounier @ kozea",
    author_email="florian.mounier@kozea.fr",
    url="http://github.com/Kozea/wdb",
    license='GPLv3',
    packages=[],
    install_requires=['wdb >= 3.2.1'],
    data_files=[(site_packages_path, ['flask-wdb.pth'])],
    description="Hook to replace flask werkzeug debugger with wdb."
)
