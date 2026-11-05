import unittest,math,json,io
from PIL import Image
from demo import demo
from motion import pose,render,export,validate,sub,length,template,cutouts

class MotionTests(unittest.TestCase):
    def test_all_views_and_actions_rigid_lengths(self):
        for view in ('front','side','back'):
            _,rig,layers=demo(view);validate(rig)
            for action in ('walk','dash'):
                for i in range(121):
                    transforms,ds=pose(rig,action,i/120)
                    for d in ds:
                        self.assertAlmostEqual(length(sub(d['knee'],d['hip'])),d['lengths'][0],places=8)
                        self.assertAlmostEqual(length(sub(d['ankle'],d['knee'])),d['lengths'][1],places=8)
                        self.assertLess(d['reach_error'],1e-4)
                        self.assertEqual(transforms[d['side']+'_foot'][0],d['ankle'])
    def test_loop_exact_no_duplicate_endpoint(self):
        for view in ('front','side','back'):
            _,r,l=demo(view)
            for action in ('walk','dash'):
                self.assertEqual(pose(r,action,0),pose(r,action,1))
                self.assertEqual(render(r,l,action,0)[0].tobytes(),render(r,l,action,1)[0].tobytes())
                self.assertNotEqual(render(r,l,action,0)[0].tobytes(),render(r,l,action,23/24)[0].tobytes())
    def test_foot_contact_world_space(self):
        for view in ('front','side','back'):
            _,r,_=demo(view)
            for action in ('walk','dash'):
                cfg=template(action)
                for index in (0,1):
                    vals=[]
                    for q in (.05,.25,.5,.75,.95):
                        # evaluate within one foot's single contact interval
                        t=q*cfg['stance']-index*.5;_,d=pose(r,action,t);foot=d[index]
                        self.assertTrue(foot['contact']);vals.append([foot['ankle'][0]+foot['ground_velocity']*t*cfg['duration'],foot['ankle'][1]])
                    for v in vals:self.assertLess(length(sub(v,vals[0])),1e-7)
    def test_distinct_templates(self):
        _,r,_=demo('side');a,_=pose(r,'walk',.25);b,_=pose(r,'dash',.25)
        self.assertNotEqual(a,b);self.assertLess(template('dash')['stance'],.5);self.assertGreater(template('walk')['stance'],.5)
    def test_export_contract_alpha_canvas_pivot(self):
        for view in ('front','side','back'):
            _,r,l=demo(view);sheet,m=export(r,l,'walk')
            self.assertEqual(m['view'],view);self.assertEqual(m['status'],'draft');self.assertEqual(m['rootPivot'],[192,210]);self.assertEqual(len(m['frames']),24)
            self.assertEqual(m['fps']*m['duration'],24);self.assertEqual(sheet.size,(2304,1536));self.assertEqual(sheet.mode,'RGBA');self.assertEqual(sheet.getpixel((0,0))[3],0)
            self.assertFalse(m['quality']['borderAlpha']);self.assertLess(m['quality']['maxContactStepSlipPx'],1e-6)
            for f in m['frames']:self.assertEqual((f['rect']['w'],f['rect']['h']),(384,384));self.assertLess(f['time'],m['duration'])
            json.dumps(m);b=io.BytesIO();sheet.save(b,format='PNG');self.assertEqual(Image.open(io.BytesIO(b.getvalue())).mode,'RGBA')
    def test_missing_parts_and_bad_coordinates_rejected(self):
        _,r,_=demo('front');del r['parts']['left_foot']
        with self.assertRaises(ValueError):validate(r)
        _,r,_=demo('side');r['parts']['head']['start']=[float('nan'),1]
        with self.assertRaises(ValueError):validate(r)
    def test_import_does_not_mutate_original(self):
        im,r,_=demo('back');before=im.tobytes();layers=cutouts(im,r);self.assertEqual(im.tobytes(),before);self.assertEqual(len(layers),12)
    def test_view_identity_and_no_mirror(self):
        f,_,_=demo('front');s,_,_=demo('side');b,_,_=demo('back')
        self.assertNotEqual(f.tobytes(),b.tobytes());self.assertNotEqual(f.tobytes(),s.tobytes())
        for v in ('front','side','back'):
            _,r,l=demo(v);self.assertLess(r['parts']['left_thigh']['start'][0],r['parts']['right_thigh']['start'][0]);self.assertNotEqual(l['left_thigh'].getpixel(tuple(r['parts']['left_thigh']['start'])),l['right_thigh'].getpixel(tuple(r['parts']['right_thigh']['start'])))
if __name__=='__main__':unittest.main()
