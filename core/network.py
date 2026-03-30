import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_secure_session():
    session = requests.Session()
    session.verify = False
    return session


global_session = get_secure_session()
