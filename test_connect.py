import requests
import time

BASE_URL = 'http://127.0.0.1:5001'
session_learner = requests.Session()
session_mentor = requests.Session()

# 1. Login as Learner
r = session_learner.post(f'{BASE_URL}/login', data={'email': 'alex@example.com', 'password': 'learner123'})
print("Learner Login:", r.status_code)

# 2. Login as Mentor
r = session_mentor.post(f'{BASE_URL}/login', data={'email': 'sarah@skillsync.com', 'password': 'mentor123'})
print("Mentor Login:", r.status_code)

# 3. Learner requests connection with Mentor (Sarah's ID is likely 1 because she's first in init_sample_data mentors)
r = session_learner.post(f'{BASE_URL}/api/connect/request/1')
print("Request Connection:", r.status_code, r.json())
conn_id = r.json().get('connection_id')

# 4. Mentor polls notifications
r = session_mentor.get(f'{BASE_URL}/api/connect/notifications')
print("Mentor Notifications:", r.status_code, r.json())

# 5. Mentor accepts connection
if conn_id:
    r = session_mentor.post(f'{BASE_URL}/api/connect/accept/{conn_id}')
    print("Accept Connection:", r.status_code, r.json())

# 6. Learner polls notifications to get Zoom link
r = session_learner.get(f'{BASE_URL}/api/connect/notifications')
print("Learner Notifications:", r.status_code, r.json())

# 7. Learner checks dashboard for session history
r = session_learner.get(f'{BASE_URL}/dashboard')
print("Learner Dashboard History Present:", "Live Connections" in r.text)

print("Verification complete.")
