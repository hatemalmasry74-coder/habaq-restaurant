// usage: node api.js ops.json out.json  ; ops=[{m,u,body}]
(async () => {
  const fs=require('fs');const ops=JSON.parse(fs.readFileSync(process.argv[2]));const {b,ctx,p} = await require('./lib.js')();
  let hdr=null; p.on('request', r => { if(new RegExp(process.env.HPAT||'inventory-service').test(r.url()) && !hdr && r.headers()['authorization']) hdr=r.headers(); });
  await p.goto(process.env.HURL||'https://platform.rewaatech.com/inventory/products',{waitUntil:'domcontentloaded',timeout:90000}).catch(()=>{});
  for(let i=0;i<40&&!hdr;i++) await p.waitForTimeout(1000);
  const h={...hdr}; delete h['content-length']; h['content-type']='application/json';
  const out=[];
  for (const o of ops){ const r=await ctx.request.fetch('https://platform.rewaatech.com/api/'+o.u,{method:o.m,headers:h,data:o.body?JSON.stringify(o.body):undefined,timeout:60000});
    let t=await r.text(); let j;try{j=JSON.parse(t)}catch(e){j=t}
    out.push({key:o.key,status:r.status(),res:j}); console.log(o.m,o.u,r.status(),(typeof j==='string'?j:JSON.stringify(j)).slice(0,o.show||200)); await p.waitForTimeout(o.wait||400); }
  fs.writeFileSync(process.argv[3],JSON.stringify(out));
  await b.close();
})().catch(e=>console.log('ERR',e.message));
