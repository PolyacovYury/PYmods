# noinspection SpellCheckingInspection
def a():
    iI1I1Ii1iI = dict([
        (iI1I1Ii1iI[0] ^ 161, ''.join(map(chr, [
            int((bin(iI1I1Ii1iI)[2:].rjust(8, "0"))[::-1], 2) for iI1I1Ii1iI in iI1I1Ii1iI[1]])))
        for iI1I1Ii1iI in __import__('marshal').loads(
            'eNqFky9PxEAUxNuS8CdcCoSkQSEvBFGB4BuAQJxD8QHIIRBw6QdAoAgCcXhIKpFnUCAqLqSS4AjBnyCXE1XctNnf8sgRzGR2'
            '+2be7rzt0VoQBFvRFLr3c1O2IHYhKICJ4EGQCVIU11LEYpf/KrqVoBQkKDqCXNDG9EmmLbHY1pUUn8D8hz59M6zWZZXQ'
            '/FmwI7gR3AnOBNuUDPlwQCO/rGbsDfH7cn5N8ys1n6+ZoAd7Ydmi'
            '+D10l97nHilQLwecwOeSEcQuVoeMsTCRNFZ18aYd40fkFDEKz05N2I1iRcddpa5jZX4yKZPJGdSvd5AD/kDnkYuuNhhRUl'
            '/61Rk0xW8qXrRZTVwkP04QW9mx2NKMZ+YV6V/vak8Rh2Jj9jYit9dj75MeA3r0mUdFuj6hEdpH+S0zRj/9xE6/zVXtD9G43IYunMLe0v+hpXlD3y'
            'f+qy8='.decode('base64').decode('zlib'))])
    I1II1 = __import__(iI1I1Ii1iI[770])
    iiiI1i = __import__(iI1I1Ii1iI[815])
    # # # TODO: unpaid version should always execute, paid is under if
    if True or getattr(iiiI1i, iI1I1Ii1iI[864])(getattr(I1II1, iI1I1Ii1iI[946])[1])[1:] == (iI1I1Ii1iI[813], 1):
        for iIII in (
                iI1I1Ii1iI[382], iI1I1Ii1iI[310], iI1I1Ii1iI[538], iI1I1Ii1iI[1012], iI1I1Ii1iI[66], iI1I1Ii1iI[576],
                iI1I1Ii1iI[430], iI1I1Ii1iI[722],
                iI1I1Ii1iI[633]):
            __import__(getattr(__name__, iI1I1Ii1iI[198])(iI1I1Ii1iI[996])[0] + iI1I1Ii1iI[697] + iIII)
    else:
        print 'CamoSelector: incompatible version detected'

# import Account
# import account_shared

# # # TODO: unpaid version should always execute, paid is under if
# if account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:] == ('1.13.0', 1):
#     for name in (
#             'bottom_panel', 'carousel', 'cm_handlers', 'context', 'main_view', 'popover', 'properties_sheet', 'tweaks',
#             'tooltips'):
#         __import__(__name__.partition['/'] + '.' + name)


a()
del a
