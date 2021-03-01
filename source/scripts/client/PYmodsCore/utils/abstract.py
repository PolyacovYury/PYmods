import sys

__all__ = ('redirect_traceback',)


def redirect_traceback(callback, func_code):  # noinspection PyUnusedLocal
    def result(*a, **k):
        info = None
        try:
            return callback(*a, **k)
        except Exception:  # Code to remove this wrapper from traceback
            info = sys.exc_info()
            new_tb = info[2].tb_next  # https://stackoverflow.com/q/44813333
            if new_tb is None:  # exception occurs inside this wrapper, not inside of the callback
                new_tb = _generate_new_tb(func_code)  # so we point at the place of callback definition
            raise info[0], info[1], new_tb
        finally:
            del info

    return result


def _generate_new_tb(co):  # https://unterwaditzer.net/2018/python-custom-tracebacks.html
    ns = {}
    exec (compile(''.join(('\n' * (co.co_firstlineno - 1), 'def ', co.co_name, '(): 1/0')), co.co_filename, 'exec'), ns)
    tb_obj = None
    try:
        ns[co.co_name]()
    except ZeroDivisionError:
        tb_obj = sys.exc_info()[2].tb_next
    return tb_obj
