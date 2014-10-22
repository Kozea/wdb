from wdb import Wdb
import argparse
import sys
import os

parser = argparse.ArgumentParser(description='Wdb, the web python debugger.')
parser.add_argument('--shell', dest='shell', action='store_true',
                    help='open a debugger shell only.')

parser.add_argument('file', nargs='?', help='the path to the file to debug.')
parser.add_argument('args', nargs='*', help='arguments to the debugged file.')


def main():
    """Wdb entry point"""
    args = parser.parse_known_args()[0]
    if args.shell:
        Wdb.get().shell()

    elif args.file:
        if not os.path.exists(args.file):
            print('Error:', args.file, 'does not exist')
            sys.exit(1)

        del sys.argv[0]
        sys.path[0] = os.path.dirname(args.file)

        Wdb.get().run_file(args.file)


if __name__ == '__main__':
    main()
