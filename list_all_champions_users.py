import os
from sqlalchemy import create_engine, text

db_url = os.environ.get('PRODUCTION_DATABASE_URL')
engine = create_engine(db_url)

with engine.connect() as conn:
    print('--- Champions ---')
    res = conn.execute(text('SELECT full_name, email, phone_number, assigned_champion_code FROM champions'))
    for row in res:
        print(row)
    print('--- Users ---')
    res = conn.execute(text('SELECT username, email FROM users'))
    for row in res:
        print(row)
