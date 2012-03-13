def connect():
    global conn

    if conn == None:
        conn = httplib.HTTPConnection(API_HOSTNAME, API_PORT)
        conn.connect()

    return conn

