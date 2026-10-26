#!/usr/bin/env python3
"""ViralShopee IA 2.0 - local prototype. Uses Python stdlib, Pillow, ffmpeg, espeak (optional)."""
import json, os, re, subprocess, threading, urllib.request, urllib.parse, urllib.error, shutil, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from io import BytesIO

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(exist_ok=True)
CONFIG=ROOT/'config.json'; DB=ROOT/'data.json'
DEFAULT_CONFIG={'product_feed_url':'','product_feed_token':'','daily_target':10,'video_style':'mix','require_human_review':True,'affiliate_disclosure':'Publicidade: este conteúdo contém link de afiliado.','notes':'Use apenas imagens e materiais que você tem autorização para utilizar.'}
DEMO=[
 {'id':'demo-1','name':'Organizador de cozinha compacto','price':'29,90','category':'Casa e organização','rating':'4,8','sales':'1.200+','commission':'Não informada','affiliate_url':'','image_url':'','benefits':['Ajuda a aproveitar espaços pequenos','Visual simples e funcional','Boa ideia para organização'],'source':'Demonstração (dados fictícios)','status':'new'},
 {'id':'demo-2','name':'Luminária decorativa LED','price':'39,90','category':'Casa e decoração','rating':'4,7','sales':'850+','commission':'Não informada','affiliate_url':'','image_url':'','benefits':['Iluminação decorativa','Combina com diferentes ambientes','Opção para presentear'],'source':'Demonstração (dados fictícios)','status':'new'},
 {'id':'demo-3','name':'Acessório organizador de cabos','price':'12,99','category':'Tecnologia','rating':'4,9','sales':'2.000+','commission':'Não informada','affiliate_url':'','image_url':'','benefits':['Ajuda a organizar fios','Pequeno e fácil de guardar','Útil para mesa de trabalho'],'source':'Demonstração (dados fictícios)','status':'new'},
 {'id':'demo-4','name':'Kit de potes herméticos','price':'49,90','category':'Cozinha','rating':'4,8','sales':'670+','commission':'Não informada','affiliate_url':'','image_url':'','benefits':['Organização de mantimentos','Tamanhos variados conforme o kit','Visual organizado na despensa'],'source':'Demonstração (dados fictícios)','status':'new'},
 {'id':'demo-5','name':'Suporte ajustável para celular','price':'19,90','category':'Tecnologia','rating':'4,6','sales':'1.500+','commission':'Não informada','affiliate_url':'','image_url':'','benefits':['Ajuste de ângulo','Útil para chamadas e vídeos','Compacto para guardar'],'source':'Demonstração (dados fictícios)','status':'new'},
 {'id':'demo-6','name':'Bolsa organizadora de viagem','price':'34,90','category':'Viagem','rating':'4,7','sales':'900+','commission':'Não informada','affiliate_url':'','image_url':'','benefits':['Ajuda a separar itens na mala','Formato compacto','Prática para viagens'],'source':'Demonstração (dados fictícios)','status':'new'},
 {'id':'demo-7','name':'Escova de limpeza multiuso','price':'16,90','category':'Casa','rating':'4,7','sales':'1.100+','commission':'Não informada','affiliate_url':'','image_url':'','benefits':['Para tarefas de limpeza do dia a dia','Fácil de armazenar','Acessório multiuso'],'source':'Demonstração (dados fictícios)','status':'new'},
 {'id':'demo-8','name':'Necessaire com divisórias','price':'24,90','category':'Beleza e viagem','rating':'4,8','sales':'730+','commission':'Não informada','affiliate_url':'','image_url':'','benefits':['Ajuda a organizar pequenos itens','Boa para levar em viagens','Compartimentos conforme o modelo'],'source':'Demonstração (dados fictícios)','status':'new'},
 {'id':'demo-9','name':'Luz noturna com sensor','price':'27,90','category':'Casa e tecnologia','rating':'4,6','sales':'1.000+','commission':'Não informada','affiliate_url':'','image_url':'','benefits':['Iluminação auxiliar','Pode ser útil em corredores','Confira o tipo de alimentação no anúncio'],'source':'Demonstração (dados fictícios)','status':'new'},
 {'id':'demo-10','name':'Garrafa com marcador de horário','price':'22,90','category':'Acessórios','rating':'4,5','sales':'780+','commission':'Não informada','affiliate_url':'','image_url':'','benefits':['Marcadores visuais de horário','Formato portátil','Confira capacidade e material no anúncio'],'source':'Demonstração (dados fictícios)','status':'new'}]

def load_json(path, default):
 try: return json.loads(path.read_text('utf-8'))
 except Exception: return default

def save_json(path, data): path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def config():
 c=load_json(CONFIG,DEFAULT_CONFIG.copy()); return {**DEFAULT_CONFIG,**c}
def data(): return load_json(DB,{'products':DEMO,'videos':[]})
def make_id(): return str(int(time.time()*1000))
def pricefmt(v):
 s=str(v or '').strip()
 if not s: return 'consulte o anúncio'
 if s.startswith('R$'): return s
 return 'R$ '+s

def scripts(p, style='mix'):
 name=p.get('name','Achadinho'); price=pricefmt(p.get('price')); benefits=p.get('benefits') or ['Confira os detalhes no anúncio']
 b=[str(x).strip() for x in benefits if str(x).strip()][:3]
 hook=f'Olha esse achadinho que encontrei! 👀'
 demo=f'{name}: uma opção para quem procura praticidade.'
 demo+=' '.join(b)
 demo+=f' O preço informado é {price}. Confira o anúncio para ver as opções, medidas e condições atualizadas.'
 cta='Gostou? Confira os detalhes pelo link de afiliada.' if p.get('affiliate_url') else 'Gostou? Adicione seu link de afiliada antes de publicar.'
 disc=config().get('affiliate_disclosure','Publicidade: este conteúdo contém link de afiliado.')
 return {'hook':hook,'narration':f'{hook} {demo} {cta}','caption':f'{name} ✨\nPreço informado: {price}\n{cta}\n{disc}\n{p.get("affiliate_url","")}', 'scenes':[{'title':'ACHADINHO DO DIA','text':hook,'seconds':3},{'title':name,'text':(b[0] if b else 'Confira os detalhes do produto')[:110],'seconds':4},{'title':f'POR {price}','text':(b[1] if len(b)>1 else 'Veja os detalhes no anúncio')[:110],'seconds':4},{'title':'CONFIRA NO LINK','text':cta,'seconds':3}], 'style':style}

def render_mp4(p, video, style='product'):
 try:
  from PIL import Image, ImageDraw, ImageFont, ImageOps
 except ImportError: raise RuntimeError('Instale Pillow com: python -m pip install Pillow')
 ffmpeg=shutil.which('ffmpeg')
 if not ffmpeg: raise RuntimeError('FFmpeg não foi encontrado. Instale o FFmpeg e tente novamente.')
 vid=video['id']; work=OUT/('work_'+vid); work.mkdir(exist_ok=True)
 W,H=720,1280
 font_paths=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf']
 reg_paths=['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
 def font(sz,bold=True):
  for fp in (font_paths if bold else reg_paths):
   if os.path.exists(fp): return ImageFont.truetype(fp,sz)
  return ImageFont.load_default()
 bg=(20,22,37); accent=(255,115,57); white=(255,255,255); muted=(220,223,235)
 image=None; url=p.get('image_url','')
 if url.startswith('https://') or url.startswith('http://'):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
   with urllib.request.urlopen(req,timeout=8) as r: raw=r.read(8*1024*1024)
   image=Image.open(BytesIO(raw)).convert('RGB')
  except Exception: image=None
 scenes=video.get('scenes') or scripts(p)['scenes']; durations=[]
 for i,sc in enumerate(scenes):
  im=Image.new('RGB',(W,H),bg); d=ImageDraw.Draw(im)
  # simple gradient backdrop
  for y in range(H):
   t=y/H; col=(int(22+16*t),int(23+7*t),int(43+18*t)); d.line((0,y,W,y),fill=col)
  d.rounded_rectangle((32,30,W-32,H-30),radius=32,outline=(74,76,104),width=3)
  d.rounded_rectangle((54,58,300,108),radius=20,fill=accent)
  d.text((72,70),'VIRALSHOPEE IA',font=font(21),fill=(20,22,37))
  if image is not None:
   thumb=ImageOps.contain(image,(W-110,510))
   x=(W-thumb.width)//2; y=150+(510-thumb.height)//2
   im.paste(thumb,(x,y))
  else:
   # illustrated product card placeholder, clearly marked
   d.rounded_rectangle((75,165,W-75,665),radius=30,fill=(36,39,62),outline=(90,92,124),width=2)
   d.text((W//2,360),'ACHADINHO',font=font(35),fill=accent,anchor='mm')
   d.text((W//2,420),'foto do produto não fornecida',font=font(21,False),fill=muted,anchor='mm')
  title=str(sc.get('title',p.get('name','Achadinho')))
  # title wrapping
  def wrap(text, f, maxw):
   words=str(text).split(); lines=[]; line=''
   for word in words:
    test=(line+' '+word).strip()
    if d.textbbox((0,0),test,font=f)[2] <= maxw: line=test
    else:
     if line: lines.append(line)
     line=word
   if line: lines.append(line)
   return lines
  y0=715
  for line in wrap(title,font(42),W-110)[:3]:
   d.text((W//2,y0),line,font=font(42),fill=white,anchor='mm'); y0+=56
  body=str(sc.get('text',''))
  y0=max(y0+35,850)
  for line in wrap(body,font(28,False),W-110)[:5]:
   d.text((W//2,y0),line,font=font(28,False),fill=muted,anchor='mm'); y0+=42
  if i==2:
   d.rounded_rectangle((100,1040,W-100,1120),radius=25,fill=accent)
   d.text((W//2,1080),pricefmt(p.get('price')),font=font(34),fill=bg,anchor='mm')
  d.text((W//2,H-82),'Confira preço, estoque e detalhes no anúncio',font=font(17,False),fill=muted,anchor='mm')
  path=work/f'scene_{i:02d}.png'; im.save(path); durations.append(max(2,int(sc.get('seconds',3))))
 # Create silent video from slides; use image concat demuxer
 concat=work/'concat.txt'
 with concat.open('w',encoding='utf8') as f:
  for i,dur in enumerate(durations): f.write(f"file '{(work/f'scene_{i:02d}.png').as_posix()}'\nduration {dur}\n")
  f.write(f"file '{(work/f'scene_{len(durations)-1:02d}.png').as_posix()}'\n")
 mp4=OUT/f'viralshopee_{vid}.mp4'
 cmd=[ffmpeg,'-y','-f','concat','-safe','0','-i',str(concat)]
 audio=work/'narration.wav'; has_audio=False
 espeak=shutil.which('espeak')
 if espeak:
  try:
   subprocess.run([espeak,'-v','pt-br','-s','155','-w',str(audio),video['scripts']['narration']],capture_output=True,text=True,timeout=30,check=True)
   cmd += ['-i',str(audio)]; has_audio=True
  except Exception: has_audio=False
 cmd += ['-vf','fps=25,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','24','-movflags','+faststart']
 if has_audio: cmd += ['-c:a','aac','-b:a','128k','-shortest']
 else: cmd += ['-an']
 cmd += [str(mp4)]
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
 if r.returncode: raise RuntimeError('FFmpeg falhou: '+r.stderr[-900:])
 video['file']=f'output/{mp4.name}'; video['duration_seconds']=sum(durations); video['audio']=('Narração gerada com espeak' if has_audio else 'Sem áudio: instale espeak com voz pt-br para narração local'); video['rendered_at']=time.strftime('%Y-%m-%d %H:%M:%S')
 return video

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a): pass
 def send_json(self,obj,status=200):
  raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers(); self.wfile.write(raw)
 def body(self):
  n=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n).decode() or '{}')
 def do_GET(self):
  path=urllib.parse.urlparse(self.path).path
  if path=='/': self.serve(ROOT/'index.html'); return
  if path=='/api/state': self.send_json({'config':config(),'data':data(),'capabilities':{'ffmpeg':bool(shutil.which('ffmpeg')),'pillow':True,'espeak':bool(shutil.which('espeak')),'real_product_feed_configured':bool(config().get('product_feed_url'))}}); return
  if path.startswith('/output/'):
   f=(ROOT/path.lstrip('/')).resolve()
   if not str(f).startswith(str(OUT.resolve())) or not f.exists(): self.send_error(404); return
   self.serve(f); return
  self.send_error(404)
 def serve(self,f):
  if not f.exists(): self.send_error(404); return
  raw=f.read_bytes(); typ='text/html; charset=utf-8' if f.suffix=='.html' else ('video/mp4' if f.suffix=='.mp4' else 'application/octet-stream')
  self.send_response(200); self.send_header('Content-Type',typ); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
 def do_POST(self):
  path=urllib.parse.urlparse(self.path).path
  try: body=self.body()
  except Exception: self.send_json({'error':'JSON inválido'},400); return
  d=data(); c=config()
  if path=='/api/config':
   for k in ['product_feed_url','product_feed_token','daily_target','video_style','require_human_review','affiliate_disclosure']:
    if k in body: c[k]=body[k]
   save_json(CONFIG,c); self.send_json({'ok':True,'config':c}); return
  if path=='/api/search':
   url=c.get('product_feed_url','').strip()
   if not url:
    self.send_json({'products':d['products'],'demo':True,'message':'Modo demonstração: configure um feed/API autorizado para buscar produtos reais.'}); return
   if not url.startswith('https://'):
    self.send_json({'error':'Por segurança, o feed deve usar HTTPS.'},400); return
   try:
    headers={'Accept':'application/json','User-Agent':'ViralShopeeIA/2.0'}
    if c.get('product_feed_token'): headers['Authorization']='Bearer '+c['product_feed_token']
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=20) as res: payload=json.loads(res.read(12*1024*1024).decode('utf-8'))
    products=payload.get('products',payload if isinstance(payload,list) else [])
    normalized=[]
    for i,p in enumerate(products[:100]):
     if not isinstance(p,dict): continue
     benefits=p.get('benefits',p.get('features',[])); benefits=benefits if isinstance(benefits,list) else [str(benefits)]
     normalized.append({'id':str(p.get('id') or 'feed-'+str(i)+'-'+str(int(time.time()))),'name':p.get('name') or p.get('title') or 'Produto sem nome','price':p.get('price',''),'category':p.get('category','Achadinhos variados'),'rating':p.get('rating','Não informado'),'sales':p.get('sales',p.get('sold','Não informado')),'commission':p.get('commission','Não informada'),'affiliate_url':p.get('affiliate_url',p.get('link','')),'image_url':p.get('image_url',p.get('image','')),'benefits':benefits,'source':'Feed/API configurado','status':'new'})
    existing={x['id']:x for x in d['products']}
    for p in normalized: existing[p['id']]=p
    d['products']=list(existing.values()); save_json(DB,d)
    self.send_json({'products':normalized,'demo':False,'message':f'{len(normalized)} produtos recebidos do feed configurado.'})
   except Exception as e: self.send_json({'error':'Não foi possível consultar o feed: '+str(e)},502)
   return
  if path=='/api/product':
   p=body.get('product',{}); p['id']=p.get('id') or make_id(); p.setdefault('status','new'); p.setdefault('benefits',[])
   d['products']=[x for x in d['products'] if x.get('id')!=p['id']]+[p]; save_json(DB,d); self.send_json({'ok':True,'product':p}); return
  if path=='/api/generate':
   pid=body.get('product_id'); p=next((x for x in d['products'] if x.get('id')==pid),None)
   if not p: self.send_json({'error':'Produto não encontrado'},404); return
   v={'id':make_id(),'product_id':pid,'product_name':p.get('name','Produto'),'status':'Aguardando revisão','approved':False,'style':body.get('style','product'),'scripts':scripts(p,body.get('style','product')),'file':'','created_at':time.strftime('%Y-%m-%d %H:%M:%S')}
   try: v=render_mp4(p,v,body.get('style','product'))
   except Exception as e: self.send_json({'error':'Falha ao gerar MP4: '+str(e)},500); return
   d['videos'].insert(0,v); p['status']='video criado'; save_json(DB,d); self.send_json({'ok':True,'video':v}); return
  if path=='/api/batch':
   target=max(1,min(30,int(body.get('count',c.get('daily_target',10)))))
   existing_ids={v.get('product_id') for v in d['videos'] if v.get('created_at','').startswith(time.strftime('%Y-%m-%d'))}
   candidates=[p for p in d['products'] if p.get('id') not in existing_ids][:target]
   if not candidates: candidates=d['products'][:target]
   made=[]; errors=[]
   for p in candidates:
    v={'id':make_id()+str(len(made)),'product_id':p.get('id'),'product_name':p.get('name','Produto'),'status':'Aguardando revisão','approved':False,'style':'product','scripts':scripts(p,'product'),'file':'','created_at':time.strftime('%Y-%m-%d %H:%M:%S')}
    try:
     v=render_mp4(p,v,'product'); d['videos'].insert(0,v); p['status']='video criado'; made.append(v)
    except Exception as e: errors.append({'product':p.get('name'),'error':str(e)})
   save_json(DB,d); self.send_json({'ok':True,'created':len(made),'videos':made,'errors':errors,'message':f'{len(made)} vídeo(s) criado(s) e aguardando revisão.'}); return
  if path=='/api/review':
   vid=body.get('video_id'); v=next((x for x in d['videos'] if x.get('id')==vid),None)
   if not v: self.send_json({'error':'Vídeo não encontrado'},404); return
   action=body.get('action')
   v['status']='Aprovado para publicação' if action=='approve' else 'Rejeitado'; v['approved']=action=='approve'; v['reviewed_at']=time.strftime('%Y-%m-%d %H:%M:%S'); save_json(DB,d); self.send_json({'ok':True,'video':v}); return
  if path=='/api/export':
   self.send_json({'ok':True,'data':d}); return
  self.send_json({'error':'Rota não encontrada'},404)

def main():
 print('ViralShopee IA 2.0: http://127.0.0.1:8765')
 print('Feche com Ctrl+C. Esta versão é local; para uso público, hospede com autenticação e HTTPS.')
 ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
if __name__=='__main__': main()
