import csv,json,zipfile,tempfile
from datetime import datetime
from pathlib import Path
from database import connect
from services.security import require_admin,audit
from services.backup import create_backup

IMPORTABLE_TABLES={'categories','suppliers','clients','sellers','price_grids'}
_HIDDEN_PREFIXES=('sqlite_','product_search','fts5_')

def _quote(name):
    if not str(name).replace('_','').isalnum():
        raise ValueError('Nom de table invalide')
    return '"'+str(name).replace('"','""')+'"'

def table_inventory():
    with connect() as conn:
        names=[r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        result=[]
        for name in names:
            if name.startswith(_HIDDEN_PREFIXES) or name.startswith('product_search_'):
                continue
            count=conn.execute(f"SELECT COUNT(*) n FROM {_quote(name)}").fetchone()['n']
            result.append(dict(name=name,rows=int(count),importable=name in IMPORTABLE_TABLES))
        return result

def export_table_csv(table,destination):
    inventory={r['name'] for r in table_inventory()}
    if table not in inventory:raise ValueError('Table inconnue')
    path=Path(destination)
    with connect() as conn:
        columns=[r['name'] for r in conn.execute(f"PRAGMA table_info({_quote(table)})")]
        rows=conn.execute(f"SELECT * FROM {_quote(table)}").fetchall()
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8-sig') as fh:
        writer=csv.writer(fh);writer.writerow(columns)
        for row in rows:writer.writerow([row[c] for c in columns])
    return path

def import_reference_csv(table,source):
    if table not in IMPORTABLE_TABLES:
        raise ValueError('Import direct interdit pour cette table.')
    path=Path(source)
    if not path.is_file():raise ValueError('Fichier CSV introuvable.')
    with path.open('r',newline='',encoding='utf-8-sig') as fh:
        reader=csv.DictReader(fh)
        if not reader.fieldnames:raise ValueError('CSV sans en-tête.')
        rows=list(reader)
        headers=[h.strip() for h in reader.fieldnames if h and h.strip()]
    if not rows:raise ValueError('CSV vide.')
    with connect() as conn:
        info=conn.execute(f"PRAGMA table_info({_quote(table)})").fetchall()
        schema={r['name']:r for r in info}
    unknown=[h for h in headers if h not in schema]
    if unknown:raise ValueError('Colonnes inconnues: '+', '.join(unknown))
    # Never reuse exported primary keys. The destination owns its identifiers.
    insert_columns=[h for h in headers if not (h=='id' and schema[h]['pk'])]
    if not insert_columns:raise ValueError('Aucune colonne importable.')
    required=[r['name'] for r in info if r['notnull'] and r['dflt_value'] is None and not r['pk']]
    missing=[name for name in required if name not in insert_columns]
    if missing:raise ValueError('Colonnes obligatoires manquantes: '+', '.join(missing))
    safety=create_backup()
    placeholders=','.join('?' for _ in insert_columns)
    cols=','.join(_quote(c) for c in insert_columns)
    sql=f"INSERT INTO {_quote(table)} ({cols}) VALUES ({placeholders})"
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE');require_admin(conn)
        try:
            for row in rows:
                values=[row.get(c,'') for c in insert_columns]
                conn.execute(sql,values)
            problems=conn.execute('PRAGMA foreign_key_check').fetchall()
            if problems:raise ValueError('Relations invalides après import.')
            audit(conn,'DATABASE_TABLE_IMPORT',table,f'{len(rows)} rows; safety={safety}')
            conn.commit()
        except Exception:
            conn.rollback();raise
    return dict(rows=len(rows),safety=str(safety))

def integrity_status():
    with connect() as conn:
        integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
        fk=conn.execute('PRAGMA foreign_key_check').fetchall()
    return dict(ok=(integrity=='ok' and not fk),integrity=integrity,foreign_key_errors=len(fk))


def export_schema_sql(destination):
    """Export the live SQLite application schema as readable SQL."""
    path=Path(destination)
    with connect() as conn:
        rows=conn.execute("""SELECT type,name,sql FROM sqlite_master
                             WHERE sql IS NOT NULL
                               AND name NOT LIKE 'sqlite_%'
                               AND name NOT LIKE 'product_search_%'
                             ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 WHEN 'trigger' THEN 2 ELSE 3 END,name""").fetchall()
        version=conn.execute('PRAGMA user_version').fetchone()[0]
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8') as fh:
        fh.write('-- ToDo POS SQLite schema export\n')
        fh.write(f'-- Generated: {datetime.now().isoformat(timespec="seconds")}\n')
        fh.write(f'-- user_version: {version}\n\nPRAGMA foreign_keys=ON;\n\n')
        for row in rows:
            sql=(row['sql'] or '').strip()
            if sql:
                fh.write(sql.rstrip(';')+';\n\n')
    return path

def export_database_bundle(destination):
    """Create a reviewable delivery bundle: schema.sql + one CSV per table + manifest."""
    path=Path(destination)
    if path.suffix.lower()!='.zip':path=path.with_suffix('.zip')
    inventory=table_inventory()
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        schema_path=export_schema_sql(root/'schema.sql')
        tables_dir=root/'tables';tables_dir.mkdir()
        exported=[]
        for item in inventory:
            name=item['name']
            csv_path=tables_dir/f'{name}.csv'
            export_table_csv(name,csv_path)
            exported.append({'table':name,'rows':item['rows'],'file':f'tables/{name}.csv'})
        with connect() as conn:
            version=conn.execute('PRAGMA user_version').fetchone()[0]
            integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
        manifest={
            'format':'todo-database-export',
            'version':1,
            'created_at':datetime.now().isoformat(timespec='seconds'),
            'sqlite_user_version':int(version),
            'integrity':integrity,
            'tables':exported,
        }
        (root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        path.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
            z.write(schema_path,'schema.sql')
            z.write(root/'manifest.json','manifest.json')
            for item in exported:
                z.write(root/item['file'],item['file'])
    return path
