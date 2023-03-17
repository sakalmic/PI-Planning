import requests


class User:

    session = None
    CERTFILE = False

    def __init__(self, username, password):
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verification = self.CERTFILE

    def get_certfile(self):
        return self.CERTFILE

    def create_session(self, username, password):
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verification = self.CERTFILE
        return self.session

    def destroy_session(self):
        self.session = None
        return True

    def get_session(self):
        return self.session
