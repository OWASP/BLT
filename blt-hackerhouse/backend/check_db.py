import sqlite3
c = sqlite3.connect('blt_hackerhouse.db')
pc = list(c.execute('SELECT * FROM poll_cursors'))
print('poll_cursors:', pc)
ev = list(c.execute('SELECT id, source, event_type, actor_name FROM events ORDER BY id LIMIT 5'))
print(f'events ({len(ev)}):')
for r in ev:
    print(f'  {r[0]}: {r[1]} / {r[2]} / {r[3]}')
co = list(c.execute('SELECT id, display_name, score FROM contributors ORDER BY score DESC'))
print(f'contributors ({len(co)}):')
for r in co:
    print(f'  {r[0]}: {r[1]} score={r[2]}')
av = list(c.execute('SELECT contributor_id, floor, room FROM avatar_state'))
print(f'avatars ({len(av)}):')
for r in av:
    print(f'  {r[0]}: floor={r[1]} room={r[2]}')
