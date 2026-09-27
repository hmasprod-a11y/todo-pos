"""Offline ToDo licence issuer. Keep the private key OUTSIDE the application/repository."""
import argparse,base64,json
from datetime import date
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def generate_keypair(private_path,public_path):
    private=Ed25519PrivateKey.generate()
    private_path.write_bytes(private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    public=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    public_path.write_text(base64.b64encode(public).decode('ascii'),encoding='utf-8')

def sign_license(private_path,customer,machine_id,issued_at,expires_at,out):
    private=serialization.load_pem_private_key(private_path.read_bytes(),password=None)
    payload={'customer':customer,'machine_id':machine_id.upper(),'issued_at':issued_at,'expires_at':expires_at}
    canonical=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    payload['signature']=base64.b64encode(private.sign(canonical)).decode('ascii')
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest='cmd',required=True)
    g=sub.add_parser('keygen');g.add_argument('--private',required=True);g.add_argument('--public',required=True)
    s=sub.add_parser('sign');s.add_argument('--private',required=True);s.add_argument('--customer',required=True);s.add_argument('--machine',required=True);s.add_argument('--expires',required=True);s.add_argument('--out',required=True);s.add_argument('--issued',default=str(date.today()))
    a=p.parse_args()
    if a.cmd=='keygen':generate_keypair(Path(a.private),Path(a.public))
    else:sign_license(Path(a.private),a.customer,a.machine,a.issued,a.expires,Path(a.out))
