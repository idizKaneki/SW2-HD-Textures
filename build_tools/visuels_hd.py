from PIL import Image, ImageDraw, ImageFont, ImageEnhance
U='/root/.claude/uploads/816673d2-973f-5f0a-a0c2-6fd201879715/'
H='/home/claude/'
SERIF='/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc'
SERIF_B='/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'
SANS='/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc'
SANS_R='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
F=lambda p,s: ImageFont.truetype(p,s,index=0)
RED=(196,38,38); GOLD=(214,196,160); CREAM=(245,238,224); BG=(10,8,6); MUTED=(170,158,135)
def shot(n): return Image.open(U+n+'-image.png').convert('RGB')
def clean(n): return shot(n).crop((64,36,2560,1440))          # retire le compteur FPS, reste en 16:9
def gradient(w,h,stops):
    g=Image.new('L',(w,1)); px=g.load()
    for x in range(w):
        t=x/(w-1); a=0
        for (t0,a0),(t1,a1) in zip(stops,stops[1:]):
            if t0<=t<=t1: a=a0+(a1-a0)*(t-t0)/(t1-t0)
        px[x,0]=int(a)
    return g.resize((w,h))
def tracked(d,xy,txt,font,fill,track):
    x,y=xy
    for ch in txt: d.text((x,y),ch,font=font,fill=fill); x+=d.textlength(ch,font=font)+track
    return x
def label(d,xy,txt,hd):
    f=F(SANS,30); w=tracked(ImageDraw.Draw(Image.new('RGB',(1,1))),(0,0),txt,f,0,4)
    x,y=xy; d.rectangle((x,y,x+w+36,y+52),fill=RED if hd else (40,36,30))
    tracked(d,(x+18,y+6),txt,f,CREAM,4)

def header():
    W,Hh=1300,372
    src=clean('af9d109e').crop((1100,110,2496,510)).resize((W,Hh),Image.LANCZOS)
    src=ImageEnhance.Contrast(src).enhance(1.06)
    src=Image.composite(Image.new('RGB',(W,Hh),BG),src,gradient(W,Hh,[(0,250),(0.34,228),(0.56,40),(1,0)]))
    d=ImageDraw.Draw(src); x0=56
    tracked(d,(x0,62),'SAMURAI WARRIORS 2',F(SANS,22),GOLD,5)
    d.rectangle((x0,100,x0+64,104),fill=RED)
    d.text((x0-3,112),'HD Textures',font=F(SERIF,78),fill=CREAM)
    d.text((x0,222),'7,392 textures  ·  2x  ·  AI upscale',font=F(SANS,28),fill=GOLD)
    d.text((x0,262),'Textures HD',font=F(SANS_R,24),fill=MUTED)
    src.save('header_1300x372.png')

def principale():
    base=clean('af9d109e').resize((1920,1080),Image.LANCZOS)
    calque=Image.new('RGB',(1920,1080),BG); calque.paste(base,(300,0))
    im=Image.composite(calque,Image.new('RGB',(1920,1080),BG),gradient(1920,1080,[(0,0),(300/1919,0),(640/1919,255),(1,255)]))
    im=Image.composite(Image.new('RGB',(1920,1080),BG),im,gradient(1920,1080,[(0,250),(0.40,215),(0.60,25),(1,0)]))
    d=ImageDraw.Draw(im); x0=110
    tracked(d,(x0,170),'SAMURAI WARRIORS 2',F(SANS,30),GOLD,7)
    d.rectangle((x0,222,x0+90,227),fill=RED)
    d.text((x0-4,242),'HD Textures',font=F(SERIF,112),fill=CREAM)
    d.text((x0,402),'7,392 textures, twice as sharp',font=F(SANS,40),fill=GOLD)
    items=['Characters, officers & soldiers','Weapons, scenery & skies','Menus, portraits & loading screens','Press F11 in game to compare']
    y=510
    for t in items:
        d.rectangle((x0,y+17,x0+10,y+27),fill=RED)
        d.text((x0+30,y),t,font=F(SANS_R,36),fill=(236,228,212)); y+=62
    d.text((x0,y+40),'Same art style, only sharper. No game file modified.',font=F(SANS_R,28),fill=MUTED)
    d.text((x0,y+80),'Même direction artistique, en plus net. Aucun fichier du jeu modifié.',font=F(SANS_R,28),fill=MUTED)
    im.save('galerie_01_principale.png')

PAIRES=[('yukimura','Yukimura Sanada','f5a9897c','af9d109e',(649,341)),
        ('oichi','Oichi','3e123384','fc0a0cce',(770,380)),
        ('kotaro','Kotarō Fūma','b7773b30','78a2bbac',(700,392)),
        ('ieyasu','Ieyasu Tokugawa','d76577f4','bed0ca4b',(688,420))]
def comparaisons(n0):
    for i,(k,nom,a,b,(cx,cy)) in enumerate(PAIRES):
        im=Image.new('RGB',(1920,1080),BG); d=ImageDraw.Draw(im)
        box=(cx-232,cy-120,cx+233,cy+380)
        for j,f in enumerate((a,b)):
            p=shot(f).crop(box).resize((930,1000),Image.LANCZOS)
            im.paste(p,(20+j*950,20))
            label(d,(44+j*950,44),'ORIGINAL' if j==0 else 'HD',j==1)
        bar=Image.new('RGB',(1920,60),BG); im.paste(bar,(0,1020)); d=ImageDraw.Draw(im)
        d.text((44,1026),nom,font=F(SERIF_B,32),fill=CREAM)
        t='Character select  ·  zoom x2  ·  before / after'
        d.text((1876-d.textlength(t,font=F(SANS_R,26)),1032),t,font=F(SANS_R,26),fill=MUTED)
        im.save('galerie_%02d_%s.png'%(n0+i,k))
    return n0+len(PAIRES)

def textures(n):
    s1=Image.open(H+'visages_selection_1.jpg').convert('RGB'); s2=Image.open(H+'visages_selection_2.jpg').convert('RGB')
    rows=[(s1,40),(s2,40),(s2,820)]
    im=Image.new('RGB',(1920,1080),BG); d=ImageDraw.Draw(im)
    d.text((80,40),'The textures themselves',font=F(SERIF_B,44),fill=CREAM)
    d.text((80,104),'Original texture vs HD texture, same zoom',font=F(SANS_R,28),fill=MUTED)
    S=420; x0=(1920-3*S-2*40)//2+80; y0=200
    for c,(src,y) in enumerate(rows):
        o=src.crop((0,y,380,y+380)).resize((S,S),Image.LANCZOS)
        h=src.crop((1170,y,1550,y+380)).resize((S,S),Image.LANCZOS)
        x=x0+c*(S+40); im.paste(o,(x,y0)); im.paste(h,(x,y0+S+20))
    f=F(SANS,28)
    for txt,yy,hd in (('ORIGINAL',y0+S//2-26,False),('HD',y0+S+20+S//2-26,True)):
        w=d.textlength(txt,font=f)+36; d.rectangle((x0-40-w,yy,x0-40,yy+52),fill=RED if hd else (40,36,30)); d.text((x0-40-w+18,yy+6),txt,font=f,fill=CREAM)
    im.save('galerie_%02d_textures.png'%n); return n+1

def chainner(n):
    src=shot('ff4d4a95').crop((540,200,1880,930))
    src.thumbnail((1760,860),Image.LANCZOS)
    im=Image.new('RGB',(1920,1080),BG); d=ImageDraw.Draw(im)
    d.text((80,40),'Made locally, on a home PC',font=F(SERIF_B,44),fill=CREAM)
    d.text((80,104),'chaiNNer  ·  1x-DXTless-SourceEngine  →  4x-UltraSharpV2  →  resize 50 %  =  2x',font=F(SANS_R,28),fill=GOLD)
    x=(1920-src.width)//2; y=170
    d.rectangle((x-3,y-3,x+src.width+2,y+src.height+2),outline=(60,54,44),width=3)
    im.paste(src,(x,y)); im.save('galerie_%02d_chainner.png'%n); return n+1

def jeu(n):
    for f in ('1bf226e3','87e46ff6'):
        clean(f).resize((1920,1080),Image.LANCZOS).save('galerie_%02d_en_jeu.png'%n); n+=1
    return n

header(); principale()
n=comparaisons(2); n=textures(n); n=jeu(n); chainner(n)
