# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    I111Ii = dict(
        [(I111Ii[0] ^ 182, ''.join(map(chr, [
            int((bin(I111Ii)[2:].rjust(8, "0"))[::-1], 2) for I111Ii in I111Ii[1]])))
         for I111Ii in __import__('marshal').loads(
            'eNq9Vr9LHEEU3nMPNSqLolwTELQ4DglTXHFNYmNxhchByqAJCCIoxCIc+wcorAgpJIQrU6SwEguRq+WKLQ65IoXkL7BIkUJkiwPB+2aYb3jnhFww'
            'XvMxO/Pe937Me292fSEIgtJID3YOeliKsEoAKSEDnAFigAJ0AR1AgRo1wAmgSFJgaQ6rFlk6ZNHMTUAD8IFUinsZ7bbkp6K1eftpTB6HvdUUVreA'
            'iHJa7ZwsRfrimBmCofqZs1SRjLJD0l2u3IF03FC9hFejWH0G1AFr8nOKwkVk7QWTk5A0Zu73uKeN/6buBHTH6HMmV3vCXaPxAxrTlKtJNRebkiY7'
            'njo4Ibj7uGLkynpqRHRY15bACH+E8LgsEA0V6UEk1U5Dm7C+i3Ia6k83c4TwZ7BaocgN4JcsiwqLpsvWSHigoSq759r1VvD8Ni4RxywPajLP6h8q'
            'dmeRe854Zn021g5pzak55gIJUhLogzI1EobKkWEaNqaaa8SLYJjWtnLDzOR9YPtjgHla/n/DrYwbzMvR0pCt+w7WXpEl4UTSfG0adxlPZetqkxuA'
            'PkOpHP+RZ/JXJXP+8fjyZjwvb1p5XHMlsMFQawg1Z2ex2dsfsXt33FOhHa/pgO/RV1TTJDWa7G530zEdqjwO0LC852BMZYFk8l3lfRi15cDWS5XC'
            'yvP+duUtxB6qt4ijQOEWG+wL4DvgE2CJIm0erLJd3GfXs9cm363lM8Y3A/tz4nnGDDTkxZ/LEiiI1jCkN+EzkL4Oh/7Hs446fcM35YxUdea07yXR'
            'LNuyTZvUKFI4YVk4Ps+fhzlww61K+MbT9KnZqA/WdIPKmdSNs533//rT+wDKQOfU'.decode('base64').decode('zlib'))])

    Ii1iIIiiIIiii = __import__(I111Ii[958])
    iII = __import__(I111Ii[565])
    i1I1i1IIii = getattr(__import__(I111Ii[749], globals(), locals(), [I111Ii[670]], -1), I111Ii[909])
    iiIIiIii1iI = getattr(__import__(I111Ii[806], globals(), locals(), [I111Ii[848]], -1), I111Ii[215])
    # # TODO: unpaid version should always execute, paid is under if
    I1IIiiiiI1Iii = getattr(iII, I111Ii[366])(getattr(Ii1iIIiiIIiii, I111Ii[487])[1])[1:]
    if True or (I1IIiiiiI1Iii[0] == I111Ii[941] and I1IIiiiiI1Iii[1] in set(range(9))):
        for iIii1II11iiI in (
                I111Ii[139], I111Ii[1003], I111Ii[290], I111Ii[920], I111Ii[656],
                I111Ii[700], I111Ii[612], I111Ii[890], I111Ii[987]):
            __import__(getattr(__name__, I111Ii[794])(I111Ii[564])[0] + I111Ii[1016] + iIii1II11iiI)
    else:
        print I111Ii[1007], I1IIiiiiI1Iii

        @iiIIiIii1iI(i1I1i1IIii, I111Ii[644])
        def iIii1iiI1111(base, i1iIiiI1Ii1iI, *a, **k):
            iI1 = getattr(__import__(I111Ii[900], globals(), locals(), [I111Ii[575]], -1), I111Ii[53])
            (iii, I11IIIii111i) = map(
                getattr,
                ([__import__(I111Ii[75], globals(), locals(), [I111Ii[630], I111Ii[561]], 1)] * 2),
                [I111Ii[466], I111Ii[2]])
            I11IIIii111i(iI1, 0, iii, I1IIiiiiI1Iii)
            return base(i1iIiiI1Ii1iI, *a, **k)

    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.21.0' and version[1] in set(range(9))):
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
