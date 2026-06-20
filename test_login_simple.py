import requests

session = requests.Session()
BASE_URL = 'http://localhost:5000'

print('Testing hospital login with correct credentials...')
print()

login_data = {
    'username': 'hospital1',
    'password': 'pass123'
}

# Send POST without following redirects to see what happens
r = session.post(BASE_URL + '/hospital-login', data=login_data, allow_redirects=False)
print('Login POST status:', r.status_code)

if r.status_code == 302:
    location = r.headers.get('Location')
    print('Redirect location:', location)
    print()
    print('Following redirect...')
    
    # Now follow the redirect
    r2 = session.get(BASE_URL + location)
    print('Dashboard response status:', r2.status_code)
    print('Dashboard response length:', len(r2.text), 'bytes')
    
    # Check for key elements
    if 'Hospital Dashboard' in r2.text:
        print('✓ Dashboard title found')
    if 'refreshDashboardStats' in r2.text:
        print('✓ refreshDashboardStats function found')
    if 'DOMContentLoaded' in r2.text:
        print('✓ DOMContentLoaded event listener found')
else:
    print('Expected 302 redirect, got:', r.status_code)
    print(r.text[:500])
