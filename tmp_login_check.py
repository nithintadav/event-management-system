from route import app

with app.test_client() as client:
    resp = client.post('/login', data={'email': 'admin@example.com', 'password': 'Admin@2026!'}, follow_redirects=False)
    print('status', resp.status_code)
    print('location', resp.headers.get('Location'))
    print(resp.get_data(as_text=True)[:500])
