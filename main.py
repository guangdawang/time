import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

DB_NAME = "tasks.db"
DEFAULT_FONT = ("Noto Sans CJK SC", 10)
TODAY = date.today().isoformat()  # 格式 YYYY-MM-DD

# ---------- 数据库初始化 ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 原有任务表
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
    # 新增：每日重点表
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_focus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            focus_date TEXT NOT NULL,
            sort_order INTEGER NOT NULL CHECK(sort_order BETWEEN 1 AND 3),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            UNIQUE(focus_date, task_id),
            UNIQUE(focus_date, sort_order)
        )
    ''')
    # 清理旧日期的重点记录（非必须，但保持库整洁）
    c.execute("DELETE FROM daily_focus WHERE focus_date < ?", (TODAY,))
    conn.commit()
    conn.close()

# ---------- 数据库操作 ----------
def fetch_tasks(status_filter="all"):
    """
    查询任务，同时返回今日重点信息（sort_order，若没有则为 NULL）
    排序规则：今日重点置顶（按 sort_order），其余按 id 降序
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    base_query = """
        SELECT t.id, t.title, t.tag, t.status, df.sort_order
        FROM tasks t
        LEFT JOIN daily_focus df ON t.id = df.task_id AND df.focus_date = ?
    """
    params = [TODAY]
    if status_filter == "pending":
        base_query += " WHERE t.status='pending'"
    elif status_filter == "done":
        base_query += " WHERE t.status='done'"

    # 排序：今日重点优先（sort_order 小的在前），其余按 id DESC
    base_query += " ORDER BY CASE WHEN df.sort_order IS NULL THEN 1 ELSE 0 END, df.sort_order ASC, t.id DESC"
    c.execute(base_query, params)
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

# ---------- 每日重点操作 ----------
def get_today_focus_count():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM daily_focus WHERE focus_date = ?", (TODAY,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_today_focus_tasks():
    """返回今日重点列表（task_id, sort_order）"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT task_id, sort_order FROM daily_focus WHERE focus_date = ? ORDER BY sort_order", (TODAY,))
    tasks = c.fetchall()
    conn.close()
    return tasks

def add_focus(task_id, sort_order):
    """将任务设为今日重点，如果序号已被占用则报错"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO daily_focus (task_id, focus_date, sort_order) VALUES (?, ?, ?)",
                  (task_id, TODAY, sort_order))
        conn.commit()
        success = True
        msg = ""
    except sqlite3.IntegrityError as e:
        conn.rollback()
        success = False
        # 分析具体约束冲突
        if "UNIQUE constraint failed: daily_focus.focus_date, daily_focus.sort_order" in str(e):
            msg = f"优先级 {sort_order} 已被占用，请先调整顺序或选择其他优先级。"
        elif "UNIQUE constraint failed: daily_focus.focus_date, daily_focus.task_id" in str(e):
            msg = "该任务已经是今日重点。"
        else:
            msg = "操作失败，请重试。"
    finally:
        conn.close()
    return success, msg

def remove_focus(task_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM daily_focus WHERE focus_date = ? AND task_id = ?", (TODAY, task_id))
    conn.commit()
    conn.close()

def is_task_focus(task_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT sort_order FROM daily_focus WHERE focus_date = ? AND task_id = ?", (TODAY, task_id))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None  # 返回序号或 None

# ---------- 标签选择/输入组件（不变） ----------
class TagInputWidget(tk.Frame):
    def __init__(self, parent, initial_tags=None, **kw):
        super().__init__(parent, **kw)
        self.selected_tags = []
        self.sugg_frame = tk.Frame(self)
        self.sugg_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(self.sugg_frame, text="可选标签：", font=DEFAULT_FONT).pack(side=tk.LEFT)
        self.sugg_inner = tk.Frame(self.sugg_frame)
        self.sugg_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_frame = tk.Frame(self)
        self.input_frame.pack(fill=tk.X, pady=(0, 5))
        self.entry = tk.Entry(self.input_frame, font=DEFAULT_FONT)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self.add_tag_from_entry)
        tk.Button(self.input_frame, text="添加", command=self.add_tag_from_entry,
                  bg="#4CAF50", fg="white", font=DEFAULT_FONT).pack(side=tk.LEFT, padx=5)
        self.tags_display = tk.Frame(self)
        self.tags_display.pack(fill=tk.X)
        self.refresh_suggestions()
        if initial_tags:
            for t in initial_tags:
                if t.strip():
                    self.selected_tags.append(t.strip())
            self.refresh_display()

    def refresh_suggestions(self):
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
        return ",".join(self.selected_tags)

# ---------- 主应用 ----------
class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("个人任务管理 - 今日重点")
        self.root.geometry("860x520")
        self.root.option_add("*Font", DEFAULT_FONT)

        self.filter_var = tk.StringVar(value="all")
        self.create_widgets()
        self.refresh_list()

        # 启动时检查今日重点，为空则弹出提醒
        if get_today_focus_count() == 0:
            self.root.after(500, self.show_focus_reminder)

    def show_focus_reminder(self):
        """每日首次启动时提醒设置今日重点"""
        # 仅当今天还没设置过任何重点时弹出
        if get_today_focus_count() > 0:
            return
        reminder = tk.Toplevel(self.root)
        reminder.title("今日重点")
        reminder.geometry("360x150")
        reminder.transient(self.root)
        reminder.grab_set()
        tk.Label(reminder, text="今天需要完成的最重要的三件事是什么？\n请从任务列表中右键选择“设为今日重点”。",
                 font=DEFAULT_FONT, justify=tk.LEFT).pack(padx=20, pady=15)
        tk.Button(reminder, text="知道了", command=reminder.destroy,
                  bg="#4CAF50", fg="white", font=DEFAULT_FONT).pack(pady=5)

    def create_widgets(self):
        # 筛选栏
        filter_frame = tk.Frame(self.root)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(filter_frame, text="筛选：", font=DEFAULT_FONT).pack(side=tk.LEFT)
        # 增加了“今日重点”选项
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                    values=["all", "pending", "done", "focus"], state="readonly", width=8)
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())

        # 按钮栏
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
        # 新增：直接标记为重点的按钮（快速选择优先级）
        tk.Button(btn_frame, text="设为今日重点", command=self.set_focus_priority, bg="#9C27B0", fg="white",
                  font=DEFAULT_FONT).pack(side=tk.LEFT, padx=2)

        # 任务列表
        columns = ("id", "focus", "title", "tag", "status")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("focus", text="今日重点")   # 新列
        self.tree.heading("title", text="任务标题")
        self.tree.heading("tag", text="标签")
        self.tree.heading("status", text="状态")

        self.tree.column("id", width=40)
        self.tree.column("focus", width=70, anchor="center")
        self.tree.column("title", width=250)
        self.tree.column("tag", width=150)
        self.tree.column("status", width=80)

        self.tree.tag_configure("done", foreground="gray", font=("Noto Sans CJK SC", 10, "overstrike"))
        self.tree.tag_configure("focus", background="#FFF9C4")  # 浅黄色背景，突出重点

        scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=5)

        # 右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="设为今日重点 (1)", command=lambda: self.set_focus_priority(1))
        self.context_menu.add_command(label="设为今日重点 (2)", command=lambda: self.set_focus_priority(2))
        self.context_menu.add_command(label="设为今日重点 (3)", command=lambda: self.set_focus_priority(3))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="取消今日重点", command=self.remove_focus_from_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="编辑任务", command=self.open_edit_dialog)
        self.context_menu.add_command(label="删除任务", command=self.delete_selected)
        self.context_menu.add_command(label="切换完成状态", command=self.toggle_selected)

        self.tree.bind("<Button-2>", self.show_context_menu)   # 右键（Linux/Windows）
        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """弹出右键菜单，根据任务是否为重点调整菜单状态"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            # 判断当前任务是否为重点
            task_id = self.tree.item(item)["values"][0]
            focus_order = is_task_focus(task_id)
            if focus_order is not None:
                # 已设为重点，禁用“设为...”命令，启用“取消”
                self.context_menu.entryconfigure(0, state="disabled")
                self.context_menu.entryconfigure(1, state="disabled")
                self.context_menu.entryconfigure(2, state="disabled")
                self.context_menu.entryconfigure(3, state="normal")   # 取消
            else:
                # 未设为重点
                self.context_menu.entryconfigure(0, state="normal")
                self.context_menu.entryconfigure(1, state="normal")
                self.context_menu.entryconfigure(2, state="normal")
                self.context_menu.entryconfigure(3, state="disabled")
            self.context_menu.post(event.x_root, event.y_root)

    def refresh_list(self):
        # 清空现有行
        for item in self.tree.get_children():
            self.tree.delete(item)

        filter_val = self.filter_var.get()
        if filter_val == "focus":
            # 仅显示今日重点
            tasks = fetch_tasks("all")  # 取全部再过滤，因为数据库查询可能复杂，这样简单
            tasks = [t for t in tasks if t[4] is not None]
        else:
            filter_map = {"all": "all", "pending": "pending", "done": "done"}
            tasks = fetch_tasks(filter_map.get(filter_val, "all"))

        for task in tasks:
            task_id, title, tag, status, focus_order = task
            focus_display = f"★{focus_order}" if focus_order else "—"
            display_status = "已完成" if status == "done" else "待完成"

            item_id = self.tree.insert("", tk.END, values=(task_id, focus_display, title, tag, display_status))
            # 已完成样式
            if status == "done":
                self.tree.item(item_id, tags=("done",))
            # 重点背景色
            if focus_order is not None:
                self.tree.item(item_id, tags=("focus",))

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

    # ---------- 今日重点操作方法 ----------
    def set_focus_priority(self, order=None):
        """通过按钮或菜单设置重点优先级；order 为 None 时弹出对话框选择"""
        task = self.get_selected_task()
        if not task:
            return
        task_id = task[0]
        # 如果已为重点，提示先取消
        if is_task_focus(task_id) is not None:
            messagebox.showinfo("提示", "该任务已经是今日重点，请先取消再重新设置。")
            return

        # 检查今日是否已满 3 个
        count = get_today_focus_count()
        if count >= 3:
            messagebox.showwarning("限制", "今日重点最多 3 个，请先取消一个再添加。")
            return

        # 如果 order 未指定，弹出简单输入框
        if order is None:
            dialog = tk.Toplevel(self.root)
            dialog.title("选择优先级")
            dialog.geometry("250x120")
            dialog.transient(self.root)
            dialog.grab_set()
            tk.Label(dialog, text="选择优先级（1 = 最重要）", font=DEFAULT_FONT).pack(pady=5)
            var = tk.IntVar(value=1)
            for i in range(1, 4):
                tk.Radiobutton(dialog, text=f"优先级 {i}", variable=var, value=i,
                               font=DEFAULT_FONT).pack(anchor=tk.W, padx=20)
            def confirm():
                self._do_add_focus(task_id, var.get())
                dialog.destroy()
            tk.Button(dialog, text="确定", command=confirm, bg="#4CAF50", fg="white",
                      font=DEFAULT_FONT).pack(pady=5)
        else:
            self._do_add_focus(task_id, order)

    def _do_add_focus(self, task_id, order):
        success, msg = add_focus(task_id, order)
        if success:
            self.refresh_list()
        else:
            messagebox.showerror("操作失败", msg)

    def remove_focus_from_selected(self):
        task = self.get_selected_task()
        if not task:
            return
        task_id = task[0]
        if is_task_focus(task_id) is None:
            messagebox.showinfo("提示", "该任务不是今日重点。")
            return
        remove_focus(task_id)
        self.refresh_list()

    # ---------- 原有对话框 ----------
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