def request(method, api_uri, params=None, headers={}):
    global session_id

    if not session_id == None:
        headers["X-Session-Token"] = session_id

    conn = connect()
    conn.request(method.upper(), "%s/%s" % (API_BASE,api_uri), params, headers)
    response = conn.getresponse()
    data = response.read()

    print method, api_uri, params
    print data

    try:
        response_data = json.loads(data)
    except ValueError, e:
        # Some data is not JSON
        print "Response data is not JSON"
        sys.exit(1)

    print response_data

    if response_data['status'] == "OK":
        del response_data['status']
        return response_data['result']
    else:
        return response_data['result']

