"""Small, repeatable SQLite migrations which preserve existing document data."""
import re
import sqlite3


def allow_blog_documents(con: sqlite3.Connection) -> None:
    schema = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='items'").fetchone()[0]
    if "'blog'" in schema:
        return
    old = "'note','project','paper','log'"
    if old not in schema:
        raise RuntimeError('Unrecognized document type constraint; migration not applied')
    if con.in_transaction:
        raise RuntimeError('Document type migration needs its own transaction')
    dependents = [row[0] for row in con.execute("SELECT sql FROM sqlite_master WHERE tbl_name='items' AND type IN ('index','trigger') AND sql IS NOT NULL")]
    sequence = con.execute("SELECT rowid,seq FROM sqlite_sequence WHERE name='items'").fetchone()
    # SQLite cannot extend a CHECK constraint in place. Keep child references
    # pointing at `items` while atomically replacing only that table.
    con.execute('PRAGMA foreign_keys=OFF')
    try:
        con.execute('BEGIN IMMEDIATE')
        replacement = re.sub(r'^CREATE TABLE\s+(?:"items"|items)', 'CREATE TABLE items_blog_upgrade', schema, count=1, flags=re.I)
        if replacement == schema:
            raise RuntimeError('Unrecognized items table definition')
        con.execute(replacement.replace(old, old + ",'blog'", 1))
        columns = ','.join('"'+row[1]+'"' for row in con.execute('PRAGMA table_info(items)'))
        con.execute(f'INSERT INTO items_blog_upgrade ({columns}) SELECT {columns} FROM items')
        if con.execute('SELECT COUNT(*) FROM items').fetchone()[0] != con.execute('SELECT COUNT(*) FROM items_blog_upgrade').fetchone()[0]:
            raise RuntimeError('Document copy count mismatch')
        con.execute('DROP TABLE items')
        con.execute('ALTER TABLE items_blog_upgrade RENAME TO items')
        for statement in dependents:
            con.execute(statement)
        con.execute("DELETE FROM sqlite_sequence WHERE name='items'")
        if sequence is not None:
            con.execute("INSERT INTO sqlite_sequence(rowid,name,seq) VALUES(?,'items',?)", (sequence[0], sequence[1]))
        if con.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise RuntimeError('Document migration changed a reference')
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.execute('PRAGMA foreign_keys=ON')
