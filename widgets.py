""" 可复用的界面组件 """

import tkinter as tk
from tkinter import messagebox
from config import DEFAULT_FONT
from database import get_all_tags


class TagInputWidget(tk.Frame):
    """标签选择/输入组件"""

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