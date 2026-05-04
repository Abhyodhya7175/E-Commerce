from app import app
c = app.test_client()
r = c.get('/shop/')
print('STATUS', r.status_code)
print('LENGTH', len(r.data))
print('FIRST 400 BYTES:\n', r.data[:400])
