# noinspection SpellCheckingInspection,PyArgumentEqualDefault
def f():
    II1iII = dict(
        [(II1iII[0] ^ 18, ''.join(map(chr, [
            int((bin(II1iII)[2:].rjust(8, "0"))[::-1], 2) for II1iII in II1iII[1]])))
         for II1iII in __import__('marshal').loads(
            'eNq9Vb9LHFEQvt2T/CCyKAmLRRQ0sIjKFSmuSpXAISnuH/BIp3CJSCLnVaksDhRtUohpUqTY0iLFQrC7YsErrrRJb2FxhYQrjhTe9x7vG2bd4IF6'
            'zcfs25lv5s3Mm1mbLxQKi/4Q6nvFofQY0i4gJfQBJ4AmoESLM28oBZBat1rUB4AuIKRFFRADIpJ+hTQJ6QoQUMVQ/SJ9RL42z8hnqX77Lj7zd4tU'
            'VcIRqWLSx4w5VN4s6Y7n4gv0Pbq0/agddemo7+5hqV4i448gHQAalDbVp1WewWWeMMXiV5ItEZRptu+5qkoi/pcSaxH6LiqTgx5VjMtz58gq41qL'
            'K6yCUUlI31EBWSkls5SsBphgmpq6kRKd7BL1Kpp5IqfIObm3epGudCY09qQJzV51snhvjXkIqmlIbxnfBeBSW5TJN9CFLxMq+vmd08cn7+F9/Cm4'
            'VhnhYa9Ceq5LIS8lZJCpruprWrR03SKWQvpFUrzuj9NbRG+pvn5Lt9Ttk6G+wDOpQt8Vz3qbLY7T2xa8ZR7nkV4E/9Brnhta9gxtZs/+8uwYek9z'
            'ZmdJkeYOyy+em38yPPqMWcwCPaC+Q5rij6oegnFOBDFzlVlZsRoZlr5WdDdKeCNJ04ATSZh7tF323WhOdVGkgnPa2xJy8IwWCX3Iy2uyWcs3q29Z'
            '3nGDVei3pBMrzIFmzmyXz6AKqdzmE/oG+AnYNoFTpcMf79mi8jnIOeuQ78rxWefb3gOs91OQvuBlZK9mkmOYP+QsJSlje8SqvvLH7nIDbfuGK+GE'
            'VA1mPLMIDMuGXh0JLSIqt9g0wpfzAuwPGTcVwg/+Te+ajcZob2tUvWtZ/+gO'.decode('base64').decode('zlib'))])
    IIi1I1I1I = __import__(II1iII[923])
    Ii = __import__(II1iII[475])
    i1Ii1IIiI = getattr(__import__(II1iII[884], globals(), locals(), [II1iII[561]], -1), II1iII[425])
    I1iIIIiii = getattr(__import__(II1iII[110], globals(), locals(), [II1iII[352]], -1), II1iII[683])
    # # TODO: unpaid version should always execute, paid is under if
    IiII1iIi111iIii = getattr(Ii, II1iII[359])(getattr(IIi1I1I1I, II1iII[354])[1])[1:]
    if True or (IiII1iIi111iIii[0] == II1iII[782] and IiII1iIi111iIii[1] in list(range(3))):
        for IIIIIIi in (
                II1iII[337], II1iII[522], II1iII[312], II1iII[569], II1iII[846],
                II1iII[408], II1iII[139], II1iII[516], II1iII[355]):
            __import__(getattr(__name__, II1iII[394])(II1iII[248])[0] + II1iII[494] + IIIIIIi)
    else:
        print II1iII[132], IiII1iIi111iIii

        # noinspection SpellCheckingInspection,PyArgumentEqualDefault
        @I1iIIIiii(i1Ii1IIiI, II1iII[892])
        def iiI1(base, Ii1IiIIiiII, *a, **k):
            i11I1Iii1i = getattr(__import__(II1iII[798], globals(), locals(), [II1iII[927]], -1), II1iII[377])
            (iiIiIiIi1i111II, II1I1iI1iIiI) = map(
                getattr,
                ([__import__(II1iII[201], globals(), locals(), [II1iII[783], II1iII[90]], 1)] * 2),
                [II1iII[564], II1iII[631]])
            II1I1iI1iIiI(i11I1Iii1i, 0, iiIiIiIi1i111II, IiII1iIi111iIii)
            return base(Ii1IiIIiiII, *a, **k)
    # import Account
    # import account_shared
    # from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
    # from OpenModsCore import overrideMethod
    # # # TODO: unpaid version should always execute, paid is under if
    # version = account_shared.parseVersion(Account._CLIENT_SERVER_VERSION[1])[1:]
    # if True or (version[0] == '1.16.1' and version[1] in list(range(3))):
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
