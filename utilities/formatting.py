# Time formatting from speedrunbot
def realtime(time): # turns XXX.xxx into h m s ms
    ms = int(time*1000)
    s,ms = divmod(ms,1000)
    m,s = divmod(s,60)
    h,m = divmod(m,60)  # separates time into h m s ms
    ms = "{:03d}".format(ms)
    s = "{:02d}".format(s)  #pads ms and s with 0s
    if h>0:
        m = "{:02d}".format(m)  #if in hours, pad m with 0s
    f = [str((h>0) * (str(h)+'h')), str(m)+'m', str(s)+'s', (str(ms)+'ms') * (ms!='000')]
    for e in f:
        if not e:
            f.remove(e) #remove item if empty
    return " ".join(f) #src formatting 0

def pformat(text):
    text = text.lower()
    text = text.replace(" ","_")
    for s in "%()":
        text = text.replace(s,"")
    return text

def hformat(text):
    text = text.replace("_"," ")
    return text.title()

def barpercent(percentage):
    if percentage >= 100:
        bar = "—————————————————————————⬤"
    elif percentage >= 96:
        bar = "————————————————————————⬤—"
    elif percentage >= 92:
        bar = "———————————————————————⬤——"
    elif percentage >= 88:
        bar = "——————————————————————⬤———"
    elif percentage >= 84:
        bar = "—————————————————————⬤————"
    elif percentage >= 80:
        bar = "————————————————————⬤—————"
    elif percentage >= 76:
        bar = "———————————————————⬤——————"
    elif percentage >= 72:
        bar = "——————————————————⬤———————"
    elif percentage >= 68:
        bar = "—————————————————⬤————————"
    elif percentage >= 64:
        bar = "————————————————⬤—————————"
    elif percentage >= 60:
        bar = "———————————————⬤——————————"
    elif percentage >= 56:
        bar = "——————————————⬤———————————"
    elif percentage >= 52:
        bar = "—————————————⬤————————————"
    elif percentage >= 48:
        bar = "————————————⬤—————————————"
    elif percentage >= 44:
        bar = "———————————⬤——————————————"
    elif percentage >= 40:
        bar = "——————————⬤———————————————"
    elif percentage >= 36:
        bar = "—————————⬤————————————————"
    elif percentage >= 32:
        bar = "————————⬤—————————————————"
    elif percentage >= 28:
        bar = "———————⬤——————————————————"
    elif percentage >= 24:
        bar = "——————⬤———————————————————"
    elif percentage >= 20:
        bar = "—————⬤————————————————————"
    elif percentage >= 16:
        bar = "————⬤—————————————————————"
    elif percentage >= 12:
        bar = "———⬤——————————————————————"
    elif percentage >= 8:
        bar = "——⬤———————————————————————"
    elif percentage >= 4:
        bar = "—⬤————————————————————————"
    else:
        bar = "⬤—————————————————————————"
    return bar
