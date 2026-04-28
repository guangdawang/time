import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

DB_NAME = "tasks.db"
DEFAULT_FONT = ("Noto Sans CJK SC", 10)

# ---------- 数据库初始化 ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            tag TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# ---------- 数据库操作 ----------
def fetch_tasks(status_filter="all"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if status_filter == "pending":
        c.execute("SELECT id, title, tag, status FROM tasks WHERE status='pending' ORDER BY id DESC")
    elif status_filter == "done":
        c.execute("SELECT id, title, tag, status FROM tasks WHERE status='done' ORDER BY id DESC")
    else:
        c.execute("SELECT id, title, tag, status FROM tasks ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def add_task(title, tag):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (title, tag) VALUES (?, ?)", (title, tag))
    conn.commit()
    conn.close()

def update_task(task_id, title, tag):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE tasks SET title=?, tag=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (title, tag, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def toggle_status(task_id, current_status):
    new_status = "done" if current_status == "pending" else "pending"
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE tasks SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (new_status, task_id))
    conn.commit()
    conn.close()

def get_all_tags():
    """从所有任务中提取不重复的标签列表"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT tag FROM tasks WHERE tag != ''")
    rows = c.fetchall()
    conn.close()
    tags_set = set()
    for (tag_str,) in rows:
        for t in tag_str.split(","):
            t = t.strip()
            if t:
                tags_set.add(t)
    return sorted(tags_set, key=str.lower)

# ---------- 标签选择/输入组件 ----------
class TagInputWidget(tk.Frame):
    """输入标签的控件：建议标签 + 输入框 + 已选标签条"""
    def __init__(self, parent, initial_tags=None, **kw):
        super().__init__(parent, **kw)
        self.selected_tags = []  # 当前已选标签列表

        # ---- 标签建议区域 ----
        self.sugg_frame = tk.Frame(self)
        self.sugg_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(self.sugg_frame, text="可选标签：", font=DEFAULT_FONT).pack(side=tk.LEFT)
        self.sugg_inner = tk.Frame(self.sugg_frame)
        self.sugg_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ---- 输入框 ----
        self.input_frame = tk.Frame(self)
        self.input_frame.pack(fill=tk.X, pady=(0, 5))
        self.entry = tk.Entry(self.input_frame, font=DEFAULT_FONT)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self.add_tag_from_entry)
        tk.Button(self.input_frame, text="添加", command=self.add_tag_from_entry,
                  bg="#4CAF50", fg="white", font=DEFAULT_FONT).pack(side=tk.LEFT, padx=5)

        # ---- 已选标签展示区 ----
        self.tags_display = tk.Frame(self)
        self.tags_display.pack(fill=tk.X)

        # 刷新建议标签
        self.refresh_suggestions()

        # 如果传入了初始标签，预加载
        if initial_tags:
            for t in initial_tags:
                if t.strip():
                    self.selected_tags.append(t.strip())
            self.refresh_display()

    def refresh_suggestions(self):
        """从数据库重新加载可选标签，并渲染为按钮"""
        for widget in self.sugg_inner.winfo_children():
            widget.destroy()

        all_tags = get_all_tags()
        for tag in all_tags:
            if tag not in self.selected_tags:
                btn = tk.Button(self.sugg_inner, text=tag, font=DEFAULT_FONT,
                                command=lambda t=tag: self.add_tag(t),
                                relief="groove", padx=4, pady=0)
                btn.pack(side=tk.LEFT, padx=2, pady=2)

    def add_tag_from_entry(self, event=None):
        tag = self.entry.get().strip()
        if tag and tag not in self.selected_tags:
            self.selected_tags.append(tag)
            self.entry.delete(0, tk.END)
            self.refresh_display()
            self.refresh_suggestions()
        elif tag in self.selected_tags:
            messagebox.showinfo("提示", f"标签「{tag}」已存在")
            self.entry.delete(0, tk.END)

    def add_tag(self, tag):
        """从建议按钮添加标签"""
        if tag not in self.selected_tags:
            self.selected_tags.append(tag)
            self.refresh_display()
            self.refresh_suggestions()

    def remove_tag(self, tag):
        self.selected_tags.remove(tag)
        self.refresh_display()
        self.refresh_suggestions()

    def refresh_display(self):
        for widget in self.tags_display.winfo_children():
            widget.destroy()
        for tag in self.selected_tags:
            frame = tk.Frame(self.tags_display, bg="#e0e0e0")
            frame.pack(side=tk.LEFT, padx=2, pady=2)
            tk.Label(frame, text=tag, font=DEFAULT_FONT, bg="#e0e0e0").pack(side=tk.LEFT, padx=4)
            btn_del = tk.Button(frame, text="×", font=DEFAULT_FONT, relief="flat",
                                bg="#e0e0e0", command=lambda t=tag: self.remove_tag(t))
            btn_del.pack(side=tk.LEFT)

    def get_tags_string(self):
        """返回逗号分隔的标签字符串，用于存储"""
        return ",".join(self.selected_tags)

# ---------- 主应用 ----------
class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("个人任务管理")
        self.root.geometry("780x480")
        self.root.option_add("*Font", DEFAULT_FONT)

        self.filter_var = tk.StringVar(value="all")
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self):
        # 筛选栏
        filter_frame = tk.Frame(self.root)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(filter_frame, text="筛选：", font=DEFAULT_FONT).pack(side=tk.LEFT)
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                    values=["all", "pending", "done"], state="readonly", width=8)
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())

        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(btn_frame, text="新建任务", command=self.open_add_dialog, bg="#4CAF50", fg="white",
                  font=DEFAULT_FONT).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="编辑任务", command=self.open_edit_dialog, bg="#2196F3", fg="white",
                  font=DEFAULT_FONT).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="删除任务", command=self.delete_selected, bg="#f44336", fg="white",
                  font=DEFAULT_FONT).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="切换完成状态", command=self.toggle_selected, bg="#FF9800", fg="white",
                  font=DEFAULT_FONT).pack(side=tk.LEFT, padx=2)

        # 任务列表
        columns = ("id", "title", "tag", "status")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="任务标题")
        self.tree.heading("tag", text="标签")
        self.tree.heading("status", text="状态")

        self.tree.column("id", width=40)
        self.tree.column("title", width=250)
        self.tree.column("tag", width=150)
        self.tree.column("status", width=80)

        self.tree.tag_configure("done", foreground="gray", font=("Noto Sans CJK SC", 10, "overstrike"))

        scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=5)

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        filter_val = self.filter_var.get()
        tasks = fetch_tasks(filter_val if filter_val != "all" else "all")

        for task in tasks:
            task_id, title, tag, status = task
            display_status = "已完成" if status == "done" else "待完成"
            item_id = self.tree.insert("", tk.END, values=(task_id, title, tag, display_status))
            if status == "done":
                self.tree.item(item_id, tags=("done",))

    def get_selected_task(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个任务")
            return None
        item = self.tree.item(selection[0])
        task_id = item["values"][0]
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, title, tag, status FROM tasks WHERE id=?", (task_id,))
        task = c.fetchone()
        conn.close()
        return task

    def open_add_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("新建任务")
        dialog.geometry("500x280")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="任务标题：", font=DEFAULT_FONT).grid(row=0, column=0, padx=10, pady=10, sticky="ne")
        title_entry = tk.Entry(dialog, width=40, font=DEFAULT_FONT)
        title_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        tk.Label(dialog, text="标签：", font=DEFAULT_FONT).grid(row=1, column=0, padx=10, pady=10, sticky="ne")
        tag_widget = TagInputWidget(dialog)
        tag_widget.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        def save():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("提示", "任务标题不能为空")
                return
            tags = tag_widget.get_tags_string()
            add_task(title, tags)
            self.refresh_list()
            dialog.destroy()

        tk.Button(dialog, text="保存", command=save, bg="#4CAF50", fg="white",
                  font=DEFAULT_FONT).grid(row=2, column=0, columnspan=2, pady=10)

    def open_edit_dialog(self):
        task = self.get_selected_task()
        if not task:
            return

        task_id, title, tag_str, status = task
        initial_tags = [t.strip() for t in tag_str.split(",") if t.strip()]

        dialog = tk.Toplevel(self.root)
        dialog.title("编辑任务")
        dialog.geometry("500x280")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="任务标题：", font=DEFAULT_FONT).grid(row=0, column=0, padx=10, pady=10, sticky="ne")
        title_entry = tk.Entry(dialog, width=40, font=DEFAULT_FONT)
        title_entry.insert(0, title)
        title_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        tk.Label(dialog, text="标签：", font=DEFAULT_FONT).grid(row=1, column=0, padx=10, pady=10, sticky="ne")
        tag_widget = TagInputWidget(dialog, initial_tags=initial_tags)
        tag_widget.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        def save():
            new_title = title_entry.get().strip()
            if not new_title:
                messagebox.showwarning("提示", "任务标题不能为空")
                return
            new_tags = tag_widget.get_tags_string()
            update_task(task_id, new_title, new_tags)
            self.refresh_list()
            dialog.destroy()

        tk.Button(dialog, text="保存", command=save, bg="#2196F3", fg="white",
                  font=DEFAULT_FONT).grid(row=2, column=0, columnspan=2, pady=10)

    def delete_selected(self):
        task = self.get_selected_task()
        if not task:
            return
        if messagebox.askyesno("确认删除", f"确定要删除任务「{task[1]}」吗？"):
            delete_task(task[0])
            self.refresh_list()

    def toggle_selected(self):
        task = self.get_selected_task()
        if not task:
            return
        toggle_status(task[0], task[3])
        self.refresh_list()


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()
