const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});
for(const n of [1,2,3]){const p=await b.newPage({viewport:{width:1080,height:1350}});
await p.goto('file://'+__dirname+'/post'+n+'.html');await p.waitForTimeout(1500);await p.evaluate(()=>document.fonts.ready);
await p.screenshot({path:__dirname+'/nasaq-post-'+n+'.png'});}
await b.close()})();
