# Drawings (Engineering > Drawings): section placement, one sheet per canvas, drag and drop, notes, project round trip, PDF export.
import asyncio, sys, os, tempfile, json
from playwright.async_api import async_playwright
APP = '/home/claude/tilesmith-desktop/app/index.html'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(accept_downloads=True, viewport={'width': 1500, 'height': 900}); pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('file://' + APP); await pg.wait_for_timeout(800)
        ok = True
        def chk(c, m):
            nonlocal ok
            print(('PASS ' if c else 'FAIL ') + m); ok = ok and c
        chk(await pg.evaluate("()=>{const s=[...document.querySelectorAll('#left summary')].find(x=>x.textContent.trim()=='Drawings');let q=s;while(q&&q.parentElement&&q.parentElement.id!='left')q=q.parentElement;return !!q&&q.querySelector('summary').textContent.trim()=='Engineering'}"), 'Drawings sits under Engineering')
        await pg.evaluate("()=>{S.cols=6;S.rows=3;storeWall();addWall(false);S.drTitle='Test';sync();drwOpen()}"); await pg.wait_for_timeout(300)
        d = await pg.evaluate("()=>{const d=$('#drwStage')._d;return{n:d.items.length,N:d.N,tiles:d.items.filter(i=>i.t=='rect'&&i.g).length}}")
        chk(d['n'] > 50 and d['N'] >= 5, f'sheet is built with a scale {d}')
        chk(await pg.evaluate("()=>$('#drwStage')._d.items.filter(i=>i.t=='text'&&i.s=='3000 mm').length")==1, 'wall width is dimensioned in mm')
        bx = await pg.evaluate("()=>{const e=document.querySelector('#drwStage [data-g=\"w1\"]').getBoundingClientRect();return[e.left+e.width/2,e.top+e.height/2]}")
        await pg.mouse.move(*bx); await pg.mouse.down(); await pg.mouse.move(bx[0] + 40, bx[1] + 60, steps=5); await pg.mouse.up()
        dd = await pg.evaluate("()=>[walls[1].dx,walls[1].dy,S.dx,S.dy,cur]")
        chk(dd[0] > 0 and dd[1] > 0 and dd[0] == dd[2] and dd[1] == dd[3] and dd[4] == 1, f'dragging a wall moves it on the sheet {dd}')
        await pg.click('[data-d=note]'); await pg.keyboard.type('Truss'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        chk(await pg.evaluate("()=>S.drNotes.length==1&&S.drNotes[0].t=='Truss'"), 'a note can be added and edited')
        o = json.loads(await pg.evaluate("()=>{const o=stateObj();return JSON.stringify({w:o.walls.map(w=>({dx:w.dx,dy:w.dy})),n:o.S.drNotes})}"))
        await pg.evaluate("()=>{walls.forEach(w=>{w.dx=0;w.dy=0});S.dx=S.dy=0;S.drNotes=[]}")
        await pg.evaluate("(s)=>applyState(JSON.parse(s))", json.dumps({'sv': 23, 'S': {'drNotes': o['n']}, 'walls': o['w']}))
        chk(await pg.evaluate("()=>S.drNotes.length==1&&walls.length==2&&walls[1].dx>0"), 'drawing positions and notes come back when a project is opened')
        await pg.click('[data-d=reset]'); chk(await pg.evaluate("()=>walls.every(w=>!w.dx&&!w.dy)&&S.drNotes.length==0"), 'Reset layout clears positions and notes')
        async with pg.expect_download() as dl: await pg.click('[data-d=pdf]')
        f = await dl.value; path = os.path.join(tempfile.mkdtemp(), 'd.pdf'); await f.save_as(path); data = open(path, 'rb').read()
        chk(data[:5] == b'%PDF-' and b'/Type /Page ' in data and f.suggested_filename.startswith('TileSmith-drawings-'), f'PDF exported ({len(data)} bytes)')
        await pg.keyboard.press('Escape'); chk(await pg.evaluate("()=>!document.getElementById('drwEd')"), 'Escape closes the editor')
        chk(not errs, f'no page errors {errs[:3]}')
        await b.close(); print('ALL OK' if ok else 'FAILED'); sys.exit(0 if ok else 1)
asyncio.run(main())
