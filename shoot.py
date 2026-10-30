# Skärmdumpar: .venv/bin/python shoot.py <bas-url> <prefix> <sökväg>... (sparas i ../motorpuls/previews/)
# Ex: shoot.py http://127.0.0.1:8765 lokal / /artikel/slug/
import asyncio, os, re, sys
from playwright.async_api import async_playwright
OUT = os.environ.get("SHOTS", "/workspace/motorpuls/previews")
base, prefix, paths = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3:]
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome")
        for path in paths:
            name = "front" if path == "/" else re.sub(r"[^a-z0-9]+", "-", path.strip("/").split("/")[-1])
            for w, h in ((1440, 900), (390, 844)):
                ctx = await br.new_context(viewport={"width": w, "height": h}, device_scale_factor=2 if w < 500 else 1)
                pg = await ctx.new_page()
                await pg.goto(base + path, wait_until="networkidle"); await pg.evaluate("document.fonts.ready")
                await pg.evaluate("(async()=>{for(let y=0;y<document.body.scrollHeight;y+=400){scrollTo(0,y);await new Promise(r=>setTimeout(r,50))}scrollTo(0,0)})()")
                await pg.wait_for_timeout(600)
                f = f"{OUT}/{prefix}-{name}-{w}.png"; await pg.screenshot(path=f, full_page=True); print(f)
                await ctx.close()
        await br.close()
asyncio.run(main())
