import sys,tempfile,unittest,base64,json
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'todo'))
import database
from services.license import verify_license_document,license_status
from services.license_policy import load_license_policy,save_license_policy
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

class LicenseTests(unittest.TestCase):
    def make_doc(self,machine='ABC',days=30):
        private=Ed25519PrivateKey.generate()
        public=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        payload={'customer':'TODO MARKET','machine_id':machine,'issued_at':str(date.today()),'expires_at':str(date.today()+timedelta(days=days))}
        canonical=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        payload['signature']=base64.b64encode(private.sign(canonical)).decode()
        return payload,base64.b64encode(public).decode()
    def test_valid_signed_machine_bound_license(self):
        doc,pub=self.make_doc()
        today=date.today()
        result=verify_license_document(doc,pub,machine_id='ABC',today=today)
        self.assertTrue(result['valid']);self.assertEqual(result['customer'],'TODO MARKET')
        self.assertEqual(result['issued_at'],str(today))
        self.assertEqual(result['days_remaining'],30)
    def test_invalid_issued_date_is_rejected(self):
        doc,pub=self.make_doc()
        bad=dict(doc);bad['issued_at']='not-a-date'
        private=Ed25519PrivateKey.generate()
        public=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        payload={k:bad[k] for k in ('customer','machine_id','issued_at','expires_at')}
        canonical=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        bad['signature']=base64.b64encode(private.sign(canonical)).decode()
        pub=base64.b64encode(public).decode()
        with self.assertRaises(ValueError):verify_license_document(bad,pub,machine_id='ABC')

    def test_tamper_machine_and_expiry_are_rejected(self):
        doc,pub=self.make_doc()
        bad=dict(doc);bad['customer']='OTHER'
        with self.assertRaises(ValueError):verify_license_document(bad,pub,machine_id='ABC')
        with self.assertRaises(ValueError):verify_license_document(doc,pub,machine_id='XYZ')
        expired,pub2=self.make_doc(days=-1)
        with self.assertRaises(ValueError):verify_license_document(expired,pub2,machine_id='ABC')

    def test_license_policy_moves_enforcement_out_of_sqlite_and_is_one_way(self):
        old_base=database.BASE_DIR
        with tempfile.TemporaryDirectory() as td:
            database.BASE_DIR=Path(td)
            try:
                save_license_policy('PUBLIC-KEY',True,maintenance=True)
                policy=load_license_policy()
                self.assertTrue(policy['enforced']);self.assertEqual(policy['public_key_b64'],'PUBLIC-KEY')
                self.assertNotIn('PUBLIC-KEY',(Path(td)/'data'/'license_policy.dat').read_text(encoding='utf-8'))
                with self.assertRaises(PermissionError):save_license_policy('PUBLIC-KEY',False)
                with self.assertRaises(PermissionError):save_license_policy('OTHER-KEY',True)
            finally:
                database.BASE_DIR=old_base

if __name__=='__main__':unittest.main()
