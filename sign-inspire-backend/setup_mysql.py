"""
MySQL 数据库设置脚本
用于创建数据库和测试连接
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# 从环境变量读取配置
load_dotenv(override=True)  # 强制重新加载
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "sign_inspire")

# 调试输出（可选，注释掉以减少输出）
# print(f"[DEBUG] Loaded config:")
# print(f"   DB_HOST={DB_HOST}")
# print(f"   DB_PORT={DB_PORT}")
# print(f"   DB_USER={DB_USER}")
# print(f"   DB_PASSWORD={'*' * len(DB_PASSWORD) if DB_PASSWORD else '(empty)'}")
# print(f"   DB_NAME={DB_NAME}")
# print()

def test_connection():
    """Test MySQL connection"""
    try:
        print(f"[INFO] Testing MySQL connection...")
        print(f"   Host: {DB_HOST}:{DB_PORT}")
        print(f"   User: {DB_USER}")
        print(f"   Password: {'*' * len(DB_PASSWORD) if DB_PASSWORD else '(empty)'}")
        
        # Connect to MySQL (without specifying database)
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            charset='utf8mb4',
            autocommit=True
        )
        
        print("[SUCCESS] MySQL connection successful!")
        return conn
    except pymysql.err.OperationalError as e:
        if e.args[0] == 1045:
            print(f"[ERROR] Connection failed: Invalid username or password")
            print(f"   Details: {e}")
            print("\n[TIP] Please check DB_USER and DB_PASSWORD in .env file")
        else:
            print(f"[ERROR] Connection failed: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return None

def create_database(conn):
    """Create database"""
    try:
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SHOW DATABASES LIKE '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if exists:
            print(f"[INFO] Database '{DB_NAME}' already exists")
        else:
            # Create database
            print(f"[INFO] Creating database '{DB_NAME}'...")
            cursor.execute(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"[SUCCESS] Database '{DB_NAME}' created successfully!")
        
        cursor.close()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create database: {e}")
        return False

def main():
    print("=" * 60)
    print("MySQL Database Setup Tool")
    print("=" * 60)
    print()
    
    # 测试连接
    conn = test_connection()
    if not conn:
        print("\n[ERROR] Cannot connect to MySQL, please check configuration")
        return
    
    print()
    
    # 创建数据库
    if create_database(conn):
        print()
        print("=" * 60)
        print("[SUCCESS] Database setup completed!")
        print("=" * 60)
        print("\nYou can now start the application:")
        print("  fastapi dev app/main.py")
    else:
        print("\n[ERROR] Database setup failed")
    
    conn.close()

if __name__ == "__main__":
    main()
