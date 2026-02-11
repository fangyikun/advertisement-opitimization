"""
手动执行全球规则种子：当 rules 表为空时写入
适用于：新库初始化、或清空规则后恢复默认
用法: python seed_rules.py
"""
from app.database import init_db, engine, USE_DATABASE

if __name__ == "__main__":
    if not USE_DATABASE or engine is None:
        print("⚠️ 数据库未连接，请先配置并启动 MySQL")
        exit(1)
    print("🚀 初始化表并执行规则种子...")
    init_db()
    from app.database import _seed_rules_if_empty
    _seed_rules_if_empty(engine)
    print("✅ 完成")
