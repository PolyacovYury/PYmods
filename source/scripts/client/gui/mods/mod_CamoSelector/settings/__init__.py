# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    IIi1ii1i = dict(
        [(IIi1ii1i[0] ^ 21, ''.join(map(chr, [
            int((bin(IIi1ii1i)[2:].rjust(8, "0"))[::-1], 2) for IIi1ii1i in IIi1ii1i[1]])))
         for IIi1ii1i in __import__('marshal').loads(
            'eNq9Vj1II0EU3k2CP5wsipJKlLMIQWRFwXCFlUjgUlic5cmVB7GwkLCFnRZbCYJIGsHCIiAHKVLE3mIFi5SprrLw4IoT5Fi4VJdvx'
            '/nGF9cY0KT5mJ2Z931v3nvzZr9+tCwrm2hDcQ8jByMfEBBCQBXgAVxAC9AApGmxAagAMiS9sNujKYyuyNIgS8RcB5QB30jlci6k7pX8dKk2oz'
            '+V5Gdr4JKzOOUYRo6MRoMW2xyZBammqPYxSjPEkQfLgGPAOWAXMM8tN1woUMh8tmLmbsj3oPmU+L82Zj8w8XUSmCR7Or'
            '/F3PMTKRYfLMOyfLrH7wQWo5T0GRyPHuxwLiL4Q9sVW9t2xN4k1H0p2OvQTUm1snRtKalT+0CNCjfXSJphVk3R8EIoqlN4OoHRGoXuAL'
            '+lRY58LQbR50IEeXlNm9S4hcYkF8yV9GUCXi/H4hznjHiofVZqcwmtZswMc5oEgayXZVr4PCr7hoqzRzMTv+uBqv1IDjKSmzjbUI9NdTbR'
            '/0L6iUJaYD37vJwhO0hFxjmQPTbyYAvQccEC2YadmA6cl8wpNoDucU7J/LoxrpnEb/GoVYTTxqjEuV+2nvvLuQL2jchThvTUeO'
            '/Idnhv69S6unM9KaSm3IwMZsfJskENRx7fle2wEfMmV0QgFP1RUrdmRzKHz0OsLNZsfehA1mQoH1cWw+NLwhcxz81uzCPckiXgxVAtWjp'
            '+hzpHajQtPtXmS/7ExJxIQVlWSU3WS1p0dEU6newD6Rf73R4WvNjZVXaBKh0q8a523P1I6Lvkq9Miw80+XTN8MS+xWjB9LU8442rw1p+xUm9'
            '/FL3uU6H7xAtx8OpP738gyum2'.decode('base64').decode('zlib'))])

    II1I111iiII1I1 = __import__(IIi1ii1i[813])
    II1 = __import__(IIi1ii1i[111])
    iii1 = getattr(__import__(IIi1ii1i[30], globals(), locals(), [IIi1ii1i[444]], -1), IIi1ii1i[92])
    iiIiiiI = getattr(__import__(IIi1ii1i[327], globals(), locals(), [IIi1ii1i[777]], -1), IIi1ii1i[162])
    # # TODO: unpaid version should always execute, paid is under if
    I1i1111 = getattr(II1, IIi1ii1i[266])(getattr(II1I111iiII1I1, IIi1ii1i[148])[1])[1:]
    if True or (I1i1111[0] == IIi1ii1i[58] and I1i1111[1] in list(range(9))):
        for IIIiIIIii1II in (
                IIi1ii1i[492], IIi1ii1i[343], IIi1ii1i[748], IIi1ii1i[659], IIi1ii1i[641],
                IIi1ii1i[922], IIi1ii1i[255], IIi1ii1i[506], IIi1ii1i[607]):
            __import__(getattr(__name__, IIi1ii1i[288])(IIi1ii1i[498])[0] + IIi1ii1i[699] + IIIiIIIii1II)
    else:
        print IIi1ii1i[457], I1i1111

        # noinspection PyArgumentEqualDefault
        @iiIiiiI(iii1, IIi1ii1i[593])
        def i1iIIi11iIiI(base, ii11111II, *a, **k):
            iI1i1Ii1 = getattr(__import__(IIi1ii1i[804], globals(), locals(), [IIi1ii1i[398]], -1), IIi1ii1i[522])
            (i11I11iii, i1Ii1ii) = map(
                getattr,
                ([__import__(IIi1ii1i[582], globals(), locals(), [IIi1ii1i[503], IIi1ii1i[567]], 1)] * 2),
                [IIi1ii1i[958], IIi1ii1i[722]])
            i1Ii1ii(iI1i1Ii1, 0, i11I11iii, I1i1111)
            return base(ii11111II, *a, **k)

    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.18.1' and version[1] in list(range(9))):
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
