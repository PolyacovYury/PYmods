import BigWorld
from functools import partial

__all__ = ('sendChatMessage',)
MAX_CHAT_MESSAGE_LENGTH = 220


def sendChatMessage(fullMsg, chanId, delay):
    currPart, remains = __splitChatMessage(fullMsg)
    __sendChatMessagePart(currPart, chanId)
    if remains:
        BigWorld.callback(delay / 1000.0, partial(sendChatMessage, remains, chanId, delay))


def __splitChatMessage(msg):
    if len(msg) <= MAX_CHAT_MESSAGE_LENGTH:
        return msg, ''
    strPart = msg[:MAX_CHAT_MESSAGE_LENGTH]
    splitPos = strPart.rfind(' ')
    if splitPos == -1:
        splitPos = MAX_CHAT_MESSAGE_LENGTH
    return msg[:splitPos], msg[splitPos:]


def __sendChatMessagePart(msg, chanId):
    import BattleReplay
    from messenger import MessengerEntry
    from messenger.m_constants import PROTO_TYPE
    from messenger.proto import proto_getter
    msg = msg.encode('utf-8')
    proto = proto_getter(PROTO_TYPE.BW_CHAT2).get()
    if proto is None or BattleReplay.isPlaying():
        MessengerEntry.g_instance.gui.addClientMessage('OFFLINE: %s' % msg, True)
    elif chanId in (0, 1):  # 0 == 'All', 1 == 'Team'
        proto.arenaChat.broadcast(msg, int(not chanId))
    elif chanId == 2:
        proto.unitChat.broadcast(msg, 1)
