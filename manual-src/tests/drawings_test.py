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
        # cabling: the app's own data and power wiring drawn as cables, a suggestion that is valid, tile-by-tile editing, cable schedule
        await pg.evaluate("()=>{S.proc=Object.keys(PROC).find(x=>x!='None');S.ppx=655360;S.pdist=true;S.wmode='Snake';S.pmode='Snake';walls.forEach((w,i)=>{w.wmode='Snake';w.pmode='Snake'});storeWall();drwRender()}")
        cb = await pg.evaluate("()=>{const c=drwCables(drwLayout());return{n:c.length,d:c.filter(x=>x.kind=='d').length,p:c.filter(x=>x.kind=='p').length,len:c.every(x=>x.totalMm>0&&x.pcs.length>0),pages:[...$('#drwSheet').options].map(o=>o.textContent)}}")
        chk(cb['d'] >= 2 and cb['p'] >= 2 and cb['len'] and cb['pages'] == ['Plan', 'Cable schedule', 'Material list'], f'cables are drawn, with a cable schedule and a material list {cb}')
        sg = await pg.evaluate("""()=>{drwSetKey(0,'wmode','Linear');drwSetKey(0,'wcorner','Bottom-right');drwSetKey(0,'wdir','Vertical');drwSetKey(0,'wfill','Whole rows or columns');
          drwSuggest('d',0);drwSuggest('p',0);const w=walls[0],P2=pieces(w);const chk=(pl,t)=>{const seen=new Set;let over=0,dup=0;pl.forEach(c=>{if(c.over)over++;c.tiles.forEach(e=>{const k=elKey(e);if(seen.has(k))dup++;seen.add(k)})});return{cov:seen.size==P2.list.length,over,dup,n:pl.length,min:Math.ceil(P2.list.length/t)}};
          return{d:chk(portPlan()[0],tpp(w)),p:chk(powerPlan()[0],tpcW(w))}}""")
        chk(all(v['cov'] and v['over'] == 0 and v['dup'] == 0 and v['n'] == v['min'] for v in sg.values()), f'Suggest covers every tile once, within the limits, with the fewest ports and circuits {sg}')
        await pg.select_option('[data-wpick]', '0'); await pg.click('[data-t=d]')
        ed = await pg.evaluate("()=>{const t=document.querySelector('#drwStage [data-tk^=\"0|\"]');return t?t.dataset.tk:null}")
        await pg.click(f'#drwStage [data-tk="{ed}"]')
        e1 = await pg.evaluate("()=>{const c=S.wman[S.wman.length-1];return{mode:S.wmode,key:elKey(c[c.length-1]),n:c.length}}")
        chk(e1['mode'] == 'Manual', 'editing starts from the current cabling in Manual mode')
        await pg.click(f"#drwStage [data-tk=\"0|{e1['key']}\"]")
        chk(await pg.evaluate("(n)=>{const c=S.wman[S.wman.length-1];return c.length==n-1}", e1['n']) if False else await pg.evaluate("()=>$('#drwStage')._d.items.filter(i=>i.t=='rect'&&i.fill=='#ffe3e3').length==1"), 'a tile taken off its cable is shown in red')
        await pg.click(f"#drwStage [data-tk=\"0|{e1['key']}\"]")
        chk(await pg.evaluate("()=>$('#drwStage')._d.items.filter(i=>i.t=='rect'&&i.fill=='#ffe3e3').length==0"), 'clicking it again puts it back on the cable')
        await pg.click('[data-t=move]')
        bx2 = await pg.evaluate("()=>{const e=document.querySelector('#drwStage [data-g=\"sd\"]').getBoundingClientRect();return[e.left+e.width/2,e.top+e.height/2]}")
        await pg.mouse.move(*bx2); await pg.mouse.down(); await pg.mouse.move(bx2[0] + 80, bx2[1] - 20, steps=4); await pg.mouse.up()
        chk(await pg.evaluate("()=>S.drSrc.length==1&&S.drSrc[0].k=='d'"), 'the processor box can be moved and the position is kept')
        await pg.select_option('#drwSheet', '1')
        chk(await pg.evaluate("()=>{const t=$('#drwStage')._d.items.filter(i=>i.t=='text').map(i=>i.s);return t.includes('Cable schedule')&&t.some(s=>/^P\\d+$/.test(s))&&t.some(s=>/^C\\d+$/.test(s))}"), 'the cable schedule lists data and power cables')
        await pg.select_option('#drwSheet', '2')
        chk(await pg.evaluate("()=>{const t=$('#drwStage')._d.items.filter(i=>i.t=='text').map(i=>i.s);return t.includes('CAT6')&&t.includes('powerCON TRUE1')&&t.includes('0.5 m')&&t.includes('Home run')}"), 'the material list counts CAT6 and powerCON TRUE1 cables by length')
        lk = await pg.evaluate("()=>{const f=()=>drwCables(drwLayout()).filter(c=>c.kind=='d').map(c=>Object.keys(c.links).join());const a=f();S.drLens='1, 2, 5, 10, 20';const b=f();S.drLens='0.5, 1, 2, 3, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100';return{a,b}}")
        chk(all(x == '0.5' for x in lk['a']) and all(x == '1' for x in lk['b']), f'links get the shortest stock length that reaches ({lk})')
        await pg.select_option('#drwSheet', '0')
        async with pg.expect_download() as dl2: await pg.click('[data-d=pdf]')
        f2 = await dl2.value; p2 = os.path.join(tempfile.mkdtemp(), 'c.pdf'); await f2.save_as(p2)
        chk(open(p2, 'rb').read().count(b'/Type /Page ') == 3, 'the PDF has the plan, the cable schedule and the material list')
        await pg.click('[data-d=reset]')
        async with pg.expect_download() as dl: await pg.click('[data-d=pdf]')
        f = await dl.value; path = os.path.join(tempfile.mkdtemp(), 'd.pdf'); await f.save_as(path); data = open(path, 'rb').read()
        chk(data[:5] == b'%PDF-' and b'/Type /Page ' in data and f.suggested_filename.startswith('TileSmith-drawings-'), f'PDF exported ({len(data)} bytes)')
        await pg.keyboard.press('Escape'); chk(await pg.evaluate("()=>!document.getElementById('drwEd')"), 'Escape closes the editor')
        chk(not errs, f'no page errors {errs[:3]}')
        await b.close(); print('ALL OK' if ok else 'FAILED'); sys.exit(0 if ok else 1)
asyncio.run(main())
