const { chromium } = require('playwright');
const C=require(require('path').join(__dirname,'..','creds.json'));
module.exports = async function(){
  const b = await chromium.launch();
  const ctx = await b.newContext({ locale: 'ar-SA', viewport:{width:1440,height:900} });
  const p = await ctx.newPage();
  await p.goto('https://platform.rewaatech.com/ar/mfe/login', { waitUntil: 'networkidle', timeout: 60000 });
  await p.getByRole('button', { name: 'تسجيل الدخول بالبريد الإلكتروني' }).click();
  await p.locator('input[type=email]').fill(C.rewaa_email);
  await p.locator('input[type=password]').fill(C.rewaa_password);
  await p.keyboard.press('Enter');
  await p.waitForURL(/home/, {timeout:60000});
  return {b,ctx,p};
}
