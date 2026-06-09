from src.db.session import SessionLocal
from sqlalchemy import text

sql = open('/app/migrations/0007_add_video_project_items.sql').read()
db = SessionLocal()
try:
    db.execute(text(sql))
    db.commit()
    print('Migration 0007 applied successfully')
    result = db.execute(text("SELECT tablename FROM pg_tables WHERE tablename = 'video_project_items'"))
    rows = list(result)
    print('Table video_project_items exists:', len(rows) > 0)
    result2 = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='video_project_board_nodes' AND column_name='item_id'"))
    rows2 = list(result2)
    print('Column item_id in board_nodes exists:', len(rows2) > 0)
except Exception as e:
    db.rollback()
    import traceback; traceback.print_exc()
    print(f'Error: {e}')
finally:
    db.close()
