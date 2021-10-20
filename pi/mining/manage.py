import sys
from socket import socket, AF_INET, SOCK_DGRAM, timeout


if __name__ == "__main__" and len(sys.argv) == 2:
    cmd = sys.argv[1]
    client_socket = socket(AF_INET, SOCK_DGRAM)
    client_socket.settimeout(4)
    sensor_ip = "192.168.43.107"
    sensor_port = 12000
    try:
        if(cmd == "relay_on"):
            client_socket.sendto("relayOn".encode(), (sensor_ip, sensor_port))
            client_socket.recvfrom(1024)
            print("relay turned on")
        elif(cmd == "relay_off"):
            client_socket.sendto("relayOff".encode(), (sensor_ip, sensor_port))
            client_socket.recvfrom(1024)
            print("relay turned off")
        elif(cmd == "get_data"):
            client_socket.sendto("getSensorData".encode(),
                                 (sensor_ip, sensor_port))
            message, _ = client_socket.recvfrom(1024)
            print(message)
        elif(cmd == "reset_energy"):
            client_socket.sendto(
                "resetSensorEnergy".encode(), (sensor_ip, sensor_port))
            message, _ = client_socket.recvfrom(1024)
            print("energy reset success")
        elif(cmd == "relay_state"):
            client_socket.sendto("getRelayState".encode(),
                                 (sensor_ip, sensor_port))
            message, _ = client_socket.recvfrom(1024)
            if(message.decode() == "1"):
                print("on")
            else:
                print("off")
        else:
            print("argument not correct")
    except timeout:
        print("unable to connect to nodemcu")
else:
    print("1 argument is required!")
