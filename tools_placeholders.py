# Generates neutral abstract placeholder images (no photos). Run: python tools_placeholders.py
import numpy as np
from PIL import Image, ImageFilter
rng = np.random.default_rng(7)
specs = {
 # name: (top color, horizon glow color, streak color)
 "elbil":    ((14,22,30),  (64,140,170), (190,230,240)),
 "sportbil": ((22,16,16),  (190,70,40),  (255,200,160)),
 "tesla":    ((16,17,20),  (120,128,140),(235,238,242)),
 "laddning": ((12,20,18),  (40,150,110), (190,245,215)),
 "bransle":  ((24,20,12),  (170,130,50), (250,225,170)),
 "hero":     ((10,12,16),  (210,90,40),  (255,220,190)),
}
W,H = 1600,1000
y = np.linspace(0,1,H)[:,None]; x = np.linspace(0,1,W)[None,:]
for name,(top,glow,streak) in specs.items():
    top=np.array(top,float); glow=np.array(glow,float); st=np.array(streak,float)
    hz = 0.52 + rng.uniform(-.04,.04)
    # sky: dark to glow near horizon
    g = np.exp(-((y-hz)/0.22)**2) * (0.55+0.45*np.exp(-((x-rng.uniform(.3,.7))/0.45)**2))
    img = top[None,None,:]*(1-g[...,None]) + glow[None,None,:]*g[...,None]
    # floor: darker reflective
    floor = (y>hz).astype(float)
    img = img*(1-0.55*floor[...,None]*np.clip((y-hz)*3,0,1)[...,None])
    # light streaks (long exposure)
    lay = np.zeros((H,W))
    for i in range(5):
        cy = hz + rng.uniform(.02,.2); slope = rng.uniform(-.08,.08); th = rng.uniform(.002,.006)
        line = np.exp(-((y-(cy+slope*(x-.5)))/th)**2) * np.clip(np.sin(np.pi*np.clip((x-rng.uniform(0,.3))/rng.uniform(.6,1),0,1)),0,1)
        lay += line*rng.uniform(.4,1)
    im = Image.fromarray(np.clip(lay*255,0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
    lay = np.asarray(im,float)/255
    img = img*(1-lay[...,None]) + st[None,None,:]*lay[...,None]
    # vignette + grain
    v = 1-0.35*(((x-.5)*1.6)**2+((y-.5)*1.4)**2)
    img = img*v[...,None] + rng.normal(0,3,(H,W,1))
    out = Image.fromarray(np.clip(img,0,255).astype(np.uint8))
    for w in (1600,800):
        out.resize((w,int(w*H/W)),Image.LANCZOS).save(f"img/{name}-{w}.webp",quality=72)
print("ok")
