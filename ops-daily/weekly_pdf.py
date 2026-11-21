import json,sys,os,subprocess
H=os.path.dirname(os.path.abspath(__file__));os.chdir(H)
WT=sys.argv[1];J=json.load(open(f'out/weekly_{WT}.json'))
exec(open('lib.py').read())
G='#2E6B3A';AM='#B7791F';RD='#9B2C2C'
AR={'01':'يناير','02':'فبراير','03':'مارس','04':'أبريل','05':'مايو','06':'يونيو','07':'يوليو','08':'أغسطس','09':'سبتمبر','10':'أكتوبر','11':'نوفمبر','12':'ديسمبر'}
dar=lambda d:f"{int(d[8:])} {AR[d[5:7]]}"
WDN=['الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت','الأحد']
import datetime as dt
wdn=lambda d:WDN[dt.date.fromisoformat(d).weekday()]
def kp(items,cols=4): return f'<div class="kgrid" style="grid-template-columns:repeat({cols},1fr)">'+''.join(f'<div class="kpi"><div class="kl">{a}</div><div class="kv" style="color:{c}">{b}</div><div class="ks">{t}</div></div>' for a,b,t,c in items)+'</div>'
def tbl(head,body,cls='t',fs=None): return f'<table class="{cls}"{f" style=font-size:{fs}px" if fs else ""}><tr>'+''.join(f'<th>{h}</th>' for h in head)+'</tr>'+''.join('<tr>'+''.join(f'<td{" class=nm" if j==0 else ""}>{c}</td>' for j,c in enumerate(r))+'</tr>' for r in body)+'</table>'
def pill(t,k): return f'<span class="pill {k}">{t}</span>'
def chg(a,b): 
    if not b: return '—'
    c=(a/b-1)*100;col=G if c>=0 else RD
    return f'<span style="color:{col};font-weight:800"><bdi dir="ltr">{"+" if c>0 else ""}{c:.0f}%</bdi></span>'
short=lambda n:(n.split(' - ')[0] if ' - ' in n else n.split(' — ')[-1] if ' — ' in n else n)[:24]
W,PW=J['W'],J['PW'];avg=W/7;BE=1498;above=sum(1 for x in J['week'] if x['r']['total']>=BE)
diffs=sum(x['diff'] for x in J['week'])
PER=f"{dar(J['WF'])} – {dar(J['WT'])} {J['WT'][:4]}"
# 1 summary
alerts=[]
if avg<BE: alerts.append(f"متوسط البيع اليومي {f(avg)} ر.س أقل من نقطة التعادل ({f(BE)}) — {above} أيام فقط فوقها")
if J['ops']['dr_days']<7: alerts.append(f"نماذج الورديات سُجّلت في {J['ops']['dr_days']} أيام فقط من 7")
if J['ops']['nocash']: alerts.append(f"{len(J['ops']['nocash'])} وردية نقدية بدون إيصال استلام")
if abs(diffs)>20: alerts.append(f"فرق التقفيلات مع رواء {f(diffs,2)} ر.س")
nr=sum(x['sales'] for x in J['norec'])
if nr: alerts.append(f"أصناف بدون وصفة بمبيعات {f(nr)} ر.س")
sl('ملخص الأسبوع',PER,kp([('مبيعات الأسبوع',f(W,2),f'ر.س · {chg(W,PW)} عن الأسبوع السابق',MAR),('متوسط البيع اليومي',f(avg),f'ر.س · التعادل {f(BE)} · {above}/7 أيام فوقه',G if avg>=BE else RD),
 ('الفواتير',f(J['INV']),f"متوسط {f(W/J['INV'],2)} ر.س · {chg(J['INV'],J['PINV'])}",MAR),('الربح التقديري',f(J['PROFIT']),'ر.س بعد التكلفة والتكاليف الثابتة',G if J['PROFIT']>=0 else RD),
 ('تكلفة الأصناف',f(J['cogs_est']),f"ر.س · {J['cogs_est']/J['NET']*100:.1f}% من الصافي",MAR),('التكاليف الثابتة',f(J['FIXW']),'ر.س حصة الأسبوع (31,236 شهرياً)',MAR),
 ('المطابقة مع رواء',f(diffs,2),'ر.س فرق التقفيلات خلال الأسبوع',G if abs(diffs)<=20 else AM),('توقع الأسبوع القادم',f(sum(x['fc'] for x in J['fc'])),'ر.س',MAR)])+
 '<div class="verdict" style="font-size:21px;line-height:1.75"><b>أهم التنبيهات:</b> '+' · '.join(alerts)+'</div>')
# 2 daily
data=[(f"{wdn(x['day'])}\n{x['day'][8:]}".split('\n')[0],x['r']['total']) for x in J['week']]
cols=[G if v>=BE else (AM if v>=BE*0.85 else RD) for _,v in data]
rows=[(f"{wdn(x['day'])} {dar(x['day'])}",f(x['r']['total'],2),f(x['prev'],2),chg(x['r']['total'],x['prev']),x['r']['inv'],f(x['r']['total']/x['r']['inv'],2) if x['r']['inv'] else '—',f(x['plat'],2),pill('مطابق','ok') if abs(x['diff'])<=10 else pill(f"{x['diff']:+.0f}",'warn')) for x in J['week']]
rows.append(('<b>الأسبوع</b>',f'<b>{f(W,2)}</b>',f'<b>{f(PW,2)}</b>',chg(W,PW),f"<b>{J['INV']}</b>",f(W/J['INV'],2),f"<b>{f(sum(x['plat'] for x in J['week']),2)}</b>",''))
sl('المبيعات اليومية','مقارنة بنفس اليوم من الأسبوع السابق · والتقفيلات مقابل رواء',f'<div class="row" style="gap:26px"><div class="col" style="flex:.85"><div class="dchart" style="padding:10px">{vbars(data,660,430,cols,lambda v:f(v),None,BE,fs=17,lfs=16)}</div><div style="font-size:17px;color:#7a6658">الخط: نقطة التعادل {f(BE)} ر.س · أخضر فوقها · أحمر أقل منها بأكثر من 15%</div></div><div class="col" style="flex:1.15">{tbl(["اليوم","رواء","الأسبوع السابق","التغير","الفواتير","متوسط الفاتورة","المنصة","المطابقة"],rows,"t sm",16)}</div></div>')
# 3 items
IT=sorted(J['items'],key=lambda x:-x['sales']);tot=sum(x['sales'] for x in IT)
rows=[(short(x['name']),f(x['qty']),f(x['prev']),chg(x['qty'],x['prev']),f(x['sales'],2),pc(x['sales']/tot*100,0)) for x in IT[:14]]
up=sorted([x for x in IT if x['prev']>=3],key=lambda x:-(x['qty']/x['prev']))[:3];dn=sorted([x for x in IT if x['prev']>=3],key=lambda x:(x['qty']/x['prev']))[:3]
low=sorted([x for x in IT if x['qty']>0],key=lambda x:x['qty'])[:5]
side=f'<div class="h3" style="font-size:23px">الأكثر مبيعاً (كمية)</div><div class="dchart" style="padding:8px">{hbars([(short(x["name"]),x["qty"]) for x in sorted(IT,key=lambda x:-x["qty"])[:7]],760,44,MAR)}</div>'
side+=f'<div class="card" style="padding:12px 18px;font-size:18px;line-height:1.7"><b style="color:{G}">صاعد:</b> '+'، '.join(f'{short(x["name"])} ({chg(x["qty"],x["prev"])})' for x in up)+f'<br><b style="color:{RD}">هابط:</b> '+'، '.join(f'{short(x["name"])} ({chg(x["qty"],x["prev"])})' for x in dn)+f'<br><b style="color:{AM}">الأقل مبيعاً:</b> '+'، '.join(f'{short(x["name"])} ({f(x["qty"])})' for x in low)+'</div>'
sl('مبيعات الأصناف',f'{len(IT)} صنفاً مباعاً · مقارنة الكمية بالأسبوع السابق',f'<div class="row" style="gap:24px"><div class="col" style="flex:1.05">{tbl(["الصنف","الكمية","السابق","التغير","المبيعات ر.س","الحصة"],rows,"t sm",16)}</div><div class="col" style="flex:.95">{side}</div></div>')
# 4 menu engineering
ME=sorted(J['me'],key=lambda x:-x['qty'])
cc={'نجم':G,'حصان عمل':AM,'لغز':'#5B6F8A','ضعيف':RD}
rows=[(short(x['name']),f(x['qty']),f(x['price'],2),f(x['uc'],2),f(x['margin'],2),pc(x['mpct'],0),f'<span class="pill" style="background:{cc[x["cls"]]}22;color:{cc[x["cls"]]}">{x["cls"]}</span>') for x in ME[:13]]
leg=[('نجم','شعبي وهامشه عالٍ — حافظ عليه وأبرزه'),('حصان عمل','شعبي وهامشه أقل — راجع التكلفة أو السعر'),('لغز','هامش عالٍ ومبيعات أقل — روّج له'),('ضعيف','مبيعات وهامش أقل — طوّره أو استبدله')]
sl('هندسة المنيو (ربحية الأصناف)','السعر الصافي والتكلفة من الوصفات والهامش لكل صنف',f'<div class="row" style="gap:24px"><div class="col" style="flex:1.3">{tbl(["الصنف","الكمية","السعر الصافي","التكلفة","الهامش","هامش %","التصنيف"],rows,"t sm",16)}</div><div class="col" style="flex:.7">'+''.join(f'<div class="card" style="padding:14px 18px;border-right:7px solid {cc[a]}"><b style="color:{cc[a]};font-size:22px">{a}</b><div style="font-size:18px;color:#5b4a40">{b}</div></div>' for a,b in leg)+'</div></div>')
# 5 consumption
def qfmt(q,u):
    if u in('جم','g') and q>=1000: return f'{q/1000:,.2f} كجم'
    if u in('مل','ml') and q>=1000: return f'{q/1000:,.2f} لتر'
    return f'{q:,.0f} {u}'
cr=[(c['name'],qfmt(c['qty'],c['unit']),f(c['cost'],2),pc(c['cost']/J['COGS']*100,0)) for c in J['cl'][:13]]
sl('استهلاك المواد حسب الوصفات','الاستهلاك النظري للأسبوع من المبيعات × الوصفات — للمقارنة بالجرد',f'<div class="row" style="gap:26px"><div class="col" style="flex:1.1">{tbl(["المادة","الكمية","التكلفة ر.س","الحصة"],cr,"t sm",17)}</div><div class="col" style="flex:.9">'+
 kp([('تكلفة الأصناف ذات الوصفة',f(J['COGS'],2),f"ر.س · {J['COGS']/J['covered']*100:.1f}% من صافيها",MAR),('أصناف بدون وصفة',f(nr),'ر.س مبيعات · تكلفتها تقديرية',AM)],2)+
 f'<div class="card" style="padding:14px 20px;font-size:18px;line-height:1.7">بدون وصفة: '+'، '.join(f'{short(x["name"])} ({f(x["qty"])})' for x in sorted(J['norec'],key=lambda x:-x['sales']))+'</div><div class="card" style="padding:14px 20px;font-size:18px;color:#5b4a40">الأكواب الورقية وحدها: '+next((f"{f(c['qty'])} كوب بتكلفة {f(c['cost'],2)} ر.س" for c in J['cl'] if c['name']=='أكواب ورقية'),'—')+'</div></div></div>')
# 6 weekday comparison & forecast
rows=[(f"{x['wd']} {dar(x['day'])}",f(x['cur'],2))+tuple(f(v,2) for v in (x['h']+[0,0,0])[:3])+(chg(x['cur'],sum(x['h'])/len(x['h'])) if x['h'] else '—',) for x in J['cmp']]
fr=[(f"{x['wd']} {dar(x['day'])}",f(x['fc']),f"{f(x['lo'])} – {f(x['hi'])}",pill('فوق التعادل','ok') if x['fc']>=BE else pill('تحت التعادل','bad')) for x in J['fc']]
sl('المقارنات والتنبؤات',f"نفس اليوم في الأسابيع الثلاثة السابقة · وتوقع الأسبوع القادم (اتجاه آخر 14 يوماً {(J['trend']-1)*100:+.0f}%)",f'<div class="row" style="gap:24px"><div class="col" style="flex:1.1"><div class="h3" style="font-size:22px">مقارنة نفس اليوم</div>{tbl(["اليوم","هذا الأسبوع","قبل أسبوع","قبل أسبوعين","قبل 3 أسابيع","مقابل المتوسط"],rows,"t sm",15)}</div><div class="col" style="flex:.9"><div class="h3" style="font-size:22px">توقع الأسبوع القادم — {f(sum(x["fc"] for x in J["fc"]))} ر.س</div>{tbl(["اليوم","المتوقع","النطاق","الحالة"],fr,"t sm",16)}<div style="font-size:15px;color:#7a6658">الطريقة: متوسط نفس اليوم لآخر 4 أسابيع × اتجاه المبيعات الأخير. النطاق = أقل وأعلى قيمة تاريخية.</div></div></div>')
# 7 operations
O=J['ops']
sl('التشغيل والرقابة','',kp([('نماذج الورديات',str(O['dr']),f"في {O['dr_days']} أيام من 7 · إنجاز {O['dr_avg']:.0f}%",G if O['dr_days']>=7 else RD),('زيارات موثقة بالمنصة',str(O['vis']),'خلال الأسبوع',AM if not O['vis'] else G),
 ('نقد بدون إيصال',str(len(O['nocash'])),'وردية',RD if O['nocash'] else G),('فواتير شراء',str(len(O['pur'])),'سُجلت بالمنصة هذا الأسبوع',MAR)])+
 '<div class="card" style="padding:22px 28px;font-size:21px;line-height:1.85"><b style="color:'+MAR+'">التوصيات للأسبوع القادم:</b><br>• إلزام نموذج الوردية يومياً (صباح وليل) — سُجّل في يومين فقط هذا الأسبوع.<br>• تسجيل الزيارات الإشرافية في المنصة بعد كل زيارة.<br>• إيصال استلام لكل وردية فيها نقد في نفس اليوم.<br>• رفع المبيعات فوق التعادل: تنشيط ساعات الذروة والعروض على الأصناف «اللغز» ذات الهامش العالي.<br>• إكمال وصفات الأصناف بدون وصفة (المنتجات الشتوية، المعمول، Coffee Day).</div>')
tail=open('tail.txt').read()
tail=tail.replace("TAG='التقرير الشهري · أكتوبر 2026'",f"TAG='التقرير الأسبوعي · {PER}'")
tail=tail.replace('التقرير الشهري<br>أكتوبر 2026',f'التقرير الأسبوعي<br>{dar(J["WF"])} – {dar(J["WT"])}')
tail=tail.replace('المبيعات · مطابقة رواء والمنصة · الأصناف · المشتريات · نقطة التعادل · التنبؤات','المبيعات · الأصناف وهندسة المنيو · الاستهلاك · المقارنات والتنبؤات · التشغيل')
tail=tail.replace('الفترة: 1 – 31 أكتوبر 2026',f'الفترة: {PER}')
tail=tail.replace("open('report.html','w')",f"open('out/weekly_{WT}.html','w')")
exec(tail)
pdf=os.path.join(H,'out',f'حباق-التقرير-الأسبوعي-{J["WF"]}-{WT}.pdf')
r=subprocess.run(['node','pdf.js',os.path.join(H,'out',f'weekly_{WT}.html'),pdf,os.path.join(H,'out','wshots_'+WT)],capture_output=True,text=True);print(r.stdout.strip()[-200:],r.stderr[-300:]);print(pdf)
