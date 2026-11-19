import json,datetime,math,collections
QR=open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath('lib.py')),'qr.svg')).read().replace('<svg ','<svg style="width:100%;height:100%;display:block" ',1)
MAR,ACC,ORG,BRN,INK,CRM,SAND,LINE,GRN,RED='#8B2F2B','#A83C38','#B5621B','#8B6E55','#2C1A0E','#F5F0E8','#F0E7DA','#E0D8C8','#2E6B3F','#B3261E'
FONT="'Cairo',Tahoma,sans-serif"
def f(x,n=0): s=f"{abs(x):,.{n}f}";return ('−' if x<0 else '')+s
def bd(x,n=0): return f'<bdi dir="ltr">{f(x,n)}</bdi>'
def pc(x,n=1,sign=False): return f'<bdi dir="ltr">{"+" if sign and x>0 else ""}{x:.{n}f}%</bdi>'
PHONE='<bdi dir="ltr">+966 56 677 0809</bdi>'
AUTHOR,AUTHOR_T,GM,GM_T='حاتم عطية','مدير العمليات المالية والتشغيلية','أحمد القحطاني','المدير العام'
css=f'''@page{{size:1920px 1080px;margin:0}}*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:{FONT};color:{INK};direction:rtl;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.s{{width:1920px;height:1080px;position:relative;overflow:hidden;background:{CRM};page-break-after:always;display:flex;flex-direction:column;padding:64px 110px 110px}}
.wm{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-25deg);font-size:420px;font-weight:900;color:rgba(117,82,59,.05);white-space:nowrap}}
.hd{{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px solid {ACC};padding-bottom:16px;margin-bottom:30px;position:relative}}
.hd h2{{font-size:54px;font-weight:900;color:{MAR};line-height:1.15}}.hd .k{{font-size:25px;color:{ORG};font-weight:700;margin-top:4px}}
.brand{{text-align:left;font-size:21px;color:{BRN};font-weight:700;line-height:1.4}}.brand b{{display:block;font-size:30px;color:{MAR};font-weight:900}}
.ft{{position:absolute;left:0;right:0;bottom:0;height:62px;background:{MAR};color:rgba(255,255,255,.88);display:flex;justify-content:space-between;align-items:center;padding:0 110px;font-size:20px}}.ft b{{color:#fff}}
.body{{flex:1;position:relative;display:flex;flex-direction:column;gap:24px;min-height:0}}
.row{{display:flex;gap:44px;flex:1;align-items:stretch}}.col{{display:flex;flex-direction:column;gap:20px;flex:1;min-width:0}}
.kgrid{{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}}.k4{{grid-template-columns:repeat(4,1fr)}}
.kpi{{background:#fff;border:2px solid {LINE};border-radius:18px;padding:22px 30px;border-top:8px solid {ACC}}}
.kl{{font-size:24px;color:{BRN};font-weight:700}}.kv{{font-size:56px;font-weight:900;line-height:1.25}}.ks{{font-size:20px;color:{BRN}}}
.pos{{color:{GRN}!important}}.neg{{color:{RED}!important}}.b{{font-weight:800}}
.verdict{{background:{MAR};color:#fff;border-radius:18px;padding:26px 36px;font-size:27px;line-height:1.7}}.verdict b{{color:#F3D9B1}}
.t{{width:100%;border-collapse:collapse;background:#fff;border-radius:14px;overflow:hidden;font-size:23px;font-variant-numeric:tabular-nums}}
.t th{{background:{MAR};color:#fff;font-weight:700;padding:11px 14px;text-align:right;font-size:21px}}
.t td{{padding:8px 14px;border-top:1.5px solid {LINE}}}.t tr:nth-child(even) td{{background:#FBF8F3}}.t td.nm{{font-weight:700}}.t tr.tot td{{background:{SAND}!important;font-weight:900}}
.t.sm{{font-size:20px}}.t.sm td{{padding:6px 12px}}.t.sm th{{font-size:18px;padding:8px 12px}}
.note{{font-size:21px;color:{BRN};line-height:1.6}}
.card{{background:#fff;border:2px solid {LINE};border-radius:18px;padding:22px 28px}}
.h3{{font-size:30px;font-weight:900;color:{MAR}}}
.pill{{padding:2px 12px;border-radius:999px;font-weight:800;font-size:19px;white-space:nowrap}}.ok{{background:#E3F0E6;color:{GRN}}}.warn{{background:#FBF0D9;color:#9A6400}}.bad{{background:#FBE4E2;color:{RED}}}
.fgrid{{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;flex:1;align-content:center}}
.fc{{background:#fff;border:2px solid {LINE};border-radius:18px;padding:22px 26px;border-top:8px solid {ORG}}}.fc.good{{border-top-color:{GRN}}}.fc.crit{{border-top-color:{RED}}}
.fc h3{{font-size:28px;font-weight:900;color:{MAR};margin-bottom:8px}}.fc p{{font-size:21px;line-height:1.6}}
.dchart{{background:#fff;border:2px solid {LINE};border-radius:18px;padding:18px 22px}}
.plr{{display:flex;justify-content:space-between;font-size:26px;padding:9px 0;border-bottom:1.5px dashed {LINE}}}.plr.tot{{font-weight:800;border-bottom:2px solid {INK}}}.plr.fin{{border:0;font-weight:900;font-size:34px}}
'''
def vbars(data,w,h,cols,fmt=f,sub=None,line=None,line_lbl='نقطة التعادل',fs=24,lfs=22):
    n=len(data);vals=[v for _,v in data]+([line] if line else []);mx=max(max(vals),0)*1.15;mn=min(min(vals),0)*1.25
    RM=190 if line else 0;gap=(w-RM)/n;bw=gap*0.58;top=36;bot=h-(92 if sub else 64)
    Y=lambda v:top+(mx-v)/(mx-mn)*(bot-top);o=[f'<line x1="0" y1="{Y(0):.1f}" x2="{w-RM}" y2="{Y(0):.1f}" stroke="{LINE}" stroke-width="2"/>']
    for k,(lab,v) in enumerate(data):
        x=w-RM-(k+0.5)*gap;y0,y1=sorted((Y(0),Y(v)))
        o.append(f'<rect x="{x-bw/2:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{max(y1-y0,1):.1f}" rx="5" fill="{cols[k]}"/>')
        ty=(Y(v)-10) if v>=0 else ((Y(0)-10) if Y(v)-Y(0)<fs+18 else (Y(v)+fs+4))
        o.append(f'<text x="{x:.1f}" y="{ty:.1f}" text-anchor="middle" font-family="{FONT}" font-size="{fs}" font-weight="800" fill="{INK}">{fmt(v)}</text>')
        o.append(f'<text direction="rtl" x="{x:.1f}" y="{bot+36}" text-anchor="middle" font-family="{FONT}" font-size="{lfs}" font-weight="700" fill="{INK}">{lab}</text>')
        if sub: o.append(f'<text direction="rtl" x="{x:.1f}" y="{bot+68}" text-anchor="middle" font-family="{FONT}" font-size="{lfs-3}" fill="{BRN}">{sub[k]}</text>')
    if line:
        y=Y(line);o.append(f'<line x1="0" y1="{y:.1f}" x2="{w-RM+10}" y2="{y:.1f}" stroke="{RED}" stroke-width="4" stroke-dasharray="14 10"/>')
        o.append(f'<rect x="{w-RM+14}" y="{y-48:.1f}" width="{RM-14}" height="96" rx="10" fill="{RED}"/><text direction="rtl" x="{w-RM/2+7}" y="{y-10:.1f}" text-anchor="middle" font-family="{FONT}" font-size="21" font-weight="700" fill="#fff">{line_lbl}</text><text x="{w-RM/2+7}" y="{y+28:.1f}" text-anchor="middle" font-family="{FONT}" font-size="30" font-weight="900" fill="#fff">{f(line)}</text>')
    return f'<svg direction="ltr" style="direction:ltr" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(o)}</svg>'
def daily(days,w=1680,h=560,BE=None):
    n=len(days);mx=max(max(v for _,v,_ in days),BE)*1.1;RM=190;gap=(w-RM)/n;bw=gap*0.66;top=30;bot=h-74
    Y=lambda v:top+(mx-v)/mx*(bot-top);o=[f'<line x1="0" y1="{bot}" x2="{w-RM}" y2="{bot}" stroke="{LINE}" stroke-width="2"/>']
    for k,(d,v,v2) in enumerate(days):
        dt=datetime.date.fromisoformat(d);x=w-RM-(k+0.5)*gap;c=GRN if v>=BE else (ORG if v>=BE*0.8 else RED)
        o.append(f'<rect x="{x-bw/2:.1f}" y="{Y(v):.1f}" width="{bw:.1f}" height="{bot-Y(v):.1f}" rx="3" fill="{c}"/>')
        if v2: o.append(f'<circle cx="{x:.1f}" cy="{Y(v2):.1f}" r="6" fill="#fff" stroke="{INK}" stroke-width="2.5"/>')
        o.append(f'<text x="{x:.1f}" y="{bot+28}" text-anchor="middle" font-family="{FONT}" font-size="19" font-weight="700" fill="{INK}">{dt.day}</text>')
        if dt.weekday()==4: o.append(f'<text direction="rtl" x="{x:.1f}" y="{bot+54}" text-anchor="middle" font-family="{FONT}" font-size="15" fill="{BRN}">جمعة</text>')
    y=Y(BE);o.append(f'<line x1="0" y1="{y:.1f}" x2="{w-RM+10}" y2="{y:.1f}" stroke="{RED}" stroke-width="3.5" stroke-dasharray="12 9"/>')
    o.append(f'<rect x="{w-RM+14}" y="{y-46:.1f}" width="{RM-14}" height="92" rx="10" fill="{RED}"/><text direction="rtl" x="{w-RM/2+7}" y="{y-8:.1f}" text-anchor="middle" font-family="{FONT}" font-size="21" font-weight="700" fill="#fff">نقطة التعادل</text><text x="{w-RM/2+7}" y="{y+28:.1f}" text-anchor="middle" font-family="{FONT}" font-size="29" font-weight="900" fill="#fff">{f(BE)}</text>')
    return f'<svg direction="ltr" style="direction:ltr" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(o)}</svg>'
def hbars(data,w=900,rowh=54,col=MAR):
    mx=max(v for _,v in data);lw=360;bw=w-lw-120;o=[]
    for k,(lab,v) in enumerate(data):
        y=k*rowh;bl=v/mx*bw
        o.append(f'<text x="{w}" y="{y+rowh/2+8}" text-anchor="end" font-family="{FONT}" font-size="23" font-weight="600" fill="{INK}">{lab}</text>')
        o.append(f'<rect x="{w-lw-bl}" y="{y+9}" width="{bl:.1f}" height="{rowh-18}" rx="5" fill="{col}"/>')
        o.append(f'<text x="{w-lw-bl-12}" y="{y+rowh/2+8}" text-anchor="end" font-family="{FONT}" font-size="23" font-weight="700" fill="{INK}">{f(v)}</text>')
    return f'<svg direction="ltr" style="direction:ltr" width="{w}" height="{rowh*len(data)}" viewBox="0 0 {w} {rowh*len(data)}">{"".join(o)}</svg>'
def donut(parts,size=380,hole=0.6,center=('','')):
    Rr=size/2;r=Rr*hole;cx=cy=Rr;tot=sum(v for _,v,_ in parts);a=-math.pi/2;o=[]
    for lab,v,col in parts:
        if v<=0: continue
        b=a+2*math.pi*v/tot;lg=1 if b-a>math.pi else 0
        p=lambda R_,t:(cx+R_*math.cos(t),cy+R_*math.sin(t));x1,y1=p(Rr,a);x2,y2=p(Rr,b);x3,y3=p(r,b);x4,y4=p(r,a)
        o.append(f'<path d="M{x1:.1f},{y1:.1f} A{Rr},{Rr} 0 {lg} 1 {x2:.1f},{y2:.1f} L{x3:.1f},{y3:.1f} A{r},{r} 0 {lg} 0 {x4:.1f},{y4:.1f} Z" fill="{col}" stroke="{CRM}" stroke-width="4"/>');a=b
    o.append(f'<text x="{cx}" y="{cy-4}" text-anchor="middle" font-family="{FONT}" font-size="{int(size/10)}" font-weight="900" fill="{INK}">{center[0]}</text><text x="{cx}" y="{cy+size/12}" text-anchor="middle" font-family="{FONT}" font-size="{int(size/20)}" fill="{BRN}">{center[1]}</text>')
    return f'<svg direction="ltr" style="direction:ltr" width="{size}" height="{size}" viewBox="0 0 {size} {size}">{"".join(o)}</svg>'
def legend(parts,tot):
    return '<div style="display:flex;flex-direction:column;gap:12px;min-width:520px">'+''.join(f'<div style="display:grid;grid-template-columns:28px 1fr 170px 100px;gap:14px;align-items:center;font-size:24px;background:#fff;border-radius:12px;padding:10px 18px;border:1.5px solid {LINE}"><span style="width:24px;height:24px;border-radius:6px;background:{c}"></span><b>{l}</b><span style="text-align:left">{f(v)}</span><span style="text-align:left;font-weight:800;color:{MAR}">{v/tot*100:.1f}%</span></div>' for l,v,c in parts)+'</div>'
def qrbox(size,cap,dark=False):
    return f'<div style="display:flex;align-items:center;gap:18px"><div style="width:{size}px;height:{size}px;background:#fff;border-radius:14px;padding:10px;border:2px solid {LINE}">{QR}</div><div style="font-size:19px;line-height:1.6;color:{"#fff" if dark else BRN}"><b style="font-size:23px">نَسَق لحلول الأعمال والتشغيل</b><br>Nassaq Operations &amp; Business Solutions<br>{cap}</div></div>'
S=[];sl=lambda t,k,b:S.append((t,k,b))
