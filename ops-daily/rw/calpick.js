// pick date in a PrimeNG p-calendar: (page, calendarLocator, {y,m(1-12),d})
const AR={'يناير':1,'فبراير':2,'مارس':3,'أبريل':4,'إبريل':4,'مايو':5,'يونيو':6,'يوليو':7,'أغسطس':8,'سبتمبر':9,'أكتوبر':10,'نوفمبر':11,'ديسمبر':12,'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,'July':7,'August':8,'September':9,'October':10,'November':11,'December':12};
module.exports=async function(p,cal,t){
  const btn=cal.locator('button'); if(await btn.count()) await btn.first().click(); else await cal.locator('input').first().click();
  await p.waitForTimeout(1200);
  for(let k=0;k<24;k++){
    const mt=(await p.locator('.p-datepicker .p-datepicker-month').first().innerText()).trim();
    const yt=parseInt((await p.locator('.p-datepicker .p-datepicker-year').first().innerText()).trim());
    const m=AR[mt]; if(!m) throw new Error('month? '+mt);
    if(yt===t.y && m===t.m) break;
    const back=(yt>t.y)||(yt===t.y&&m>t.m);
    await p.locator(back?'.p-datepicker-prev':'.p-datepicker-next').first().click(); await p.waitForTimeout(300);
  }
  await p.locator('.p-datepicker td:not(.p-datepicker-other-month) span:not(.p-disabled)').filter({hasText:new RegExp('^'+t.d+'$')}).first().click();
  await p.waitForTimeout(800);
  return await cal.locator('input').first().inputValue();
};
