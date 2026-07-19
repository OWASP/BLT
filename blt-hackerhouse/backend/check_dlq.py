import sqlite3
c = sqlite3.connect('blt_hackerhouse.db')
rows = c.execute("SELECT id, source, event_type, actor_name, error FROM dead_letter_queue").fetchall()
print(f'DLQ count: {len(rows)}')
for r in rows:
    print(f'  {r[0]}: {r[1]} / {r[2]} / {r[3]}')
    print(f'  error: {str(r[4])[:200]}')
