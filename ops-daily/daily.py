# usage: python3 daily.py [BUSINESS_DAY]  -> out/data_<day>.json ; fixes misdated closings (approved rule)
import json,sys,os,subprocess,datetime as dt
from collections import defaultdict
H=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,H)
import plat
now=dt.datetime.utcnow()+dt.timedelta(hours=3)
DAY=sys.argv[1] if len(sys.argv)>1 else (now-dt.timedelta(days=1)).date().isoformat()
MS=DAY[:8]+'01'
P={c:plat.coll(c) for c in ['cashier_reports','revenue_receipts','purchases_invoices','purchases_suppliers','cost_ingredients','cost_recipes']}
CFG=plat.getdoc('fc_meta/config')
SUP=P['purchases_suppliers']
# 1 fix misdated closings: night closing saved after midnight with next calendar date
fixed=[]
for k,v in P['cashier_reports'].items():
    c=v.get('createdAt');d=v.get('date')
    if not c or not d or d<MS: continue
    t=dt.datetime.fromisoformat(str(c).replace('Z','+00:00'));D=dt.date.fromisoformat(d)
    if t.date()==D and t.hour<6:
        nd=(D-dt.timedelta(days=1)).isoformat();r=plat.patch('cashier_reports/'+k,{'date':nd,'editedAt':now.isoformat()+'Z','editedBy':'المطابقة اليومية — تصحيح التاريخ'})
        fixed.append((d,nd,v.get('grandTotal'),r));v['date']=nd
# 2 Rewaa pull MTD + products
rj=os.path.join(H,'cache',f'rewaa_{DAY}.json')
if not os.path.exists(rj): subprocess.run(['node','pull_days.js',MS,DAY,rj],cwd=os.path.join(H,'rw'),timeout=900)
RW=json.load(open(rj))
f=lambda v,k:float(v.get(k) or 0)
def pcl(day):
    p=defaultdict(float);n=0;ids=[]
    for k,v in P['cashier_reports'].items():
        if v.get('date')!=day: continue
        n+=1;ids.append(k);p['cash']+=f(v,'cashSales');p['card']+=f(v,'mada')+f(v,'visa')+f(v,'masterCard')
        p['apps']+=sum(f(v,x) for x in ('keeta','hungerStation','ninja','jahez','chefz','otherApp','myTable','gulf','transfer'));p['total']+=f(v,'grandTotal')
    return dict(p),n,ids
def rwd(day):
    x=RW['days'].get(day) or {};pm={m['name']:float(m['total'] or 0) for m in ((x.get('pay') or {}).get('paymentMethodsValues') or [])}
    r=dict(cash=pm.get('Cash',0),card=pm.get('Credit Card',0)+pm.get('Rewaa Pay',0),apps=sum(v for k,v in pm.items() if k not in('Cash','Credit Card','Rewaa Pay')))
    r['pay_total']=sum(r.values());s=x.get('sum') or {};r['total']=float(s.get('totalSalesTaxInclusive') or r['pay_total']);r['invoices']=int(s.get('totalNoOfInvoices') or 0)
    r['anomaly']=abs(r['pay_total']-r['total'])>1;return r
days=[];d0=dt.date.fromisoformat(MS)
while d0<=dt.date.fromisoformat(DAY):
    ds=d0.isoformat();p,n,ids=pcl(ds);r=rwd(ds);days.append(dict(day=ds,n=n,p=p,r=r,diff=round(p.get('total',0)-r['total'],2)));d0+=dt.timedelta(days=1)
# 3 revenue receipts (MTD)
linked={v.get('linkedCashierReport'):v for v in P['revenue_receipts'].values()}
nocash=[];rec_tot=0
for k,v in P['cashier_reports'].items():
    if v.get('date','')<MS or v.get('date','')>DAY: continue
    cash=f(v,'cashSales');r=linked.get(k)
    if r: rec_tot+=float(r.get('cashAmount') or 0)
    elif cash>0: nocash.append(dict(day=v['date'],shift='الظهر' if dt.datetime.fromisoformat(str(v['createdAt']).replace('Z','+00:00')).hour>=6 else 'الليل',cash=cash))
day_rec=[v for v in P['revenue_receipts'].values() if v.get('date')==DAY]
# 4 pending invoices
pend=[]
for k,v in P['purchases_invoices'].items():
    if v.get('date','')>='2026-11-01' and not v.get('rewaaRef'):
        pend.append(dict(id=k,date=v.get('date'),no=v.get('number'),sup=SUP.get(v.get('supplierId'),{}).get('name',''),total=v.get('total'),vat=v.get('vat'),desc=v.get('desc'),lines=v.get('lines') or [],pay=v.get('payMethod')))
synced=[dict(date=v.get('date'),no=v.get('number'),sup=SUP.get(v.get('supplierId'),{}).get('name',''),total=v.get('total'),ref=v.get('rewaaRef'),at=v.get('rewaaSyncedAt')) for v in P['purchases_invoices'].values() if str(v.get('rewaaSyncedAt',''))[:10]==now.date().isoformat()]
# 5 prices & links
V={str(x['id']):x for x in RW.get('products',[])}
pdiff=[];unl=[]
for k,g in P['cost_ingredients'].items():
    vid=str(g.get('rewaaVariantId') or '')
    if not vid or vid not in V:
        if g['name'] not in ('ماء',) and 'منظفات' not in g['name']: unl.append(g['name'])
        continue
    fct=1000 if g.get('rewaaUnit') in('كجم','لتر') and g.get('unit') in('جم','مل') else 1
    pp=float(g.get('price') or 0)/float(g.get('pack') or 1)*fct;rp=float(V[vid].get('buyPrice') or 0)
    if abs(pp-rp)>max(0.02,0.01*pp) and g['name']!='سلك مواعين': pdiff.append(dict(name=g['name'],plat=round(pp,3),rewaa=rp,unit=g.get('rewaaUnit')))
data=dict(day=DAY,generated=now.strftime('%Y-%m-%d %H:%M'),fixed=fixed,days=days,nocash=sorted(nocash,key=lambda x:x['day']),rec_mtd=rec_tot,day_receipts=len(day_rec),
          pending=pend,synced=synced,pdiff=pdiff,unlinked=unl,counts=dict(ings=len(P['cost_ingredients']),inv_total=len(P['purchases_invoices'])))
json.dump(data,open(os.path.join(H,'out',f'data_{DAY}.json'),'w'),ensure_ascii=False,default=str)
# 6 items & analysis & consumption
import recipes_lib,collections
def agg(rows):
    o={}
    for r in rows:
        n=r['variantName'].strip();x=o.setdefault(n,dict(name=n,qty=0.0,sales=0.0,net=0.0))
        x['qty']+=float(r.get('totalQuantity') or 0);x['sales']+=float(r.get('salesInclusive') or 0);x['net']+=float(r.get('netSales') or 0)
    return o
IDAY=agg(RW.get('items_day',[]));IMTD=agg(RW.get('items_mtd',[]))
SKIPN={'رقم الجهاز - number device'}
sold=[x for x in IDAY.values() if x['qty']>0 and x['name'] not in SKIPN]
dayn=sum(1 for x in days if x['r']['total']>0)
for x in sold:
    m=IMTD.get(x['name']);x['mtd_avg']=(m['qty']/max(dayn,1)) if m else 0
notsold=sorted([m for n,m in IMTD.items() if m['qty']>0 and n not in IDAY and n not in SKIPN],key=lambda m:-m['qty'])[:8]
per_item=recipes_lib.build(P['cost_ingredients'],P['cost_recipes'],CFG.get('map',{}))
cons=collections.Counter();norec=[];item_cost={}
for x in sold:
    acc=per_item(x['name'])
    if acc is None:
        if x['sales']>0: norec.append(dict(name=x['name'],qty=x['qty'],sales=x['sales']))
        continue
    uc=0
    for iid,q in acc.items():
        cons[iid]+=q*x['qty'];g=P['cost_ingredients'].get(iid,{});uc+=q*float(g.get('price') or 0)/float(g.get('pack') or 1)
    item_cost[x['name']]=uc;x['unit_cost']=uc;x['cost']=uc*x['qty']
cl=[]
for iid,q in cons.items():
    g=P['cost_ingredients'].get(iid,{});u=g.get('unit') or ''
    cost=q*float(g.get('price') or 0)/float(g.get('pack') or 1)
    cl.append(dict(name=g.get('name',iid),qty=q,unit=u,cost=cost))
cl.sort(key=lambda c:-c['cost'])
y=[x for x in days if x['day']==DAY][0]
wd=dt.date.fromisoformat(DAY).weekday();same=[x['r']['total'] for x in days if x['day']!=DAY and x['r']['total']>0 and dt.date.fromisoformat(x['day']).weekday()==wd]
others=[x['r']['total'] for x in days if x['day']!=DAY and x['r']['total']>0]
inv=y['r']['invoices'];net=y['r']['total']/1.15;qtot=sum(x['qty'] for x in sold)
recipe_cogs=sum(c['cost'] for c in cl);covered=sum(x['net'] for x in sold if x['name'] in item_cost)
analysis=dict(total=y['r']['total'],net=net,invoices=inv,avg_ticket=y['r']['total']/inv if inv else 0,items=qtot,items_per_inv=qtot/inv if inv else 0,
  mtd_avg=sum(others)/len(others) if others else 0,same_wd_avg=sum(same)/len(same) if same else 0,same_wd_n=len(same),weekday=wd,
  recipe_cogs=recipe_cogs,covered_net=covered,cogs_pct=recipe_cogs/covered*100 if covered else 0,norec_sales=sum(x['sales'] for x in norec))
data.update(items=sorted(sold,key=lambda x:-x['sales']),notsold=notsold,consumption=cl,norec=norec,analysis=analysis)
json.dump(data,open(os.path.join(H,'out',f'data_{DAY}.json'),'w'),ensure_ascii=False,default=str)
print('items',len(sold),'top',[(x['name'][:20],x['qty']) for x in sorted(sold,key=lambda x:-x['qty'])[:5]],'cogs',round(recipe_cogs,2),round(analysis['cogs_pct'],1),'norec',[x['name'][:20] for x in norec])
y=[x for x in days if x['day']==DAY][0]
print('DAY',DAY,'closings',y['n'],'plat',y['p'].get('total',0),'rewaa',y['r']['total'],'diff',y['diff'],'| fixed',fixed,'| pending',[(x['date'],x['no'],x['sup'],x['total']) for x in pend],'| nocash',len(nocash),'| pdiff',pdiff,'| unlinked',unl)
