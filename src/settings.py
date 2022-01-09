import os

from dotenv import load_dotenv


load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
