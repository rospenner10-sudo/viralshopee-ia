#!/usr/bin/env python3
"""ViralShopee IA 2.2 - vídeos verticais com narração Edge TTS."""
import asyncio
import base64
import hmac
import json
import os
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
CONFIG = ROOT / "config.json"
DB = ROOT / "data.json"

DEFAULT_CONFIG = {
    "product_feed_url": "",
    "product_feed_token": "",
    "daily_target": 10,
    "video_style": "mix",
    "require_human_review": True,
    "affiliate_disclosure": "Publicidade: este conteúdo contém link de afiliado.",
    "notes": "Use apenas imagens e materiais que você tem autorização para utilizar."
}

DEMO = [
    {"id":"demo-1","name":"Organizador de cozinha compacto","price":"29,90","category":"Casa e organização","rating":"4,8","sales":"1.200+","commission":"Não informada","affiliate_url":"","image_url":"","benefits":["Ajuda a aproveitar espaços pequenos","Visual simples e funcional","Boa ideia para organização"],"source":"Demonstração (dados fictícios)","status":"new"},
    {"id":"demo-2","name":"Luminária decorativa LED","price":"39,90","category":"Casa e decoração","rating":"4,7","sales":"850+","commission":"Não informada","affiliate_url":"","image_url":"","benefits":["Iluminação decorativa","Combina com diferentes ambientes","Opção para presentear"],"source":"Demonstração (dados fictícios)","status":"new"},
    {"id":"demo-3","name":"Acessório organizador de cabos","price":"12,99","category":"Tecnologia","rating":"4,9","sales":"2.000+","commission":"Não informada","affiliate_url":"","image_url":"","benefits":["Ajuda a organizar fios","Pequeno e fácil de guardar","Útil para mesa de trabalho"],"source":"Demonstração (dados fictícios)","status":"new"},
    {"id":"demo-4","name":"Kit de potes herméticos","price":"49,90","category":"Cozinha","rating":"4,8","sales":"670+","commission":"Não informada","affiliate_url":"","image_url":"","benefits":["Organização de mantimentos","Tamanhos variados conforme o kit","Visual organizado na despensa"],"source":"Demonstração (dados fictícios)","status":"new"},
    {"id":"demo-5","name":"Suporte ajustável para celular","price":"19,90","category":"Tecnologia","rating":"4,6","sales":"1.500+","commission":"Não informada","affiliate_url":"","image_url":"","benefits":["Ajuste de ângulo","Útil para chamadas e vídeos","Compacto para guardar"],"source":"Demonstração (dados fictícios)","status":"new"},
    {"id":"demo-6","name":"Bolsa organizadora de viagem","price":"34,90","category":"Viagem","rating":"4,7","sales":"900+","commission":"Não informada","affiliate_url":"","image_url":"","benefits":["Ajuda a separar itens na mala","Formato compacto","Prática para viagens"],"source":"Demonstração (dados fictícios)","status":"new"},
    {"id":"demo-7","name":"Escova de limpeza multiuso","price":"16,90","category":"Casa","rating":"4,7","sales":"1.100+","commission":"Não informada","affiliate_url":"","image_url":"","benefits":["Para tarefas de limpeza do dia a dia","Fácil de armazenar","Acessório multiuso"],"source":"Demonstração (dados fictícios)","status":"new"},
    {"id":"demo-8","name":"Necessaire com divisórias","price":"24,90","category":"Beleza e viagem","rating":"4,8","sales":"730+","commission":"Não informada","image_url":"","affiliate_url":"","benefits":["Ajuda a organizar pequenos itens","Boa para levar em viagens","Compartimentos conforme o modelo"],"source":"Demonstração (dados fictícios)","status":"new"},
    {"id":"demo-9","name":"Luz noturna com sensor","price":"27,90","category":"Casa e tecnologia","rating":"4,6","sales":"1.000+","commission":"Não informada","image_url":"","affiliate_url":"","benefits":["Iluminação auxiliar","Pode ser útil em corredores","Confira o tipo de alimentação no anúncio"],"source":"Demonstração (dados fictícios)","status":"new"},
    {"id":"demo-10","name":"Garrafa com marcador de horário","price":"22,90","category":"Acessórios","rating":"4,5","sales":"780+","commission":"Não informada","image_url":"","affiliate_url":"","benefits":["Marcadores visuais de horário","Formato portátil","Confira capacidade e material no anúncio"],"source":"Demonstração (dados fictícios)","status":"new"}
]

def load_json(path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return default

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def config():
    return {**DEFAULT_CONFIG, **load_json(CONFIG, {})}

def data():
    return load_json(DB, {"products": DEMO.copy(), "videos": []})

def make_id():
    return str(int(time.time() * 1000))

def pricefmt(value):
    value = str(value or "").strip()
    if not value:
        return "consulte o anúncio"
    return value if value.startswith("R$") else "R$ " + value

def scripts(product, style="mix"):
    name = product.get("name", "Achadinho")
    price = pricefmt(product.get("price"))
    benefits = [str(x).strip() for x in (product.get("benefits") or []) if str(x).strip()][:3]
    if not benefits:
        benefits = ["Confira os detalhes no anúncio"]
    hook = "Olha esse achadinho que encontrei!"
    demo = f"{name}: uma opção para quem procura praticidade. " + " ".join(benefits)
    demo += f" O preço informado é {price}. Confira o anúncio para ver as opções, medidas e condições atualizadas."
    cta = "Gostou? Confira os detalhes pelo link de afiliada." if product.get("affiliate_url") else "Gostou? Adicione seu link de afiliada antes de publicar."
    disclosure = config().get("affiliate_disclosure", DEFAULT_CONFIG["affiliate_disclosure"])
    return {
        "hook": hook,
        "narration": f"{hook} {demo} {cta}",
        "caption": f"{name} ✨\nPreço informado: {price}\n{cta}\n{disclosure}\n{product.get('affiliate_url','')}",
        "scenes": [
            {"title":"ACHADINHO DO DIA","text":hook,"seconds":3},
            {"title":name,"text":benefits[0][:110],"seconds":4},
            {"title":f"POR {price}","text":(benefits[1] if len(benefits)>1 else "Veja os detalhes no anúncio")[:110],"seconds":4},
            {"title":"CONFIRA NO LINK","text":cta,"seconds":3}
        ],
        "style": style
    }

def wrap_text(draw, text, font, max_width):
    lines, line = [], ""
    for word in str(text).split():
        test = (line + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def make_voice(text, output_mp3, voice_name):
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("A biblioteca edge-tts não está instalada. Confira requirements.txt e o deploy.") from exc

    async def run():
        communicator = edge_tts.Communicate(text=text, voice=voice_name, rate="+0%", volume="+0%")
        await communicator.save(str(output_mp3))

    asyncio.run(run())
    if not output_mp3.exists() or output_mp3.stat().st_size < 1000:
        raise RuntimeError("O serviço de voz não gerou um MP3 válido.")

def render_mp4(product, video, style="product"):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg não encontrado no servidor.")
    work = OUT / ("work_" + video["id"])
    work.mkdir(parents=True, exist_ok=True)
    width, height = 720, 1280
    bold_paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
    regular_paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                     "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]

    def font(size, bold=True):
        for path in (bold_paths if bold else regular_paths):
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    background = (20, 22, 37)
    accent = (255, 115, 57)
    white = (255, 255, 255)
    muted = (220, 223, 235)
    image = None
    image_url = product.get("image_url", "")
    if image_url.startswith(("https://", "http://")):
        try:
            req = urllib.request.Request(image_url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as response:
                raw = response.read(8 * 1024 * 1024)
            image = Image.open(BytesIO(raw)).convert("RGB")
        except Exception:
            image = None

    scenes = video.get("scripts", {}).get("scenes") or scripts(product)["scenes"]
    durations = []
    for index, scene in enumerate(scenes):
        im = Image.new("RGB", (width, height), background)
        draw = ImageDraw.Draw(im)
        for y in range(height):
            t = y / height
            color = (int(22 + 16*t), int(23 + 7*t), int(43 + 18*t))
            draw.line((0, y, width, y), fill=color)
        draw.rounded_rectangle((32, 30, width-32, height-30), radius=32, outline=(74,76,104), width=3)
        draw.rounded_rectangle((54,58,300,108), radius=20, fill=accent)
        draw.text((72,70), "VIRALSHOPEE IA", font=font(21), fill=background)
        if image is not None:
            thumb = ImageOps.contain(image, (width-110, 510))
            im.paste(thumb, ((width-thumb.width)//2, 150+(510-thumb.height)//2))
        else:
            draw.rounded_rectangle((75,165,width-75,665), radius=30, fill=(36,39,62), outline=(90,92,124), width=2)
            draw.text((width//2,360), "ACHADINHO", font=font(35), fill=accent, anchor="mm")
            draw.text((width//2,420), "foto do produto não fornecida", font=font(21,False), fill=muted, anchor="mm")
        y0 = 715
        for line in wrap_text(draw, scene.get("title", product.get("name","Achadinho")), font(42), width-110)[:3]:
            draw.text((width//2,y0),line,font=font(42),fill=white,anchor="mm")
            y0 += 56
        y0 = max(y0+35, 850)
        for line in wrap_text(draw, scene.get("text",""), font(28,False), width-110)[:5]:
            draw.text((width//2,y0),line,font=font(28,False),fill=muted,anchor="mm")
            y0 += 42
        if index == 2:
            draw.rounded_rectangle((100,1040,width-100,1120),radius=25,fill=accent)
            draw.text((width//2,1080),pricefmt(product.get("price")),font=font(34),fill=background,anchor="mm")
        draw.text((width//2,height-82),"Confira preço, estoque e detalhes no anúncio",font=font(17,False),fill=muted,anchor="mm")
        im.save(work / f"scene_{index:02d}.png")
        durations.append(max(2, int(scene.get("seconds",3))))

    concat = work / "concat.txt"
    with concat.open("w", encoding="utf-8") as handle:
        for index, duration in enumerate(durations):
            handle.write(f"file '{(work / f'scene_{index:02d}.png').as_posix()}'\nduration {duration}\n")
        handle.write(f"file '{(work / f'scene_{len(durations)-1:02d}.png').as_posix()}'\n")

    mp4 = OUT / f"viralshopee_{video['id']}.mp4"
    mp3 = work / "narration.mp3"
    voices = ["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"]
    voice = voices[int(video.get("voice_index", 0)) % len(voices)]

    # Falha explicitamente se a voz não puder ser criada: não entrega MP4 silencioso como sucesso.
    make_voice(video["scripts"]["narration"], mp3, voice)
    cmd = [
        ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-i", str(mp3), "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-vf", "fps=25,format=yuv420p", "-c:a", "aac", "-b:a", "128k",
        "-af", "apad", "-shortest", "-movflags", "+faststart", str(mp4)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError("FFmpeg falhou ao incorporar a voz: " + result.stderr[-900:])
    probe = shutil.which("ffprobe")
    if probe:
        check = subprocess.run([probe,"-v","error","-select_streams","a:0",
            "-show_entries","stream=codec_type","-of","default=noprint_wrappers=1:nokey=1",str(mp4)],
            capture_output=True,text=True,timeout=15)
        if check.returncode or "audio" not in check.stdout:
            raise RuntimeError("O MP4 final não contém faixa de áudio.")
    video["file"] = f"output/{mp4.name}"
    video["duration_seconds"] = sum(durations)
    video["audio"] = f"Narração Edge TTS ({voice})"
    video["rendered_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return video

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def authorized(self):
        username = os.environ.get("APP_USERNAME", "").strip()
        password = os.environ.get("APP_PASSWORD", "")
        if not username or not password:
            return False
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            raw = base64.b64decode(header.split(" ",1)[1]).decode("utf-8")
            user, pwd = raw.split(":",1)
            return hmac.compare_digest(user,username) and hmac.compare_digest(pwd,password)
        except Exception:
            return False

    def unauthorized(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate",'Basic realm="ViralShopee IA", charset="UTF-8"')
        self.send_header("Content-Length","0")
        self.end_headers()

    def send_json(self, obj, status=200):
        raw = json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw)))
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def body(self):
        length = int(self.headers.get("Content-Length","0"))
        return json.loads(self.rfile.read(length).decode() or "{}")

    def do_GET(self):
        if not self.authorized():
            self.unauthorized()
            return
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            self.serve(ROOT / "index.html")
        elif path == "/api/state":
            self.send_json({"config":config(),"data":data(),"capabilities":{
                "ffmpeg":bool(shutil.which("ffmpeg")),"pillow":True,
                "edge_tts":__import__("importlib").util.find_spec("edge_tts") is not None,
                "real_product_feed_configured":bool(config().get("product_feed_url"))}})
        elif path.startswith("/output/"):
            file_path = (ROOT / path.lstrip("/")).resolve()
            if not str(file_path).startswith(str(OUT.resolve())) or not file_path.exists():
                self.send_error(404)
            else:
                self.serve(file_path)
        else:
            self.send_error(404)

    def serve(self, file_path):
        if not file_path.exists():
            self.send_error(404)
            return
        raw = file_path.read_bytes()
        content_type = "text/html; charset=utf-8" if file_path.suffix == ".html" else ("video/mp4" if file_path.suffix == ".mp4" else "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(raw)))
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if not self.authorized():
            self.unauthorized()
            return
        path = urllib.parse.urlparse(self.path).path
        try:
            body = self.body()
        except Exception:
            self.send_json({"error":"JSON inválido"},400)
            return
        db = data()
        cfg = config()

        if path == "/api/config":
            for key in ["product_feed_url","product_feed_token","daily_target","video_style","require_human_review","affiliate_disclosure"]:
                if key in body:
                    cfg[key] = body[key]
            save_json(CONFIG,cfg)
            self.send_json({"ok":True,"config":cfg})
            return

        if path == "/api/search":
            url = cfg.get("product_feed_url","").strip()
            if not url:
                self.send_json({"products":db["products"],"demo":True,"message":"Modo demonstração: configure um feed/API autorizado para buscar produtos reais."})
                return
            if not url.startswith("https://"):
                self.send_json({"error":"Por segurança, o feed deve usar HTTPS."},400)
                return
            try:
                headers = {"Accept":"application/json","User-Agent":"ViralShopeeIA/2.2"}
                if cfg.get("product_feed_token"):
                    headers["Authorization"] = "Bearer " + cfg["product_feed_token"]
                request = urllib.request.Request(url,headers=headers)
                with urllib.request.urlopen(request,timeout=20) as response:
                    payload = json.loads(response.read(12*1024*1024).decode("utf-8"))
                products = payload.get("products",[]) if isinstance(payload,dict) else payload
                normalized = []
                for index, item in enumerate(products[:100]):
                    if not isinstance(item,dict):
                        continue
                    benefits = item.get("benefits",item.get("features",[]))
                    if not isinstance(benefits,list):
                        benefits = [str(benefits)]
                    normalized.append({
                        "id":str(item.get("id") or f"feed-{index}-{int(time.time())}"),
                        "name":item.get("name") or item.get("title") or "Produto sem nome",
                        "price":item.get("price",""),"category":item.get("category","Achadinhos variados"),
                        "rating":item.get("rating","Não informado"),"sales":item.get("sales",item.get("sold","Não informado")),
                        "commission":item.get("commission","Não informada"),
                        "affiliate_url":item.get("affiliate_url",item.get("link","")),
                        "image_url":item.get("image_url",item.get("image","")),
                        "benefits":benefits,"source":"Feed/API configurado","status":"new"})
                existing = {item["id"]:item for item in db["products"]}
                for item in normalized:
                    existing[item["id"]] = item
                db["products"] = list(existing.values())
                save_json(DB,db)
                self.send_json({"products":normalized,"demo":False,"message":f"{len(normalized)} produtos recebidos do feed configurado."})
            except Exception as exc:
                self.send_json({"error":"Não foi possível consultar o feed: "+str(exc)},502)
            return

        if path == "/api/product":
            product = body.get("product",{})
            product["id"] = product.get("id") or make_id()
            product.setdefault("status","new")
            product.setdefault("benefits",[])
            db["products"] = [item for item in db["products"] if item.get("id") != product["id"]] + [product]
            save_json(DB,db)
            self.send_json({"ok":True,"product":product})
            return

        if path == "/api/generate":
            product_id = body.get("product_id")
            product = next((item for item in db["products"] if item.get("id") == product_id),None)
            if not product:
                self.send_json({"error":"Produto não encontrado"},404)
                return
            video = {"id":make_id(),"product_id":product_id,"product_name":product.get("name","Produto"),
                "status":"Aguardando revisão","approved":False,"style":body.get("style","product"),
                "scripts":scripts(product,body.get("style","product")),"file":"",
                "created_at":time.strftime("%Y-%m-%d %H:%M:%S"),"voice_index":len(db.get("videos",[]))}
            try:
                video = render_mp4(product,video,body.get("style","product"))
            except Exception as exc:
                self.send_json({"error":"Falha ao gerar MP4: "+str(exc)},500)
                return
            db["videos"].insert(0,video)
            product["status"] = "video criado"
            save_json(DB,db)
            self.send_json({"ok":True,"video":video})
            return

        if path == "/api/batch":
            target = max(1,min(30,int(body.get("count",cfg.get("daily_target",10)))))
            today = time.strftime("%Y-%m-%d")
            existing_ids = {v.get("product_id") for v in db["videos"] if v.get("created_at","").startswith(today)}
            candidates = [p for p in db["products"] if p.get("id") not in existing_ids][:target]
            if not candidates:
                candidates = db["products"][:target]
            made, errors = [], []
            for product in candidates:
                video = {"id":make_id()+str(len(made)),"product_id":product.get("id"),
                    "product_name":product.get("name","Produto"),"status":"Aguardando revisão",
                    "approved":False,"style":"product","scripts":scripts(product,"product"),"file":"",
                    "created_at":time.strftime("%Y-%m-%d %H:%M:%S"),
                    "voice_index":len(db.get("videos",[]))+len(made)}
                try:
                    video = render_mp4(product,video,"product")
                    db["videos"].insert(0,video)
                    product["status"] = "video criado"
                    made.append(video)
                except Exception as exc:
                    errors.append({"product":product.get("name"),"error":str(exc)})
            save_json(DB,db)
            self.send_json({"ok":True,"created":len(made),"videos":made,"errors":errors,
                "message":f"{len(made)} vídeo(s) criado(s) e aguardando revisão."})
            return

        if path == "/api/review":
            video_id = body.get("video_id")
            video = next((item for item in db["videos"] if item.get("id") == video_id),None)
            if not video:
                self.send_json({"error":"Vídeo não encontrado"},404)
                return
            action = body.get("action")
            video["status"] = "Aprovado para publicação" if action == "approve" else "Rejeitado"
            video["approved"] = action == "approve"
            video["reviewed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_json(DB,db)
            self.send_json({"ok":True,"video":video})
            return

        if path == "/api/export":
            self.send_json({"ok":True,"data":db})
            return

        self.send_json({"error":"Rota não encontrada"},404)

def main():
    host = "0.0.0.0"
    port = int(os.environ.get("PORT","8765"))
    if not os.environ.get("APP_USERNAME") or not os.environ.get("APP_PASSWORD"):
        raise SystemExit("Configure APP_USERNAME e APP_PASSWORD antes de iniciar o servidor.")
    print(f"ViralShopee IA 2.2 escutando em {host}:{port} (autenticação ativada)")
    ThreadingHTTPServer((host,port),Handler).serve_forever()

if __name__ == "__main__":
    main()
