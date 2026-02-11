"""
数据库初始化脚本
用于手动创建数据库表
"""
from app.database import init_db

if __name__ == "__main__":
    print("🚀 开始初始化数据库...")
    try:
        init_db()
        print("✅ 数据库初始化成功！")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        print("\n请检查：")
        print("1. MySQL 服务是否启动")
        print("2. .env 文件中的数据库配置是否正确")
        print("3. 数据库是否已创建")
