import unittest,threading,urllib.request
from http.server import ThreadingHTTPServer
from server import Handler
class PlaybackRouteTest(unittest.TestCase):
 def test_clock_served_before_app(self):
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   root='http://127.0.0.1:'+str(server.server_port)
   with urllib.request.urlopen(root+'/playback.js') as response:self.assertIn('const SpritePlayback=',response.read().decode())
   with urllib.request.urlopen(root+'/') as response:
    html=response.read().decode();self.assertLess(html.index('/playback.js'),html.index('/app.js'))
  finally:server.shutdown();server.server_close();thread.join()
