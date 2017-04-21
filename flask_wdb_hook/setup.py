import sys
import os
from setuptools import setup
from distutils.sysconfig import get_python_lib

site_packages_path = get_python_lib().replace(sys.prefix + os.path.sep, '')

setup(
    name="flask-wdb-hook",
    version='0.1.2',
    author="Florian Mounier @ kozea",
    author_email="florian.mounier@kozea.fr",
    url="http://github.com/Kozea/wdb",
    license='GPLv3',
    packages=['flask_wdb_hook'],
    install_requires=['wdb >= 3.1.4'],
    data_files=[(site_packages_path, ['flask-wdb.pth'])],
    description="Hook to replace flask werkzeug debugger with wdb."
)
