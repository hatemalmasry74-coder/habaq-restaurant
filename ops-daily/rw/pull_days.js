// usage: node pull_days.js FROM TO out.json  -> per UTC day: payment methods + sales summary ; plus products (buyPrice)
(async () => {
  const fs=require('fs');const {b,ctx,p} = await require('./lib.js')();
  let hdr=null,ihdr=null;
  p.on('request', r => { const h=r.headers(); if(!h['authorization'])return; if(/reporting-bridge/.test(r.url())&&!hdr) hdr=h; if(/inventory-service/.test(r.url())&&!ihdr) ihdr=h; });
  for(let i=0;i<40&&!hdr;i++) await p.waitForTimeout(1000);
  const H=x=>{const h={...x};delete h['content-length'];return h;};
  const g=async(u,h)=>{for(let t=0;t<3;t++){const r=await ctx.request.get(u,{headers:H(h),timeout:60000}); if(r.ok()) return await r.json(); await p.waitForTimeout(2000);} return null;};
  const out={days:{},products:[]};
  for(let d=new Date(process.argv[2]+'T00:00:00Z'); d<=new Date(process.argv[3]+'T00:00:00Z'); d.setUTCDate(d.getUTCDate()+1)){
    const ds=d.toISOString().slice(0,10), q=`startDate=${ds}T00:00:00.000Z&endDate=${ds}T23:59:59.999Z`;
    const pay=await g(`https://platform.rewaatech.com/api/reporting-bridge/dashboard/payment-methods-report?${q}&location=&timezone=UTC&startTime=00:00:00&endTime=23:59:59`,hdr);
    const sum=await g(`https://platform.rewaatech.com/api/reporting-bridge/sales/timeperiod/summary/v2?${q}`,hdr);
    out.days[ds]={pay,sum}; console.log(ds, pay?'ok':'fail', sum?sum.totalSalesTaxInclusive:'-');
  }
  const items=async(from,to)=>{let all=[],off=0;const q=`startDate=${from}T00:00:00.000Z&endDate=${to}T23:59:59.999Z`;while(true){const r=await g(`https://platform.rewaatech.com/api/reporting-bridge/sales/timeperiod/product-sales?${q}&limit=200&offset=${off}&sortField=net_sales&sortOrder=desc&timezone=UTC`,hdr);const a=(r&&r.results)||[];all=all.concat(a);if(a.length<200)break;off+=200;}return all;};
  out.items_day=await items(process.argv[3],process.argv[3]); out.items_mtd=await items(process.argv[2],process.argv[3]); console.log('items',out.items_day.length,out.items_mtd.length);
  await p.goto('https://platform.rewaatech.com/inventory/products',{waitUntil:'domcontentloaded',timeout:90000}).catch(()=>{});
  for(let i=0;i<40&&!ihdr;i++) await p.waitForTimeout(1000);
  if(ihdr){ for(let off=0;off<1000;off+=100){ const r=await g(`https://platform.rewaatech.com/api/inventory-service/variants/v2?fromDate=&toDate=&search=&scannerCode=&channel=&type=&offset=${off}&limit=100&sortBy=createdAt&sortDirection=desc&filters=&stockLocationIds=%5B1%5D`,ihdr); const arr=(r&&(r.result||r.data||r.variants))||[]; out.products=out.products.concat(arr); if(arr.length<100)break; } }
  fs.writeFileSync(process.argv[4],JSON.stringify(out)); console.log('products',out.products.length);
  await b.close();
})().catch(e=>console.log('ERR',e.message));
