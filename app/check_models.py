from neo4j import GraphDatabase

# Ghi thẳng pass cũ của bạn vào đây, không dùng os.getenv nữa
driver = GraphDatabase.driver(
    "neo4j+s://f7d40e28.databases.neo4j.io", 
    auth=("neo4j", "5A6B22jjvwzpFUsAJDSiKqDdnoFLQIXc3GVCDHoNyOs") 
)
driver.verify_connectivity()
print("Kết nối thành công!")