# -*- coding: utf-8 -*-
import os
import sys
import socket
import time

from enum import Enum
from threading import Thread

from apscheduler.schedulers.background import BackgroundScheduler


MAX_CLIENT_MSG_SIZE = 8192
ENCODING = 'utf-8'


# id: [time connected, last time stamp, curr_size, last_size]
clients = {
    
}


def format_speed(speed):
    if speed > 1073741824:
        return f'{speed / 1073741824} GiB/s'
    if speed > 1048576:
        return f'{speed / 1048576} MiB/s'
    if speed > 1024:
        return f'{speed / 1024} KiB/s'
    return f'{speed} byte/s'


def print_speeds():
    curr_time = time.time()
    for client_id in clients.keys():
        curr_time_diff = curr_time - clients[client_id][1]
        total_time_diff = curr_time - clients[client_id][0]
        curr_size_diff = clients[client_id][2] - clients[client_id][3]
        total_size_diff = clients[client_id][2]
        clients[client_id][3] = clients[client_id][2]
        clients[client_id][1] = curr_time
        curr_speed = format_speed(curr_size_diff / curr_time_diff)
        avg_speed = format_speed(total_size_diff / total_time_diff)
        print(f"ID: {client_id}, Speed: {curr_speed}, AvgSpeed: {avg_speed}")


class XTerraClientMsgType(Enum):
    UNKNOWN_PROTOCOL = 0
    UNKNOWN_TYPE = 1
    OPTIONS = 2
    DATA = 3
    FINISHED = 4


def recv_client_msg(__socket):
    return __socket.recv(MAX_CLIENT_MSG_SIZE)


def get_data(msg):
    return msg[13:]


def send_unknown_protocol(__socket):
    data = b'X-TERRA UNKNOWN_PROTOCOL'
    __socket.send(data)


def send_ready(__socket):
    data = b'X-TERRA READY'
    __socket.send(data)


def send_success(__socket):
    data = b'X-TERRA SUCCESS'
    __socket.send(data)


def send_failure(__socket):
    data = b'X-TERRA FAILURE'
    __socket.send(data)


def send_disconnected(__socket):
    data = b'X-TERRA DISCONNECTED'
    __socket.send(data)


def get_filename_and_filesize(msg):
    msg = msg[16:].split(b' ')
    filename = msg[0][9:]
    filesize = msg[1][9:]
    return filename.decode(ENCODING), int(filesize.decode(ENCODING))


def get_client_msg_type(msg):
    msg = bytes(msg)
    if not msg.startswith(b'X-TERRA'):
        return XTerraClientMsgType.UNKNOWN_PROTOCOL
    msg = msg[8:]
    if msg.startswith(b'OPTIONS'):
        return XTerraClientMsgType.OPTIONS
    if msg.startswith(b'DATA'):
        return XTerraClientMsgType.DATA
    if msg.startswith(b'FINISHED'):
        return XTerraClientMsgType.FINISHED
    return XTerraClientMsgType.UNKNOWN_TYPE


def client_worker(__socket, addr, client_id):
    msg = recv_client_msg(__socket)

    if get_client_msg_type(msg) != XTerraClientMsgType.OPTIONS:
        send_unknown_protocol(__socket)
        clients.pop(client_id)
        return __socket.close()

    filename, filesize = get_filename_and_filesize(msg)

    if not os.path.isdir('uploads'):
        os.mkdir('uploads')

    file = open(os.path.join('uploads', filename), 'wb')

    send_ready(__socket)

    while True:
        msg = recv_client_msg(__socket)

        if get_client_msg_type(msg) == XTerraClientMsgType.FINISHED:
            if clients[client_id][2] == filesize:
                send_success(__socket)
            else:
                send_failure(__socket)
            break

        if get_client_msg_type(msg) == XTerraClientMsgType.DATA:
            data = get_data(msg)
            file.write(data)
            clients[client_id][2] += len(data)
            send_ready(__socket)
            continue

        send_disconnected(__socket)

    clients.pop(client_id)
    file.close()
    return __socket.close()


def main(host, port):
    scheduler = BackgroundScheduler()
    scheduler.add_job(print_speeds, 'interval', seconds=3)
    scheduler.start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.bind((host, port))

    server.listen()

    i = 0
    while True:

        connection, addr = server.accept()

        curr_time = time.time()
        clients[i] = [curr_time, curr_time, 0, 0]
        thread = Thread(target=client_worker, args=(connection, addr, i))
        thread.start()
        i += 1

    scheduler.shutdown()


if __name__ == '__main__':
    port = int(sys.argv[1])

    main('', port)
