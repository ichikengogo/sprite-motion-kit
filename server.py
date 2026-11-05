"""Loopback-only, no persistent uploads. Run python server.py; open localhost:8765."""
import base64,io,json,zipfile,argparse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from PIL import Image,UnidentifiedImageError
from motion import validate,cutouts,export,require_ready
from demo import demo
from assist import suggest,parse_command
WEB=Path(__file__).parent/'web'
MAX_BODY=12*1024*1024
Image.MAX_IMAGE_PIXELS=16_000_000

def png(im):
    out=io.BytesIO();im.save(out,format='PNG');return out.getvalue()
def image_data(im):return 'data:image/png;base64,'+base64.b64encode(png(im)).decode()
class Handler(BaseHTTPRequestHandler):
    def send(self,body,typ='application/json',code=200):
        self.send_response(code);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path=='/api/demo':
            result={}
            for view in ('front','side','back'):
                im,rig,_=demo(view);result[view]={'image':image_data(im),'rig':rig,'demo':True}
            self.send(json.dumps(result).encode());return
        if self.path not in ('/','/app.js','/coordinates.js','/playback.js','/style.css'):self.send(b'Not found','text/plain',404);return
        p=WEB/({'/':'index.html'}.get(self.path,self.path[1:]));self.send(p.read_bytes(),{'html':'text/html; charset=utf-8','js':'text/javascript','css':'text/css'}[p.suffix[1:]])
    def do_POST(self):
        try:
            # Reject cross-origin requests. No CORS, remote binding, or filesystem paths in API.
            host=self.headers.get('Host','')
            if host.split(':')[0] not in ('127.0.0.1','localhost'): raise ValueError('Loopback Host required')
            if self.headers.get('Origin') not in (None,'http://'+host):raise ValueError('Cross-origin request refused')
            if self.path not in ('/api/render','/api/export','/api/suggest','/api/command'):self.send(b'Not found','text/plain',404);return
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=MAX_BODY:raise ValueError('Request must be <=12MB')
            data=json.loads(self.rfile.read(n))
            if self.path=='/api/command':
                self.send(json.dumps({'action':parse_command(data['command'])}).encode());return
            if self.path=='/api/suggest':
                raw=base64.b64decode(data['image'].split(',',1)[1],validate=True);im=Image.open(io.BytesIO(raw))
                if im.format!='PNG':raise ValueError('PNG only')
                im.load();rig,report=suggest(im.convert('RGBA'),data['view'],data.get('facing','right'));self.send(json.dumps({'rig':rig,'report':report}).encode());return
            rig=data['rig'];validate(rig)
            require_ready(rig)
            if data.get('demo'):
                _,canonical,layers=demo(rig['view'])
                if rig!=canonical:raise ValueError('Edited demo needs imported-image mode')
            else:
                raw=base64.b64decode(data['image'].split(',',1)[1],validate=True)
                im=Image.open(io.BytesIO(raw))
                if im.format!='PNG':raise ValueError('PNG only')
                im.load();im=im.convert('RGBA');validate(rig,im)
                if im.getchannel('A').getextrema()[0]==255:raise ValueError('Transparent background required; remove background first')
                layers=cutouts(im,rig)
                replacements=data.get('partImages',{})
                if not isinstance(replacements,dict) or any(k not in rig['parts'] for k in replacements):raise ValueError('Unknown replacement part')
                for name,encoded in replacements.items():
                    layer=Image.open(io.BytesIO(base64.b64decode(encoded.split(',',1)[1],validate=True)))
                    if layer.format!='PNG' or layer.size!=(384,384):raise ValueError('Replacement must be full-canvas 384x384 PNG')
                    layer.load();layer=layer.convert('RGBA')
                    if layer.getchannel('A').getextrema()[0]==255:raise ValueError('Replacement layer needs alpha transparency')
                    layers[name]=layer
                alternate=data.get('walkPartImages',{})
                if not isinstance(alternate,dict) or set(alternate)-{'left_thigh','right_thigh','left_shin','right_shin','left_hip','right_hip','garment_left','garment_right','garment_waist'}:raise ValueError('Unknown walk cloth part')
                for name,encoded in alternate.items():
                    layer=Image.open(io.BytesIO(base64.b64decode(encoded.split(',',1)[1],validate=True)))
                    if layer.format!='PNG' or layer.size!=(384,384):raise ValueError('Walk cloth must be full-canvas384 PNG')
                    layer.load();layer=layer.convert('RGBA')
                    if layer.getchannel('A').getextrema()[0]==255:raise ValueError('Walk cloth needs transparency')
                    layers['walk:'+name]=layer
                if any(layer.getbbox() is None for layer in layers.values()):raise ValueError('One or more masks contain no visible pixels')
            action=parse_command(data['command']) if data.get('command') else data['action']
            sheet,meta=export(rig,layers,action)
            if self.path=='/api/render':self.send(json.dumps({'sheet':image_data(sheet),'meta':meta}).encode())
            else:
                buf=io.BytesIO()
                with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
                    z.writestr('sheet.png',png(sheet));z.writestr('animation.json',json.dumps(meta,indent=2));z.writestr('rig.json',json.dumps(rig,indent=2))
                self.send(buf.getvalue(),'application/zip')
        except (ValueError,KeyError,TypeError,IndexError,AttributeError,OverflowError,UnidentifiedImageError,Image.DecompressionBombError) as e:self.send(json.dumps({'error':str(e)}).encode(),code=400)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    print(f'Sprite Motion Lab: http://127.0.0.1:{args.port} (local only)',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
