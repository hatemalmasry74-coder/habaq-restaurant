# per-sold-item raw material consumption from platform recipes (same logic as the Rewaa recipe sync)
import re,collections
norm=lambda s:re.sub(r'\s+',' ',str(s)).strip().lower()
PKG={'كوب شاي بخار - CUP TEA BOKHAR':'cup','كوب شاي تلقيمة - CUP TEA TALQIMA':'cup','كوب نعناع طايفي - Taifi':'cup','قهوة سعودي كوب - Saudi coffee Cup':'cup','Coffee Day - قهوة اليوم':'cup',
 'آيس تي حبّاق - Ice Tea':'pcup','كركدية حبق - hibiscus':'pcup','مسخن دجاج - chiken':'paper','فيتا تين - Fitatin':'paper','سباريلا - sbarila':'paper','2 بابكا زعتر - Babka Zaatar 2':'paper','2 بابكا شوكليت - Babka chocolate2':'paper',
 'بوكس جمعات حبّاق - Big Box':'box','Halloumi Focaccia — فوكاشيا حلومي':'paper','Tuna Pesto Focaccia — فوكاشيا تونة بالبيستو':'paper'}
PKGING={'cup':'8scCSHpgQYLhjKkax4Qt','pcup':'s4KvMUoqLijYn15HRzbr','paper':'QebXkhNnVR8Du3FCafIt','box':'sEx05THYcxC3nUyQy8YO'}
SKIP={'hjqJ4pwKbcg3ds3Z8oMs'}
def build(I,R,MAPCFG):
    MAP={norm(k):v for k,v in MAPCFG.items()};SEED={v.get('seedKey'):(k,v) for k,v in R.items() if v.get('seedKey')}
    def flat(r,mult,acc,d=0):
        y=float(r.get('yield') or 1) or 1
        for it in r.get('items') or []:
            q=float(it.get('qty') or 0)*mult/y
            if it.get('recId'):
                s=R.get(it['recId'])
                if s and d<6: flat(s,q,acc,d+1)
            elif it.get('ingId') and it['ingId'] not in SKIP: acc[it['ingId']]+=q
    def per_item(name):
        nm=re.sub(r'\s+',' ',name).strip();m=MAP.get(norm(nm))
        if not(m and m.get('rec')): return None
        key=m['rec'];r=SEED.get(key.replace('seed:',''),(None,None))[1] if key.startswith('seed:') else R.get(key)
        if not r: return None
        acc=collections.Counter();flat(r,float(m.get('f') or 1),acc)
        p=PKG.get(nm)
        if p and PKGING[p] in I: acc[PKGING[p]]+=1
        return acc
    return per_item
