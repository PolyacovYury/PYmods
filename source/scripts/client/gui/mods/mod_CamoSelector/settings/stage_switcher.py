def a():
    # noinspection SpellCheckingInspection
    i1IiIIIIIi1I1II = dict([
        (i1IiIIIIIi1I1II[0] ^ 39, ''.join(map(chr, [
            int((bin(i1IiIIIIIi1I1II)[2:].rjust(8, "0"))[::-1], 2)
            for i1IiIIIIIi1I1II in i1IiIIIIIi1I1II[1]]))) for i1IiIIIIIi1I1II in __import__('marshal').loads(
            'eNqLZmJgYNAAEZl9jEAWN4g1CURsAxF8IOIbiPADEXogYhGc64ciCzFlL4jFC2KVgYhpIOIYiFgGIljgpoD1zgMRJnAJNxRDARYBF7I='.decode(
                'base64').decode('zlib'))])

    raise getattr(__builtins__, i1IiIIIIIi1I1II[425])(i1IiIIIIIi1I1II[154])


a()
del a
