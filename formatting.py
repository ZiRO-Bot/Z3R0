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
    f = [str((h>0) * (str(h)+'h ')), str(m)+'m', str(s)+'s', (str(ms)+'ms') * (ms!='000')]
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