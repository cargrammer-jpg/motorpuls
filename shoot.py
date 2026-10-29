import asyncio, subprocess, time
from playwright.async_api import async_playwright
srv = subprocess.Popen(["python3","-m","http.server","8765","--bind","127.0.0.1"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(1)
B="http://127.0.0.1:8765/"
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome")
        async def shot(url,w,h,out,full=True,scroll=None):
            pg = await br.new_page(viewport={"width":w,"height":h},device_scale_factor=2 if w<500 else 1)
            await pg.goto(B+url); await pg.evaluate("document.fonts.ready")
            await pg.evaluate("(async()=>{for(let y=0;y<document.body.scrollHeight;y+=400){scrollTo(0,y);await new Promise(r=>setTimeout(r,60))}scrollTo(0,0)})()"); await pg.evaluate("localStorage.clear(); if(!location.search) document.getElementById('nyhetsbrev').hidePopover?.()"); await pg.wait_for_timeout(600)
            if scroll is not None:
                await pg.evaluate(f"window.scrollTo(0,{scroll})"); await pg.wait_for_timeout(500)
            await pg.screenshot(path="previews/"+out, full_page=full)
            await pg.close()
        await shot("index.html",1440,900,"front-1440.png")
        await shot("index.html",390,844,"front-390.png")
        await shot("artikel.html",390,844,"artikel-390.png")
        await shot("index.html?nyhetsbrev",390,844,"popup-390.png",full=False,scroll=1400)
        await br.close()
asyncio.run(main()); srv.terminate()
