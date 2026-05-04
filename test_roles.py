from app import app
c = app.test_client()
for path in ['/shop/', '/admin/', '/login', '/register']:
    r = c.get(path)
    print(path, r.status_code)
    print(r.data.decode('utf-8')[:200])
    print('---')
