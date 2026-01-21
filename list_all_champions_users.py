import os
from sqlalchemy import create_engine, text


def main():
    db_url = os.environ.get('PRODUCTION_DATABASE_URL')
    if not db_url:
        print('PRODUCTION_DATABASE_URL not set')
        return

    # Normalize Postgres URL if needed
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

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


if __name__ == '__main__':
    main()
