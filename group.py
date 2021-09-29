import socket
from collections import defaultdict
from time import sleep

from colors import color

fg = color.fg
style = color.style


class Group:
    """
    Group class to manage group functions
    """

    def __init__(
        self, name: str, admin: str, conn: socket, type: str, secret_key: str
    ) -> None:
        """

        :param name:  name of the group
        :param admin: name of admin of the group
        :param conn: client socket
        :param type: type of group (open/secret/private)
        :param secret_key: secret key if the group is of type "secret"
        """

        self.name = name
        self.admin = admin
        self.type = type
        self.secret_key = secret_key
        self.is_alive = True

        self.members = set()
        self.members.add(admin)

        self.muted_users = defaultdict(lambda: False)

        self.waiting_users = set()
        self.waiting_clients = dict()

        self.clients = defaultdict(bool)
        self.clients[admin] = conn

    # ---------------------------------------
    # | COMMON BASE FUNCTIONS               |
    # ---------------------------------------

    # !! PRIVATE FUNCTIONS !!

    def valid_user(self, user: str) -> bool:
        try:
            _ = self.clients[user]
            return True
        except KeyError:
            return False

    def _add_user(self, user: str, conn: socket) -> None:
        """
        function to add the desired user to the group
        :param user: name of the user to add
        :param conn: socket object of the user
        :return: None
        """
        self.members.add(user)
        self.clients[user] = conn

    def _remove_user(self, user: str) -> None:
        """
        function to erase the desired user from the group
        :param user: name of the user to remove
        :return: None
        """
        del self.clients[user]
        self.members.remove(user)

    # !! PUBLIC FUNCTIONS !!
    def welcome_user(self, user: str) -> None:
        """
        A function to greet a new member of the group
        :param user: name to user to welcome
        :return:
        """
        message = f"{fg.green} {user} has just landed! {style.reset}"
        self.broadcast("", message)

    def broadcast(self, name: str, message: str) -> None:
        """
        Function to broadcast a message to the group members
        :param name: sender
        :param message: the message
        :return: None
        """

        sender = name
        if name:
            sender += ":"
        for member in self.members:
            if member != name:
                self.clients[member].send(f"{sender} {message}".encode())

    def private_message(self, sender: str, receiver: str, message: str) -> None:
        """
        Function for sending from a user to certain user(s)
        :param sender: sender
        :param receiver: receiver(s)
        :param message: message
        :return: None
        """
        self.clients[receiver].send(f"(private) {sender}: {message}".encode())

    def quit(self, user: str) -> None:
        """
        Function to remove the user who left the group
        :param user: the user who wants to leave the group
        :return: None
        """
        self.clients[user].send(f"{fg.red}You left the group {style.reset}".encode())

        self._remove_user(user)
        quit_message = f"{fg.red}{user} left the group {style.reset}"
        self.broadcast("", quit_message)

        if user == self.admin:
            if len(self.members):
                new_admin = next(iter(self.clients))
                self.changeadmin(new_admin)
            else:
                self.destruct()

    def strength(self, user: str) -> None:
        """
        Sends the information about the number of current online users of the group to the enquirer
        :param user: the enquirer
        :return: None
        """
        members = str(len(self.members))
        message = f"{fg.yellow} Currently {members} members are online in the group {style.reset}".encode()
        self.clients[user].sendall(message)

    def whosonline(self, user: str) -> None:
        """
        Sends a string containing names name of current online members of the group to the enquirer

        :param user: the enquirer
        :return: None
        """
        message = (
            f"SERVER: {fg.yellow} Currently online are: {style.reset}".encode()
            + b", ".join([i.encode() for i in self.members])
        )
        self.clients[user].sendall(message)

    def whosadmin(self, user: str) -> None:
        """
        Sends the name of the group admin to the enquirer
        :param user: the enquirer
        :return: None
        """
        self.clients[user].send(
            f"SERVER: {fg.red} {self.admin} {style.reset} {fg.yellow} is currently the admin of group {self.name} {style.reset}".encode()
        )

    # !!!ADMIN FUNCTIONS!!!

    def mute(self, users: str) -> None:
        """
        [admin function] Function to mute (they can only see messages) users of the group
        :param users: user(s) to mute
        :return: None
        """
        users = users.strip()
        users = users.split(",")
        users = [i.strip() for i in users]
        print(users)
        for user in users:
            if not self.muted_users[user] and user in self.members:
                self.clients[user].send(
                    f"{fg.yellow} You were muted by {self.admin} {style.reset}".encode()
                )
                self.muted_users[user] = self.clients[user]
                self.broadcast(
                    "", f"{fg.cyan}{user} was muted by {self.admin}{style.reset}"
                )

    def unmute(self, users: str):
        """
        [admin function] Function to unmute users of the group
        :param users: user(s) to unmute
        :return: None
        """
        users = users.strip()
        users = users.split(",")
        users = [i.strip() for i in users]

        for user in users:
            if self.muted_users[user]:
                self.broadcast(
                    "", f"{fg.lightblue}{user} was umuted by {self.admin}{style.reset}"
                )
                self.clients[user].send(
                    f"{fg.green} You were unmuted by {self.admin}".encode()
                )
                self.muted_users[user] = False

    def kick(self, user: str) -> None:
        """
        [admin function] Function to kick users out of the group
        :param user:
        :return: None
        """
        if user == self.admin:
            self.clients[self.admin].send(
                f"{fg.lightred} You cannot kick yourself from the group {style.reset} ".encode()
            )
            return

        self.clients[user].send(
            f"{fg.red}You were kicked out from the group {style.reset}".encode()
        )
        self._remove_user(user)

        kick_message = f"{fg.red} user {user} was kicked from the group by admin {self.admin} {style.reset}"
        self.broadcast("", kick_message)

    def changeadmin(self, user: str) -> None:
        """
        [admin function] To transfer the ownership of group to another person
        :param user: the new owner/admin of the group
        :return: None
        """
        change_message = f"{fg.lightcyan}Ownership of the group was transferred from {self.admin} to {user} {style.reset}"
        self.broadcast("", change_message)
        self.admin = user

    def destruct(self) -> None:
        """
        [admin function] To destroy the group completely kicking out every member including the admin
        :return: None
        """
        destruct_message = f"{fg.red} Admin destroyed the group {style.reset}"
        self.broadcast("", destruct_message)
        self.members = set()
        self.is_alive = False

    # ---------------------------------------
    # | FUNCTIONS FOR PRIVATE ROOM           |
    # ---------------------------------------

    def _remove_from_waiting_list(self, name: str) -> None:
        """
        method to remove a user from waiting list
        :param name: name of the user to be removed
        """
        del self.waiting_clients[name]
        self.waiting_users.remove(name)

    def whoswaiting(self) -> None:
        """
        method to send a string containing names name of current waiting members of the group
        :return: None
        """
        message = (
            f"SERVER: {fg.yellow} Currently waitng users are: {style.reset}".encode()
            + b", ".join(
                [f"{fg.orange}{i.encode()}{style.reset}" for i in self.waiting_users]
            )
        )
        self.clients[self.admin].sendall(message)

    def accept(self, name: str) -> None:
        """
        method to accept a user in waitng list
        :param name: username of the user wanting to enter the group
        :return: None
        """

        try:

            _ = self.waiting_clients[name]

            try:
                self.waiting_clients[name].send(
                    f"{fg.green}Your request to join the group has been accepted.{style.reset}".encode()
                )
            except:
                self.clients[self.admin].send(
                    f"{fg.lightcyan} Looks like the user was tired of waiting and left {style.reset}".encode()
                )
                self._remove_from_waiting_list(name)
                return

            self.welcome_user(name)
            self.members.add(name)
            self.clients[name] = self.waiting_clients[name]
            self._remove_from_waiting_list(name)

        except:
            self.clients[self.admin].send("No such user in the waiting list".encode())

    def reject(self, name: str) -> None:
        """
        method to reject a user in waitng list
        :param name: username of the user wanting to enter the group
        :return: None
        """

        try:

            _ = self.waiting_clients[name]

            try:
                self.waiting_clients[name].send(
                    f"{fg.red}Your request to join the group has been rejected.{style.reset}".encode()
                )
                sleep(2)
                # self.waiting_clients[name].send("!!!KILL!!!".encode())

            except:
                self.clients[self.admin].send(
                    f"{fg.lightcyan} Looks like the user was tired of waiting and left {style.reset}".encode()
                )

            self._remove_from_waiting_list(name)

        except:
            self.clients[self.admin].send("No such user in the waiting list".encode())

    def private_accept(self, conn: socket, name: str) -> None:
        """
        Function to accept or reject a user trying to enter in a private group
        :param conn: socket
        :param name: username of the user trying to connect
        :return: bool
        """

        conn.send(
            f"{fg.lightblue} Your request has been sent successfully to the admin of the group {style.reset}".encode()
        )

        self.clients[self.admin].send(
            f"{fg.lightcyan} user {name} has requested to join the group.{style.reset}".encode()
        )

        self.waiting_users.add(name)
        self.waiting_clients[name] = conn

    # ---------------------------------------
    # | FUNCTIONS FOR SECRET ROOM           |
    # ---------------------------------------

    def secret_accept(self, conn: socket, name: str) -> bool:
        """
        Function to accept or reject a user trying to enter in a secret group
        :param conn: socket
        :param name: username of the user trying to connect
        :return: bool
        """
        conn.send("Enter password to prove you are worthy: ".encode())
        passwd = conn.recv(1024).decode()
        if self.valid(passwd):
            self._add_user(name, conn)
            conn.send("Welcome to the secret chat".encode())
            return True
        else:
            conn.send("Wrong password".encode())
            return False

    def valid(self, secret_key):
        return secret_key == self.secret_key

    # ---------------------------------------
    # | FUNCTIONS FOR OPEN ROOM             |
    # ---------------------------------------

    def open_accept(self, conn: socket, name: str) -> None:
        """
        Function to accept a user trying to enter in a open group
        :param conn: socket
        :param name: username of the user trying to connect
        :return: bool
        """
        self.welcome_user(name)
        self._add_user(name, conn)
        self.clients[name].send("Welcome to the chatroom".encode())
