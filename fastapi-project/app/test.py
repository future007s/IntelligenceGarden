import taos


def test_connection():
    try:
        conn = taos.connect(
            host="tdengine",
            # host="47.95.172.26",
            user="root",
            password="taosdata",
            port=6030,
            timezone="Asia/Shanghai",
        )
        print("TDengine connection successful")
    except Exception as e:
        print(f"TDengine connection failed: {e}")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM farm_info LIMIT 1")
        result = cursor.fetchall()
        print("Query executed successfully:", result)
    except Exception as e:
        print(f"Query execution failed: {e}")
    finally:
        cursor.close()
        conn.close()
        print("Connection closed")


if __name__ == "__main__":
    test_connection()
# This script tests the connection to a TDengine database and executes a simple query.
