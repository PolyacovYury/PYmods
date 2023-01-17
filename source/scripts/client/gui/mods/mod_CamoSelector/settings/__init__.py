# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    iII1I = dict(
        [(iII1I[0] ^ 166, ''.join(map(chr, [
            int((bin(iII1I)[2:].rjust(8, "0"))[::-1], 2) for iII1I in iII1I[1]])))
         for iII1I in __import__('marshal').loads(
            'eNq9lr+LE0EUx3eT4A9OVsUzhYWiRQgiiyiszRUimMIiYCfcYefhXXGChC0EQSy2srIQBLGw2NLCItjYpNgixTbC/QVyoIXFIQtudXk7zmd4ccSI'
            'mubxdmbe9735zpvv7Pr5IAj6rZnZ2gxn3mHxnoopMJWYt2JSMTERZ9ozLxIv+23EVi2mFNMlYigmF9MD9Kt4a+LtgfJCzEjMlBwNQALAJnkb0DER'
            'PRY3JtJ4O3zmNrmZSMAbYF4zW1BayQYr8jZ4d0kZM1ZByUhz5WhqyjjL54LrDHXXZ7a/Kt7kb+ubLJjyQcu2QAWdOacwBLnHxDu8mGaodAt8F9BD'
            '4j2Dg8Z7pT7N4s/iHdFtMdRNWJIyIey0eCuEjWlR150phSd6WyUoY+7MomfUFH6CTnSVRjpHrBuz9FyhXDFp4C+Hlg135hVbcKCR3sdNYfwoE5mn'
            'DE+XmNhrogKheN8Ye8TYiLHHkqMDSqqQzZJPsuSYePuakpTOoVUMERN97XOg3ksFJ8W7QaJGUL7oiAS82iMtCXffKdwuOdIl5JCx/indXNvw0iVv'
            'ofv0ChGZvn492E0Jc6xdbdlshdbnTDf19s8XYl5BLjCWaT3dI9tKe5l7e9le5t7uoWELvHkfZfEl+jlDkSrevFxzUOgr3oBuiJm7YIVW/sgj+gON'
            '3PHouI+DjuY+9pTmDmWDrd4PLS8xD647hV0tS3cCK6+R1knPY2MidkIrZGNAHRv1L558E3s7sOozIEfseT5rzWTqeV0+yIF2WTyhbZ+LeSPmoZiL'
            'LJkycYsmdJ+1Z2wK3r7F+yHmod3HnJiXf9DjBurJ/3jej/87lT/XXuIfzwHbAOjM'.decode('base64').decode('zlib'))])

    iI11I = __import__(iII1I[448])
    I11111i = __import__(iII1I[956])
    iI111111i1iIii = getattr(__import__(iII1I[72], globals(), locals(), [iII1I[742]], -1), iII1I[953])
    I1111II1 = getattr(__import__(iII1I[681], globals(), locals(), [iII1I[713]], -1), iII1I[550])
    # # TODO: unpaid version should always execute, paid is under if
    iI1iI1ii1IIiIIi = getattr(I11111i, iII1I[483])(getattr(iI11I, iII1I[539])[1])[1:]
    if True or (iI1iI1ii1IIiIIi[0] == iII1I[607] and iI1iI1ii1IIiIIi[1] in list(range(9))):
        for IiiI11I11 in (
                iII1I[247], iII1I[79], iII1I[179], iII1I[272], iII1I[456],
                iII1I[254], iII1I[42], iII1I[462], iII1I[406]):
            __import__(getattr(__name__, iII1I[739])(iII1I[913])[0] + iII1I[988] + IiiI11I11)
    else:
        print iII1I[629], iI1iI1ii1IIiIIi

        # noinspection PyArgumentEqualDefault
        @I1111II1(iI111111i1iIii, iII1I[731])
        def Iii(base, i1Iiii, *a, **k):
            ii1i1I = getattr(__import__(iII1I[578], globals(), locals(), [iII1I[798]], -1), iII1I[976])
            (II1Iiii1II, IIiIi111II1i) = map(
                getattr,
                ([__import__(iII1I[707], globals(), locals(), [iII1I[831], iII1I[32]], 1)] * 2),
                [iII1I[661], iII1I[941]])
            IIiIi111II1i(ii1i1I, 0, II1Iiii1II, iI1iI1ii1IIiIIi)
            return base(i1Iiii, *a, **k)

    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.19.1' and version[1] in list(range(9))):
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
