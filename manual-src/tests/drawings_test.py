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
        # cabling: separate sheets for data (blue) and power (red), drawn from the app's own wiring
        await pg.evaluate("()=>{S.proc=Object.keys(PROC).find(x=>x!='None');S.ppx=655360;S.pdist=true;S.wmode='Snake';S.pmode='Snake';walls.forEach((w,i)=>{w.wmode='Snake';w.pmode='Snake'});storeWall();drwRender()}")
        sheets = await pg.evaluate("()=>[...$('#drwSheet').options].map(o=>o.textContent)")
        chk(sheets == ['Plan', 'Data cables', 'Power cables'], f'a plan, a data and a power sheet {sheets}')
        cb = await pg.evaluate("()=>{const d=drwCables(drwLayout('data'),'d'),p=drwCables(drwLayout('power'),'p');return{d:d.length,p:p.length,ok:[...d,...p].every(x=>x.pcs.length>0&&x.pts.length==x.pcs.length)}}")
        chk(cb['d'] >= 2 and cb['p'] >= 2 and cb['ok'], f'cables are found for both kinds {cb}')
        sg = await pg.evaluate("""()=>{drwSetKey(0,'wmode','Linear');drwSetKey(0,'wcorner','Bottom-right');drwSetKey(0,'wdir','Vertical');drwSetKey(0,'wfill','Whole rows or columns');
          drwSuggest('d',0);drwSuggest('p',0);const w=walls[0],P2=pieces(w);const chk=(pl,t)=>{const seen=new Set;let over=0,dup=0;pl.forEach(c=>{if(c.over)over++;c.tiles.forEach(e=>{const k=elKey(e);if(seen.has(k))dup++;seen.add(k)})});return{cov:seen.size==P2.list.length,over,dup,n:pl.length,min:Math.ceil(P2.list.length/t)}};
          return{d:chk(portPlan()[0],tpp(w)),p:chk(powerPlan()[0],tpcW(w))}}""")
        chk(all(v['cov'] and v['over'] == 0 and v['dup'] == 0 and v['n'] == v['min'] for v in sg.values()), f'Suggest covers every tile once, within the limits, with the fewest ports and circuits {sg}')
        await pg.select_option('#drwSheet', '1')
        look = await pg.evaluate("()=>{const t=$('#drwStage')._d.items.filter(i=>i.t=='text');const poly=$('#drwStage')._d.items.filter(i=>i.t=='pl').map(i=>i.col);return{hdr:t.some(x=>x.s.startsWith('DATA CABLING  -  CAT6')),badge:t.some(x=>/^P\\d+$/.test(x.s)&&x.size>=5),blue:poly.length>0&&poly.every(c=>c=='#1747c4')}}")
        chk(look['hdr'] and look['badge'] and look['blue'], f'data sheet: CAT6 heading, big port numbers, all cables blue {look}')
        await pg.select_option('#drwSheet', '2')
        chk(await pg.evaluate("()=>{const t=$('#drwStage')._d.items;return t.some(x=>x.t=='text'&&x.s.startsWith('POWER CABLING  -  powerCON TRUE1'))&&t.filter(i=>i.t=='pl').every(i=>i.col=='#c4161c')&&t.some(x=>x.t=='text'&&/^C\\d+$/.test(x.s))}"), 'power sheet: powerCON TRUE1 heading, circuit numbers, all cables red')
        chk(await pg.evaluate("()=>{const L=drwLayout('data'),e=L.bx.length>1?L.pos[1].x-(L.pos[0].x+L.bx[0].W):1e9;return L.bx.length<2||e*L.s>=31}"), 'walls keep room between them for the cable numbers')
        await pg.select_option('#drwSheet', '1'); await pg.click('[data-t=edit]')
        ed = await pg.evaluate("()=>{const t=document.querySelector('#drwStage [data-tk^=\"0|\"]');return t?t.dataset.tk:null}")
        await pg.click(f'#drwStage [data-tk="{ed}"]')
        e1 = await pg.evaluate("()=>{const c=S.wman[S.wman.length-1];return{mode:S.wmode,key:elKey(c[c.length-1]),n:c.length}}")
        chk(e1['mode'] == 'Manual', 'editing starts from the current cabling in Manual mode')
        await pg.click(f"#drwStage [data-tk=\"0|{e1['key']}\"]")
        chk(await pg.evaluate("()=>$('#drwStage')._d.items.filter(i=>i.t=='rect'&&i.fill=='#ffe45c').length==1"), 'a tile taken off its cable turns yellow')
        await pg.click(f"#drwStage [data-tk=\"0|{e1['key']}\"]")
        chk(await pg.evaluate("()=>$('#drwStage')._d.items.filter(i=>i.t=='rect'&&i.fill=='#ffe45c').length==0"), 'clicking it again puts it back on the cable')
        await pg.click('[data-t=move]')
        sh = await pg.evaluate("()=>{S.drPow=false;const a=drwKinds();S.drPow=true;S.drData=false;const b=drwKinds();S.drData=true;return[a,b,drwKinds()]}")
        chk(sh == [['plan', 'data'], ['plan', 'power'], ['plan', 'data', 'power']], f'data and power sheets can be switched off {sh}')
        await pg.select_option('#drwSheet', '0')
        async with pg.expect_download() as dl2: await pg.click('[data-d=pdf]')
        f2 = await dl2.value; p2 = os.path.join(tempfile.mkdtemp(), 'c.pdf'); await f2.save_as(p2)
        chk(open(p2, 'rb').read().count(b'/Type /Page ') == 3, 'the PDF has the plan, the data sheet and the power sheet')
        await pg.click('[data-d=reset]')
        async with pg.expect_download() as dl: await pg.click('[data-d=pdf]')
        f = await dl.value; path = os.path.join(tempfile.mkdtemp(), 'd.pdf'); await f.save_as(path); data = open(path, 'rb').read()
        chk(data[:5] == b'%PDF-' and b'/Type /Page ' in data and f.suggested_filename.startswith('TileSmith-drawings-'), f'PDF exported ({len(data)} bytes)')
        await pg.keyboard.press('Escape'); chk(await pg.evaluate("()=>!document.getElementById('drwEd')"), 'Escape closes the editor')
        chk(not errs, f'no page errors {errs[:3]}')
        await b.close(); print('ALL OK' if ok else 'FAILED'); sys.exit(0 if ok else 1)
asyncio.run(main())
