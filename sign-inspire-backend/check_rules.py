"""
检查数据库中的规则和当前状态
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "sign_inspire")

try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4'
    )
    
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SHOW TABLES LIKE 'rules'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        print("[ERROR] Table 'rules' does not exist!")
        print("Please start the application first to create tables.")
    else:
        # 查询规则数量
        cursor.execute("SELECT COUNT(*) FROM rules")
        count = cursor.fetchone()[0]
        print(f"[INFO] Total rules in database: {count}")
        
        if count == 0:
            print("\n[WARNING] No rules found in database!")
            print("This is why CURRENT_PLAYLIST is 'default'.")
            print("\nTo fix this:")
            print("1. Go to Dashboard page (http://localhost:5173)")
            print("2. Create a new rule (e.g., '如果当前多云，请播放咖啡广告')")
            print("3. Click '确认并生效' to save it")
            print("4. The rule will be saved to MySQL database")
            print("5. Player page will automatically show the coffee ad when weather matches")
        else:
            # 显示所有规则
            cursor.execute("SELECT id, store_id, name, priority, conditions, action FROM rules ORDER BY priority DESC")
            rules = cursor.fetchall()
            
            print("\n[INFO] Rules in database:")
            print("=" * 80)
            for rule in rules:
                rule_id, store_id, name, priority, conditions, action = rule
                print(f"\nID: {rule_id}")
                print(f"Store: {store_id}")
                print(f"Name: {name}")
                print(f"Priority: {priority}")
                print(f"Conditions: {conditions}")
                print(f"Action: {action}")
            print("=" * 80)
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"[ERROR] {e}")
