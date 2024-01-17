import socket
import time
from threading import Thread
import tkinter as tk
import json
import re

from traceback import format_exc
import xml.etree.ElementTree as ET
from pathlib import Path
import os

class LoginWindow():

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("fs登录")
        self.root.resizable(False, False)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = 300
        height = 200
        x = int(screen_width / 2 - width / 2)
        y = int(screen_height / 2 - height / 2)
        size = '{}x{}+{}+{}'.format(width, height, x, y)
        self.root.geometry(size)
        self.label = tk.Label(self.root, text="HOST：")
        self.label2 = tk.Label(self.root, text="端口:")
        self.label3 = tk.Label(self.root, text="密码:")
        self.entry = tk.Entry(self.root)
        self.entry2 = tk.Entry(self.root)
        self.entry3 = tk.Entry(self.root, show="*")

        self.label.grid(row=0, column=0)
        self.entry.grid(row=0, column=1)
        self.label2.grid(row=1, column=0)
        self.entry2.grid(row=1, column=1)
        self.label3.grid(row=2, column=0)
        self.entry3.grid(row=2, column=1)

        self.entry.insert(0, "192.168.10.249")
        self.entry2.insert(0, "8021")
        self.entry3.insert(0, "fs8021")
        self.button = tk.Button(self.root, text="Login", command=self.login)

        self.button.grid(row=3, column=0, columnspan=2)

    def login(self):
        try:
            self.host = self.entry.get()
            self.port = int(self.entry2.get())
            self.password = self.entry3.get()
            self.root.destroy()
        except:
            pass


class Window:
    def __init__(self, host, port, password):
        print(os.path.join(Path(__file__).parent.as_posix() , "config.xml"))
        tree = ET.parse(os.path.join(Path(__file__).parent.as_posix() , "config.xml"))
        self.config_root = tree.getroot()
        self.root = tk.Tk()
        self.root.title("fs")
        self.menubar = tk.Menu(self.root)
        self.view_menu = tk.Menu(self.menubar, tearoff=0)
        self.show_all = tk.BooleanVar()
        self.varAbleLs = []
        showLs = [i.text for i in self.config_root.find("showLs").findall("text")]
        self.show_ls = showLs.copy()
        self.show_all.set(True)
        self.showText = showLs.copy()

        # CODEC API BACKGROUND_JOB CHANNEL_STATE CHANNEL_EXECUTE_COMPLETE CHANNEL_EXECUTE CHANNEL_HANGUP HEARTBEAT RE_SCHEDULE
        self.view_menu.add_checkbutton(label="Show All", onvalue=1, offvalue=0, variable=self.show_all,
                                       command=self.disable_all_varable)
        for ll in range(len(self.showText)):
            vv = tk.BooleanVar()
            self.varAbleLs.append(vv)
            self.view_menu.add_checkbutton(label=self.showText[ll], onvalue=1, offvalue=0, variable=vv,
                                           command=self.show_in_screen)
        self.menubar.add_cascade(label="过滤", menu=self.view_menu)
        self.check_thread = Thread(target=self.checkVarAble)
        self.check_thread.daemon = True
        self.check_thread.start()
        self.root.config(menu=self.menubar)
        self.root.resizable(False, False)
        self.text = tk.Text(self.root, bg="black", fg="green")
        self.text.pack(fill="both")
        self.entry = tk.Entry(self.root)
        self.entry.pack(fill="both")
        self.entry.bind("<Return>", self.run_cmd)
        self.fsClient = FsClient(password="fs8021", host=host, port=port, window=self)

        self.cmd_dict = {
            "clear": self.clear_history
        }

    def show_in_screen(self):
        # API BACKGROUND_JOB CHANNEL_STATE CHANNEL_EXECUTE_COMPLETE CHANNEL_EXECUTE CHANNEL_HANGUP HEARTBEAT RE_SCHEDULE
        self.show_ls = []
        index = 0
        for var in self.varAbleLs:
            if var.get():
                self.show_ls.append(self.showText[index])
            index += 1
        self.reFlash()
        for msg in filter(lambda item: item['Event-Name'] in self.show_ls, self.fsClient.msg_ls):
            self.text.insert("end", f"filter:{msg}\n\n")
        self.text.see("end")

    def disable_all_varable(self):
        for var in self.varAbleLs:
            var.set(False)
        self.show_ls = ['CODEC', 'API', 'BACKGROUND_JOB', 'CHANNEL_STATE', 'CHANNEL_EXECUTE_COMPLETE',
                        'CHANNEL_EXECUTE', 'CHANNEL_HANGUP', 'HEARTBEAT', 'RE_SCHEDULE']
        self.reFlash()
        if self.show_all.get():
            for msg in self.fsClient.msg_ls:
                self.text.insert("end", f"{msg}\n\n")
            self.text.see("end")

    def checkVarAble(self):
        while True:
            for var in self.varAbleLs:
                if var.get():
                    self.show_all.set(False)
            time.sleep(0.1)

    def run_cmd(self, event):
        def _t():
            # 获取输入的命令
            cmd = self.entry.get()
            # 清空输入框
            self.entry.delete(0, "end")
            # 在文本框中显示命令
            self.text.insert("end", f"> {cmd}\n")
            # 执行命令，并获取返回的结果
            # result = os.popen(cmd).read()
            if cmd not in self.cmd_dict:
                self.fsClient.sendCmd(cmd)
            else:
                self.cmd_dict[cmd]()
            # 在文本框中显示结果
            self.text.see("end")

        Thread(target=_t).start()

    def reFlash(self):
        self.text.delete(1.0, "end")
        self.text.see("end")

    def clear_history(self):
        self.fsClient.clear_history()
        self.reFlash()


class FsClient:

    def __init__(self, window, host="192.168.10.249", port=8021, password=""):
        self.window = window
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        self.msg_ls = []

        recv_thread = Thread(target=self.recv)
        recv_thread.daemon = True
        recv_thread.start()

        heartbeat_thread = Thread(target=self.heartbeat)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        # send authentication
        self.sendCmd(f'auth {password}\r\n\r\n')
        self.sendCmd('event json ALL\r\n\r\n')

    def sendCmd(self, cmd: str):
        # send command
        self.sock.send(cmd.encode())
        print("客户端执行:", cmd)
        # todo 获取执行这条命令返回的结果

    def clear_history(self):
        self.msg_ls = []

    def heartbeat(self):
        while True:
            self.sock.send(b'heartbeat\r\n\r\n')
            time.sleep(1.0)

    def recv(self):
        while True:
            msg = self.sock.recv(10240).decode()

            if "ERR command not found" not in msg:
                print("服务端返回:", msg)
                # 添加事件列表
                parts = re.split(r'Content-Length: \d+', msg)
                # create an empty list to store the json objects
                # loop through the parts
                for part in parts:
                    # strip the whitespace and the Content-Type line
                    part = part.strip()
                    part = re.sub(r'Content-Type: .+\n', '', part)
                    # if the part is not empty, parse it as json and append it to the list
                    if part:
                        part = part.strip()
                        try:
                            json_object = json.loads(part)
                            self.msg_ls.append(json_object)
                            print("增加事件:", json_object)
                            if json_object['Event-Name'] in self.window.show_ls:
                                self.window.text.insert("end", msg + "\n")
                                self.window.text.see("end")
                        except json.decoder.JSONDecodeError:
                            pass


loginWindow = LoginWindow()
loginWindow.root.mainloop()
window = Window(loginWindow.host, loginWindow.port, loginWindow.password)
window.root.mainloop()
