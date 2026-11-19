(async () => {
  const fs=require('fs');const {b,ctx,p} = await require('./lib.js')();const pick=require('./calpick.js');
  p.setDefaultTimeout(8000);
  const A=JSON.parse(process.argv[2]);
  p.on('response', async r => { if(/return|purchase-order|stock-control/.test(r.url()) && ['POST','PUT'].includes(r.request().method())) { let t='';try{t=await r.text()}catch(e){} console.log('RESP',r.status(),r.url().slice(0,100),t.slice(0,400)); } });
  const step=async(n,f)=>{try{const x=await f();console.log('ok',n,x||'')}catch(e){console.log('FAIL',n,e.message.split('\n')[0])}};
  await p.goto(A.url,{waitUntil:'commit',timeout:60000}).catch(()=>{});
  await p.waitForTimeout(14000);
  await step('sup',async()=>{ const s=p.locator('p-autocomplete[formcontrolname=supplier] input'); await s.click(); await s.fill(A.sup); await p.waitForTimeout(3000); await p.locator('li').filter({hasText:A.sup}).first().click(); await p.waitForTimeout(1500);});
  await step('date',async()=>await pick(p,p.locator('p-calendar[formcontrolname=issueDate]'),A.date));
  await step('invno',async()=>{ await p.locator('input[formcontrolname=supplierInvoiceNumber]').fill(A.no);});
  if(A.notes) await step('notes',async()=>{ await p.locator('textarea').first().fill(A.notes);});
  for(const it of A.items){
    await step('prod',async()=>{ const pv=p.locator('input[placeholder="أدخل اسم المنتج أو رمز SKU"]'); await pv.click(); await pv.fill(it.q); await p.waitForTimeout(4000); await p.locator('li').filter({hasText:it.q}).first().click(); await p.waitForTimeout(3500);});
    await step('qty',async()=>{ const ins=await p.evaluate(()=>[...document.querySelectorAll('input')].map(a=>a.getAttribute('formcontrolname')).filter(Boolean)); console.log('   fcs',ins.join(','));
       const q=p.locator('input[formcontrolname=newQuantity], input[formcontrolname=returnQuantity]').last(); await q.click(); await q.fill(String(it.qty)); await q.press('Tab');});
    await step('cost',async()=>{ const c=p.locator('input[formcontrolname=cost]').last(); if(await c.count() && it.cost){ await c.click(); await c.fill(String(it.cost)); await c.press('Tab');} });
    if(it.tax) await step('tax',async()=>{ const dd=p.locator('p-dropdown[formcontrolname=taxId]').last(); await dd.locator('.p-dropdown-trigger').click(); await p.waitForTimeout(1500); const opts=await p.locator('.p-dropdown-item').allInnerTexts(); console.log('   taxopts',opts.join(' | ')); await p.locator('.p-dropdown-item').filter({hasText:it.tax}).first().click(); await p.waitForTimeout(1500); });
  }
  await step('paid',async()=>{ const r=p.locator('p-radiobutton, .p-radiobutton').first(); await r.scrollIntoViewIfNeeded(); await r.click(); await p.waitForTimeout(2000);});
  await step('method',async()=>{ const all=await p.locator('p-dropdown').all(); let target=null; for(const d of all){ if((await d.getAttribute('formcontrolname'))!=='taxId') target=d; } await target.locator('.p-dropdown-trigger').click(); await p.waitForTimeout(1500); await p.locator('.p-dropdown-item,[role=option]').filter({hasText:A.pay}).first().click(); await p.waitForTimeout(800);});
  await step('amount',async()=>{ const a=p.locator('input[formcontrolname=amount]'); if(await a.count()){ await a.fill(String(A.amount)); await a.press('Tab'); }});
  await step('due',async()=>{ const cs=await p.locator('p-calendar[formcontrolname=paymentDueDate]').all(); for(const c of cs){ if(await c.isVisible()) return await pick(p,c,A.due); } });
  await step('deliv',async()=>{ const cs=await p.locator('p-calendar[formcontrolname=deliveryDate]').all(); for(const c of cs){ if(await c.isVisible()) return await pick(p,c,A.date); } });
  await p.evaluate(()=>window.scrollTo(0,document.body.scrollHeight)); await p.waitForTimeout(800);
  await p.screenshot({path:A.shot}); fs.writeFileSync(A.shot+'.txt',await p.evaluate(()=>document.body.innerText));
  if(A.go) await step('submit',async()=>{ const bt=p.locator('button').filter({hasText:A.action}).last(); console.log('   enabled',await bt.isEnabled()); await bt.click(); await p.waitForTimeout(9000);});
  console.log('AT',p.url());
  await b.close();
})().catch(e=>console.log('ERR',e.message));
