# European defaults: 230 V / 16 A, Schuko / CEE / Socapex distribution, powerCON TRUE1 and etherCON cable names, A4 label sheets.
import asyncio, sys
from playwright.async_api import async_playwright
APP = '/home/claude/tilesmith-desktop/app/index.html'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1500, 'height': 900})
        errs = []; pg.on('pageerror', lambda e: errs.push(str(e)))
        await pg.goto('file://' + APP); await pg.evaluate("()=>{localStorage.clear()}"); await pg.reload(); await pg.wait_for_timeout(800)
        ok = True
        def chk(c, m):
            nonlocal ok
            print(('PASS ' if c else 'FAIL ') + m); ok = ok and c
        d = await pg.evaluate("()=>({v:S.pvolt,a:S.pamps,w:S.pwallA,pdt:S.pdt,name:PD().name,circ:circW(),volts:[...document.querySelector('[data-k=pvolt]').options].map(o=>+o.value),data:S.drDataCable,pow:S.drPowCable,first:Object.keys(PDT)[0]})")
        chk(d['v'] == 230 and d['a'] == 16 and d['w'] == 16, f"defaults are 230 V, 16 A breaker, 16 A wall circuit {d['v'], d['a'], d['w']}")
        chk(d['name'] == 'Schuko' and d['pdt'] == d['first'], f"default distribution is powerCON TRUE1 to Schuko, and it is the fallback {d['pdt']}")
        chk(abs(d['circ'] - 230 * 16 * .8) < 1e-6 and d['volts'][0] == 230, f"one circuit carries {d['circ']} W at 80 %, 230 V listed first")
        chk(d['data'] == 'CAT6 etherCON' and d['pow'] == 'powerCON TRUE1', f"drawing cable types are CAT6 etherCON and powerCON TRUE1")
        k = await pg.evaluate("()=>Object.keys(PDT)")
        chk(all(x in k for x in ['powerCON TRUE1 to CEE 16 A (1 circuit per cable)', 'CEE 16 A 3-phase (3 circuits per cable)', 'CEE 32 A 3-phase (3 circuits per cable)', 'Socapex (6 circuits per cable)']) and k.index('Socapex (6 circuits per cable)') < k.index('L14-30 (2 circuits per cable)'), 'European cables come first, the North American ones stay at the end')
        await pg.evaluate("()=>{S.pdist=true;storeWall();sync();document.querySelectorAll('#left details').forEach(d=>d.open=true)}")
        await pg.select_option('[data-k=pdt]', 'CEE 16 A 3-phase (3 circuits per cable)')
        lab = await pg.evaluate("()=>[1,2,3,4].map(cLabel)")
        chk(lab == ['1-L1', '1-L2', '1-L3', '2-L1'], f'3-phase CEE cables label the phases L1, L2, L3 {lab}')
        await pg.select_option('[data-k=pdt]', 'powerCON TRUE1 to CEE 16 A (1 circuit per cable)')
        chk(await pg.evaluate("()=>S.pvolt==230&&S.pamps==16"), 'single CEE 16 A circuits are 230 V, 16 A')
        await pg.select_option('[data-k=pdt]', 'powerCON to Edison (1 circuit per cable)')
        chk(await pg.evaluate("()=>S.pvolt==120&&S.pamps==15"), 'the Edison option still works for tours (120 V, 15 A)')
        await pg.select_option('[data-k=pdt]', 'powerCON TRUE1 to Schuko (1 circuit per cable)')
        rows = await pg.evaluate("()=>{S.pdist=true;S.pmode='Snake';S.cols=6;S.rows=4;storeWall();sync();return specSections().flatMap(([t,r])=>r.map(x=>x[0]))}")
        chk('Schuko plugs needed' in rows and not any('Edison' in r for r in rows), 'engineering names Schuko plugs, not Edison')
        g = await pg.evaluate("()=>{const g=LBL[S.lblSize];return{n:S.lblSize,w:g.pw,h:g.ph,fx:2*g.x+g.c*g.w+(g.c-1)*g.gx,fy:2*g.y+g.r*g.h+(g.r-1)*g.gy,first:Object.keys(LBL)[0]}}")
        chk(g['n'] == g['first'] and g['w'] == 210 and abs(g['fx'] - 210) < .5 and abs(g['fy'] - 297) < .5, f"default label sheet is an A4 sheet that fits the page {g}")
        chk(not errs, f'no page errors {errs[:3]}')
        await b.close(); print('ALL OK' if ok else 'FAILED'); sys.exit(0 if ok else 1)
asyncio.run(main())
