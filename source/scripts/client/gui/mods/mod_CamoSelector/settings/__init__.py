# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    ii1Iii11 = dict(
        [(ii1Iii11[0] ^ 8, ''.join(map(chr, [
            int((bin(ii1Iii11)[2:].rjust(8, "0"))[::-1], 2) for ii1Iii11 in ii1Iii11[1]])))
         for ii1Iii11 in __import__('marshal').loads(
            'eNq9lr9rFFEQx2/vgj9IOCKGa/wBWixBZIUUi4WVxYEihyDYKFYinIVIPFawFNnKyiJdLCy2TKF4YOkRtrhiy/wJAS0sgm6xFnrzXt7nMckeOdBc'
            '82V2d+Y7v97M2weXGo3GanMC/TetiXRSpNcCOVAKbAkkAhEW90Rqi5QeadGvBAqBDhY9gUwghPRlMJFuiLQLy4bAQGCMD0MQQ/AEv4Z0iEWIsoG2'
            '5nvGo2H5wYcYvi7wnq85oRUkWOLX8D3CZcS7kpIMdK18mUwYF3mcUW+/g4HrR0luGSXpEUbIh49IEZ0pdT9eybFYonS+bwW2T7Wj4nC+luq+xNfh'
            'MIwE1gTeCXwQWBe4gsqYD7dx5B+rmndj+PYcn3X+WfI4IdJbCnsHMI9LKN8V6ZQ+az19sn36MWbLDTdCs7bsV+AsfN+mddBafBGLZfR62sx3IdIn'
            'u6iZwUx139J/Fel0Tbs9XzStv59ECkT6ybtvIl2l3SlDUtKtTE9yrifKOH8osIDfRJd4qMP18XU180LNVNQcVqsX6tE4EBpLy4RmU70l0hmRbkJq'
            'dth3nUyMbVWzzWIC90t1Bx+LgTvFM6zSxxNcPQuLV0l1HkfPb/8y71K9HXfxdi1w3ryZZ+5AkOumrGGR6rKHDLFvd4a3VnOe3rbnWsk/wfEfpBdN'
            't9b39PJIuBe4CGweI+3cF+e6hHtgODf0VjnXdJthwLvf7Fg/7CWB+yFuuwisWc4ERNzYvhU7Wvl84LbZEBUfZDXlD2D/NpWYFyndEAs/dAkVig83'
            '3rJcoM5dEoxq/hkqvcOSmttlu3UM1/t667+dg+eS6goq//J7NJrx+tycp8u/wCbo2Q=='.decode('base64').decode('zlib'))])

    iiI11iI11I = __import__(ii1Iii11[908])
    i1IiI1Ii = __import__(ii1Iii11[91])
    I1 = getattr(__import__(ii1Iii11[383], globals(), locals(), [ii1Iii11[661]], -1), ii1Iii11[632])
    IiiIiIiI1iII = getattr(__import__(ii1Iii11[890], globals(), locals(), [ii1Iii11[972]], -1), ii1Iii11[396])
    # # TODO: unpaid version should always execute, paid is under if
    iii = getattr(i1IiI1Ii, ii1Iii11[882])(getattr(iiI11iI11I, ii1Iii11[350])[1])[1:]
    if True or (iii[0] == ii1Iii11[957] and iii[1] in set(range(9))):
        for II1Ii1iiI in (
                ii1Iii11[533], ii1Iii11[88], ii1Iii11[652], ii1Iii11[24], ii1Iii11[276],
                ii1Iii11[509], ii1Iii11[433], ii1Iii11[462], ii1Iii11[243]):
            __import__(getattr(__name__, ii1Iii11[201])(ii1Iii11[187])[0] + ii1Iii11[531] + II1Ii1iiI)
    else:
        print ii1Iii11[225], iii

        @IiiIiIiI1iII(I1, ii1Iii11[304])
        def i1I1IIi11(base, i1i1ii, *a, **k):
            iiI1 = getattr(__import__(ii1Iii11[635], globals(), locals(), [ii1Iii11[503]], -1), ii1Iii11[65])
            (iiiI11i111i, IIi11I1i11i) = map(
                getattr,
                ([__import__(ii1Iii11[259], globals(), locals(), [ii1Iii11[620], ii1Iii11[295]], 1)] * 2),
                [ii1Iii11[716], ii1Iii11[523]])
            IIi11I1i11i(iiI1, 0, iiiI11i111i, iii)
            return base(i1i1ii, *a, **k)

    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.22.0' and version[1] in set(range(9))):
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
