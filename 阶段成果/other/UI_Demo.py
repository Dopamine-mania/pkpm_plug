import tkinter as tk
from tkinter import ttk, messagebox

def run_demo():
    messagebox.showinfo("运行提示", "正在连接 PKPM-CAE 接口...\n正在读取 Excel 参数...\n即将开始生成叠合梁模型。")

root = tk.Tk()
root.title("叠合梁大开洞自动化建模插件 V1.0 - 专业版")
root.geometry("600x550")

# 设置风格
style = ttk.Style()
style.configure("TLabel", font=("微软雅黑", 10))
style.configure("TButton", font=("微软雅黑", 10, "bold"))

# --- 1. 基础几何参数 ---
frame_geo = ttk.LabelFrame(root, text=" 1. 基础几何参数 ", padding=10)
frame_geo.pack(fill="x", padx=10, pady=5)

labels_geo = ["梁总长 (mm):", "梁高度 (mm):", "梁宽度 (mm):", "预制层厚度 (mm):"]
default_values = ["8100", "1100", "500", "400"]

for i, label in enumerate(labels_geo):
    lbl = ttk.Label(frame_geo, text=label)
    lbl.grid(row=i//2, column=(i%2)*2, sticky="e", pady=2)
    ent = ttk.Entry(frame_geo, width=15)
    ent.insert(0, default_values[i])
    ent.grid(row=i//2, column=(i%2)*2 + 1, padx=5, pady=2)

# --- 2. 洞口参数管理 ---
frame_hole = ttk.LabelFrame(root, text=" 2. 洞口参数管理 (支持多洞口) ", padding=10)
frame_hole.pack(fill="x", padx=10, pady=5)

tree = ttk.Treeview(frame_hole, columns=("pos", "width", "height"), show="headings", height=3)
tree.heading("pos", text="距离起点位置(mm)")
tree.heading("width", text="洞口宽度(mm)")
tree.heading("height", text="洞口高度(mm)")
tree.column("pos", width=150, anchor="center")
tree.column("width", width=150, anchor="center")
tree.column("height", width=150, anchor="center")
tree.pack(side="left")

tree.insert("", "end", values=("2550", "2500", "400"))
tree.insert("", "end", values=("6000", "500", "400"))

btn_frame = ttk.Frame(frame_hole)
btn_frame.pack(side="right", padx=5)
ttk.Button(btn_frame, text="添加洞口", width=10).pack(pady=2)
ttk.Button(btn_frame, text="删除选中", width=10).pack(pady=2)

# --- 3. 配筋与荷载设置 ---
frame_rebar = ttk.LabelFrame(root, text=" 3. 配筋与两阶段计算步设置 ", padding=10)
frame_rebar.pack(fill="x", padx=10, pady=5)

ttk.Label(frame_rebar, text="纵筋直径:").grid(row=0, column=0)
ttk.Entry(frame_rebar, width=8).grid(row=0, column=1, padx=5)
ttk.Label(frame_rebar, text="加强筋直径:").grid(row=0, column=2)
ttk.Entry(frame_rebar, width=8).grid(row=0, column=3, padx=5)

cb_analysis = ttk.Checkbutton(frame_rebar, text="开启两阶段内力遗传计算步")
cb_analysis.invoke()
cb_analysis.grid(row=1, column=0, columnspan=2, pady=5, sticky="w")

# --- 4. 底部执行区 ---
btn_run = ttk.Button(root, text="▶ 一键生成 PKPM-CAE 模型", command=run_demo)
btn_run.pack(pady=15, fill="x", padx=20)

log_text = tk.Text(root, height=5, bg="#f0f0f0", font=("Consolas", 9))
log_text.pack(fill="x", padx=10, pady=5)
log_text.insert("1.0", "[系统日志] 等待用户输入参数...\n[系统日志] 核心建模引擎已准备就绪。")

root.mainloop()