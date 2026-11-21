// node weekly_pull.js HIST_FROM HIST_TO W_FROM W_TO P_FROM P_TO out.json
(async () => {
  const fs=require('fs');const {b,ctx,p} = await require('./lib.js')();
  let hdr=null; p.on('request', r => { const h=r.headers(); if(h['authorization']&&/reporting-bridge/.test(r.url())&&!hdr) hdr=h; });
  for(let i=0;i<40&&!hdr;i++) await p.waitForTimeout(1000);
  const H={...hdr};delete H['content-length'];
  const g=async u=>{for(let t=0;t<3;t++){const r=await ctx.request.get(u,{headers:H,timeout:60000}); if(r.ok()) return await r.json(); await p.waitForTimeout(2000);} return null;};
  const A=process.argv, out={days:{}};
  for(let d=new Date(A[2]+'T00:00:00Z'); d<=new Date(A[3]+'T00:00:00Z'); d.setUTCDate(d.getUTCDate()+1)){
    const ds=d.toISOString().slice(0,10), q=`startDate=${ds}T00:00:00.000Z&endDate=${ds}T23:59:59.999Z`;
    out.days[ds]={pay:await g(`https://platform.rewaatech.com/api/reporting-bridge/dashboard/payment-methods-report?${q}&location=&timezone=UTC&startTime=00:00:00&endTime=23:59:59`),sum:await g(`https://platform.rewaatech.com/api/reporting-bridge/sales/timeperiod/summary/v2?${q}`)};
    console.log(ds, out.days[ds].sum?out.days[ds].sum.totalSalesTaxInclusive:'-');
  }
  const items=async(from,to)=>{let all=[],off=0;const q=`startDate=${from}T00:00:00.000Z&endDate=${to}T23:59:59.999Z`;while(true){const r=await g(`https://platform.rewaatech.com/api/reporting-bridge/sales/timeperiod/product-sales?${q}&limit=200&offset=${off}&sortField=net_sales&sortOrder=desc&timezone=UTC`);const a=(r&&r.results)||[];all=all.concat(a);if(a.length<200)break;off+=200;}return all;};
  out.items_w=await items(A[4],A[5]); out.items_p=await items(A[6],A[7]); console.log('items',out.items_w.length,out.items_p.length);
  fs.writeFileSync(A[8],JSON.stringify(out)); await b.close();
})().catch(e=>console.log('ERR',e.message));
