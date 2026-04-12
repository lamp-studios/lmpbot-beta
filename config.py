import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        self.token = os.getenv("DANGER_DONTSHARETOYKEN")
        self.prefix = "."
