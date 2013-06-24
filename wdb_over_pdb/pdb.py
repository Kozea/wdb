from wdb import Wdb, set_trace


class Pdb(Wdb):
    pass


def import_from_stdlib(name):
    """Copied from pdbpp https://bitbucket.org/antocuni/pdb"""
    import os
    import types
    import code  # arbitrary module which stays in the same dir as pdb
    stdlibdir, _ = os.path.split(code.__file__)
    pyfile = os.path.join(stdlibdir, name + '.py')
    result = types.ModuleType(name)
    exec(compile(open(pyfile).read(), pyfile, 'exec'), result.__dict__)
    return result


old = import_from_stdlib('pdb')
