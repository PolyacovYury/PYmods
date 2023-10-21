# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    Iii1i = dict(
        [(Iii1i[0] ^ 108, ''.join(map(chr, [
            int((bin(Iii1i)[2:].rjust(8, "0"))[::-1], 2) for Iii1i in Iii1i[1]])))
         for Iii1i in __import__('marshal').loads(
            'eNq9ljFoFFEQhjd7h1GUxaBsYRHQYhGRLVJcZWVxhUrQSsRgJcJZWMhxVqIobGVlETsFhQUhpBC53ihbpDi7lHZaWKQIsshhYeY93jfMseKC5pqf'
            'uffe/P/MvHmzd/N0FEVn430Y3F7YtxKxCoEKqAU2BUYCucBUYCKQ4rEqUApkkF4U65hYewIJRxzVO+gz+LZYg89T3SA+t3sPqlVgHaoS+pKYU6Pm'
            'ST8fBOnbTkg6scWZ4HvXCk0QqkNxPNV7oUqpuCvOisBzgdcC9wXOcWSbjUsI6c9pw9o2fHuBz4tfjkMefULLAfdzDKmmOiK3HlSnhOowLaUl0eaa'
            'NLg9les5ipuqpVYtC24zNfUsX0T8SMN95JQ9/9MFfBJrQawfrD1kbcjadYn0BJHqWyigb3nxgzOsFaTldr+h1kVN3ZQ5haCydVnBo7BNnXH7I9z0'
            '5b3pzFNtOZpnJTekkodaTrMHUoilMNc8s1ANvtuh1SPLqW35HtC3g3YHjV/xwWs86vy3qfxCrC6RjsyL8keWRO08LAUvuWb6lLZzKjtknOSa63sr'
            'VNk5lNguWacGytxtmPJNndO1HZs3hKatvEaqj6Mw5jT6mgg0qsQOqI80oTuya1t+xx6+KtZxWHSKJjYtVSvJcuazXZoEPf1XsRbhq61lS+c9eozX'
            'MTHrHU1x01h28V3sBLXKXoCWeNnG9zMOtXoWJvDgCjAMG/7wKynsSVpPvzMzXzAX2q2G9tGAtlrGtxHPXfKaZHmBQbEJ1ZAHNjMeHMsd+8DGeGQc'
            'Lrh95Wu4S7+h47UPvGS3+tdqDNt1SdtzvnQf6L8nf/3T+xu1R+oF'.decode('base64').decode('zlib'))])

    iI1ii = __import__(Iii1i[941])
    i1Ii = __import__(Iii1i[264])
    II11i = getattr(__import__(Iii1i[317], globals(), locals(), [Iii1i[704]], -1), Iii1i[499])
    I1iIIi111II1 = getattr(__import__(Iii1i[46], globals(), locals(), [Iii1i[309]], -1), Iii1i[419])
    # # TODO: unpaid version should always execute, paid is under if
    I1Ii1i1i1i1iI = getattr(i1Ii, Iii1i[965])(getattr(iI1ii, Iii1i[984])[1])[1:]
    if True or (I1Ii1i1i1i1iI[0] == Iii1i[660] and I1Ii1i1i1i1iI[1] in set(range(9))):
        for i1Ii1iIiiIi in (
                Iii1i[551], Iii1i[630], Iii1i[495], Iii1i[875], Iii1i[602],
                Iii1i[137], Iii1i[60], Iii1i[431], Iii1i[236]):
            __import__(getattr(__name__, Iii1i[690])(Iii1i[168])[0] + Iii1i[17] + i1Ii1iIiiIi)
    else:
        print Iii1i[893], I1Ii1i1i1i1iI

        @I1iIIi111II1(II11i, Iii1i[251])
        def IiiII1iIIiIiii1(base, IIii1iiI1i, *a, **k):
            i11i1I1i1i1I1ii = getattr(__import__(Iii1i[787], globals(), locals(), [Iii1i[656]], -1), Iii1i[795])
            (IIi1iiI1III, i1III) = map(
                getattr,
                ([__import__(Iii1i[448], globals(), locals(), [Iii1i[315], Iii1i[360]], 1)] * 2),
                [Iii1i[114], Iii1i[975]])
            i1III(i11i1I1i1i1I1ii, 0, IIi1iiI1III, I1Ii1i1i1i1iI)
            return base(IIii1iiI1i, *a, **k)

    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.22.1' and version[1] in set(range(9))):
    #     for name in (
    #             'bottom_panel', 'carousel', 'cm_handlers', 'context', 'main_view',
    #             'popover', 'properties_sheet', 'tweaks', 'tooltips'):
    #         __import__(__name__.partition('/')[0] + '.' + name)
    # else:
    #     print 'CamoSelector: incompatible version detected:', version
    #
    #     @overrideMethod(CustomizationContext, 'init')
    #     def new_init(base, self, *a, **k):
    #         from OpenModsCore import BigWorld_callback
    #         from .shared import createVersionDialog, onVehicleLoadedOnce
    #         onVehicleLoadedOnce(BigWorld_callback, 0, createVersionDialog, version)
    #         return base(self, *a, **k)


f()
del f
