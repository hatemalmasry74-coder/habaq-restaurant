# usage: python3 daily_pdf.py DAY  -> out/حباق-التقرير-اليومي-<DAY>.pdf
import json,sys,os,subprocess
H=os.path.dirname(os.path.abspath(__file__));os.chdir(H)
DAY=sys.argv[1];J=json.load(open(f'out/data_{DAY}.json'))
TR=json.load(open(f'out/transfers_{DAY}.json')) if os.path.exists(f'out/transfers_{DAY}.json') else []
exec(open('lib.py').read())
G='#2E6B3A';AM='#B7791F';RD='#9B2C2C'
AR={'01':'يناير','02':'فبراير','03':'مارس','04':'أبريل','05':'مايو','06':'يونيو','07':'يوليو','08':'أغسطس','09':'سبتمبر','10':'أكتوبر','11':'نوفمبر','12':'ديسمبر'}
dar=lambda d:f"{int(d[8:])} {AR[d[5:7]]}"
def kp(items,cols=4): return f'<div class="kgrid" style="grid-template-columns:repeat({cols},1fr)">'+''.join(f'<div class="kpi"><div class="kl">{a}</div><div class="kv" style="color:{c}">{b}</div><div class="ks">{t}</div></div>' for a,b,t,c in items)+'</div>'
def tbl(head,body,cls='t',fs=None): return f'<table class="{cls}"{f" style=font-size:{fs}px" if fs else ""}><tr>'+''.join(f'<th>{h}</th>' for h in head)+'</tr>'+''.join('<tr>'+''.join(f'<td{" class=nm" if j==0 else ""}>{c}</td>' for j,c in enumerate(r))+'</tr>' for r in body)+'</table>'
def pill(t,k): return f'<span class="pill {k}">{t}</span>'
def st(df): return pill('مطابق','ok') if abs(df)<=10 else (pill('فرق بسيط','warn') if abs(df)<=150 else pill('فرق','bad'))
days=J['days'];y=[x for x in days if x['day']==DAY][0];mtd=[x for x in days if x['r']['total'] or x['n']]
PT=sum(x['p'].get('total',0) for x in mtd);RT=sum(x['r']['total'] for x in mtd)
pend=J['pending'];done=TR or J['synced'];nocash=J['nocash']
alerts=[]
if abs(y['diff'])>10: alerts.append(f"فرق مبيعات اليوم {f(y['diff'],2)} ر.س بين التقفيل ورواء")
if y['n']<2 and y['r']['total']>0: alerts.append(f"عدد التقفيلات {y['n']} — المتوقع تقفيلان (ظهر وليل)")
if pend: alerts.append(f"{len(pend)} فاتورة بالمنصة تحتاج قراراً قبل نقلها لرواء")
nc_day=[x for x in nocash if x['day']==DAY]
if nc_day: alerts.append(f"{len(nc_day)} وردية اليوم بدون إيصال استلام نقدية")
if J['fixed']: alerts.append(f"تم تصحيح تاريخ {len(J['fixed'])} تقفيل تلقائياً")
if y['r'].get('anomaly'): alerts.append('تقرير طرق الدفع في رواء غير مطابق لتقرير المبيعات — اعتُمد تقرير المبيعات')
# 1 summary
sl('ملخص اليوم',f'يوم العمل {dar(DAY)} {DAY[:4]} · تم التوليد {J["generated"]} بتوقيت الرياض',kp([
 ('مبيعات رواء',f(y['r']['total'],2),f"ر.س شاملة الضريبة · {y['r']['invoices']} فاتورة",MAR),('تقفيلات المنصة',f(y['p'].get('total',0),2),f"ر.س · {y['n']} تقفيل",MAR),
 ('الفرق',f(y['diff'],2),'ر.س (المنصة − رواء)',G if abs(y['diff'])<=10 else (AM if abs(y['diff'])<=150 else RD)),('منذ بداية الشهر',f(RT),f'ر.س رواء · فرق {f(PT-RT,2)}',MAR),
 ('فواتير نُقلت لرواء',str(len(done)),'شراء ومصروفات اليوم',G),('فواتير معلّقة',str(len(pend)),'تحتاج قراراً',RD if pend else G),
 ('نقد بدون إيصال',str(len(nocash)),f'وردية منذ بداية الشهر · {f(sum(x["cash"] for x in nocash))} ر.س',RD if nocash else G),('فروقات أسعار',str(len(J['pdiff'])),'بين المنصة ورواء',AM if J['pdiff'] else G)])+
 (f'<div class="verdict" style="font-size:22px;line-height:1.8"><b>تنبيهات اليوم:</b> '+' · '.join(alerts)+'</div>' if alerts else '<div class="verdict" style="font-size:22px;background:#2E6B3A"><b>✔ لا توجد تنبيهات:</b> المنصة ورواء متطابقان لهذا اليوم.</div>'))
# 2 sales
rows=[(x['day'][5:],x['n'],f(x['p'].get('total',0),2),f(x['r']['total'],2),bd(x['diff'],2),st(x['diff'])) for x in mtd]
half=(len(rows)+1)//2
br=[('كاش',y['p'].get('cash',0),y['r']['cash']),('شبكة',y['p'].get('card',0),y['r']['card']),('تطبيقات التوصيل',y['p'].get('apps',0),y['r']['apps']),('الإجمالي',y['p'].get('total',0),y['r']['total'])]
sl('المبيعات: التقفيلات مقابل رواء',f'تفصيل {dar(DAY)} + منذ بداية الشهر · ر.س',f'<div class="row" style="gap:26px"><div class="col" style="flex:.8">{tbl(["طريقة الدفع","المنصة","رواء","الفرق"],[(a,f(b,2),f(c,2),bd(b-c,2)) for a,b,c in br],"t",20)}<div class="card" style="font-size:19px;line-height:1.7">يوم العمل من ~3 فجراً إلى ~3 فجراً. الفرق في توزيع الكاش/الشبكة بين يومين متتاليين غالباً توقيت تقفيل.</div></div><div class="col" style="flex:1.2"><div class="row" style="gap:16px;flex:0"><div class="col" style="flex:1">{tbl(["اليوم","ت","المنصة","رواء","الفرق","الحالة"],rows[:half],"t sm",15)}</div><div class="col" style="flex:1">{tbl(["اليوم","ت","المنصة","رواء","الفرق","الحالة"],rows[half:]+[("<b>الشهر</b>","",f"<b>{f(PT,2)}</b>",f"<b>{f(RT,2)}</b>",f"<b>{bd(PT-RT,2)}</b>","")],"t sm",15)}</div></div></div></div>')
# 3 purchases
dr=[(x.get('date',''),f"{x.get('sup','')} — {x.get('no','')}",f(float(x.get('total') or 0),2),x.get('doc') or x.get('ref',''),x.get('note','')) for x in done]
pr=[(x['date'],f"{x['sup']} — {x['no']}",f(float(x['total'] or 0),2),x.get('desc') or '',pill('يحتاج قرار','bad')) for x in pend]
sl('المشتريات والمصروفات','نقل فواتير المنصة إلى رواء',('<div class="h3">ما نُقل اليوم</div>'+tbl(['التاريخ','المورد والفاتورة','المبلغ','المستند في رواء','ملاحظة'],dr,'t',18) if dr else '<div class="card" style="font-size:22px">لا توجد فواتير جديدة نُقلت في هذه الدورة.</div>')+
 ('<div class="h3" style="margin-top:14px">معلّقة تحتاج قراراً</div>'+tbl(['التاريخ','المورد والفاتورة','المبلغ','الوصف','الحالة'],pr,'t',18) if pr else '<div class="card" style="font-size:22px;border-right:8px solid #2E6B3A">✔ لا توجد فواتير معلّقة — كل فواتير المنصة منذ 1 نوفمبر منقولة.</div>'))
# 4 receipts
nr=[(dar(x['day']),x['shift'],f(x['cash'],2)) for x in nocash[-14:]]
sl('استلام الإيرادات النقدية','إيصالات الاستلام في المنصة مقابل الكاش في التقفيلات',kp([('إيصالات يوم العمل',str(J['day_receipts']),'إيصال مسجل',G if J['day_receipts'] else AM),('النقد المستلم منذ بداية الشهر',f(J['rec_mtd'],2),'ر.س بإيصالات',G),('ورديات بدون إيصال',str(len(nocash)),f"{f(sum(x['cash'] for x in nocash),2)} ر.س",RD if nocash else G)],3)+
 (tbl(['اليوم','الوردية','النقد ر.س'],nr,'t sm',18) if nr else '<div class="card" style="font-size:22px">✔ كل ورديات الشهر التي فيها نقد لها إيصال استلام.</div>'))
# 5 prices & data quality
pd_=[(x['name'],x['unit'],f(x['plat'],3),f(x['rewaa'],3),bd(x['rewaa']-x['plat'],3)) for x in J['pdiff']]
fx=[(a,b,f(float(c or 0),2),'تم') for a,b,c,_ in J['fixed']]
sl('الأسعار وجودة البيانات','',('<div class="h3">فروقات سعر الشراء (لكل وحدة رواء)</div>'+tbl(['المادة','الوحدة','المنصة','رواء (آخر شراء)','الفرق'],pd_,'t',19) if pd_ else '<div class="card">✔ الأسعار متطابقة.</div>')+
 (f'<div class="card" style="font-size:20px">مواد غير مرتبطة برواء: {"، ".join(J["unlinked"])}</div>' if J['unlinked'] else '')+
 ('<div class="h3">تقفيلات صُحّح تاريخها تلقائياً</div>'+tbl(['التاريخ المسجل','يوم العمل','المبلغ','الحالة'],fx,'t sm',18) if fx else '')+
 '<p class="note">رواء يحدّث سعر الشراء تلقائياً من آخر فاتورة؛ اعتماد السعر في المنصة يكون بقرار الإدارة.</p>')
tail=open('tail.txt').read()
tail=tail.replace("TAG='التقرير الشهري · أكتوبر 2026'",f"TAG='التقرير اليومي · {DAY}'")
tail=tail.replace('التقرير الشهري<br>أكتوبر 2026',f'التقرير اليومي<br>{dar(DAY)} {DAY[:4]}')
tail=tail.replace('المبيعات · مطابقة رواء والمنصة · الأصناف · المشتريات · نقطة التعادل · التنبؤات','مطابقة المنصة مع رواء · المبيعات · المشتريات والمصروفات · استلام الإيرادات · الأسعار')
tail=tail.replace('الفترة: 1 – 31 أكتوبر 2026',f'يوم العمل: {DAY}')
tail=tail.replace("open('report.html','w')",f"open('out/daily_{DAY}.html','w')")
exec(tail)
pdf=os.path.join(H,'out',f'حباق-التقرير-اليومي-{DAY}.pdf')
r=subprocess.run(['node','pdf.js',os.path.join(H,'out',f'daily_{DAY}.html'),pdf,os.path.join(H,'out','shots_'+DAY)],capture_output=True,text=True);print(r.stdout.strip()[-200:],r.stderr[-300:]);print(pdf)
