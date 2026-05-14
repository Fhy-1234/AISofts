import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import pyaudio
import numpy as np
import threading
import time
import json
import os
import sys
import psutil
from PIL import Image, ImageTk
import winsound
import keyboard
from plyer import notification
import collections

def resource_path(relative_path):
    """获取打包后资源的绝对路径"""
    try:
        # 打包后的临时文件夹
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境下的当前目录
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_app_directory():
    """获取应用程序目录（打包后为EXE所在目录，开发时为当前目录）"""
    if getattr(sys, 'frozen', False):
        # 打包后的情况
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.abspath(".")

class HearingAssistant:
    def __init__(self):
        # 程序配置 - 使用应用程序目录
        app_dir = get_app_directory()
        self.config_file = os.path.join(app_dir, "config.json")
        self.default_config = {
            "password": "123456",
            "threshold": 60,  # 默认分贝阈值
            "max_count": 3,   # 最大提醒次数
            "auto_start": False,
            "target_processes": ["chrome.exe", "notepad.exe"],  # 要关闭的进程名列表
            "hotkey": "ctrl+alt+d",  # 显示/隐藏窗口的快捷键
            "alert_text": "环境声音过大，请注意文明游戏。",  # 警报窗口文字
            "notification_text": "因环境音量过大，已经关闭程序。",  # 退出通知文字
            "smoothing_window": 5,  # 平滑窗口大小
            "calibration_offset": 0,  # 校准偏移量
            "min_volume_threshold": 0.001,  # 最小音量阈值，避免除零错误
            "start_monitoring_on_launch": True  # 启动时是否开始监控
        }
        
        # 确保配置文件存在
        self.ensure_config_file()
        
        # 加载配置
        self.load_config()
        
        # 程序状态
        self.is_running = True
        self.is_monitoring = self.config.get("start_monitoring_on_launch", True)  # 根据配置决定初始状态
        self.alert_count = 0
        self.last_alert_time = 0
        self.window_visible = False  # 窗口可见状态
        self.current_db = 0  # 当前分贝值
        
        # 分贝值平滑处理
        self.db_history = collections.deque(maxlen=self.config.get("smoothing_window", 5))
        self.db_smoothed = 0
        
        # 音频设置 - 优化参数
        self.CHUNK = 1024  # 增加块大小以提高稳定性
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100  # 标准CD音质采样率
        self.audio = None
        self.stream = None
        self.audio_lock = threading.Lock()  # 音频资源锁
        
        # 音频设备检测
        self.available_devices = self.get_audio_devices()
        self.selected_device_index = None
        
        # 创建主窗口
        self.create_main_window()
        
        # 注册全局快捷键
        self.register_hotkey()
        
        # 启动声音监控线程
        self.monitor_thread = threading.Thread(target=self.sound_monitor, daemon=True)
        self.monitor_thread.start()
        
        print("听力精灵已启动...")
        print(f"使用快捷键 {self.config['hotkey']} 显示/隐藏窗口")
        print(f"当前分贝阈值: {self.config['threshold']} dB")
        print(f"监控状态: {'运行中' if self.is_monitoring else '已停止'}")
        print(f"配置文件位置: {self.config_file}")
        print("调试信息: 程序正在运行，可以使用以下方法终止:")
        print("1. 使用主窗口的退出按钮")
        print("2. 在控制台按 Ctrl+C")
        print("3. 使用任务管理器结束Python进程")
        
        # 启动主事件循环
        self.root.mainloop()

    def get_audio_devices(self):
        """获取可用的音频输入设备"""
        devices = []
        try:
            audio = pyaudio.PyAudio()
            for i in range(audio.get_device_count()):
                device_info = audio.get_device_info_by_index(i)
                if device_info.get('maxInputChannels', 0) > 0:
                    devices.append({
                        'index': i,
                        'name': device_info.get('name', f'Device {i}'),
                        'default_sample_rate': device_info.get('defaultSampleRate', 44100)
                    })
            audio.terminate()
        except Exception as e:
            print(f"获取音频设备失败: {e}")
        return devices

    def ensure_config_file(self):
        """确保配置文件存在"""
        # 使用绝对路径检查配置文件
        config_path = self.config_file
        if not os.path.exists(config_path):
            print(f"配置文件不存在，创建默认配置: {config_path}")
            # 确保目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            self.save_config(self.default_config)

    def load_config(self):
        """加载配置文件"""
        try:
            config_path = self.config_file
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并配置，确保新字段有默认值
                    self.config = {**self.default_config, **loaded_config}
                    
                    # 兼容旧版本配置：将单个进程名转换为进程列表
                    if "target_process" in self.config and "target_processes" not in self.config:
                        old_process = self.config["target_process"]
                        if old_process and old_process.strip():
                            self.config["target_processes"] = [p.strip() for p in old_process.split(",") if p.strip()]
                        else:
                            self.config["target_processes"] = []
                        # 删除旧的配置项
                        del self.config["target_process"]
                    
                    print("配置加载成功")
            else:
                self.config = self.default_config.copy()
                self.save_config(self.config)
                print("使用默认配置")
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.config = self.default_config.copy()
            self.save_config(self.config)

    def save_config(self, config=None):
        """保存配置文件"""
        try:
            if config is None:
                config = self.config
                
            config_path = self.config_file
            # 确保目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
                
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print("配置保存成功")
        except Exception as e:
            print(f"保存配置失败: {e}")

    def update_button_state(self):
        """更新按钮状态"""
        if self.is_monitoring:
            self.enable_button.config(state='disabled', bg='lightgreen')
            self.disable_button.config(state='normal', bg='lightgray')
            self.status_label.config(text="监控状态: 运行中", fg='green')
        else:
            self.enable_button.config(state='normal', bg='lightgray')
            self.disable_button.config(state='disabled', bg='lightcoral')
            self.status_label.config(text="监控状态: 已停止", fg='red')

    def enable_monitoring(self):
        """启用监控"""
        self.is_monitoring = True
        self.alert_count = 0
        self.update_button_state()
        if self.window_visible:
            messagebox.showinfo("提示", "功能已启用")

    def disable_monitoring(self):
        """关闭监控（需要密码）"""
        password = simpledialog.askstring("密码验证", "请输入密码:", show='*')
        if password == self.config["password"]:
            self.is_monitoring = False
            self.update_button_state()
            if self.window_visible:
                messagebox.showinfo("提示", "功能已关闭")
        else:
            if self.window_visible:
                messagebox.showerror("错误", "密码错误！")
            # 密码错误时不改变监控状态

    def show_settings(self):
        """显示设置窗口"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("设置")
        settings_window.geometry("550x700")  # 增加高度以容纳新设置
        settings_window.resizable(False, False)
        settings_window.transient(self.root)  # 设置为主窗口的子窗口
        settings_window.grab_set()  # 模态窗口
        
        # 创建一个框架用于滚动
        canvas = tk.Canvas(settings_window)
        scrollbar = ttk.Scrollbar(settings_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 使用网格布局排列设置项
        row = 0
        
        # 分贝阈值设置
        ttk.Label(scrollable_frame, text="分贝阈值:", font=('微软雅黑', 10)).grid(row=row, column=0, sticky='w', pady=10, padx=10)
        threshold_var = tk.StringVar(value=str(self.config["threshold"]))
        threshold_entry = ttk.Entry(scrollable_frame, textvariable=threshold_var, width=15)
        threshold_entry.grid(row=row, column=1, sticky='w', pady=10, padx=10)
        ttk.Label(scrollable_frame, text="(当环境声音超过此值时触发警报)", font=('Arial', 8)).grid(row=row, column=2, sticky='w', pady=10)
        row += 1
        
        # 最大提醒次数
        ttk.Label(scrollable_frame, text="最大提醒次数:", font=('微软雅黑', 10)).grid(row=row, column=0, sticky='w', pady=10, padx=10)
        count_var = tk.StringVar(value=str(self.config["max_count"]))
        count_entry = ttk.Entry(scrollable_frame, textvariable=count_var, width=15)
        count_entry.grid(row=row, column=1, sticky='w', pady=10, padx=10)
        ttk.Label(scrollable_frame, text="(超过此次数后将终止目标进程)", font=('Arial', 8)).grid(row=row, column=2, sticky='w', pady=10)
        row += 1
        
        # 平滑窗口大小
        ttk.Label(scrollable_frame, text="平滑窗口大小:", font=('微软雅黑', 10)).grid(row=row, column=0, sticky='w', pady=10, padx=10)
        smoothing_var = tk.StringVar(value=str(self.config.get("smoothing_window", 5)))
        smoothing_entry = ttk.Entry(scrollable_frame, textvariable=smoothing_var, width=15)
        smoothing_entry.grid(row=row, column=1, sticky='w', pady=10, padx=10)
        ttk.Label(scrollable_frame, text="(数值越大分贝显示越平滑)", font=('Arial', 8)).grid(row=row, column=2, sticky='w', pady=10)
        row += 1
        
        # 校准偏移
        ttk.Label(scrollable_frame, text="分贝校准偏移:", font=('微软雅黑', 10)).grid(row=row, column=0, sticky='w', pady=10, padx=10)
        calibration_var = tk.StringVar(value=str(self.config.get("calibration_offset", 0)))
        calibration_entry = ttk.Entry(scrollable_frame, textvariable=calibration_var, width=15)
        calibration_entry.grid(row=row, column=1, sticky='w', pady=10, padx=10)
        ttk.Label(scrollable_frame, text="(正数增加灵敏度，负数降低)", font=('Arial', 8)).grid(row=row, column=2, sticky='w', pady=10)
        row += 1
        
        # 启动时监控状态
        ttk.Label(scrollable_frame, text="启动时监控状态:", font=('微软雅黑', 10)).grid(row=row, column=0, sticky='w', pady=10, padx=10)
        start_monitoring_var = tk.BooleanVar(value=self.config.get("start_monitoring_on_launch", True))
        start_monitoring_cb = ttk.Checkbutton(scrollable_frame, 
                                            text="启动时自动开始监控",
                                            variable=start_monitoring_var)
        start_monitoring_cb.grid(row=row, column=1, columnspan=2, sticky='w', pady=10, padx=10)
        row += 1
        
        # 目标进程名列表
        ttk.Label(scrollable_frame, text="目标进程名:", font=('微软雅黑', 10)).grid(row=row, column=0, sticky='w', pady=10, padx=10)
        # 将进程列表转换为逗号分隔的字符串 - 使用当前配置而不是默认配置
        processes_str = ", ".join(self.config.get("target_processes", []))
        process_var = tk.StringVar(value=processes_str)
        process_entry = ttk.Entry(scrollable_frame, textvariable=process_var, width=30)
        process_entry.grid(row=row, column=1, columnspan=2, sticky='ew', pady=10, padx=10)
        ttk.Label(scrollable_frame, text="多个进程用逗号分隔，如: chrome.exe, notepad.exe", font=('Arial', 8)).grid(row=row+1, column=1, columnspan=2, sticky='w', padx=10)
        row += 2
        
        # 快捷键设置
        ttk.Label(scrollable_frame, text="显示/隐藏快捷键:", font=('微软雅黑', 10)).grid(row=row, column=0, sticky='w', pady=10, padx=10)
        hotkey_var = tk.StringVar(value=self.config.get("hotkey", "ctrl+alt+d"))
        hotkey_entry = ttk.Entry(scrollable_frame, textvariable=hotkey_var, width=15)
        hotkey_entry.grid(row=row, column=1, sticky='w', pady=10, padx=10)
        ttk.Label(scrollable_frame, text="格式: ctrl+alt+字母", font=('Arial', 8)).grid(row=row, column=2, sticky='w', pady=10)
        row += 1
        
        # 警报文字设置
        ttk.Label(scrollable_frame, text="警报窗口文字:", font=('微软雅黑', 10)).grid(row=row, column=0, sticky='w', pady=10, padx=10)
        alert_text_var = tk.StringVar(value=self.config.get("alert_text", "环境声音过大，请注意文明游戏。"))
        alert_text_entry = ttk.Entry(scrollable_frame, textvariable=alert_text_var, width=30)
        alert_text_entry.grid(row=row, column=1, columnspan=2, sticky='ew', pady=10, padx=10)
        row += 1
        
        # 退出通知文字设置
        ttk.Label(scrollable_frame, text="退出通知文字:", font=('微软雅黑', 10)).grid(row=row, column=0, sticky='w', pady=10, padx=10)
        notification_text_var = tk.StringVar(value=self.config.get("notification_text", "因环境音量过大，已经关闭程序。"))
        notification_text_entry = ttk.Entry(scrollable_frame, textvariable=notification_text_var, width=30)
        notification_text_entry.grid(row=row, column=1, columnspan=2, sticky='ew', pady=10, padx=10)
        ttk.Label(scrollable_frame, text="(终止程序后显示的系统通知)", font=('Arial', 8)).grid(row=row+1, column=1, columnspan=2, sticky='w', padx=10)
        row += 2
        
        # 密码设置区域
        password_frame = ttk.LabelFrame(scrollable_frame, text="密码设置")
        password_frame.grid(row=row, column=0, columnspan=3, sticky='ew', pady=15, padx=10)
        password_frame.columnconfigure(1, weight=1)
        
        # 修改密码按钮
        change_password_button = ttk.Button(password_frame, 
                                          text="修改密码", 
                                          command=self.change_password,
                                          width=15)
        change_password_button.grid(row=0, column=0, padx=10, pady=10)
        
        # 重置密码按钮
        reset_password_button = ttk.Button(password_frame, 
                                         text="重置密码", 
                                         command=self.reset_password,
                                         width=15)
        reset_password_button.grid(row=0, column=1, padx=10, pady=10)
        
        # 密码状态显示
        self.password_status_label = ttk.Label(password_frame, 
                                             text=f"当前密码状态: 已设置",
                                             font=('Arial', 9))
        self.password_status_label.grid(row=1, column=0, columnspan=2, pady=5)
        row += 1
        
        # 音频设备选择
        if self.available_devices:
            ttk.Label(scrollable_frame, text="音频输入设备:", font=('微软雅黑', 10)).grid(row=row, column=0, sticky='w', pady=10, padx=10)
            device_names = [f"{d['name']} (Rate: {int(d['default_sample_rate'])})" for d in self.available_devices]
            device_var = tk.StringVar(value=device_names[0] if device_names else "")
            device_combo = ttk.Combobox(scrollable_frame, textvariable=device_var, values=device_names, width=30)
            device_combo.grid(row=row, column=1, columnspan=2, sticky='ew', pady=10, padx=10)
            row += 1
            
            # 测试音频设备按钮
            def test_audio_device():
                selected_index = device_combo.current()
                if selected_index >= 0:
                    device = self.available_devices[selected_index]
                    messagebox.showinfo("测试", f"已选择设备: {device['name']}\n采样率: {device['default_sample_rate']}Hz")
            
            ttk.Button(scrollable_frame, text="测试音频设备", 
                      command=test_audio_device, width=15).grid(row=row, column=1, pady=5)
            row += 1
        
        # 开机自启
        auto_start_var = tk.BooleanVar(value=self.config["auto_start"])
        auto_start_cb = ttk.Checkbutton(scrollable_frame, 
                                       text="开机自动运行",
                                       variable=auto_start_var)
        auto_start_cb.grid(row=row, column=0, columnspan=3, sticky='w', pady=15, padx=10)
        row += 1
        
        # 按钮区域
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=20)
        
        def save_settings():
            try:
                # 更新配置
                self.config["threshold"] = int(threshold_var.get())
                self.config["max_count"] = int(count_var.get())
                
                # 处理目标进程：将逗号分隔的字符串转换为列表
                processes_str = process_var.get().strip()
                if processes_str:
                    processes_list = [p.strip() for p in processes_str.split(",") if p.strip()]
                    self.config["target_processes"] = processes_list
                else:
                    self.config["target_processes"] = []
                
                self.config["auto_start"] = auto_start_var.get()
                self.config["start_monitoring_on_launch"] = start_monitoring_var.get()
                
                # 新配置项
                self.config["smoothing_window"] = int(smoothing_var.get())
                self.config["calibration_offset"] = float(calibration_var.get())
                
                # 更新平滑窗口大小
                self.db_history = collections.deque(maxlen=self.config["smoothing_window"])
                
                new_hotkey = hotkey_var.get().strip().lower()
                if new_hotkey and new_hotkey != self.config.get("hotkey"):
                    self.config["hotkey"] = new_hotkey
                    # 重新注册快捷键
                    self.register_hotkey()
                
                self.config["alert_text"] = alert_text_var.get()
                self.config["notification_text"] = notification_text_var.get()
                
                # 保存配置
                self.save_config()
                self.set_auto_start(auto_start_var.get())
                
                messagebox.showinfo("提示", "设置已保存")
                settings_window.destroy()
            except ValueError as e:
                messagebox.showerror("错误", f"请输入有效的数字: {e}")
        
        # 保存按钮
        ttk.Button(button_frame, text="保存设置", command=save_settings, width=15).pack(side='left', padx=10)
        
        # 取消按钮
        def cancel_settings():
            settings_window.destroy()
        
        ttk.Button(button_frame, text="取消", command=cancel_settings, width=15).pack(side='left', padx=10)
        
        # 配置列权重
        scrollable_frame.columnconfigure(2, weight=1)
        
        # 打包滚动区域
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def change_password(self):
        """修改密码（需要验证旧密码）"""
        # 验证旧密码
        old_password = simpledialog.askstring("验证旧密码", "请输入当前密码:", show='*')
        if old_password is None:  # 用户点击取消
            return
        
        if old_password != self.config["password"]:
            messagebox.showerror("错误", "旧密码错误！")
            return
        
        # 输入新密码
        new_password = simpledialog.askstring("设置新密码", "请输入新密码:", show='*')
        if new_password is None:  # 用户点击取消
            return
        
        if not new_password:
            messagebox.showerror("错误", "密码不能为空！")
            return
        
        # 确认新密码
        confirm_password = simpledialog.askstring("确认新密码", "请再次输入新密码:", show='*')
        if confirm_password is None:  # 用户点击取消
            return
        
        if new_password != confirm_password:
            messagebox.showerror("错误", "两次输入的密码不一致！")
            return
        
        # 更新密码
        self.config["password"] = new_password
        self.save_config()
        messagebox.showinfo("成功", "密码修改成功！")
        
        # 更新密码状态显示
        if hasattr(self, 'password_status_label'):
            self.password_status_label.config(text="当前密码状态: 已设置")

    def reset_password(self):
        """重置密码为默认密码"""
        # 验证当前密码
        current_password = simpledialog.askstring("验证密码", "请输入当前密码以重置:", show='*')
        if current_password is None:  # 用户点击取消
            return
        
        if current_password != self.config["password"]:
            messagebox.showerror("错误", "密码错误，无法重置！")
            return
        
        # 确认重置
        if messagebox.askyesno("确认重置", "确定要将密码重置为默认密码 '123456' 吗？"):
            self.config["password"] = self.default_config["password"]
            self.save_config()
            messagebox.showinfo("成功", "密码已重置为默认密码 '123456'")
            
            # 更新密码状态显示
            if hasattr(self, 'password_status_label'):
                self.password_status_label.config(text="当前密码状态: 已重置为默认")

    def show_about(self):
        """显示关于信息"""
        about_text = f"""听力精灵 v1.2

作者: Fhy
功能: 监控环境声音并在声音过大时进行提醒
描述: 帮助使用者养成良好的习惯，避免长时间暴露在高分贝环境。

分贝检测优化:
- 使用汉宁窗减少频谱泄漏
- 加权移动平均平滑处理
- 动态性能调整
- 音频设备自动检测

快捷键: {self.config.get("hotkey", "ctrl+alt+d")} (显示/隐藏窗口)

密码重置: 如果忘记密码，可以删除配置文件来重置密码

版权所有 © 2025"""
        
        messagebox.showinfo("关于", about_text)

    def quit_app(self):
        """退出程序（需要密码验证）"""
        password = simpledialog.askstring("退出确认", "请输入密码退出程序:", show='*')
        if password == self.config["password"]:
            # 清理资源
            self.is_running = False
            try:
                keyboard.remove_hotkey(self.config['hotkey'])
            except:
                pass
            
            # 清理音频资源
            self.cleanup_audio()
            
            # 退出程序
            self.root.quit()
            self.root.destroy()
        else:
            messagebox.showerror("错误", "密码错误！")

    def create_main_window(self):
        """创建主界面"""
        self.root = tk.Tk()
        self.root.title("听力精灵 - 主界面")
        self.root.geometry("400x800")  # 增加窗口高度
        self.root.resizable(False, False)
        
        # 设置窗口图标 - 使用资源路径
        try:
            icon_path = resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(default=icon_path)
            else:
                print("图标文件不存在，跳过设置图标")
        except Exception as e:
            print(f"设置窗口图标失败: {e}")
        
        # 设置背景颜色
        self.root.configure(bg='lightblue')
        bg_color = 'lightblue'
        
        # 创建主框架
        main_frame = tk.Frame(self.root, bg=bg_color)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(main_frame, 
                              text="听力精灵", 
                              font=('微软雅黑', 20, 'bold'),
                              bg=bg_color)
        title_label.pack(pady=20)
        
        # 状态显示区域
        status_frame = tk.Frame(main_frame, bg=bg_color)
        status_frame.pack(fill='x', pady=15)
        
        # 状态显示
        self.status_label = tk.Label(status_frame, 
                               text="监控状态: 运行中",
                               font=('微软雅黑', 12),
                               bg=bg_color,
                               fg='green')
        self.status_label.pack(pady=5)
        
        # 分贝显示
        self.db_label = tk.Label(status_frame, 
                               text="当前分贝: -- dB",
                               font=('微软雅黑', 10),
                               bg=bg_color)
        self.db_label.pack(pady=5)
        
        # 阈值显示
        self.threshold_label = tk.Label(status_frame, 
                                      text=f"阈值: {self.config['threshold']} dB",
                                      font=('微软雅黑', 10),
                                      bg=bg_color)
        self.threshold_label.pack(pady=5)
        
        # 警报次数显示
        self.alert_count_label = tk.Label(status_frame, 
                                        text="警报次数: 0",
                                        font=('微软雅黑', 10),
                                        bg=bg_color)
        self.alert_count_label.pack(pady=5)
        
        # 平滑分贝显示
        self.smooth_db_label = tk.Label(status_frame, 
                                      text="平滑分贝: -- dB",
                                      font=('微软雅黑', 9),
                                      bg=bg_color,
                                      fg='gray')
        self.smooth_db_label.pack(pady=2)
        
        # 按钮框架 - 使用grid布局确保按钮排列整齐
        button_frame = tk.Frame(main_frame, bg=bg_color)
        button_frame.pack(fill='both', expand=True, pady=25)
        
        # 按钮样式
        button_style = {
            'font': ('微软雅黑', 12),
            'width': 20,
            'height': 2,
            'bg': 'lightgray'
        }
        
        # 启用功能按钮
        self.enable_button = tk.Button(button_frame, 
                                      text="启用功能", 
                                      command=self.enable_monitoring,
                                      **button_style)
        self.enable_button.grid(row=0, column=0, padx=10, pady=12, sticky='ew')
        
        # 关闭功能按钮
        self.disable_button = tk.Button(button_frame, 
                                       text="关闭功能", 
                                       command=self.disable_monitoring,
                                       **button_style)
        self.disable_button.grid(row=1, column=0, padx=10, pady=12, sticky='ew')
        
        # 设置按钮
        settings_button = tk.Button(button_frame, 
                                   text="设置", 
                                   command=self.show_settings,
                                   **button_style)
        settings_button.grid(row=2, column=0, padx=10, pady=12, sticky='ew')
        
        # 关于按钮
        about_button = tk.Button(button_frame, 
                                text="关于", 
                                command=self.show_about,
                                **button_style)
        about_button.grid(row=3, column=0, padx=10, pady=12, sticky='ew')
        
        # 退出按钮
        exit_button = tk.Button(button_frame, 
                               text="退出程序", 
                               command=self.quit_app,
                               **button_style)
        exit_button.grid(row=4, column=0, padx=10, pady=12, sticky='ew')
        
        # 配置按钮框架的列权重，使按钮居中
        button_frame.columnconfigure(0, weight=1)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # 初始化按钮状态
        self.update_button_state()
        
        # 默认隐藏窗口
        self.root.withdraw()
        self.window_visible = False

    def register_hotkey(self):
        """注册全局快捷键"""
        try:
            # 先尝试移除可能已存在的快捷键
            try:
                keyboard.remove_hotkey(self.config['hotkey'])
            except:
                pass
            
            # 注册新的快捷键
            keyboard.add_hotkey(self.config['hotkey'], self.toggle_window)
            print(f"已注册快捷键: {self.config['hotkey']}")
        except Exception as e:
            print(f"注册快捷键失败: {e}")

    def toggle_window(self):
        """切换窗口显示/隐藏"""
        if self.window_visible:
            self.hide_window()
        else:
            self.show_window()

    def show_window(self):
        """显示窗口"""
        if not self.window_visible:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.window_visible = True
            # 启动UI更新
            self.start_ui_update()

    def hide_window(self):
        """隐藏窗口"""
        if self.window_visible:
            self.root.withdraw()
            self.window_visible = False
            # 停止UI更新
            self.stop_ui_update()

    def start_ui_update(self):
        """开始UI更新"""
        if hasattr(self, 'ui_update_id'):
            self.root.after_cancel(self.ui_update_id)
        self.update_ui()

    def stop_ui_update(self):
        """停止UI更新"""
        if hasattr(self, 'ui_update_id'):
            self.root.after_cancel(self.ui_update_id)

    def update_ui(self):
        """更新UI显示"""
        if self.window_visible:
            # 更新分贝显示
            self.db_label.config(text=f"当前分贝: {self.current_db:.1f} dB")
            
            # 更新平滑分贝显示
            self.smooth_db_label.config(text=f"平滑分贝: {self.db_smoothed:.1f} dB")
            
            # 根据分贝值改变颜色
            if self.current_db > self.config["threshold"]:
                self.db_label.config(fg='red')
            else:
                self.db_label.config(fg='black')
            
            # 更新警报次数显示
            self.alert_count_label.config(text=f"警报次数: {self.alert_count}")
            
            # 更新阈值显示
            self.threshold_label.config(text=f"阈值: {self.config['threshold']} dB")
        
        # 100ms后再次更新
        self.ui_update_id = self.root.after(100, self.update_ui)

    def calculate_decibel(self, data):
        """计算声音分贝值 - 优化版本"""
        try:
            # 将字节数据转换为numpy数组
            audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            
            # 应用汉宁窗减少频谱泄漏
            window = np.hanning(len(audio_data))
            audio_data = audio_data * window
            
            # 计算RMS值
            rms = np.sqrt(np.mean(audio_data**2))
            
            # 避免除零错误，设置最小阈值
            min_volume = self.config.get("min_volume_threshold", 0.001)
            if rms < min_volume:
                return 0
                
            # 计算分贝值 (参考: 16位有符号整数的最大值是32768)
            # 使用更准确的分贝计算公式
            db = 20.0 * np.log10(rms / 32768.0)
            
            # 转换为正的分贝值并添加校准偏移
            db = max(0, db + 60 + self.config.get("calibration_offset", 0))
            
            # 限制最大分贝值
            return min(db, 120)
            
        except Exception as e:
            print(f"计算分贝错误: {e}")
            return 0

    def smooth_decibel_value(self, db_value):
        """平滑分贝值，减少波动"""
        # 添加到历史记录
        self.db_history.append(db_value)
        
        # 如果历史记录不足，直接返回当前值
        if len(self.db_history) < 2:
            return db_value
        
        # 使用加权移动平均进行平滑
        weights = np.linspace(0.5, 1.0, len(self.db_history))
        weights = weights / np.sum(weights)
        
        smoothed = np.average(list(self.db_history), weights=weights)
        return smoothed

    def init_audio_stream(self):
        """初始化音频流 - 优化版本"""
        try:
            with self.audio_lock:
                # 清理现有资源
                if self.stream:
                    try:
                        self.stream.stop_stream()
                        self.stream.close()
                    except:
                        pass
                
                if self.audio:
                    try:
                        self.audio.terminate()
                    except:
                        pass
                
                # 创建新的音频流
                self.audio = pyaudio.PyAudio()
                
                # 尝试使用最佳设备
                device_index = None
                for device in self.available_devices:
                    if '麦克风' in device['name'] or 'microphone' in device['name'].lower():
                        device_index = device['index']
                        print(f"选择麦克风设备: {device['name']}")
                        break
                
                # 设置音频参数
                rate = self.RATE
                channels = self.CHANNELS
                
                # 尝试打开音频流
                self.stream = self.audio.open(
                    format=self.FORMAT,
                    channels=channels,
                    rate=rate,
                    input=True,
                    frames_per_buffer=self.CHUNK,
                    input_device_index=device_index,
                    stream_callback=None
                )
                
                print(f"音频流初始化成功: {rate}Hz, {channels}通道, {self.CHUNK}采样/块")
                return True
                
        except Exception as e:
            print(f"初始化音频流失败: {e}")
            # 尝试使用默认参数
            try:
                self.stream = self.audio.open(
                    format=self.FORMAT,
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    input=True,
                    frames_per_buffer=self.CHUNK,
                    input_device_index=None
                )
                print("使用默认参数初始化音频流成功")
                return True
            except Exception as e2:
                print(f"默认参数初始化也失败: {e2}")
                return False

    def sound_monitor(self):
        """声音监控线程 - 优化版本"""
        print("启动声音监控线程...")
        
        # 初始化音频流
        if not self.init_audio_stream():
            print("音频初始化失败，监控线程退出")
            return
        
        consecutive_errors = 0
        max_consecutive_errors = 10
        error_delay = 0.1
        
        # 性能监控
        processing_times = collections.deque(maxlen=50)
        
        while self.is_running:
            if self.is_monitoring:
                try:
                    start_time = time.time()
                    
                    # 读取音频数据
                    data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                    
                    # 计算分贝值
                    raw_db = self.calculate_decibel(data)
                    
                    # 平滑处理
                    self.db_smoothed = self.smooth_decibel_value(raw_db)
                    
                    # 使用平滑值作为当前分贝值
                    self.current_db = self.db_smoothed
                    
                    # 检测是否超过阈值
                    if self.current_db > self.config["threshold"]:
                        current_time = time.time()
                        # 防止连续触发，设置1秒冷却时间
                        if current_time - self.last_alert_time > 1:
                            self.alert_count += 1
                            self.last_alert_time = current_time
                            print(f"警报触发! 分贝: {self.current_db:.1f}, 平滑: {self.db_smoothed:.1f}, 次数: {self.alert_count}")
                            self.handle_alert()
                    
                    # 性能监控
                    processing_time = time.time() - start_time
                    processing_times.append(processing_time)
                    
                    # 每50次采样输出一次性能信息
                    if len(processing_times) == 50:
                        avg_time = sum(processing_times) / len(processing_times)
                        max_time = max(processing_times)
                        print(f"音频处理性能: 平均 {avg_time*1000:.2f}ms, 最大 {max_time*1000:.2f}ms")
                    
                    consecutive_errors = 0  # 重置错误计数
                    error_delay = 0.1  # 重置错误延迟
                    
                    # 动态调整采样间隔，保持稳定处理
                    target_interval = 0.05  # 目标20Hz采样率
                    actual_interval = max(0.01, target_interval - processing_time)
                    time.sleep(actual_interval)
                    
                except IOError as e:
                    # 处理音频缓冲区溢出等IO错误
                    consecutive_errors += 1
                    if consecutive_errors <= 3:
                        print(f"音频IO错误 ({consecutive_errors}/{max_consecutive_errors}): {e}")
                        time.sleep(error_delay)
                        error_delay *= 1.5  # 指数退避
                    else:
                        print("连续IO错误过多，尝试重新初始化音频流...")
                        if self.init_audio_stream():
                            print("音频流重新初始化成功")
                            consecutive_errors = 0
                            error_delay = 0.1
                        else:
                            print("音频流重新初始化失败，暂停监控")
                            time.sleep(2)
                            
                except Exception as e:
                    consecutive_errors += 1
                    print(f"音频监控错误 ({consecutive_errors}/{max_consecutive_errors}): {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print("连续错误过多，尝试重新初始化音频流...")
                        if self.init_audio_stream():
                            print("音频流重新初始化成功")
                            consecutive_errors = 0
                            error_delay = 0.1
                        else:
                            print("音频流重新初始化失败，暂停监控")
                            time.sleep(2)
                    else:
                        time.sleep(error_delay)
                        error_delay = min(1.0, error_delay * 1.5)  # 指数退避，最大1秒
            else:
                # 监控暂停时，重置分贝值显示
                self.current_db = 0
                self.db_smoothed = 0
                time.sleep(0.5)
        
        # 清理资源
        self.cleanup_audio()

    def cleanup_audio(self):
        """清理音频资源"""
        with self.audio_lock:
            try:
                if self.stream:
                    self.stream.stop_stream()
                    self.stream.close()
                    self.stream = None
            except:
                pass
                
            try:
                if self.audio:
                    self.audio.terminate()
                    self.audio = None
            except:
                pass

    def handle_alert(self):
        """处理警报"""
        print(f"声音过大警报! 次数: {self.alert_count}")
        
        # 前几次弹窗提醒
        if self.alert_count <= self.config["max_count"]:
            self.root.after(0, self.show_alert_window)
        else:
            # 超过次数限制，执行关闭进程操作
            self.terminate_processes()
            # 重置警报计数器
            self.alert_count = 0
            # 显示系统通知 - 使用配置中的通知文字
            self.show_notification("听力精灵", self.config.get("notification_text", "因环境音量过大，已经关闭程序。"))

    def show_alert_window(self):
        """显示警报窗口"""
        # 使用tkinter创建警报窗口
        alert_window = tk.Toplevel()
        alert_window.title("声音警报")
        alert_window.overrideredirect(True)  # 无边框
        alert_window.attributes('-topmost', True)  # 置顶
        
        # 设置窗口大小和位置
        window_width = 400
        window_height = 120
        screen_width = alert_window.winfo_screenwidth()
        screen_height = alert_window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = 50  # 屏幕上方
        alert_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 黑色半透明背景
        alert_window.configure(bg='black')
        alert_window.attributes('-alpha', 0.8)  # 半透明
        
        # 警告文字
        label = tk.Label(alert_window, 
                        text=self.config["alert_text"],
                        fg='white', 
                        bg='black',
                        font=('微软雅黑', 14, 'bold'),
                        wraplength=380)  # 自动换行
        label.pack(expand=True, fill='both')
        
        # 播放提示音
        try:
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        except:
            pass
        
        # 6秒后自动关闭
        alert_window.after(6000, alert_window.destroy)

    def check_process_exists(self, process_name):
        """检查指定进程是否存在"""
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and process_name.lower() == proc.info['name'].lower():
                    return True
            return False
        except Exception as e:
            print(f"检查进程存在性失败: {e}")
            return False

    def terminate_processes(self):
        """终止所有目标进程"""
        target_processes = self.config.get("target_processes", [])
        if not target_processes:
            print("没有配置目标进程")
            return
        
        terminated_processes = []
        failed_processes = []
        not_found_processes = []
        
        try:
            for target_process in target_processes:
                target_process = target_process.strip()
                if not target_process:
                    continue
                    
                print(f"检查进程: {target_process}")
                
                # 检查进程是否存在
                if not self.check_process_exists(target_process):
                    not_found_processes.append(target_process)
                    print(f"进程不存在: {target_process}")
                    continue
                
                # 终止进程
                process_terminated = False
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] and target_process.lower() == proc.info['name'].lower():
                        try:
                            proc.terminate()
                            print(f"已终止进程: {proc.info['name']}")
                            terminated_processes.append(proc.info['name'])
                            process_terminated = True
                        except psutil.NoSuchProcess:
                            print(f"进程已不存在: {target_process}")
                        except psutil.AccessDenied:
                            print(f"无权限终止进程: {target_process}")
                            failed_processes.append(target_process)
                        except Exception as e:
                            print(f"终止进程失败 {target_process}: {e}")
                            failed_processes.append(target_process)
                
                if not process_terminated and target_process not in failed_processes:
                    not_found_processes.append(target_process)
            
            # 显示结果消息 - 使用系统通知而不是弹窗
            message_parts = []
            if terminated_processes:
                message_parts.append(f"已终止: {', '.join(terminated_processes)}")
            if not_found_processes:
                message_parts.append(f"未运行: {', '.join(not_found_processes)}")
            if failed_processes:
                message_parts.append(f"终止失败: {', '.join(failed_processes)}")
            
            if message_parts:
                result_message = "\n".join(message_parts)
                print(f"进程终止结果:\n{result_message}")
                # 使用系统通知显示结果
                self.show_notification("进程终止结果", result_message)
            else:
                print("没有需要终止的进程")
                
        except Exception as e:
            print(f"终止进程失败: {e}")
            self.show_notification("错误", f"终止进程失败: {e}")

    def set_auto_start(self, enable):
        """设置开机自启（Windows）"""
        try:
            if os.name == 'nt':  # Windows
                import winreg
                key = winreg.HKEY_CURRENT_USER
                subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
                
                with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as reg_key:
                    if enable:
                        exe_path = os.path.abspath(sys.argv[0])
                        winreg.SetValueEx(reg_key, "HearingAssistant", 0, winreg.REG_SZ, exe_path)
                    else:
                        try:
                            winreg.DeleteValue(reg_key, "HearingAssistant")
                        except:
                            pass
        except Exception as e:
            print(f"设置开机自启失败: {e}")

    def show_notification(self, title, message):
        """显示系统通知"""
        try:
            notification.notify(
                title=title,
                message=message,
                timeout=5  # 5秒后自动关闭
            )
            print(f"显示通知: {message}")
        except Exception as e:
            print(f"显示通知失败: {e}")

if __name__ == "__main__":
    try:
        app = HearingAssistant()
    except Exception as e:
        print(f"程序启动失败: {e}")
        messagebox.showerror("错误", f"程序启动失败: {e}")