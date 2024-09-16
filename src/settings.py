import os

from dotenv import load_dotenv


load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

POSTGRES_DSN = f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

TICKETS_API_URL = os.getenv('TICKETS_API_URL')
EMPLOYEE_SURNAMES = os.getenv('EMPLOYEE_SURNAMES', '').split(',')
DEPARTMENT_ID = int(os.getenv('DEPARTMENT_ID'))
