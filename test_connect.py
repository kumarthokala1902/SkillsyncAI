import requests
import time

BASE_URL = 'http://127.0.0.1:5001'


def main():
    """Run the manual two-user smoke test against a local server."""
    session_learner = requests.Session()
    session_mentor = requests.Session()

    r = session_learner.post(f'{BASE_URL}/login', data={'email': 'alex@example.com', 'password': 'learner123'})
    print("Learner Login:", r.status_code)

    r = session_mentor.post(f'{BASE_URL}/login', data={'email': 'sarah@skillsync.com', 'password': 'mentor123'})
    print("Mentor Login:", r.status_code)

    r = session_learner.post(f'{BASE_URL}/api/connect/request/1')
    print("Request Connection:", r.status_code, r.json())
    conn_id = r.json().get('connection_id')

    r = session_mentor.get(f'{BASE_URL}/api/connect/notifications')
    print("Mentor Notifications:", r.status_code, r.json())

    if conn_id:
        r = session_mentor.post(f'{BASE_URL}/api/connect/accept/{conn_id}')
        print("Accept Connection:", r.status_code, r.json())

    r = session_learner.get(f'{BASE_URL}/api/connect/notifications')
    print("Learner Notifications:", r.status_code, r.json())

    r = session_learner.get(f'{BASE_URL}/dashboard')
    print("Learner Dashboard History Present:", "Live Connections" in r.text)
    print("Verification complete.")


if __name__ == '__main__':
    main()
