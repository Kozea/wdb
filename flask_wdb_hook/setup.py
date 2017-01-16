import sys
import os
from setuptools import setup
from distutils.sysconfig import get_python_lib

site_packages_path = get_python_lib().replace(sys.prefix + os.path.sep, '')

setup(
    name="flask-wdb-hook",
    version='0.1.1',
    author="Florian Mounier @ kozea",
    author_email="florian.mounier@kozea.fr",
    url="http://github.com/Kozea/wdb",
    license='GPLv3',
    install_requires=['wdb >= 3.1.0'],
    data_files=[(site_packages_path, ['flask-wdb.pth'])],
    description="Hook to replace flask werkzeug debugger with wdb."
)
