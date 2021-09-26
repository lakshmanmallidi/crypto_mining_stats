def connect():
    import network
    ssid = "harrypotter"
    password = "mysticforce"
    station = network.WLAN(network.STA_IF)
    if station.isconnected() == True:
        return "Already connected"
    station.active(True)
    station.connect(ssid, password)
    while station.isconnected() == False:
        pass
    return "Connection successful"
