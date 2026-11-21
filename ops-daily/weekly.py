# usage: python3 weekly.py W_FROM W_TO  (needs cache/weekly_<W_TO>.json from rw/weekly_pull.js)
import json,sys,os,subprocess,datetime as dt,collections,statistics as st
H=os.path.dirname(os.path.abspath(__file__));os.chdir(H);sys.path.insert(0,H)
import plat,recipes_lib
WF,WT=sys.argv[1],sys.argv[2];d=dt.date.fromisoformat
PF=(d(WF)-dt.timedelta(days=7)).isoformat();PT=(d(WT)-dt.timedelta(days=7)).isoformat()
RW=json.load(open(f'cache/weekly_{WT}.json'))
P={c:plat.coll(c) for c in ['cashier_reports','revenue_receipts','purchases_invoices','purchases_suppliers','cost_ingredients','cost_recipes','daily_reports','visit_reports']}
CFG=plat.getdoc('fc_meta/config');SUP=P['purchases_suppliers']
FIXED=31235.95;BE=1498
def rday(ds):
    x=RW['days'].get(ds) or {};s=x.get('sum') or {};pm={m['name']:float(m['total'] or 0) for m in ((x.get('pay') or {}).get('paymentMethodsValues') or [])}
    tot=float(s.get('totalSalesTaxInclusive') or 0);return dict(total=tot,inv=int(s.get('totalNoOfInvoices') or 0),cash=pm.get('Cash',0),card=pm.get('Credit Card',0)+pm.get('Rewaa Pay',0),apps=sum(v for k,v in pm.items() if k not in('Cash','Credit Card','Rewaa Pay')))
def rng(a,b):
    o=[];x=d(a)
    while x<=d(b): o.append(x.isoformat());x+=dt.timedelta(days=1)
    return o
WD=rng(WF,WT);PD=rng(PF,PT);ALL=sorted(RW['days'])
f_=lambda v,k:float(v.get(k) or 0)
def pclose(ds):
    t=0;n=0;cash=0
    for v in P['cashier_reports'].values():
        if v.get('date')==ds: t+=f_(v,'grandTotal');n+=1;cash+=f_(v,'cashSales')
    return t,n,cash
week=[];
for ds in WD:
    r=rday(ds);pt,n,pc=pclose(ds);pr=rday((d(ds)-dt.timedelta(days=7)).isoformat())
    week.append(dict(day=ds,r=r,plat=pt,n=n,diff=pt-r['total'],prev=pr['total']))
W=sum(x['r']['total'] for x in week);PW=sum(rday(x)['total'] for x in PD);INV=sum(x['r']['inv'] for x in week);PINV=sum(rday(x)['inv'] for x in PD)
# items
def agg(rows):
    o={}
    for r in rows:
        n=r['variantName'].strip();x=o.setdefault(n,dict(name=n,qty=0.0,sales=0.0,net=0.0))
        x['qty']+=f_(r,'totalQuantity');x['sales']+=f_(r,'salesInclusive');x['net']+=f_(r,'netSales')
    return o
IW=agg(RW['items_w']);IP=agg(RW['items_p']);SK={'رقم الجهاز - number device','ماء - water','ماء - Water'}
items=[x for x in IW.values() if x['qty']>0 and x['name'] not in SK]
per=recipes_lib.build(P['cost_ingredients'],P['cost_recipes'],CFG.get('map',{}))
cons=collections.Counter();norec=[]
for x in items:
    x['prev']=IP.get(x['name'],{}).get('qty',0);x['prev_sales']=IP.get(x['name'],{}).get('sales',0)
    acc=per(x['name'])
    if acc is None: x['uc']=None;norec.append(x);continue
    uc=0
    for iid,q in acc.items():
        g=P['cost_ingredients'].get(iid,{});cons[iid]+=q*x['qty'];uc+=q*float(g.get('price') or 0)/float(g.get('pack') or 1)
    x['uc']=uc;x['cost']=uc*x['qty'];x['price']=x['net']/x['qty'] if x['qty'] else 0;x['margin']=x['price']-uc;x['mpct']=x['margin']/x['price']*100 if x['price'] else 0
cl=[]
for iid,q in cons.items():
    g=P['cost_ingredients'].get(iid,{});cl.append(dict(name=g.get('name',iid),qty=q,unit=g.get('unit',''),cost=q*float(g.get('price') or 0)/float(g.get('pack') or 1)))
cl.sort(key=lambda c:-c['cost'])
COGS=sum(c['cost'] for c in cl);covered=sum(x['net'] for x in items if x.get('uc') is not None);norec_net=sum(x['net'] for x in norec)
NET=W/1.15;cogs_est=COGS+norec_net*(COGS/covered if covered else 0)
FIXW=FIXED*7/30;PROFIT=NET-cogs_est-FIXW
# menu engineering (items with recipe)
me=[x for x in items if x.get('uc') is not None and x['qty']>=3]
if me:
    avgq=st.mean(x['qty'] for x in me);avgm=st.mean(x['margin'] for x in me)
    for x in me: x['cls']=('نجم' if x['margin']>=avgm else 'حصان عمل') if x['qty']>=avgq else ('لغز' if x['margin']>=avgm else 'ضعيف')
# weekday comparison 4 weeks & forecast
wdn=['الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت','الأحد']
cmp=[]
for ds in WD:
    hist=[(d(ds)-dt.timedelta(days=7*k)).isoformat() for k in (1,2,3)]
    hv=[rday(h)['total'] for h in hist if h in RW['days']]
    cmp.append(dict(day=ds,wd=wdn[d(ds).weekday()],cur=rday(ds)['total'],h=hv))
last14=sum(rday(x)['total'] for x in ALL[-14:]);prev14=sum(rday(x)['total'] for x in ALL[-28:-14])
trend=(last14/prev14) if prev14 else 1;trend_adj=max(0.85,min(1.15,trend**0.5))
fc=[]
for i in range(1,8):
    nd=d(WT)+dt.timedelta(days=i);hist=[(nd-dt.timedelta(days=7*k)).isoformat() for k in (1,2,3,4)];hv=[rday(h)['total'] for h in hist if h in RW['days'] and rday(h)['total']>0]
    base=st.mean(hv) if hv else W/7;fc.append(dict(day=nd.isoformat(),wd=wdn[nd.weekday()],base=base,fc=base*trend_adj,lo=min(hv)*trend_adj if hv else 0,hi=max(hv)*trend_adj if hv else 0))
# ops
dr=[v for v in P['daily_reports'].values() if WF<=str(v.get('date'))<=WT]
dr_days=len(set(v['date'] for v in dr));dr_avg=st.mean(float(v.get('completionPct') or 0) for v in dr) if dr else 0
vis=[v for v in P['visit_reports'].values() if WF<=str(v.get('date'))<=WT]
linked={v.get('linkedCashierReport') for v in P['revenue_receipts'].values()}
nocash=[(v['date'],f_(v,'cashSales')) for k,v in P['cashier_reports'].items() if WF<=str(v.get('date'))<=WT and f_(v,'cashSales')>0 and k not in linked]
pur=[v for v in P['purchases_invoices'].values() if WF<=str(v.get('date'))<=WT]
J=dict(WF=WF,WT=WT,week=week,W=W,PW=PW,INV=INV,PINV=PINV,items=items,cl=cl,COGS=COGS,covered=covered,norec=[dict(name=x['name'],qty=x['qty'],sales=x['sales']) for x in norec],NET=NET,cogs_est=cogs_est,FIXW=FIXW,PROFIT=PROFIT,me=me,cmp=cmp,fc=fc,trend=trend,
 ops=dict(dr=len(dr),dr_days=dr_days,dr_avg=dr_avg,vis=len(vis),nocash=nocash,pur=[dict(date=v.get('date'),sup=SUP.get(v.get('supplierId'),{}).get('name',''),total=v.get('total'),ref=v.get('rewaaRef')) for v in pur]))
json.dump(J,open(f'out/weekly_{WT}.json','w'),ensure_ascii=False,default=str)
print('W',round(W,2),'PW',round(PW,2),'inv',INV,PINV,'COGS',round(COGS,2),'cogs_est',round(cogs_est),'profit',round(PROFIT),'trend',round(trend,3),'fc',round(sum(x['fc'] for x in fc)),'dr',len(dr),dr_days,round(dr_avg,1),'vis',len(vis),'nocash',nocash,'pur',len(pur))
