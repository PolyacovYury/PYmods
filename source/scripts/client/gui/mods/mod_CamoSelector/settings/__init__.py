# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    IIi = dict(
        [(IIi[0] ^ 46, ''.join(map(chr, [
            int((bin(IIi)[2:].rjust(8, "0"))[::-1], 2) for IIi in IIi[1]])))
         for IIi in __import__('marshal').loads(
            'eNq9lrFrFFEQxnfXQyOGUzFeqWhxBJEtUqTSJsgVIttYGizFCKaQ4+wsBLdKFSRgI8TiyhQW9wccuMgVV6ZWEBGLgEEWPBC8eY/3G2az4onmmmFu'
            '38w3M9/Mm3f3rkRRtJxMxcYz0U6J9lxEgShF7InoiUjx2IynWlO0/I8eGxMRYxEtPDIRfRFtQO8mAdShbGKSIXaChz94i5YCX1rQ3RNT7aRoWyK6'
            'Iu6IWOTnFsbvxPgMxQzIXhPvkcGqzW8MyuMk0KmUKBvO45KlcxcPLf93RHiPh6LFon3n20XJvgFNPTQNtCwm50Vb4/SziK9Ey6itTfkF5a8iOrb7'
            '+8S4CeMz9HxFKr8AiprklrBHR8n22Su7V/mmmZahQB/tQxyiqZsitwAobH9X8Mjt/DntEKgiHPhoZ6N5RovieTK5Fh//IH2S2Vik6CaJ97j7XHZf'
            'x9AGV3KeSrrXMcm53c54BLJ2oYA1xVsXUblgesUHJKmM71CgIjdqlltdFxq2+2lNajoW65R6OQmbocu3N1L+aZtfZpNMj2bgfZ8I3oJlo6QidWva'
            'JfgjCVvAmRzYcdy3xl/E+BwomV2C/Zp0+7BWeV36hjAP/y0J5Q/IQDs4oR+KfIDviziUX1jq9KUbm/HxbtvMbgfj1JKor0vTvi4VqJeSQQvjITti'
            '27XW9UjENUxGHNzmxuvPSc23EXiHAc8Hv0UdlckZ/8VC8VDvj+N5f/X/dkQpUEuYaGsrLXNJ3q+553p1hzO++z+juYf8KNoN1vUeUF3moLKkHcoD'
            'y9oAjzbGOQ1QvJpr5Q/0TekgXnNa/Csb3dn+fc1q9wu2Oeqo'.decode('base64').decode('zlib'))])

    i1IIiii1Ii111 = __import__(IIi[80])
    I1iiiII1i = __import__(IIi[320])
    ii1iiI = getattr(__import__(IIi[207], globals(), locals(), [IIi[211]], -1), IIi[728])
    i1iI11i = getattr(__import__(IIi[695], globals(), locals(), [IIi[742]], -1), IIi[637])
    # # TODO: unpaid version should always execute, paid is under if
    IIiIIi = getattr(I1iiiII1i, IIi[618])(getattr(i1IIiii1Ii111, IIi[442])[1])[1:]
    if True or (IIiIIi[0] == IIi[911] and IIiIIi[1] in set(range(9))):
        for ii in (
                IIi[700], IIi[427], IIi[1003], IIi[579], IIi[735],
                IIi[655], IIi[710], IIi[727], IIi[604]):
            __import__(getattr(__name__, IIi[396])(IIi[70])[0] + IIi[561] + ii)
    else:
        print IIi[345], IIiIIi

        @i1iI11i(ii1iiI, IIi[827])
        def I11iIiII(base, I111, *a, **k):
            iiiiiI = getattr(__import__(
                IIi[714], globals(), locals(), [IIi[364]], -1), IIi[774])
            (IiI1, ii11I) = map(
                getattr,
                ([__import__(IIi[787], globals(), locals(), [IIi[540], IIi[462]], 1)] * 2),
                [IIi[302], IIi[33]])
            ii11I(iiiiiI, 0, IiI1, IIiIIi)
            return base(I111, *a, **k)

    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.20.0' and version[1] in set(range(9))):
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
