import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database as db
from PIL import Image
from services.catalog import search_products
from services.images import valid_image

class PhotoCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.old=db.DB_PATH;db.DB_PATH=self.root/'db.sqlite';db.init_db()
    def tearDown(self):db.DB_PATH=self.old;self.tmp.cleanup()
    def product(self,name,path,visible=1):
        with db.connect() as c:return c.execute('INSERT INTO products(name,image_path,show_in_sale_photos) VALUES(?,?,?)',(name,str(path),visible)).lastrowid
    def image(self,name):
        p=self.root/name;Image.new('RGB',(5,5),'red').save(p);return p
    def test_missing_corrupt_directory_and_empty_are_excluded(self):
        bad=self.root/'bad.png';bad.write_bytes(b'not an image')
        for i,path in enumerate(('',self.root/'missing.png',bad,self.root)):self.product(str(i),path)
        pid=self.product('valid',self.image('ok.png'))
        self.assertEqual([r['id'] for r in search_products(images_only=True)],[pid])
        self.assertEqual(len(search_products()),5)
    def test_valid_images_define_page_boundaries(self):
        for i in range(70):self.product(f'A{i:03}',self.root/'missing.png')
        ids=[self.product(f'B{i:03}',self.image(f'{i}.png')) for i in range(7)]
        self.assertEqual([r['id'] for r in search_products(images_only=True,limit=3,offset=3)],ids[3:6])
        self.assertEqual([r['id'] for r in search_products(images_only=True,limit=3,offset=6)],ids[6:])
    def test_cache_tracks_deletion_and_same_path_replacement(self):
        photo=self.image('replace.png');pid=self.product('visible',photo)
        self.assertTrue(valid_image(str(photo)));photo.write_bytes(b'bad')
        self.assertEqual(search_products(images_only=True),[])
        Image.new('RGB',(7,7)).save(photo)
        self.assertEqual(search_products(images_only=True)[0]['id'],pid)
        photo.unlink();self.assertEqual(search_products(images_only=True),[])
    def test_explicit_hidden_image_stays_hidden(self):
        self.product('hidden',self.image('hide.png'),0);self.assertEqual(search_products(images_only=True),[])
    def test_search_and_category_still_filter_valid_images(self):
        with db.connect() as c:cat=c.execute("INSERT INTO categories(name) VALUES('Family')").lastrowid
        a=self.product('Coffee large',self.image('coffee.png'));self.product('Tea',self.image('tea.png'))
        with db.connect() as c:c.execute('INSERT INTO product_categories(product_id,category_id) VALUES(?,?)',(a,cat))
        self.assertEqual([r['id'] for r in search_products('Coffee',category=cat,images_only=True)],[a])
        self.assertEqual(search_products('Tea',category=cat,images_only=True),[])
