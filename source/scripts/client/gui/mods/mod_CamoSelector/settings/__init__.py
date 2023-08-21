# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    i1IIII = dict(
        [(i1IIII[0] ^ 174, ''.join(map(chr, [
            int((bin(i1IIII)[2:].rjust(8, "0"))[::-1], 2) for i1IIII in i1IIII[1]])))
         for i1IIII in __import__('marshal').loads(
            'eNq9VjFLHEEUvtuTqBgWRb1KBFMsQcKCVywIqSwuYORsYpXExhC4FBcIx/2ACFtdmhQHRrAIZMsUFiephCu2uGLB5vIPLEQCkbDFVrlvhv2Gp3vc'
            'gec1H29n5n3fmzdv3uzrtVwu99TqQ/Wg0LemYX0GhIQY8BPQALj0eA7LhuUP9agmgAhQpEcFEAAckh7n+xaYq5dkaQHqgC41FIFHgvfUVaRtejhc'
            'rMCWfDV+KpY/nPDIVyaccDZkaBE3GFNX8e1T0uVYzJTUZa5MmlQYq/wccZ1O3TVStwSrc9/4OiNKepOXfAHrMawbHmhAt1OyOIylI2sjINVvK6Wy'
            'ZU1GJP1Ay0zIwDXVXySiyEJXkiXAV8B3wCfAOpd0ObFNIfOZZIx1yXeT8mnxQ1zdR7CaLJod+dnk4nNseo511aaauZcN5s+7u33NErFbjFqdH63U'
            'w6aHsWpCSHtswmOe6yrSzUTlykscZbSbgGAC+sWsubz7AXPQk/v9AWtGVnbMDJkIbOn2FmUxm1FhxsMdVFLvYD1jNfk8rZjFEMgzCmV8SugNYIoa'
            'DXlkbRmaiaUsmafunlHWXdDrHJHs26Gx36vQ9FZfIk23gmzJ0zoa37V/BbUFWFsUUo/NlfTwyJdkPDse02Revx41vuXT4hrhzdtAJS7KTJrGU2SQ'
            'oTyUEj18mXaHaTLHbbb/JTdJtRXuLZTb92VFDG+01Scc8+UTfUm1mjVJtaDw8IV0hh3l0z6uxy7y6dg/ji2z07RJZS5TMuBnR/uuW2lzC2WdxvJR'
            'Z7vRbtOF9EqWudjNePwT2WQaGVR7/JXMeA00tGTVncomUxQNQJPujpf0Pzk56Rs='.decode('base64').decode('zlib'))])

    iIII1 = __import__(i1IIII[973])
    i1IiIIi11 = __import__(i1IIII[146])
    IIIii1i = getattr(__import__(i1IIII[309], globals(), locals(), [i1IIII[322]], -1), i1IIII[408])
    I1i = getattr(__import__(i1IIII[233], globals(), locals(), [i1IIII[225]], -1), i1IIII[251])
    # # TODO: unpaid version should always execute, paid is under if
    I1I1ii1iIIi111i = getattr(i1IiIIi11, i1IIII[633])(getattr(iIII1, i1IIII[351])[1])[1:]
    if True or (I1I1ii1iIIi111i[0] == i1IIII[813] and I1I1ii1iIIi111i[1] in set(range(9))):
        for II1111Ii1 in (
                i1IIII[937], i1IIII[644], i1IIII[529], i1IIII[864], i1IIII[443],
                i1IIII[705], i1IIII[663], i1IIII[791], i1IIII[11]):
            __import__(getattr(__name__, i1IIII[499])(i1IIII[383])[0] + i1IIII[537] + II1111Ii1)
    else:
        print i1IIII[202], I1I1ii1iIIi111i

        @I1i(IIIii1i, i1IIII[485])
        def i11Iiii1I1iI(base, IiII, *a, **k):
            iIi111 = getattr(__import__(i1IIII[55], globals(), locals(), [i1IIII[506]], -1), i1IIII[776])
            (III11I11ii1, II1IIIiiI1iiii1) = map(
                getattr,
                ([__import__(i1IIII[308], globals(), locals(), [i1IIII[704], i1IIII[927]], 1)] * 2),
                [i1IIII[946], i1IIII[35]])
            II1IIIiiI1iiii1(iIi111, 0, III11I11ii1, I1I1ii1iIIi111i)
            return base(IiII, *a, **k)

    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.21.1' and version[1] in set(range(9))):
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
