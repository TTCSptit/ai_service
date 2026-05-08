import sqlalchemy
from app.core.config import settings

def run_migration():
    engine = sqlalchemy.create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("Adding ai_data_json column to chat_history table...")
        try:
            conn.execute(sqlalchemy.text("ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS ai_data_json TEXT;"))
            conn.commit()
            print("Successfully added ai_data_json column.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_migration()
