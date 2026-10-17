import sqlite3
c = sqlite3.connect('blt_hackerhouse.db')
ev = c.execute('SELECT id, source, event_type, actor_name FROM events ORDER BY id').fetchall()
print(f'events: {len(ev)}')
for r in ev:
    print(f'  {r[0]}: {r[1]} / {r[2]} / {r[3]}')
co = c.execute('SELECT id, display_name, score FROM contributors ORDER BY score DESC').fetchall()
print(f'contributors: {len(co)}')
for r in co:
    print(f'  {r[0]}: {r[1]} score={r[2]}')
av = c.execute('SELECT floor, room, count(*) FROM avatar_state GROUP BY floor, room').fetchall()
print(f'avatars by room: {av}')
