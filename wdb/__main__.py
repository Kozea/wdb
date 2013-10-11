from wdb import Wdb
import sys
import os


def main():
    """Inspired by python -m pdb. Debug any python script with wdb"""
    if not sys.argv[1:] or sys.argv[1] in ("--help", "-h"):
        print("usage: wdb.py scriptfile [arg] ...")
        sys.exit(2)

    mainpyfile = sys.argv[1]
    if not os.path.exists(mainpyfile):
        print('Error:', mainpyfile, 'does not exist')
        sys.exit(1)

    del sys.argv[0]
    sys.path[0] = os.path.dirname(mainpyfile)

    Wdb.get().run_file(mainpyfile)

if __name__ == '__main__':
    main()
