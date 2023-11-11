# -*- coding: utf-8 -*-
import os
import sys
import socket

from enum import Enum

DATA_BLOCK_SIZE = 1024
MAX_SERVER_MSG_SIZE = 1024
ENCODING = 'utf-8'


class XTerraServerMsgType(Enum):
    UNKNOWN_PROTOCOL = 0
    UNKNOWN_TYPE = 1
    READY = 2
    SUCCESS = 3
    FAILURE = 4
    DISCONNECTED = 5


def send_options(__socket, **kwargs):
    filename = kwargs['filename']
    filesize = kwargs['filesize']
    data = b'X-TERRA OPTIONS FILENAME='
    data += str(filename).encode(ENCODING)
    data += b' FILESIZE='
    data += str(filesize).encode(ENCODING)
    __socket.send(data)


def send_data(__socket, filedata):
    data = b'X-TERRA DATA '
    data += filedata
    __socket.send(data)


def send_finished(__socket):
    data = b'X-TERRA FINISHED'
    __socket.send(data)


def recv_server_msg(__socket):
    return __socket.recv(MAX_SERVER_MSG_SIZE)


def get_server_msg_type(msg):
    msg = bytes(msg)
    if not msg.startswith(b'X-TERRA'):
        return XTerraServerMsgType.UNKNOWN_PROTOCOL
    msg = msg[8:]
    if msg.startswith(b'UNKNOWN_PROTOCOL'):
        return XTerraServerMsgType.UNKNOWN_PROTOCOL
    if msg.startswith(b'READY'):
        return XTerraServerMsgType.READY
    if msg.startswith(b'SUCCESS'):
        return XTerraServerMsgType.SUCCESS
    if msg.startswith(b'FAILURE'):
        return XTerraServerMsgType.FAILURE
    if msg.startswith(b'DISCONNECTED'):
        return XTerraServerMsgType.DISCONNECTED
    return XTerraServerMsgType.UNKNOWN_TYPE


def main(server_host, server_port, filepath, filesize):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client_socket.connect((server_host, server_port))

    filename = os.path.basename(filepath)

    send_options(client_socket, filename=filename, filesize=filesize)

    msg = recv_server_msg(client_socket)

    if not get_server_msg_type(msg) == XTerraServerMsgType.READY:
        print('Server is not ready to receive data')
        return client_socket.close()

    file = open(filepath, 'rb')

    while True:
        data = file.read(DATA_BLOCK_SIZE)

        if not data:
            send_finished(client_socket)
            msg = recv_server_msg(client_socket)
            if get_server_msg_type(msg) == XTerraServerMsgType.SUCCESS:
                print('Successfully!')
            else:
                print('Error :(')
            break

        send_data(client_socket, data)

        msg = recv_server_msg(client_socket)
        server_status = get_server_msg_type(msg)

        if server_status == XTerraServerMsgType.READY:
            continue
        if server_status == XTerraServerMsgType.DISCONNECTED:
            print('Disconnected')
            break
        else:
            print('Unexpected server status')
            break

    # TODO: Add KeyboardInterrupt and process killing handler

    file.close()
    return client_socket.close()


if __name__ == '__main__':
    server_host = socket.gethostbyname(sys.argv[1])
    server_port = int(sys.argv[2])
    filepath = sys.argv[3]
    filesize = os.path.getsize(filepath)

    main(server_host, server_port, filepath, filesize)

