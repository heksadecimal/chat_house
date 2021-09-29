import time
import socket
from threading import Thread
from group import Group

HOST = "localhost"
PORT = 5500
BUFF_SIZE = 1024
groups = dict()
SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

SPECIAL_MESSAGES = [
    "whosonline",
    "strength",
    "kick",
    "quit",
    "destruct",
    "makeowner",
    "whosadmin",
    "whoswaiting",
    "accept",
    "reject",
    "mute",
    "unmute",
]

ADMIN_ONLY = [
    "kick",
    "destruct",
    "makeowner",
    "whoswating",
    "accept",
    "reject",
    "mute",
    "unmute",
]


def private_except_message(
    username: str, client: socket, group: Group, message: str
) -> None:
    """
    Function to handle private messages
    :param username: sender
    :param client: socket object of the sender
    :param group: group object of the group sender is currently in
    :param message: the message (along with the receiver's info)
    :return:
    """
    receivers, *msg = message[1:].split()
    message = " ".join(msg)

    receivers = [i.strip() for i in receivers.split(",")]

    for member in group.members:
        if member not in receivers:
            group.private_message(username, member, message)


def private_message(username: str, client: socket, group: Group, message: str) -> None:
    """
    Function to handle private messages
    :param username: sender
    :param client: socket object of the sender
    :param group: group object of the group sender is currently in
    :param message: the message (along with the receiver's info)
    :return:
    """

    receivers, *msg = message[1:].split()
    message = " ".join(msg)

    receivers = receivers.split(",")
    for receiver in receivers:
        receiver = receiver.strip()
        if receiver in group.members:
            group.private_message(username, receiver, message)


def special_message(username: str, client: socket, group: Group, message: str) -> None:
    """
    Function to handle special messages (starting with '!')
    :param username: username of the sender
    :param client: socket object of the sender
    :param group: Group object of the sender's current group
    :param message: the message along with the special instruction
    :return: None
    """
    special, *msg = message[1:].split()
    message = " ".join(msg)

    if special not in SPECIAL_MESSAGES:
        client.sendall("No such special command! ".encode())
        return

    if username != group.admin and special in ADMIN_ONLY:
        client.sendall(
            "You can't preform this action until you are an admin :(".encode()
        )
        return

    if special == "quit":
        group.quit(username)
        # kill(client)

    elif special == "whosonline":
        group.whosonline(username)

    elif special == "strength":
        group.strength(username)

    elif special == "kick":
        group.kick(message)

    elif special == "destruct":
        group.destruct()
        del group

    elif special == "makeowner":
        group.changeadmin(message)

    elif special == "whosadmin":
        group.whosadmin(username)

    elif special == "whoswaiting":
        group.whoswaiting()

    elif special == "mute":
        group.mute(message)

    elif special == "unmute":
        group.unmute(message)

    elif special == "accept":
        if group.type != "private":
            client.send("This action is only viable in a private group")
            return

        group.accept(message)

    elif special == "reject":
        if group.type != "private":
            client.send("This action is only viable in a private group")
            return

        group.reject(message)


def listen(client: socket, username: str, group: Group):
    """
    listening thread for the server
    :param client: socket object of the user
    :param username: username of the user
    :param group: group object of the user's group
    :return: None
    """
    while True:
        try:
            if group.is_alive:
                message = client.recv(BUFF_SIZE).decode()
                if username not in group.members:
                    break

                if not group.muted_users[username]:
                    if not message:
                        message = "!quit"
                        special_message(username, client, group, message)
                        return

                    if message.startswith("@"):
                        private_message(username, client, group, message)
                    elif message.startswith("-"):
                        private_except_message(username, client, group, message)
                    elif message.startswith("!"):
                        special_message(username, client, group, message)
                    else:
                        group.broadcast(username, message)

            else:
                return

        except:
            # print(f"CONNECTION LOST TO {username}")
            break


def create_new_group(conn: socket, username: str, name: str) -> bool:
    """
    create a new group object
    :param conn: socket object of the user
    :param username: the username of the connected client
    :param name: name of the group
    :return: None
    """
    secret = None

    conn.send("Enter the type of group [open/secret/private]".encode())
    gtype = conn.recv(BUFF_SIZE).decode()

    if gtype not in ["open", "secret", "private"]:
        conn.send("Not a valid type of group".encode())
        time.sleep(1)
        conn.send("!!!KILL!!!".encode())
        return False

    if gtype == "secret":
        conn.send("Please enter a secret key for the group".encode())
        secret = conn.recv(BUFF_SIZE).decode()

    groups[name] = Group(name, username, conn, gtype, secret)
    conn.send("Creation Successful\n".encode())
    conn.send(f"You're the admin of this new {gtype} group".encode())

    return True


def service_user(conn: socket, username: str, group_name: str) -> None:
    """
    Function to allocate a new user to some group
    :param conn: socket object of client
    :param username: username of the client
    :param group_name: group name the user wants to join/create
    :return: None
    """
    if group_name in groups.keys() and groups[group_name].is_alive:
        group = groups[group_name]

        if group.type == "open":
            group.open_accept(conn, username)

        elif group.type == "secret":
            ok = group.secret_accept(conn, username)
            if not ok:
                return

        elif group.type == "private":
            group.private_accept(conn, username)

    else:

        conn.send(
            f'There is no group named "{group_name}". Would you like to create one? [y/n]'.encode()
        )
        answer = conn.recv(BUFF_SIZE).decode()

        if answer.lower() != "y":
            conn.send("!!!KILL!!!".encode())
            return

        ok = create_new_group(conn, username, group_name)

        if not ok:
            conn.send("!!!KILL!!!".encode())

    listen(conn, username, groups[group_name])


def welcome_user(conn: socket, addr: tuple) -> None:
    """
    Start the chat process
    :param conn: socket object of the client
    :param addr: ip adrress and port of the client
    :return:
    """
    ok = False
    try:
        conn.send("Welcome to chat_house!\nEnter you username:".encode())
        username = conn.recv(BUFF_SIZE).decode()

        conn.send("Enter the name of the group you want to join:".encode())
        group_name = conn.recv(BUFF_SIZE).decode()
        ok = True

    except:
        print(f"connection {addr} disappeared in midst of joining group")
        # print(f"[-] CONNECTION LOST TO {addr}")

    if ok:
        service_user(conn, username, group_name)


def start_server() -> None:
    """
    start the server
    :return: None
    """
    global SERVER
    SERVER.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    SERVER.bind((HOST, PORT))
    SERVER.listen()
    print("[+] SERVER IS UP AND RUNNING...")
    print("[+] WAITING FOR CONNECTIONS...")

    try:
        while True:
            conn, addr = SERVER.accept()
            # print(f"[+] {addr} connected to the server")
            user_thread = Thread(target=welcome_user, args=(conn, addr), daemon=True)
            user_thread.start()

    except:
        # SERVER.sendall(b"!!!KILL!!!")
        print("SERVER CRASHED")
        SERVER.close()


if __name__ == "__main__":
    start_server()
