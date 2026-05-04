from app import app

print("App blueprints:", list(app.blueprints.keys()))

with app.test_client() as c:
    r = c.get('/login')
    print(f"GET /login status: {r.status_code}")
    
    html = r.data.decode('utf-8')
    
    # Check if template rendered correctly
    if 'url_for' in html:
        print("ERROR: Jinja tags not rendered! Template not processed.")
        print(html[:500])
    else:
        print("OK: Jinja tags were processed")
        
    # Check if the link is present
    if 'Create one free' in html:
        print("OK: 'Create one free' link found")
        idx = html.find('Create one free')
        print("Link HTML:", html[max(0, idx-80):min(len(html), idx+120)])
    else:
        print("ERROR: 'Create one free' link not found")
        
    # Check if auth/register is in the HTML
    if 'auth.register' in html or '/register' in html:
        print("OK: Register route found in HTML")
    else:
        print("ERROR: Register route not found in HTML")
