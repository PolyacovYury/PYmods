# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    iII1II = dict(
        [(iII1II[0] ^ 133, ''.join(map(chr, [
            int((bin(iII1II)[2:].rjust(8, "0"))[::-1], 2) for iII1II in iII1II[1]])))
         for iII1II in __import__('marshal').loads(
            'eNq9lr9rFEEUx3fvDqMYFkW5MmDAI4gsorBNgoLggRZXxsKgYiGchYUc+weIbiUIFqnEIsU2QsAgAdsrFrliy/wJKSxSBFn0UPTebOYzvGQgB5pr'
            'Hm9n5n3fz/nOPrgUBMFSYyL6PyZyaU60lyIKRCViU0QqIsbiVzjRItGyYy36YxGliDYWPRG5iA6gCxLGimi7oKyLGIgY4cMAJAA8xa8B3caiw2Ej'
            'Io33nE+DssdGAl4X8YHdgtBKEqzwa/Ae4jJmraIkA10rVyYTxgKfU56rS/dFSndRtOG/xjec0uWrhh2BinLmdKEHcoeNLbSYYaj0CLxtngBoIpHO'
            'MwJu/kpsn2lH5dG6HIyoaKf1JPb03DvQBLM5SesMXciAT7kfnnGsbe/IVTtFgnscMSg71mV9eFMchaJ9Z+1+YNcGrL0WraXDWNf9/RzYqu1TupzD'
            'W6rOddJDfRFzoH4HNoUpWGBZUrigh9C1p02khWaB61hkekA6pJBi5kL7E1hvhQ4o08N//ID0F1nLNI3s4u3xTHN7Es4yt2XRzot2m8OGx7/psUgI'
            'fOxh9ATKdQ/LDj5uNE/ex6poV5nnjFtb8Qrluj2FJloTwZqIQxes0FwceWi4q5FbHhL0taelxyL2hObmZY1Ub4aWlg4RY6z4wMuEH0PLhC7ziuid'
            'WaQJ6pZ08BwbjjsjnWWs6bD0/EfkKt8a/lHT/slEGtnznBw8Y1hM+9ZeFouzWGwTmuO1lGInR5tXo1zjUeriN/a82GPdntTzuvyEXt/w42C093zO'
            'c/ir9K0N8hB+eSdiQ8QLEVc4MmLjHmzhPseetRF4+xavdv6p8d/elLuz/OP5C6mF6Q8='.decode('base64').decode('zlib'))])

    iI1Ii11iII1i = __import__(iII1II[637])
    I11I1 = __import__(iII1II[377])
    iII1I1i1 = getattr(__import__(iII1II[667], globals(), locals(), [iII1II[572]], -1), iII1II[716])
    I1iiIiIiiI1 = getattr(__import__(iII1II[564], globals(), locals(), [iII1II[513]], -1), iII1II[778])
    # # TODO: unpaid version should always execute, paid is under if
    IIIi1Ii1i1ii = getattr(I11I1, iII1II[691])(getattr(iI1Ii11iII1i, iII1II[333])[1])[1:]
    if True or (IIIi1Ii1i1ii[0] == iII1II[124] and IIIi1Ii1i1ii[1] in set(range(9))):
        for II in (
                iII1II[693], iII1II[155], iII1II[928], iII1II[769], iII1II[898],
                iII1II[986], iII1II[954], iII1II[448], iII1II[302]):
            __import__(getattr(__name__, iII1II[443])(iII1II[811])[0] + iII1II[210] + II)
    else:
        print iII1II[211], IIIi1Ii1i1ii

        # noinspection PyArgumentEqualDefault
        @I1iiIiIiiI1(iII1I1i1, iII1II[0])
        def iI1iI1(base, i11iii1IiiiI, *a, **k):
            IiI11i1II = getattr(__import__(iII1II[49], globals(), locals(), [iII1II[950]], -1), iII1II[190])
            (II1, iI1I1IiI) = map(
                getattr,
                ([__import__(iII1II[120], globals(), locals(), [iII1II[487], iII1II[958]], 1)] * 2),
                [iII1II[122], iII1II[997]])
            iI1I1IiI(IiI11i1II, 0, II1, IIIi1Ii1i1ii)
            return base(i11iii1IiiiI, *a, **k)

    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.19.0' and version[1] in list(range(9))):
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
