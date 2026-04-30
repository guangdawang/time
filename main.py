""" 应用程序启动入口 """

import tkinter as tk
from database import init_db
from app import TaskManagerApp

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()