#!/usr/bin/env python3

import socket
import sys
from threading import Thread

from colors import color

fg = color.fg
style = color.style

HOST = "localhost"
PORT = 5500


def kill(sock):
    sock.close()
    sys.exit()


def listen(sock):
    while True:
        try:
            data = sock.recv(1024).decode()
            if data == "!!!KILL!!!":
                kill(sock)

            if data == "":
                kill(sock)
            print(data)

        except KeyboardInterrupt:
            sock.sendall("!quit".encode())
            kill(sock)

        except:
            break


def sending(sock):
    while True:
        try:
            message = input().encode()
            sock.send(message)
            if message == "!quit":
                kill(sock)
                return

        except KeyboardInterrupt:
            sock.sendall("!quit".encode())
            kill(sock)

        except:
            print("\n You were disconnected from the server")
            break


def start_connection():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # client.settimeout(0.5)
        client.connect((HOST, PORT))
        listen_thread = Thread(target=listen, args=(client,), daemon=True)
        send_thread = Thread(target=sending, args=(client,), daemon=True)

        listen_thread.start()
        send_thread.start()
        listen_thread.join()
        exit(1)

    except KeyboardInterrupt:
        print("disconnected from the group")

    except:
        print("Looks like the server is down :(")


if __name__ == "__main__":
    start_connection()
