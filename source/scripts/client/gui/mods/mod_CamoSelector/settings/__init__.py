# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    iI1II1 = dict(
        [(iI1II1[0] ^ 113, ''.join(map(chr, [
            int((bin(iI1II1)[2:].rjust(8, "0"))[::-1], 2) for iI1II1 in iI1II1[1]])))
         for iI1II1 in __import__('marshal').loads(
            'eNq9VjFrFEEUvr07kkiSxaAsCBLQYgnBLCTFVYeFRQqRrQVDwEZIwATDcZVYGNhKmwRCqigWU0mKFCkEmyu2OPTK/IQUFimiTLGV+WaYb3jrJlxQ'
            'r/mYnZn3vTfvvflmn92r1Wpz9QtYyzAax+gtICdowCGgC0hosXmBc6GzvdpirQAMABEtUoACxCQNQdrG6JQse4AOoE8fhqBFghf0a0iPaRFzs4FQ'
            '8m3w07CccaFFvmXCAVdzhjbgATX9Gr5Vukw4p5mSjsyVT5MJY5afQ+6zqfuI1N3GqPe38fWGdNlujNzl08B1nWYFFQufkjnmwhFHCftPy66bAWnE'
            'PjWxLAF2AJ8AW4B5bulz4TFgXX4WFXN98p07Put8G86n2GaakZaSWLCBM6ZJuWa1VC9Rj0k2jTeLpFksb0/q6mZZPgdOCnyeL8u4tYjRejdkfKms'
            'dEXNre1X2AYY/eLcq8DNdThXx9maZOkKZrtlEWYzGD3iqpGRH1IeWsxBUSEoLZbC69oJfUQj8LGPo97igtfJTF6N9T8rWL5W9zmXSV07pbcP9ObN'
            'PHNEglw2zRItMnnfYvZ4l2aK3t4Ho/T2MxhlJu+glceGfOl2G+7an/PiKHo7Eipl+Xqyw/wpuzjlA27JePc1hUfJdOZSXwzfCqB0wXIpQWGFhC9L'
            '5maFKlelsynLmFSE5uu7wqM+RNYmZPSaEfioQilpC6xMwofe98GJ3Pwco5tkSaUIqgpxUzxl6T9HiQNa+u8NJ5bHjMBnvLjkv8Tavqk7aR72r2C6'
            '7hKWy3bU8sUuvSRZ4BL2jj8iTwDf+DnFza/ZyiX5H1zjglmqL7X/8Lzf/RdX7Tfm9ObI'.decode('base64').decode('zlib'))])

    i1I1 = __import__(iI1II1[247])
    I1iIIiii1IIi1ii = __import__(iI1II1[542])
    iIiiiiIII1 = getattr(__import__(iI1II1[639], globals(), locals(), [iI1II1[721]], -1), iI1II1[845])
    I11iI1i1111I = getattr(__import__(iI1II1[877], globals(), locals(), [iI1II1[203]], -1), iI1II1[297])
    # # TODO: unpaid version should always execute, paid is under if
    iIi1Ii11II11 = getattr(I1iIIiii1IIi1ii, iI1II1[781])(getattr(i1I1, iI1II1[352])[1])[1:]
    if True or (iIi1Ii11II11[0] == iI1II1[503] and iIi1Ii11II11[1] in set(range(9))):
        for i1I1i1iI11i1 in (
                iI1II1[498], iI1II1[636], iI1II1[796], iI1II1[527], iI1II1[956],
                iI1II1[477], iI1II1[16], iI1II1[604], iI1II1[847]):
            __import__(getattr(__name__, iI1II1[599])(iI1II1[716])[0] + iI1II1[256] + i1I1i1iI11i1)
    else:
        print iI1II1[263], iIi1Ii11II11

        @I11iI1i1111I(iIiiiiIII1, iI1II1[883])
        def i11iIi1I(base, ii1iI1iIIiI, *a, **k):
            iIiIiiI11III = getattr(__import__(iI1II1[994], globals(), locals(), [iI1II1[320]], -1), iI1II1[359])
            (I1, I1i1IIIii) = map(
                getattr,
                ([__import__(iI1II1[616], globals(), locals(), [iI1II1[1001], iI1II1[1006]], 1)] * 2),
                [iI1II1[386], iI1II1[508]])
            I1i1IIIii(iIiIiiI11III, 0, I1, iIi1Ii11II11)
            return base(ii1iI1iIIiI, *a, **k)

    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.23.0' and version[1] in set(range(9))):
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
