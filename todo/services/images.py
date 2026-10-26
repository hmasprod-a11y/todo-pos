from pathlib import Path
import shutil, uuid
from database import BASE_DIR
BASE=BASE_DIR
IMGDIR=BASE/"assets"/"products"

def import_image(source):
    if not source: return ""
    src=Path(source)
    if not src.exists(): return ""
    IMGDIR.mkdir(parents=True,exist_ok=True)
    dst=IMGDIR/f"{uuid.uuid4().hex}{src.suffix.lower() or '.jpg'}"
    shutil.copy2(src,dst)
    return str(dst.relative_to(BASE))

def abs_image(rel):
    if not rel:return None
    p=BASE/rel
    return p if p.exists() else None


from functools import lru_cache


def image_signature(rel):
    """File identity changes when an image is replaced at the same path."""
    path=abs_image(rel)
    if path is None:return None
    try:
        stat=path.stat()
        return str(path),stat.st_mtime_ns,stat.st_size,stat.st_ctime_ns
    except OSError:return None


@lru_cache(maxsize=2048)
def _decodable_image(signature):
    try:
        from PIL import Image
        with Image.open(signature[0]) as source:
            source.load()
            return source.width>0 and source.height>0
    except (ImportError,OSError,ValueError,SyntaxError):return False


def valid_image(rel):
    signature=image_signature(rel)
    return bool(signature and _decodable_image(signature))
