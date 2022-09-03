# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    iIi = dict(
        [(iIi[0] ^ 17, ''.join(map(chr, [
            int((bin(iIi)[2:].rjust(8, "0"))[::-1], 2) for iIi in iIi[1]])))
         for iIi in __import__('marshal').loads(
            'eNq9Vj1rFFEUnd1ZYsSwRCJjEwQthhDCFCkWAlYWK4hMYxlRixDIFhayBNKmGFKkSrFgY5FimkAICvsDVphIhAWbFDZ2FhYpgkwxEMie93zncocJ'
            'WdFsc7g7791zv+/b1Yee5y3UR7DxGtItSNuAjJADDgGbgIgazdpIakJKrtXYKABDQECNGJACQpIejXDhHqQBWYZkMcx9QA/wilQRv+W0O9A/I1p7'
            'oOP45o+kGUjnJizeM2ofyRLSF2FmCJbqPlNiTt+SKib0SJWSPqV/gbL2J89IScAkGuPLgD3APuAdYJFXTnjwDNDRP4uKbyfkO3d81rhJ0xSkXUCX'
            '0jx/zvDye89lss04ooriFcxzwjybHLRItY9MTrOlpF9y3RYltY7vuliqcFU9rMax7wI0Tp7xijF56gzZy59RipqL3H77CmmJlUkYZc7E0kkrZTol'
            'JqyXgAYbZFMPU18nTLq9rZkbFV03rBiNhm7CqMI1zqVxzYb6CeHfhfSEpD8Bv3QwLeoWuoItQlvvjVPaWEHh53gQ63qIa53ro3zEb2I8dz5baz8m'
            'au0LrYmaMAckyHRVl6mR6LqFHFjpF1lGq94krb3gHI2x5d/Ubr6RBvX/ttafQioNZ08/IvO+2wy/+e0CHtzWoxvr+a14t6zuVt3tP1kUOYMWtaZe'
            'UNNI7CwPYr0E0woPUoZfeqJTtR4s/Y7vIuozIklJwe0jzGfU/V53qzkb82F+DukONeTpCPTTEeoGjnVK5tgHpSoM/2K6LdXaTTzvB5P/x3MM6TGH'
            '7pBUXT5ZpVEzLOt6PvrUCHk5YZ6Fr6Ij7IGsyDbhA0+zf81Gd7xeG/feJe9Q6Qw='.decode('base64').decode('zlib'))])

    IIi = __import__(iIi[78])
    I111i1IiI1i = __import__(iIi[287])
    IIi11IiIi1i = getattr(__import__(iIi[214], globals(), locals(), [iIi[673]], -1), iIi[698])
    I11 = getattr(__import__(iIi[960], globals(), locals(), [iIi[262]], -1), iIi[373])
    # # TODO: unpaid version should always execute, paid is under if
    iiIiiiIIii = getattr(I111i1IiI1i, iIi[514])(getattr(IIi, iIi[543])[1])[1:]
    if True or (iiIiiiIIii[0] == iIi[63] and iiIiiiIIii[1] in list(range(9))):
        for Ii in (
                iIi[136], iIi[435], iIi[93], iIi[715], iIi[921],
                iIi[891], iIi[281], iIi[982], iIi[616]):
            __import__(getattr(__name__, iIi[748])(iIi[781])[0] + iIi[722] + Ii)
    else:
        print iIi[218], iiIiiiIIii

        @I11(IIi11IiIi1i, iIi[86])
        def i1iII1iI1iiIii1(base, Ii1, *a, **k):
            IiI1III1 = getattr(__import__(iIi[723], globals(), locals(), [iIi[369]], -1), iIi[674])
            (I1iIii1iI1I, I11iIii11I111i) = map(
                getattr,
                ([__import__(iIi[834], globals(), locals(), [iIi[296], iIi[74]], 1)] * 2),
                [iIi[462], iIi[473]])
            I11iIii11I111i(IiI1III1, 0, I1iIii1iI1I, iiIiiiIIii)
            return base(Ii1, *a, **k)

    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.18.0' and version[1] in list(range(9))):
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
