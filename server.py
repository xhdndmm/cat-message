print('''
###################################################################
#              __                                                
#  _________ _/ /_      ____ ___  ___  ______________ _____ ____ 
# / ___/ __ `/ __/_____/ __ `__ \/ _ \/ ___/ ___/ __ `/ __ `/ _ \
#/ /__/ /_/ / /_/_____/ / / / / /  __(__  |__  ) /_/ / /_/ /  __/
#\___/\__,_/\__/     /_/ /_/ /_/\___/____/____/\__,_/\__, /\___/ 
#                                                   /____/       
#cat-message-server-v1.2
#https://github.com/xhdndmm/cat-message      
#你可以输入stop来停止服务器
#You can enter stop to stop the server
#服务器日志：./server.log      
#Server log: ./server.log
#聊天记录：./chat.json
#Chat log: ./chat.json
###################################################################      
''')

import socket
import threading
import json
import os
import base64
from datetime import datetime
import logging

logging.basicConfig(filename='server.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if os.path.exists("chat.json"):
    try:
        with open("chat.json", "r") as file:
            MESSAGE_LOG = json.load(file)
    except Exception:
        MESSAGE_LOG = []
else:
    MESSAGE_LOG = []

clients = []

def read_message(sock):
    buffer = bytearray()
    while True:
        chunk = sock.recv(1024)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(chunk) < 1024:
            break
    return bytes(buffer)

def handle_client(client_socket):
    while True:
        try:
            raw_message = read_message(client_socket)
            if not raw_message:
                break
            decoded = base64.b64decode(raw_message).decode('utf-8')
            data = json.loads(decoded)
            data["ip"] = client_socket.getpeername()[0]
            if "time" not in data:
                data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            processed_message = json.dumps(data)
            broadcast(processed_message, client_socket, data)
        except Exception as e:
            logging.error(f"Client disconnected: {e}")
            break
    if client_socket in clients:
        clients.remove(client_socket)
    client_socket.close()

def save_message_to_file(username, message, ip, time):
    global MESSAGE_LOG
    MESSAGE_LOG.append({"username": username, "message": message, "ip": ip, "time": time})
    with open("chat.json", "w") as file:
        json.dump(MESSAGE_LOG, file, ensure_ascii=False, indent=4)

def broadcast(message, client_socket, data):
    for client in clients:
        if client != client_socket:
            send_to_client(message, client)
    save_message_to_file(data["username"], data["message"], data["ip"], data["time"])

def send_to_client(message, client_socket):
    try:
        encrypted = base64.b64encode(message.encode('utf-8'))
        client_socket.sendall(encrypted)
    except Exception as e:
        logging.error(f"Error sending message to client: {e}")
        if client_socket in clients:
            clients.remove(client_socket)
        client_socket.close()

def send_chat_history(client_socket):
    try:
        history_payload = {"type": "history", "data": MESSAGE_LOG}
        json_payload = json.dumps(history_payload)
        encrypted = base64.b64encode(json_payload.encode('utf-8'))
        client_socket.sendall(encrypted)
    except Exception as e:
        logging.error(f"Error sending history: {e}")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 12345))
    server.listen(5)
    server.settimeout(1)
    logging.info("Server started on port 12345")

    shutdown_flag = False

    def input_listener():
        nonlocal shutdown_flag
        while True:
            if input().strip().lower() == "stop":
                shutdown_flag = True
                break

    threading.Thread(target=input_listener, daemon=True).start()

    try:
        while not shutdown_flag:
            try:
                client_socket, addr = server.accept()
                logging.info(f"Connection from {addr} established")
                clients.append(client_socket)
                send_chat_history(client_socket)
                threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()
            except socket.timeout:
                pass
            except socket.error as e:
                logging.error(f"Socket error: {e}")
    except Exception as e:
        logging.error(f"Error in server loop: {e}")
    finally:
        for client in clients:
            try:
                client.close()
            except Exception:
                pass
        server.close()
        logging.info("Server shut down gracefully")

if __name__ == "__main__":
    start_server()