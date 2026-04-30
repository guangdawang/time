""" 主应用窗口与业务逻辑 """

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from config import DEFAULT_FONT
from database import (
    DB_NAME,
    fetch_tasks,
    add_task,
    update_task,
    delete_task,
    toggle_status,
    get_today_focus_count,
    add_focus,
    remove_focus,
    is_task_focus,
)
from widgets import TagInputWidget


class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("个人任务管理 - 今日重点")
        self.root.geometry("860x520")
        self.root.option_add("*Font", DEFAULT_FONT)

        self.filter_var = tk.StringVar(value="all")
        self.create_widgets()
        self.refresh_list()

        # 启动时若今日重点为空则弹出提醒
        if get_today_focus_count() == 0:
            self.root.after(500, self.show_focus_reminder)

    def show_focus_reminder(self):
        if get_today_focus_count() > 0:
            return
        reminder = tk.Toplevel(self.root)
        reminder.title("今日重点")
        reminder.geometry("360x150")
        reminder.transient(self.root)
        reminder.grab_set()
        tk.Label(reminder,
                 text="今天需要完成的最重要的三件事是什么？\n请从任务列表中右键选择“设为今日重点”。",
                 font=DEFAULT_FONT, justify=tk.LEFT).pack(padx=20, pady=15)
        tk.Button(reminder, text="知道了", command=reminder.destroy,
                  bg="#4CAF50", fg="white", font=DEFAULT_FONT).pack(pady=5)

    def create_widgets(self):
        style = ttk.Style()
        style.configure("Treeview", font=DEFAULT_FONT, rowheight=28)
        style.configure("Treeview.Heading", font=DEFAULT_FONT)

        # 筛选栏
        filter_frame = tk.Frame(self.root)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(filter_frame, text="筛选：", font=DEFAULT_FONT).pack(side=tk.LEFT)
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                    values=["all", "pending", "done", "focus"],
                                    state="readonly", width=8)
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())

        # 按钮栏
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(btn_frame, text="新建任务", command=self.open_add_dialog,
                  bg="#4CAF50", fg="white", font=DEFAULT_FONT).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="编辑任务", command=self.open_edit_dialog,
                  bg="#2196F3", fg="white", font=DEFAULT_FONT).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="删除任务", command=self.delete_selected,
                  bg="#f44336", fg="white", font=DEFAULT_FONT).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="切换完成状态", command=self.toggle_selected,
                  bg="#FF9800", fg="white", font=DEFAULT_FONT).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="设为今日重点", command=self.set_focus_priority,
                  bg="#9C27B0", fg="white", font=DEFAULT_FONT).pack(side=tk.LEFT, padx=2)

        # 任务列表
        columns = ("id", "focus", "title", "tag", "status")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("focus", text="今日重点")
        self.tree.heading("title", text="任务标题")
        self.tree.heading("tag", text="标签")
        self.tree.heading("status", text="状态")

        self.tree.column("id", width=40)
        self.tree.column("focus", width=70, anchor="center")
        self.tree.column("title", width=250)
        self.tree.column("tag", width=150)
        self.tree.column("status", width=80)

        self.tree.tag_configure("done", foreground="gray",
                                font=(DEFAULT_FONT, 10, "overstrike"))
        self.tree.tag_configure("focus", background="#FFF9C4")

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

        self.tree.bind("<Button-2>", self.show_context_menu)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            task_id = self.tree.item(item)["values"][0]
            focus_order = is_task_focus(task_id)
            if focus_order is not None:
                self.context_menu.entryconfigure(0, state="disabled")
                self.context_menu.entryconfigure(1, state="disabled")
                self.context_menu.entryconfigure(2, state="disabled")
                self.context_menu.entryconfigure(3, state="normal")
            else:
                self.context_menu.entryconfigure(0, state="normal")
                self.context_menu.entryconfigure(1, state="normal")
                self.context_menu.entryconfigure(2, state="normal")
                self.context_menu.entryconfigure(3, state="disabled")
            self.context_menu.post(event.x_root, event.y_root)

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        filter_val = self.filter_var.get()
        if filter_val == "focus":
            tasks = fetch_tasks("all")
            tasks = [t for t in tasks if t[4] is not None]
        else:
            filter_map = {"all": "all", "pending": "pending", "done": "done"}
            tasks = fetch_tasks(filter_map.get(filter_val, "all"))

        for task in tasks:
            task_id, title, tag, status, focus_order = task
            focus_display = f"★{focus_order}" if focus_order else "—"
            display_status = "已完成" if status == "done" else "待完成"
            item_id = self.tree.insert("", tk.END,
                                       values=(task_id, focus_display, title, tag, display_status))
            if status == "done":
                self.tree.item(item_id, tags=("done",))
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

    # ---------- 今日重点操作 ----------
    def set_focus_priority(self, order=None):
        task = self.get_selected_task()
        if not task:
            return
        task_id = task[0]
        if is_task_focus(task_id) is not None:
            messagebox.showinfo("提示", "该任务已经是今日重点，请先取消再重新设置。")
            return
        if get_today_focus_count() >= 3:
            messagebox.showwarning("限制", "今日重点最多 3 个，请先取消一个再添加。")
            return
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

    # ---------- 对话框 ----------
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