import datetime

from dateutil.relativedelta import relativedelta

# Time formatting from speedrunbot
def realtime(time):  # turns XXX.xxx into h m s ms
    ms = int(time * 1000)
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)  # separates time into h m s ms
    ms = "{:03d}".format(ms)
    s = "{:02d}".format(s)  # pads ms and s with 0s
    if h > 0:
        m = "{:02d}".format(m)  # if in hours, pad m with 0s
    f = [
        str((h > 0) * (str(h) + "h")),
        str(m) + "m",
        str(s) + "s",
        (str(ms) + "ms") * (ms != "000"),
    ]
    for e in f:
        if not e:
            f.remove(e)  # remove item if empty
    return " ".join(f)  # src formatting 0


def general_time(dt, *, source=None, accuracy=3, brief=False, suffix=True):
    now = source or datetime.datetime.utcnow()
    # Microsecond free zone
    now = now.replace(microsecond=0)
    dt = dt.replace(microsecond=0)

    # This implementation uses relativedelta instead of the much more obvious
    # divmod approach with seconds because the seconds approach is not entirely
    # accurate once you go over 1 week in terms of accuracy since you have to
    # hardcode a month as 30 or 31 days.
    # A query like "11 months" can be interpreted as "!1 months and 6 days"
    if dt > now:
        delta = relativedelta(dt, now)
        suffix = ''
    else:
        delta = relativedelta(now, dt)
        suffix = ' ago' if suffix else ''

    attrs = [
        ('year', 'y'),
        ('month', 'mo'),
        ('day', 'd'),
        ('hour', 'h'),
        ('minute', 'm'),
        ('second', 's'),
    ]

    output = []
    for attr, brief_attr in attrs:
        elem = getattr(delta, attr + 's')
        if not elem:
            continue

        if attr == 'day':
            weeks = delta.weeks
            if weeks:
                elem -= weeks * 7
                if not brief:
                    output.append(format(plural(weeks), 'week'))
                else:
                    output.append(f'{weeks}w')

        if elem <= 0:
            continue

        if brief:
            output.append(f'{elem}{brief_attr}')
        else:
            output.append(format(plural(elem), attr))

    if accuracy is not None:
        output = output[:accuracy]

    if len(output) == 0:
        return 'now'
    else:
        if not brief:
            return human_join(output, final='and') + suffix
        else:
            return ' '.join(output) + suffix


def pformat(text):
    text = text.lower()
    text = text.replace(" ", "_")
    for s in "%()":
        text = text.replace(s, "")
    return text


def hformat(text, all_upper=False):
    text = text.replace("_", " ")
    if all_upper:
        return text.upper()
    return text.title()


# Stolen from neo bot by nickofolas
def bar_make(value, gap, *, length=10, point=False, fill="█", empty=" "):
    bar = ""
    scaled_value = (value / gap) * length
    for i in range(1, (length + 1)):
        check = (i == round(scaled_value)) if point else (i <= scaled_value)
        bar += fill if check else empty
    if point and (bar.count(fill) == 0):
        bar = fill + bar[1:]
    return bar
