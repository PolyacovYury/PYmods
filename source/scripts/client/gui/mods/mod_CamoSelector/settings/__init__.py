# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    I11IiII = dict(
        [(I11IiII[0] ^ 210, ''.join(map(chr, [
            int((bin(I11IiII)[2:].rjust(8, "0"))[::-1], 2) for I11IiII in I11IiII[1]])))
         for I11IiII in __import__('marshal').loads(
            'eNq9lj2LFEEQhnd2Dj/wHBV1Q0GR4RCZ4IKJjAxWMNg/oBipsBcYnOf+AIOJjAwuERQURlQwuGBBEMENVlhwwMAD/8AFchgcMsFg4Fa3/TR19nEL'
            'npu8VH/UW9VV1dV943yr1VpqT6H/KppKh0V6KDAGaoG3AgOBDI338VRKRCr21eg3ApVAB42eQCmQQnpW3Lgi0hYs6wJrAhNsGIIcgrvYNaRDNFI2'
            'G0g03z2GhuUHCzl8XeApq2NcqzhgjV3DdwuTGXM1IVnTsfJhMm6cYzjjPhu6JyKdEWn0r/6NZjT5a4pLiyLtEN0StQ1YUnwZ6USVUL1uu2qqyUzJ'
            'vh5OpixsIGXUVa2rSVw7cNLbLXfoRJdyhe6KNlT9HeI/V0ikDvfDBGdZ4LHAc4FVgUtsmbBwHUN+2ATmJvDtOD5r/EXsztHFtSxQL40+6oCz5VDd'
            'l+Qd0Zezp1tBFVA7IZf9JPReI9Hxy/Q1rQINpVR5s/Qf8MqfqOZ2e9LEUVm1z6J2NJBfr5HtldA3EtPL5LIgiDWpKHXnGmv/jKGbAgvYGOguMNSu'
            'eV+6mnkhUPKBSrT7Ul33u1yjSRvX7FFXJHm7nFzXCfgYH1h7uCjWTol0FUPmhfiuNXL4msBbkRMm/2RtYuOZ2DjNgn+eCh2I/W93/wJzhX5OtrB2'
            'PJ6nNekq1ppX88wdCMa6hpbRKHSVpGTVV6fP1mp7ntZeinRoxg/Gu/b/L6RvIkXuAbdzXyI395O5buQcz/h++BLY1G3pKx+0RPfJwNNmNR7QyIaQ'
            '+rva7PEBsrqfYmdt1u/HHdE4hoZ/Ojr66Uh1znv6lNuE5BEfICNtM1xk87Vojj+e30iG66E='.decode('base64').decode('zlib'))])
    II11iIiI1iII = __import__(I11IiII[379])
    Ii11iIIiiIii = __import__(I11IiII[878])
    I1I1iiIi = getattr(__import__(I11IiII[455], globals(), locals(), [I11IiII[405]], -1), I11IiII[73])
    i1i1i = getattr(__import__(I11IiII[558], globals(), locals(), [I11IiII[632]], -1), I11IiII[222])
    # # TODO: unpaid version should always execute, paid is under if
    iiiiIi = getattr(Ii11iIIiiIii, I11IiII[182])(getattr(II11iIiI1iII, I11IiII[110])[1])[1:]
    if True or (iiiiIi[0] == I11IiII[318] and iiiiIi[1] in list(range(9))):
        for IiI in (
                I11IiII[881], I11IiII[673], I11IiII[951], I11IiII[789], I11IiII[679],
                I11IiII[263], I11IiII[477], I11IiII[404], I11IiII[620]):
            __import__(getattr(__name__, I11IiII[543])(I11IiII[259])[0] + I11IiII[11] + IiI)
    else:
        print I11IiII[889], iiiiIi

        # noinspection SpellCheckingInspection,PyArgumentEqualDefault
        @i1i1i(I1I1iiIi, I11IiII[440])
        def I1i11I(base, iiiiI11i11ii1I, *a, **k):
            I1I11 = getattr(__import__(I11IiII[787], globals(), locals(), [I11IiII[619]], -1), I11IiII[502])
            (I1111i11II, IiI11ii) = map(
                getattr,
                ([__import__(I11IiII[117], globals(), locals(), [I11IiII[333], I11IiII[672]], 1)] * 2),
                [I11IiII[991], I11IiII[224]])
            IiI11ii(I1I11, 0, I1111i11II, iiiiIi)
            return base(iiiiI11i11ii1I, *a, **k)
    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.17.0' and version[1] in list(range(9))):
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
