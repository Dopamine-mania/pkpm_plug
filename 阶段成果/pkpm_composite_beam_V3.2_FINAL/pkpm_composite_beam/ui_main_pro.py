"""
PKPM-CAE 叠合梁参数化建模引擎 - PyQt5 专业版UI
"""

import sys
import os
import traceback
from pathlib import Path


def _write_ui_error_log(exc: BaseException) -> None:
    try:
        base_dir = Path(__file__).resolve().parent
    except Exception:
        base_dir = Path.cwd()
    log_path = base_dir / "ui_error.log"
    try:
        log_path.write_text(
            "UI 启动/运行异常：\n\n" + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            encoding="utf-8",
        )
    except Exception:
        pass


def _show_startup_error(msg: str) -> None:
    try:
        if os.name == "nt":
            import ctypes  # noqa: PLC0415
            ctypes.windll.user32.MessageBoxW(None, msg, "PKPM-CAE Composite Beam Tool", 0x10)
            return
    except Exception:
        pass
    try:
        print(msg)
    except Exception:
        pass


try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QLabel, QLineEdit, QPushButton, QFileDialog,
        QGroupBox, QFormLayout, QTextEdit, QMessageBox, QScrollArea,
        QDoubleSpinBox, QSpinBox, QComboBox, QFrame
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
    from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPixmap, QPainter
except Exception as e:
    _write_ui_error_log(e)
    _show_startup_error(
        "无法启动 UI：缺少 PyQt5 依赖。\n\n"
        "解决办法：\n"
        "1) 先运行“安装依赖.bat”\n"
        "2) 或确保 Python 环境已安装 PyQt5\n\n"
        "已生成错误日志：ui_error.log"
    )
    raise SystemExit(1)

# 核心路径修复逻辑
def get_resource_path(relative_path):
    """获取程序运行时资源的绝对路径（兼容源码和EXE打包）"""
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)

# 修改所有涉及路径的地方
current_dir = get_resource_path("")
sys.path.insert(0, current_dir)

try:
    from main import CompositeBeamModelGenerator
    ENGINE_AVAILABLE = True
except Exception as e:
    print(f"警告: 主引擎模块未加载 - {e}")
    ENGINE_AVAILABLE = False


def _excepthook(exc_type, exc, tb):
    _write_ui_error_log(exc)
    try:
        traceback.print_exception(exc_type, exc, tb)
    except Exception:
        pass


sys.excepthook = _excepthook


class ModelGenerationThread(QThread):
    """后台模型生成线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, excel_path, output_script="pkpm_composite_beam_model.py"):
        super().__init__()
        self.excel_path = excel_path
        self.output_script = output_script

    def run(self):
        try:
            self.progress.emit("[启动] 初始化引擎...")
            generator = CompositeBeamModelGenerator(self.excel_path)

            self.progress.emit("[1/7] 解析 Excel 参数...")
            generator.parse_excel()

            self.progress.emit("[2/7] 创建几何模型...")
            generator.create_geometry()

            self.progress.emit("[3/7] 创建钢筋布置...")
            generator.create_rebars()

            # 说明：部分 PKPM-CAE 版本要求网格后才能建立嵌入关系；生成脚本会输出对应操作指南
            self.progress.emit("[4/7] 生成钢筋嵌入提示(网格后在CAE内完成)...")
            generator.create_embedment()

            self.progress.emit("[5/7] 创建预应力孔道...")
            generator.create_prestress_ducts()

            self.progress.emit("[6/7] 配置两阶段分析...")
            generator.create_two_stage_analysis()

            self.progress.emit("[7/7] 导出 Python 脚本...")
            # 输出路径策略：
            # - 源码运行：固定输出到程序目录，便于统一交付/定位
            # - EXE 运行：输出到 Excel 同目录（避免写入临时目录导致用户找不到输出文件）
            output_path = self.output_script or "pkpm_composite_beam_model.py"
            if not os.path.isabs(output_path):
                base = os.path.basename(output_path)
                if hasattr(sys, "_MEIPASS"):
                    excel_dir = os.path.dirname(os.path.abspath(self.excel_path))
                    output_path = os.path.join(excel_dir, base)
                else:
                    output_path = os.path.join(current_dir, base)
            generator.export_script(output_path)

            self.finished.emit(True, f"模型生成成功！\n输出文件: {output_path}")
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.finished.emit(False, f"错误: {str(e)}\n\n详细信息:\n{error_detail}")


class CompositeBeamUI(QMainWindow):
    """PKPM-CAE 叠合梁参数化建模 专业版UI"""

    def __init__(self):
        super().__init__()
        self.excel_path = None
        self._temp_excel_to_cleanup = None
        self._loading_excel = False
        self.init_ui()
        self.load_demo_parameters()  # 自动加载演示参数

    @staticmethod
    def create_label(text):
        """创建带中文字体的标签"""
        label = QLabel(text)
        label.setFont(QFont("Microsoft YaHei", 10))
        return label

    def init_ui(self):
        """初始化专业级UI界面"""
        self.setWindowTitle("PKPM-CAE 叠合梁参数化建模工具 V3.2")
        self.setGeometry(100, 100, 1200, 850)

        # 设置全局默认中文字体
        default_font = QFont("Microsoft YaHei", 10)
        QApplication.instance().setFont(default_font)

        # 设置应用程序样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F3F4F6;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #D1D5DB;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #1F2937;
            }
            QLabel {
                color: #374151;
            }
            QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
                padding: 6px;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                background-color: white;
                min-height: 25px;
            }
            QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
                border: 2px solid #3B82F6;
            }
            QTabWidget::pane {
                border: 2px solid #E5E7EB;
                border-radius: 6px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #E5E7EB;
                color: #4B5563;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #3B82F6;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #60A5FA;
                color: white;
            }
        """)

        # 中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ========== Logo 和标题区 ==========
        header_widget = self.create_header()
        main_layout.addWidget(header_widget)

        # ========== Excel 文件选择区 ==========
        file_group = QGroupBox("📁 Excel 参数文件")
        file_layout = QHBoxLayout()
        file_group.setLayout(file_layout)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("请选择 Excel 参数文件（或使用默认演示参数）")
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setStyleSheet("font-size: 13px;")
        file_layout.addWidget(self.file_path_edit, 3)

        browse_btn = QPushButton("📂 浏览...")
        browse_btn.clicked.connect(self.browse_excel)
        browse_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                font-weight: bold;
                background-color: #6B7280;
                color: white;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        file_layout.addWidget(browse_btn)

        load_btn = QPushButton("📥 读取 Excel")
        load_btn.clicked.connect(self.load_excel)
        load_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                font-weight: bold;
                background-color: #3B82F6;
                color: white;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        file_layout.addWidget(load_btn)

        main_layout.addWidget(file_group)

        # ========== 参数输入区（6 个标签页）==========
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Microsoft YaHei", 11))  # 设置标签页字体
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #3B82F6;
                border-radius: 8px;
                background-color: white;
                padding: 10px;
            }
            QTabBar::tab {
                font-family: "Microsoft YaHei";
                font-size: 13px;
                font-weight: bold;
            }
        """)

        # Tab 1: 几何参数
        self.create_geometry_tab()

        # Tab 2: 纵向配筋
        self.create_rebar_tab()

        # Tab 3: 箍筋
        self.create_stirrup_tab()

        # Tab 4: 洞口与倒角
        self.create_holes_tab()

        # Tab 5: 荷载与边界
        self.create_loads_tab()

        # Tab 6: 预应力
        self.create_prestress_tab()

        main_layout.addWidget(self.tab_widget, 1)

        # ========== 操作按钮区 ==========
        btn_layout = QHBoxLayout()

        generate_btn = QPushButton("🚀 一键生成模型")
        generate_btn.clicked.connect(self.generate_model)
        generate_btn.setStyleSheet("""
            QPushButton {
                padding: 15px 40px;
                font-size: 18px;
                font-weight: bold;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #10B981, stop:1 #059669);
                color: white;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #059669, stop:1 #047857);
            }
            QPushButton:pressed {
                background: #047857;
            }
        """)
        btn_layout.addStretch()
        btn_layout.addWidget(generate_btn)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # ========== 日志输出区 ==========
        log_group = QGroupBox("📊 生成日志")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet("""
            background-color: #1F2937;
            color: #10B981;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12px;
            padding: 10px;
            border-radius: 4px;
        """)
        self.log_text.append(">>> 系统已就绪，等待参数输入...")
        self.log_text.append(">>> 已自动加载演示参数 (10m 跨叠合梁)")
        log_layout.addWidget(self.log_text)

        main_layout.addWidget(log_group)

    def create_header(self):
        """创建Logo和标题区"""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #1E40AF, stop:1 #3B82F6);
                border-radius: 10px;
                padding: 20px;
            }
        """)

        header_layout = QVBoxLayout()
        header_frame.setLayout(header_layout)

        # Logo 文字
        logo_label = QLabel("PKPM-CAE")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_font = QFont("Arial", 24, QFont.Bold)
        logo_label.setFont(logo_font)
        logo_label.setStyleSheet("color: white; padding: 5px;")
        header_layout.addWidget(logo_label)

        # 主标题
        title_label = QLabel("叠合梁参数化建模自动化工具")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Microsoft YaHei", 20, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white; padding: 5px;")
        header_layout.addWidget(title_label)

        # 副标题
        subtitle_label = QLabel("T+7 专业版 | Excel驱动 • 一键生成 • 工程级质量")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_font = QFont("Microsoft YaHei", 11)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: #E0E7FF; padding: 3px;")
        header_layout.addWidget(subtitle_label)

        return header_frame

    def create_geometry_tab(self):
        """创建几何参数标签页"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(tab)
        scroll.setWidgetResizable(True)

        main_layout = QVBoxLayout()
        tab.setLayout(main_layout)

        self.geom_inputs = {}

        # ========== 截面类型选择组 ==========
        section_group = QGroupBox("截面类型选择")
        section_layout = QFormLayout()
        section_group.setLayout(section_layout)

        section_type_combo = QComboBox()
        section_type_combo.addItems(["矩形截面", "T型截面", "倒T型截面 (常用)", "工字型截面"])
        section_type_combo.setCurrentIndex(2)  # 默认倒T型
        section_type_combo.currentIndexChanged.connect(self._on_section_type_changed)
        self.geom_inputs["section_type"] = section_type_combo

        label = QLabel("截面形式:")
        label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        label.setStyleSheet("color: #1F2937;")
        section_layout.addRow(label, section_type_combo)

        # 截面示意图说明
        section_info = QLabel("矩形=无翼缘 | T型=上翼缘 | 倒T型=下翼缘 | 工字型=上下翼缘")
        section_info.setStyleSheet("color: #6B7280; font-size: 11px; font-style: italic;")
        section_layout.addRow(section_info)

        main_layout.addWidget(section_group)

        # ========== 基本尺寸组 ==========
        basic_group = QGroupBox("基本尺寸")
        basic_layout = QFormLayout()
        basic_group.setLayout(basic_layout)

        basic_fields = [
            ("L", "梁长", 10000.0, "mm"),
            ("H", "梁高", 800.0, "mm"),
            ("Tw", "腹板宽度", 250.0, "mm"),
            ("h_pre", "预制层高度", 500.0, "mm"),
            ("t_cast_cap", "现浇顶盖厚度(0=自动)", 75.0, "mm"),
        ]

        for field_name, label_text, default, unit in basic_fields:
            input_widget = QDoubleSpinBox()
            input_widget.setRange(0, 100000)
            input_widget.setValue(default)
            input_widget.setDecimals(1)
            input_widget.setSuffix(f" {unit}")
            input_widget.setMinimumWidth(150)

            label = QLabel(f"{label_text}:")
            label.setFont(QFont("Microsoft YaHei", 10))
            label.setStyleSheet("font-weight: bold; color: #374151;")

            self.geom_inputs[field_name] = input_widget
            basic_layout.addRow(label, input_widget)

        main_layout.addWidget(basic_group)

        # ========== 上翼缘参数组 ==========
        self.upper_flange_group = QGroupBox("上翼缘参数")
        upper_flange_layout = QFormLayout()
        self.upper_flange_group.setLayout(upper_flange_layout)

        upper_flange_fields = [
            ("bf_lu", "左上翼缘伸出宽", 100.0),
            ("tf_lu", "左上翼缘厚度", 150.0),
            ("bf_ru", "右上翼缘伸出宽", 100.0),
            ("tf_ru", "右上翼缘厚度", 150.0),
        ]

        for field_name, label_text, default in upper_flange_fields:
            input_widget = QDoubleSpinBox()
            input_widget.setRange(0, 5000)
            input_widget.setValue(default)
            input_widget.setDecimals(1)
            input_widget.setSuffix(" mm")
            input_widget.setMinimumWidth(150)

            label = QLabel(f"{label_text}:")
            label.setFont(QFont("Microsoft YaHei", 10))
            label.setStyleSheet("color: #374151;")

            self.geom_inputs[field_name] = input_widget
            upper_flange_layout.addRow(label, input_widget)

        main_layout.addWidget(self.upper_flange_group)

        # ========== 下翼缘参数组 ==========
        self.lower_flange_group = QGroupBox("下翼缘参数")
        lower_flange_layout = QFormLayout()
        self.lower_flange_group.setLayout(lower_flange_layout)

        lower_flange_fields = [
            ("bf_ll", "左下翼缘伸出宽", 100.0),
            ("tf_ll", "左下翼缘厚度", 150.0),
            ("bf_rl", "右下翼缘伸出宽", 100.0),
            ("tf_rl", "右下翼缘厚度", 150.0),
        ]

        for field_name, label_text, default in lower_flange_fields:
            input_widget = QDoubleSpinBox()
            input_widget.setRange(0, 5000)
            input_widget.setValue(default)
            input_widget.setDecimals(1)
            input_widget.setSuffix(" mm")
            input_widget.setMinimumWidth(150)

            label = QLabel(f"{label_text}:")
            label.setFont(QFont("Microsoft YaHei", 10))
            label.setStyleSheet("color: #374151;")

            self.geom_inputs[field_name] = input_widget
            lower_flange_layout.addRow(label, input_widget)

        main_layout.addWidget(self.lower_flange_group)

        # ========== 混凝土等级组 ==========
        concrete_group = QGroupBox("混凝土等级")
        concrete_layout = QFormLayout()
        concrete_group.setLayout(concrete_layout)

        precast_combo = QComboBox()
        precast_combo.addItems(["C30", "C35", "C40", "C45", "C50"])
        precast_combo.setCurrentText("C40")
        self.geom_inputs["precast_concrete_grade"] = precast_combo

        cast_combo = QComboBox()
        cast_combo.addItems(["C30", "C35", "C40", "C45", "C50"])
        cast_combo.setCurrentText("C35")
        self.geom_inputs["cast_concrete_grade"] = cast_combo

        concrete_layout.addRow(self.create_label("预制层等级:"), precast_combo)
        concrete_layout.addRow(self.create_label("现浇层等级:"), cast_combo)

        main_layout.addWidget(concrete_group)
        main_layout.addStretch()

        self.tab_widget.addTab(scroll, "📐 几何参数")

        # 初始化时根据默认选择更新UI状态
        self._on_section_type_changed(2)  # 默认倒T型

    def _on_section_type_changed(self, index):
        """截面类型切换时更新翼缘参数的启用状态"""
        # index: 0=矩形, 1=T型, 2=倒T型, 3=工字型
        loading = bool(getattr(self, "_loading_excel", False))

        # 上翼缘参数列表
        upper_params = ['bf_lu', 'tf_lu', 'bf_ru', 'tf_ru']
        # 下翼缘参数列表
        lower_params = ['bf_ll', 'tf_ll', 'bf_rl', 'tf_rl']
        # 现浇顶盖厚度：对所有截面类型都有效（0=自动）
        if "t_cast_cap" in self.geom_inputs:
            self.geom_inputs["t_cast_cap"].setEnabled(True)

        if index == 0:  # 矩形截面
            # 禁用所有翼缘，设为0
            self.upper_flange_group.setEnabled(False)
            self.lower_flange_group.setEnabled(False)
            if not loading:
                for p in upper_params + lower_params:
                    self.geom_inputs[p].setValue(0)
            self.upper_flange_group.setTitle("上翼缘参数 (矩形截面不需要)")
            self.lower_flange_group.setTitle("下翼缘参数 (矩形截面不需要)")

        elif index == 1:  # T型截面
            # 启用上翼缘，禁用下翼缘
            self.upper_flange_group.setEnabled(True)
            self.lower_flange_group.setEnabled(False)
            if not loading:
                for p in upper_params:
                    if self.geom_inputs[p].value() == 0:
                        self.geom_inputs[p].setValue(100.0 if 'bf' in p else 150.0)
                for p in lower_params:
                    self.geom_inputs[p].setValue(0)
            self.upper_flange_group.setTitle("上翼缘参数 ✓")
            self.lower_flange_group.setTitle("下翼缘参数 (T型截面不需要)")

        elif index == 2:  # 倒T型截面
            # 禁用上翼缘，启用下翼缘
            self.upper_flange_group.setEnabled(False)
            self.lower_flange_group.setEnabled(True)
            if not loading:
                for p in upper_params:
                    self.geom_inputs[p].setValue(0)
                for p in lower_params:
                    if self.geom_inputs[p].value() == 0:
                        self.geom_inputs[p].setValue(100.0 if 'bf' in p else 150.0)
            self.upper_flange_group.setTitle("上翼缘参数 (倒T型截面不需要)")
            self.lower_flange_group.setTitle("下翼缘参数 ✓")

        elif index == 3:  # 工字型截面
            # 启用所有翼缘
            self.upper_flange_group.setEnabled(True)
            self.lower_flange_group.setEnabled(True)
            if not loading:
                for p in upper_params + lower_params:
                    if self.geom_inputs[p].value() == 0:
                        self.geom_inputs[p].setValue(100.0 if 'bf' in p else 150.0)
            self.upper_flange_group.setTitle("上翼缘参数 ✓")
            self.lower_flange_group.setTitle("下翼缘参数 ✓")

    def create_rebar_tab(self):
        """创建纵向配筋标签页"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(tab)
        scroll.setWidgetResizable(True)

        main_layout = QVBoxLayout()
        tab.setLayout(main_layout)

        self.rebar_inputs = {}

        # 顶部钢筋组（通长筋）
        top_group = QGroupBox("顶部通长筋（全跨）")
        top_layout = QFormLayout()
        top_group.setLayout(top_layout)

        top_fields = [
            ("top_dia", "钢筋直径", 20, "mm"),
            ("top_num", "钢筋根数", 4, "根"),
            ("top_spacing", "横向间距", 80, "mm"),
            ("top_cover", "保护层厚度", 40, "mm"),
            ("top_rows", "纵筋排数(竖向)", 1, "排"),
            ("top_row_spacing", "排间净距(竖向)", 40, "mm"),
        ]

        for field_name, label_text, default, unit in top_fields:
            input_widget = QSpinBox()
            if field_name in ("top_rows",):
                input_widget.setRange(1, 5)
            elif field_name in ("top_row_spacing",):
                input_widget.setRange(0, 300)
            else:
                input_widget.setRange(0, 1000)
            input_widget.setValue(default)
            input_widget.setSuffix(f" {unit}")
            input_widget.setMinimumWidth(150)

            label = QLabel(f"{label_text}:")
            label.setFont(QFont("Microsoft YaHei", 10))  # 明确设置中文字体
            label.setStyleSheet("font-weight: bold; color: #374151;")

            self.rebar_inputs[field_name] = input_widget
            top_layout.addRow(label, input_widget)

        main_layout.addWidget(top_group)

        # 支座附加筋组（左右可不同）
        support_group = QGroupBox("支座附加筋（左右可不同）")
        support_layout = QFormLayout()
        support_group.setLayout(support_layout)

        support_fields = [
            ("left_support_top_dia", "左支座附加筋直径", 0, "mm"),
            ("left_support_top_num", "左支座附加筋根数", 0, "根"),
            ("left_support_length", "左支座区长度", 500, "mm"),
            ("right_support_top_dia", "右支座附加筋直径", 0, "mm"),
            ("right_support_top_num", "右支座附加筋根数", 0, "根"),
            ("right_support_length", "右支座区长度", 500, "mm"),
        ]

        for field_name, label_text, default, unit in support_fields:
            input_widget = QSpinBox()
            if field_name.endswith("_length"):
                input_widget.setRange(0, 50000)
            else:
                input_widget.setRange(0, 1000)
            input_widget.setValue(default)
            input_widget.setSuffix(f" {unit}")
            input_widget.setMinimumWidth(150)

            label = QLabel(f"{label_text}:")
            label.setFont(QFont("Microsoft YaHei", 10))
            label.setStyleSheet("font-weight: bold; color: #374151;")

            self.rebar_inputs[field_name] = input_widget
            support_layout.addRow(label, input_widget)

        main_layout.addWidget(support_group)

        # 底部钢筋组
        bottom_group = QGroupBox("底部纵向钢筋")
        bottom_layout = QFormLayout()
        bottom_group.setLayout(bottom_layout)

        bottom_fields = [
            ("bottom_dia", "钢筋直径", 25, "mm"),
            ("bottom_num", "钢筋根数", 6, "根"),
            ("bottom_spacing", "横向间距", 70, "mm"),
            ("bottom_cover", "保护层厚度", 40, "mm"),
            ("bottom_rows", "纵筋排数(竖向)", 1, "排"),
            ("bottom_row_spacing", "排间净距(竖向)", 40, "mm"),
        ]

        for field_name, label_text, default, unit in bottom_fields:
            input_widget = QSpinBox()
            if field_name in ("bottom_rows",):
                input_widget.setRange(1, 5)
            elif field_name in ("bottom_row_spacing",):
                input_widget.setRange(0, 300)
            else:
                input_widget.setRange(0, 1000)
            input_widget.setValue(default)
            input_widget.setSuffix(f" {unit}")
            input_widget.setMinimumWidth(150)

            label = QLabel(f"{label_text}:")
            label.setFont(QFont("Microsoft YaHei", 10))  # 明确设置中文字体
            label.setStyleSheet("font-weight: bold; color: #374151;")

            self.rebar_inputs[field_name] = input_widget
            bottom_layout.addRow(label, input_widget)

        main_layout.addWidget(bottom_group)
        main_layout.addStretch()

        self.tab_widget.addTab(scroll, "🔩 纵向配筋")

    def create_stirrup_tab(self):
        """创建箍筋标签页"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(tab)
        scroll.setWidgetResizable(True)

        main_layout = QVBoxLayout()
        tab.setLayout(main_layout)

        self.stirrup_inputs = {}

        group = QGroupBox("箍筋配置")
        layout = QFormLayout()
        group.setLayout(layout)

        fields = [
            ("stirrup_dia", "箍筋直径", 10, "mm"),
            ("stirrup_dense_spacing", "加密区间距", 100, "mm"),
            ("stirrup_normal_spacing", "非加密区间距", 200, "mm"),
            ("stirrup_dense_length", "端部加密长度", 1500, "mm"),
            ("stirrup_legs", "箍筋肢数", 4, "肢"),
            ("stirrup_cover", "箍筋保护层", 25, "mm"),
        ]

        for field_name, label_text, default, unit in fields:
            input_widget = QSpinBox()
            input_widget.setRange(0, 5000)
            input_widget.setValue(default)
            input_widget.setSuffix(f" {unit}")
            input_widget.setMinimumWidth(150)

            label = QLabel(f"{label_text}:")
            label.setFont(QFont("Microsoft YaHei", 10))  # 明确设置中文字体
            label.setStyleSheet("font-weight: bold; color: #374151;")

            self.stirrup_inputs[field_name] = input_widget
            layout.addRow(label, input_widget)

        main_layout.addWidget(group)
        main_layout.addStretch()

        self.tab_widget.addTab(scroll, "⚙️ 箍筋")

    def create_holes_tab(self):
        """创建洞口与倒角标签页"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(tab)
        scroll.setWidgetResizable(True)

        main_layout = QVBoxLayout()
        tab.setLayout(main_layout)

        self.hole_inputs = {}

        note = self.create_label("说明：每个洞口都可独立配置补强参数；生成 Excel 时会逐洞口写入 Holes sheet（多行）。")
        note.setStyleSheet("color: #059669; font-size: 11px; font-style: italic;")
        note.setWordWrap(True)
        main_layout.addWidget(note)

        def _add_int(layout: QFormLayout, key: str, label_text: str, default: int, unit: str, vmin: int, vmax: int):
            w = QSpinBox()
            w.setRange(vmin, vmax)
            w.setValue(int(default))
            w.setSuffix(f" {unit}")
            w.setMinimumWidth(150)
            self.hole_inputs[key] = w
            layout.addRow(self.create_label(f"{label_text}:"), w)

        def _add_float(layout: QFormLayout, key: str, label_text: str, default: float, unit: str, vmin: float, vmax: float, dec: int = 1):
            w = QDoubleSpinBox()
            w.setRange(float(vmin), float(vmax))
            w.setValue(float(default))
            w.setDecimals(int(dec))
            w.setSuffix(f" {unit}")
            w.setMinimumWidth(150)
            self.hole_inputs[key] = w
            layout.addRow(self.create_label(f"{label_text}:"), w)

        def _create_one_hole(idx: int) -> QGroupBox:
            title = f"洞口 {idx}" + ("" if idx == 1 else "（可选）")
            group = QGroupBox(title)
            layout = QFormLayout()
            group.setLayout(layout)

            if idx > 1:
                enable = QComboBox()
                enable.addItems(["禁用", "启用"])
                enable.setCurrentText("禁用")
                self.hole_inputs[f"hole{idx}_enabled"] = enable
                layout.addRow(self.create_label(f"洞口{idx}启用:"), enable)

            _add_int(layout, f"hole{idx}_x", "距左端距离", 2000 if idx == 1 else 0, "mm", 0, 50000)
            _add_int(layout, f"hole{idx}_z", "距底部距离", 100 if idx == 1 else 0, "mm", 0, 50000)
            _add_int(layout, f"hole{idx}_width", "洞口宽度", 800 if idx == 1 else 0, "mm", 0, 50000)
            _add_int(layout, f"hole{idx}_height", "洞口高度", 300 if idx == 1 else 0, "mm", 0, 50000)

            fillet_enable = QComboBox()
            fillet_enable.addItems(["禁用", "启用"])
            fillet_enable.setCurrentText("启用" if idx == 1 else "禁用")
            self.hole_inputs[f"fillet{idx}_enabled"] = fillet_enable
            layout.addRow(self.create_label("倒角启用:"), fillet_enable)
            _add_float(layout, f"fillet{idx}_radius", "倒角半径", 50.0 if idx == 1 else 0.0, "mm", 0.0, 5000.0, dec=1)

            layout.addRow(self.create_label("—— 洞口上下小梁配筋 ——"), QLabel(""))
            _add_int(layout, f"hole{idx}_smallbeam_long_top_dia", "顶部纵筋直径", 16 if idx == 1 else 0, "mm", 0, 60)
            _add_int(layout, f"hole{idx}_smallbeam_long_top_count", "顶部纵筋根数", 2 if idx == 1 else 0, "根", 0, 100)
            _add_int(layout, f"hole{idx}_smallbeam_long_bottom_dia", "底部纵筋直径", 16 if idx == 1 else 0, "mm", 0, 60)
            _add_int(layout, f"hole{idx}_smallbeam_long_bottom_count", "底部纵筋根数", 2 if idx == 1 else 0, "根", 0, 100)
            _add_int(layout, f"hole{idx}_smallbeam_stirrup_dia", "小梁箍筋直径", 8 if idx == 1 else 0, "mm", 0, 60)
            _add_int(layout, f"hole{idx}_smallbeam_stirrup_spacing", "小梁箍筋间距", 150 if idx == 1 else 0, "mm", 0, 50000)
            _add_int(layout, f"hole{idx}_smallbeam_stirrup_legs", "小梁箍筋肢数(总肢)", 4 if idx == 1 else 0, "肢", 0, 12)

            layout.addRow(self.create_label("—— 洞口侧边补强 ——"), QLabel(""))
            _add_int(layout, f"hole{idx}_left_reinf_length", "左侧补强长度", 500 if idx == 1 else 0, "mm", 0, 50000)
            _add_int(layout, f"hole{idx}_right_reinf_length", "右侧补强长度", 500 if idx == 1 else 0, "mm", 0, 50000)
            _add_int(layout, f"hole{idx}_side_stirrup_spacing", "侧边箍筋间距", 100 if idx == 1 else 0, "mm", 0, 50000)
            _add_int(layout, f"hole{idx}_side_stirrup_dia", "侧边箍筋直径", 10 if idx == 1 else 0, "mm", 0, 60)
            _add_int(layout, f"hole{idx}_side_stirrup_legs", "侧边箍筋肢数", 2 if idx == 1 else 0, "肢", 0, 8)
            _add_int(layout, f"hole{idx}_reinf_extend_length", "补强筋伸出长度", 300 if idx == 1 else 0, "mm", 0, 50000)

            return group

        for i in (1, 2, 3):
            main_layout.addWidget(_create_one_hole(i))

        main_layout.addStretch()

        self.tab_widget.addTab(scroll, "🔲 洞口 & 倒角")

    def create_loads_tab(self):
        """创建荷载与边界标签页"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(tab)
        scroll.setWidgetResizable(True)

        main_layout = QVBoxLayout()
        tab.setLayout(main_layout)

        self.load_inputs = {}

        # 说明：按客户要求，脚本不施加支座/荷载，仅预留对象
        note = self.create_label("说明：脚本阶段不施加支座/荷载；仅预留加载对象（梁顶面、LOAD_LINE_1/LOAD_LINE_2、LOAD_POINTS）与支座集合（SUPPORT_*）。\n请在网格划分后在 PKPM-CAE 有限元分析模块内创建 Coupling/约束，并对面/线/点施加荷载。")
        note.setStyleSheet("color: #059669; font-size: 11px; font-style: italic;")
        note.setWordWrap(True)
        main_layout.addWidget(note)

        # 荷载配置组（仅记录，不用于脚本施加载荷）
        load_group = QGroupBox("荷载配置（仅记录）")
        load_layout = QFormLayout()
        load_group.setLayout(load_layout)

        load_fields = [
            ("dead_load", "恒载 (自重+装修)", 15.0, "kN/m"),
            ("live_load", "活载", 20.0, "kN/m"),
        ]

        for field_name, label_text, default, unit in load_fields:
            input_widget = QDoubleSpinBox()
            input_widget.setRange(0, 1000)
            input_widget.setValue(default)
            input_widget.setDecimals(1)
            input_widget.setSuffix(f" {unit}")
            input_widget.setMinimumWidth(150)

            label = QLabel(f"{label_text}:")
            label.setFont(QFont("Microsoft YaHei", 10))
            label.setStyleSheet("font-weight: bold; color: #374151;")

            self.load_inputs[field_name] = input_widget
            load_layout.addRow(label, input_widget)
            input_widget.setEnabled(False)

        main_layout.addWidget(load_group)

        # 边界条件组（仅记录，不在脚本中创建 Coupling/约束）
        boundary_group = QGroupBox("支座/边界（仅记录）")
        boundary_layout = QFormLayout()
        boundary_group.setLayout(boundary_layout)

        boundary_combo = QComboBox()
        boundary_combo.addItems(["一端固支一端简支 (推荐)", "两端简支", "两端固支"])
        boundary_combo.setCurrentIndex(0)
        self.load_inputs["boundary_condition"] = boundary_combo
        boundary_combo.setEnabled(False)

        label = QLabel("支座类型:")
        label.setFont(QFont("Microsoft YaHei", 10))
        label.setStyleSheet("font-weight: bold; color: #374151;")
        boundary_layout.addRow(label, boundary_combo)

        # 边界说明（与脚本工作流一致）
        info_label = self.create_label("提示：请在网格后用 SUPPORT_REF_POINTS + SUPPORT_LEFT_FACE / SUPPORT_RIGHT_FACE / SUPPORT_RIGHT_BOTTOM_LINE 建立耦合与约束。")
        info_label.setStyleSheet("color: #059669; font-size: 11px; font-style: italic;")
        info_label.setWordWrap(True)
        boundary_layout.addRow(info_label)

        main_layout.addWidget(boundary_group)

        # 荷载工况组（仅记录）
        case_group = QGroupBox("荷载工况（仅记录）")
        case_layout = QFormLayout()
        case_group.setLayout(case_layout)

        case_combo = QComboBox()
        case_combo.addItems(["标准组合", "准永久组合", "基本组合"])
        case_combo.setCurrentText("标准组合")
        self.load_inputs["load_case"] = case_combo
        case_combo.setEnabled(False)

        label = QLabel("组合类型:")
        label.setFont(QFont("Microsoft YaHei", 10))
        label.setStyleSheet("font-weight: bold; color: #374151;")
        case_layout.addRow(label, case_combo)

        main_layout.addWidget(case_group)
        main_layout.addStretch()

        self.tab_widget.addTab(scroll, "📌 后处理(荷载/支座)")

    def create_prestress_tab(self):
        """创建预应力标签页"""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidget(tab)
        scroll.setWidgetResizable(True)

        main_layout = QVBoxLayout()
        tab.setLayout(main_layout)

        self.prestress_inputs = {}

        group = QGroupBox("预应力参数 (后台逻辑已完成)")
        layout = QFormLayout()
        group.setLayout(layout)

        prestress_enable = QComboBox()
        prestress_enable.addItems(["禁用", "启用"])
        prestress_enable.setCurrentText("禁用")
        self.prestress_inputs["enabled"] = prestress_enable

        # 注意：生成脚本侧 PreStress.value 以“应力(MPa)”处理（不是力N）
        prestress_force = QDoubleSpinBox()
        prestress_force.setRange(0, 3000)
        prestress_force.setValue(0)
        prestress_force.setDecimals(1)
        prestress_force.setSuffix(" MPa")
        prestress_force.setMinimumWidth(150)
        self.prestress_inputs["force"] = prestress_force

        prestress_method = QComboBox()
        prestress_method.addItems(["后张法(post_tension)", "先张法(pretension)"])
        prestress_method.setCurrentText("后张法(post_tension)")
        self.prestress_inputs["method"] = prestress_method

        duct_dia = QDoubleSpinBox()
        duct_dia.setRange(0, 200)
        duct_dia.setValue(90)
        duct_dia.setDecimals(1)
        duct_dia.setSuffix(" mm")
        duct_dia.setMinimumWidth(150)
        self.prestress_inputs["duct_diameter"] = duct_dia

        layout.addRow(self.create_label("预应力启用:"), prestress_enable)
        layout.addRow(self.create_label("张拉力:"), prestress_force)
        layout.addRow(self.create_label("预应力方式:"), prestress_method)
        layout.addRow(self.create_label("波纹管直径:"), duct_dia)

        info_label = self.create_label(
            "说明:\n"
            "- 后张法：预留波纹管孔道(duct_diameter>0)，并在分析阶段施加预应力。\n"
            "- 先张法：不挖孔道，直接对预应力筋/钢筋施加预应力（更利于网格稳定）。"
        )
        info_label.setStyleSheet("color: #059669; font-size: 11px; font-style: italic; padding: 10px;")
        info_label.setWordWrap(True)
        layout.addRow(info_label)

        main_layout.addWidget(group)
        main_layout.addStretch()

        self.tab_widget.addTab(scroll, "⚡ 预应力")

    def load_demo_parameters(self):
        """自动加载演示参数"""
        # 几何参数已在创建时设置默认值
        # 这里可以添加额外的演示数据加载逻辑
        self.file_path_edit.setText("【演示模式】使用默认参数 (10m跨叠合梁，C40预制+C35现浇)")
        pass

    def browse_excel(self):
        """浏览Excel文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 Excel 参数文件", "", "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.excel_path = file_path
            self.file_path_edit.setText(file_path)
            self.log_text.append(f">>> 已选择文件: {Path(file_path).name}")

    def load_excel(self):
        """读取Excel文件并将数值同步到UI界面 """
        if not self.excel_path:
            QMessageBox.warning(self, "警告", "请先选择 Excel 文件")
            return

        try:
            self.log_text.append(f">>> 正在同步 Excel 数据: {Path(self.excel_path).name}...")
            self._loading_excel = True
            
            # 调用现有的解析器获取参数对象
            from parsers.excel_parser import ExcelParser
            parser = ExcelParser(self.excel_path)
            p = parser.parse()

            # 1. 同步几何参数 (Sheet: Geometry)
            g = p.geometry

            # 截面类型推断并同步
            # 规则：有上翼缘=>T；有下翼缘=>倒T；上下都有=>工字；都无=>矩形
            eps = 1e-6
            upper_on = (max(float(g.tf_lu), float(g.tf_ru), float(g.bf_lu), float(g.bf_ru)) > eps)
            lower_on = (max(float(g.tf_ll), float(g.tf_rl), float(g.bf_ll), float(g.bf_rl)) > eps)
            if upper_on and lower_on:
                sec_idx = 3  # 工字型截面
            elif upper_on:
                sec_idx = 1  # T型截面
            elif lower_on:
                sec_idx = 2  # 倒T型截面
            else:
                sec_idx = 0  # 矩形截面

            self.geom_inputs['L'].setValue(g.L)
            self.geom_inputs['H'].setValue(g.H)
            self.geom_inputs['Tw'].setValue(g.Tw)
            self.geom_inputs['h_pre'].setValue(g.h_pre)
            if 't_cast_cap' in self.geom_inputs:
                self.geom_inputs['t_cast_cap'].setValue(float(getattr(g, 't_cast_cap', 0.0) or 0.0))
            self.geom_inputs['bf_lu'].setValue(g.bf_lu)
            self.geom_inputs['tf_lu'].setValue(g.tf_lu)
            self.geom_inputs['bf_ru'].setValue(g.bf_ru)
            self.geom_inputs['tf_ru'].setValue(g.tf_ru)
            self.geom_inputs['bf_ll'].setValue(g.bf_ll)
            self.geom_inputs['tf_ll'].setValue(g.tf_ll)
            self.geom_inputs['bf_rl'].setValue(g.bf_rl)
            self.geom_inputs['tf_rl'].setValue(g.tf_rl)
            # 截面类型：加载期间禁止触发 currentIndexChanged（避免覆盖刚同步的数值）
            _sec_combo = self.geom_inputs.get("section_type", None)
            if _sec_combo is not None:
                try:
                    _sec_combo.blockSignals(True)
                    _sec_combo.setCurrentIndex(sec_idx)
                finally:
                    try:
                        _sec_combo.blockSignals(False)
                    except Exception:
                        pass

            # 刷新启用状态/标题（loading 模式下不改数值）
            self._on_section_type_changed(sec_idx)

            # 2. 同步纵向配筋
            lr = p.long_rebar
            # 顶部通长筋（全跨）
            if getattr(lr, "mid_span_top", None):
                self.rebar_inputs['top_dia'].setValue(int(lr.mid_span_top.diameter))
                self.rebar_inputs['top_num'].setValue(int(lr.mid_span_top.count))
            # 左右支座附加筋（可选）
            if 'left_support_top_dia' in self.rebar_inputs:
                self.rebar_inputs['left_support_top_dia'].setValue(int(getattr(getattr(lr, "left_support_top_A", None), "diameter", 0) or 0))
            if 'left_support_top_num' in self.rebar_inputs:
                self.rebar_inputs['left_support_top_num'].setValue(int(getattr(getattr(lr, "left_support_top_A", None), "count", 0) or 0))
            if 'right_support_top_dia' in self.rebar_inputs:
                self.rebar_inputs['right_support_top_dia'].setValue(int(getattr(getattr(lr, "right_support_top_A", None), "diameter", 0) or 0))
            if 'right_support_top_num' in self.rebar_inputs:
                self.rebar_inputs['right_support_top_num'].setValue(int(getattr(getattr(lr, "right_support_top_A", None), "count", 0) or 0))
            # 支座区长度：0 表示默认 L/3，这里为了观感直接显示为 L/3
            try:
                L0 = float(getattr(g, "L", 0.0) or 0.0)
            except Exception:
                L0 = 0.0
            ll = float(getattr(lr, "left_support_length", 0.0) or 0.0)
            rl = float(getattr(lr, "right_support_length", 0.0) or 0.0)
            if 'left_support_length' in self.rebar_inputs:
                self.rebar_inputs['left_support_length'].setValue(int(ll if ll > 1e-6 else (L0 / 3.0 if L0 > 1e-6 else 0)))
            if 'right_support_length' in self.rebar_inputs:
                self.rebar_inputs['right_support_length'].setValue(int(rl if rl > 1e-6 else (L0 / 3.0 if L0 > 1e-6 else 0)))
            if lr.bottom_through_A:
                self.rebar_inputs['bottom_dia'].setValue(lr.bottom_through_A.diameter)
                self.rebar_inputs['bottom_num'].setValue(lr.bottom_through_A.count)
            if 'top_rows' in self.rebar_inputs:
                self.rebar_inputs['top_rows'].setValue(int(getattr(lr, "top_rows", 1) or 1))
            if 'top_row_spacing' in self.rebar_inputs:
                self.rebar_inputs['top_row_spacing'].setValue(int(float(getattr(lr, "top_row_spacing", 0.0) or 0.0)))
            if 'bottom_rows' in self.rebar_inputs:
                self.rebar_inputs['bottom_rows'].setValue(int(getattr(lr, "bottom_rows", 1) or 1))
            if 'bottom_row_spacing' in self.rebar_inputs:
                self.rebar_inputs['bottom_row_spacing'].setValue(int(float(getattr(lr, "bottom_row_spacing", 0.0) or 0.0)))

            # 3. 同步箍筋 (Sheet: Stirrups)
            st = p.stirrup
            self.stirrup_inputs['stirrup_dia'].setValue(st.dense_diameter)
            self.stirrup_inputs['stirrup_dense_spacing'].setValue(st.dense_spacing)
            self.stirrup_inputs['stirrup_normal_spacing'].setValue(st.normal_spacing)
            self.stirrup_inputs['stirrup_dense_length'].setValue(st.dense_zone_length)
            self.stirrup_inputs['stirrup_legs'].setValue(st.dense_legs)
            if 'stirrup_cover' in self.stirrup_inputs:
                self.stirrup_inputs['stirrup_cover'].setValue(int(float(getattr(st, "cover", 25.0) or 25.0)))

            # 4. 同步洞口数据（最多同步到洞口1~3）
            holes = list(p.holes or [])
            if holes:
                for idx in (1, 2, 3):
                    if idx - 1 >= len(holes):
                        if idx > 1 and f"hole{idx}_enabled" in self.hole_inputs:
                            self.hole_inputs[f"hole{idx}_enabled"].setCurrentText("禁用")
                        continue

                    h = holes[idx - 1]
                    if idx > 1 and f"hole{idx}_enabled" in self.hole_inputs:
                        self.hole_inputs[f"hole{idx}_enabled"].setCurrentText("启用")

                    self.hole_inputs[f'hole{idx}_x'].setValue(h.x)
                    self.hole_inputs[f'hole{idx}_z'].setValue(h.z)
                    self.hole_inputs[f'hole{idx}_width'].setValue(h.width)
                    self.hole_inputs[f'hole{idx}_height'].setValue(h.height)

                    if f'fillet{idx}_enabled' in self.hole_inputs:
                        self.hole_inputs[f'fillet{idx}_enabled'].setCurrentText("启用" if float(h.fillet_radius or 0.0) > 1e-6 else "禁用")
                    if f'fillet{idx}_radius' in self.hole_inputs:
                        self.hole_inputs[f'fillet{idx}_radius'].setValue(float(h.fillet_radius or 0.0))

                    # 小梁配筋（顶/底分开；若旧字段存在则回退）
                    try:
                        top_d = float(getattr(h, "small_beam_long_top_diameter", 0.0) or 0.0)
                        top_c = int(getattr(h, "small_beam_long_top_count", 0) or 0)
                        bot_d = float(getattr(h, "small_beam_long_bottom_diameter", 0.0) or 0.0)
                        bot_c = int(getattr(h, "small_beam_long_bottom_count", 0) or 0)
                        legacy_d = float(getattr(h, "small_beam_long_diameter", 0.0) or 0.0)
                        legacy_c = int(getattr(h, "small_beam_long_count", 0) or 0)
                        if top_c <= 0 or top_d <= 0:
                            top_d, top_c = legacy_d, legacy_c
                        if bot_c <= 0 or bot_d <= 0:
                            bot_d, bot_c = legacy_d, legacy_c
                        if f'hole{idx}_smallbeam_long_top_dia' in self.hole_inputs:
                            self.hole_inputs[f'hole{idx}_smallbeam_long_top_dia'].setValue(int(top_d))
                        if f'hole{idx}_smallbeam_long_top_count' in self.hole_inputs:
                            self.hole_inputs[f'hole{idx}_smallbeam_long_top_count'].setValue(int(top_c))
                        if f'hole{idx}_smallbeam_long_bottom_dia' in self.hole_inputs:
                            self.hole_inputs[f'hole{idx}_smallbeam_long_bottom_dia'].setValue(int(bot_d))
                        if f'hole{idx}_smallbeam_long_bottom_count' in self.hole_inputs:
                            self.hole_inputs[f'hole{idx}_smallbeam_long_bottom_count'].setValue(int(bot_c))
                    except Exception:
                        pass

                    if f'hole{idx}_smallbeam_stirrup_dia' in self.hole_inputs:
                        self.hole_inputs[f'hole{idx}_smallbeam_stirrup_dia'].setValue(int(float(getattr(h, "small_beam_stirrup_diameter", 0.0) or 0.0)))
                    if f'hole{idx}_smallbeam_stirrup_spacing' in self.hole_inputs:
                        self.hole_inputs[f'hole{idx}_smallbeam_stirrup_spacing'].setValue(int(float(getattr(h, "small_beam_stirrup_spacing", 0.0) or 0.0)))
                    if f'hole{idx}_smallbeam_stirrup_legs' in self.hole_inputs:
                        self.hole_inputs[f'hole{idx}_smallbeam_stirrup_legs'].setValue(int(getattr(h, "small_beam_stirrup_legs", 0) or 0))

                    # 侧边补强
                    if f'hole{idx}_left_reinf_length' in self.hole_inputs:
                        self.hole_inputs[f'hole{idx}_left_reinf_length'].setValue(int(float(getattr(h, "left_reinf_length", 0.0) or 0.0)))
                    if f'hole{idx}_right_reinf_length' in self.hole_inputs:
                        self.hole_inputs[f'hole{idx}_right_reinf_length'].setValue(int(float(getattr(h, "right_reinf_length", 0.0) or 0.0)))
                    if f'hole{idx}_side_stirrup_spacing' in self.hole_inputs:
                        self.hole_inputs[f'hole{idx}_side_stirrup_spacing'].setValue(int(float(getattr(h, "side_stirrup_spacing", 0.0) or 0.0)))
                    if f'hole{idx}_side_stirrup_dia' in self.hole_inputs:
                        self.hole_inputs[f'hole{idx}_side_stirrup_dia'].setValue(int(float(getattr(h, "side_stirrup_diameter", 0.0) or 0.0)))
                    if f'hole{idx}_side_stirrup_legs' in self.hole_inputs:
                        self.hole_inputs[f'hole{idx}_side_stirrup_legs'].setValue(int(getattr(h, "side_stirrup_legs", 0) or 0))
                    if f'hole{idx}_reinf_extend_length' in self.hole_inputs:
                        self.hole_inputs[f'hole{idx}_reinf_extend_length'].setValue(int(float(getattr(h, "reinf_extend_length", 0.0) or 0.0)))

                if len(holes) > 3:
                    self.log_text.append(f">>> ⚠ UI 当前最多展示 3 个洞口参数（Excel 共 {len(holes)} 个洞口）")

            # 5. 同步预应力 (Sheet: Prestress)
            if p.prestress:
                ps = p.prestress
                self.prestress_inputs['enabled'].setCurrentText("启用" if ps.enabled else "禁用")
                self.prestress_inputs['force'].setValue(ps.force)
                try:
                    m = str(getattr(ps, "method", "post_tension") or "post_tension").strip().lower()
                except Exception:
                    m = "post_tension"
                if m == "pretension":
                    self.prestress_inputs['method'].setCurrentText("先张法(pretension)")
                else:
                    self.prestress_inputs['method'].setCurrentText("后张法(post_tension)")
                self.prestress_inputs['duct_diameter'].setValue(ps.duct_diameter)
            else:
                self.prestress_inputs['enabled'].setCurrentText("禁用")
                self.prestress_inputs['force'].setValue(0.0)
                self.prestress_inputs['duct_diameter'].setValue(0.0)

            self.log_text.append(">>> ✅ Excel 数值已成功同步至 UI 界面！")
            QMessageBox.information(self, "同步成功", "Excel 数据已完美加载到界面，您可以继续微调参数。")
            
        except Exception as e:
            self.log_text.append(f">>> ❌ 同步失败: {str(e)}")
            QMessageBox.critical(self, "同步错误", f"Excel 数据与界面不匹配:\n{str(e)}")
        finally:
            self._loading_excel = False


    def _save_ui_params_to_excel(self, excel_path="temp_ui_params.xlsx"):
        """将UI参数保存为Excel文件（100%匹配excel_parser.py的V3.0格式）"""
        # 使用 stdlib-only minimal xlsx writer，避免依赖 openpyxl
        from parsers.xlsx_minimal_writer import write_table_workbook

        geometry_rows = [{
            "L": self.geom_inputs['L'].value(),
            "H": self.geom_inputs['H'].value(),
            "Tw": self.geom_inputs['Tw'].value(),
            "bf_lu": self.geom_inputs['bf_lu'].value(),
            "tf_lu": self.geom_inputs['tf_lu'].value(),
            "bf_ru": self.geom_inputs['bf_ru'].value(),
            "tf_ru": self.geom_inputs['tf_ru'].value(),
            "bf_ll": self.geom_inputs['bf_ll'].value(),
            "tf_ll": self.geom_inputs['tf_ll'].value(),
            "bf_rl": self.geom_inputs['bf_rl'].value(),
            "tf_rl": self.geom_inputs['tf_rl'].value(),
            "h_pre": self.geom_inputs['h_pre'].value(),
            "t_cast_cap": self.geom_inputs['t_cast_cap'].value() if ('t_cast_cap' in self.geom_inputs) else 0.0,
        }]

        top_dia = self.rebar_inputs['top_dia'].value()
        top_num = self.rebar_inputs['top_num'].value()
        left_support_dia = int(self.rebar_inputs.get('left_support_top_dia').value() if self.rebar_inputs.get('left_support_top_dia') else 0)
        left_support_num = int(self.rebar_inputs.get('left_support_top_num').value() if self.rebar_inputs.get('left_support_top_num') else 0)
        left_support_len = float(self.rebar_inputs.get('left_support_length').value() if self.rebar_inputs.get('left_support_length') else 0.0)
        right_support_dia = int(self.rebar_inputs.get('right_support_top_dia').value() if self.rebar_inputs.get('right_support_top_dia') else 0)
        right_support_num = int(self.rebar_inputs.get('right_support_top_num').value() if self.rebar_inputs.get('right_support_top_num') else 0)
        right_support_len = float(self.rebar_inputs.get('right_support_length').value() if self.rebar_inputs.get('right_support_length') else 0.0)
        bottom_dia = self.rebar_inputs['bottom_dia'].value()
        bottom_num = self.rebar_inputs['bottom_num'].value()
        top_rows = int(self.rebar_inputs.get('top_rows').value() if self.rebar_inputs.get('top_rows') else 1)
        top_row_spacing = float(self.rebar_inputs.get('top_row_spacing').value() if self.rebar_inputs.get('top_row_spacing') else 0.0)
        bottom_rows = int(self.rebar_inputs.get('bottom_rows').value() if self.rebar_inputs.get('bottom_rows') else 1)
        bottom_row_spacing = float(self.rebar_inputs.get('bottom_row_spacing').value() if self.rebar_inputs.get('bottom_row_spacing') else 0.0)
        rebar_rows = [
            # 顶部通长筋（全跨）
            {"Position": "Top Through", "Diameter_A": top_dia, "Count_A": top_num, "Diameter_B": 0, "Count_B": 0, "Extend_Length": 0},
            # 支座附加筋（可选；Extend_Length 作为支座区长度）
            {"Position": "Left Support Top", "Diameter_A": left_support_dia, "Count_A": left_support_num, "Diameter_B": 0, "Count_B": 0, "Extend_Length": left_support_len},
            {"Position": "Right Support Top", "Diameter_A": right_support_dia, "Count_A": right_support_num, "Diameter_B": 0, "Count_B": 0, "Extend_Length": right_support_len},
            # 底部通长筋
            {"Position": "Bottom Through", "Diameter_A": bottom_dia, "Count_A": bottom_num, "Diameter_B": 0, "Count_B": 0, "Extend_Length": 0},
        ]

        longitudinal_layout_rows = [
            {"Group": "Top", "Rows": top_rows, "RowSpacing": top_row_spacing},
            {"Group": "Bottom", "Rows": bottom_rows, "RowSpacing": bottom_row_spacing},
        ]

        stirrup_dia = self.stirrup_inputs['stirrup_dia'].value()
        dense_spacing = self.stirrup_inputs['stirrup_dense_spacing'].value()
        normal_spacing = self.stirrup_inputs['stirrup_normal_spacing'].value()
        dense_length = self.stirrup_inputs['stirrup_dense_length'].value()
        stirrup_rows = [
            {"Zone": "Dense", "Spacing": dense_spacing, "Legs": 4, "Diameter": stirrup_dia, "Length": dense_length, "Cover": 25},
            {"Zone": "Normal", "Spacing": normal_spacing, "Legs": 2, "Diameter": stirrup_dia, "Length": 0, "Cover": 25},
        ]

        def _hole_enabled(idx: int) -> bool:
            if idx == 1:
                return True
            w = self.hole_inputs.get(f"hole{idx}_enabled")
            if not w:
                return False
            return str(w.currentText()).strip() == "启用"

        def _hole_fillet_radius(idx: int) -> float:
            enable = self.hole_inputs.get(f"fillet{idx}_enabled")
            radius = self.hole_inputs.get(f"fillet{idx}_radius")
            if enable is None or radius is None:
                return 0.0
            if str(enable.currentText()).strip() != "启用":
                return 0.0
            return float(radius.value())
        holes_rows = []
        for idx in (1, 2, 3):
            if not _hole_enabled(idx):
                continue
            hx = self.hole_inputs.get(f"hole{idx}_x").value()
            hz = self.hole_inputs.get(f"hole{idx}_z").value()
            hw = self.hole_inputs.get(f"hole{idx}_width").value()
            hh = self.hole_inputs.get(f"hole{idx}_height").value()
            if hw <= 0 or hh <= 0:
                continue
            sb_long_top_dia = int(self.hole_inputs.get(f"hole{idx}_smallbeam_long_top_dia").value() if self.hole_inputs.get(f"hole{idx}_smallbeam_long_top_dia") else 0)
            sb_long_top_count = int(self.hole_inputs.get(f"hole{idx}_smallbeam_long_top_count").value() if self.hole_inputs.get(f"hole{idx}_smallbeam_long_top_count") else 0)
            sb_long_bottom_dia = int(self.hole_inputs.get(f"hole{idx}_smallbeam_long_bottom_dia").value() if self.hole_inputs.get(f"hole{idx}_smallbeam_long_bottom_dia") else 0)
            sb_long_bottom_count = int(self.hole_inputs.get(f"hole{idx}_smallbeam_long_bottom_count").value() if self.hole_inputs.get(f"hole{idx}_smallbeam_long_bottom_count") else 0)
            sb_stirrup_dia = int(self.hole_inputs.get(f"hole{idx}_smallbeam_stirrup_dia").value() if self.hole_inputs.get(f"hole{idx}_smallbeam_stirrup_dia") else 0)
            sb_stirrup_spacing = int(self.hole_inputs.get(f"hole{idx}_smallbeam_stirrup_spacing").value() if self.hole_inputs.get(f"hole{idx}_smallbeam_stirrup_spacing") else 0)
            sb_stirrup_legs = int(self.hole_inputs.get(f"hole{idx}_smallbeam_stirrup_legs").value() if self.hole_inputs.get(f"hole{idx}_smallbeam_stirrup_legs") else 0)
            left_reinf = int(self.hole_inputs.get(f"hole{idx}_left_reinf_length").value() if self.hole_inputs.get(f"hole{idx}_left_reinf_length") else 0)
            right_reinf = int(self.hole_inputs.get(f"hole{idx}_right_reinf_length").value() if self.hole_inputs.get(f"hole{idx}_right_reinf_length") else 0)
            side_spacing = int(self.hole_inputs.get(f"hole{idx}_side_stirrup_spacing").value() if self.hole_inputs.get(f"hole{idx}_side_stirrup_spacing") else 0)
            side_dia = int(self.hole_inputs.get(f"hole{idx}_side_stirrup_dia").value() if self.hole_inputs.get(f"hole{idx}_side_stirrup_dia") else 0)
            side_legs = int(self.hole_inputs.get(f"hole{idx}_side_stirrup_legs").value() if self.hole_inputs.get(f"hole{idx}_side_stirrup_legs") else 0)
            reinf_extend = int(self.hole_inputs.get(f"hole{idx}_reinf_extend_length").value() if self.hole_inputs.get(f"hole{idx}_reinf_extend_length") else 0)
            holes_rows.append({
                "X": hx, "Z": hz, "Width": hw, "Height": hh, "Fillet_Radius": _hole_fillet_radius(idx),
                # 兼容旧字段：不区分顶/底时，只能表达一套（这里写入顶部值）
                "SmallBeam_Long_Diameter": sb_long_top_dia, "SmallBeam_Long_Count": sb_long_top_count,
                "SmallBeam_Long_Top_Diameter": sb_long_top_dia, "SmallBeam_Long_Top_Count": sb_long_top_count,
                "SmallBeam_Long_Bottom_Diameter": sb_long_bottom_dia, "SmallBeam_Long_Bottom_Count": sb_long_bottom_count,
                "SmallBeam_Stirrup_Diameter": sb_stirrup_dia, "SmallBeam_Stirrup_Spacing": sb_stirrup_spacing,
                "SmallBeam_Stirrup_Legs": sb_stirrup_legs,
                "Left_Reinf_Length": left_reinf, "Right_Reinf_Length": right_reinf,
                "Side_Stirrup_Spacing": side_spacing, "Side_Stirrup_Diameter": side_dia, "Side_Stirrup_Legs": side_legs,
                "Reinf_Extend_Length": reinf_extend,
            })

        beam_length = self.geom_inputs['L'].value()
        dead_load_val = self.load_inputs.get('dead_load', None)
        dead_load = -abs(dead_load_val.value()) if dead_load_val else -15.0
        live_load_val = self.load_inputs.get('live_load', None)
        live_load = -abs(live_load_val.value()) if live_load_val else -20.0
        loads_rows = [
            {"Case": "Dead Load", "Stage": "Construction", "Type": "Distributed", "X": None, "X1": 0, "X2": beam_length, "Direction": "Z", "Magnitude": dead_load},
            {"Case": "Dead Load", "Stage": "Service", "Type": "Distributed", "X": None, "X1": 0, "X2": beam_length, "Direction": "Z", "Magnitude": dead_load},
            {"Case": "Live Load", "Stage": "Service", "Type": "Distributed", "X": None, "X1": 0, "X2": beam_length, "Direction": "Z", "Magnitude": live_load},
        ]

        prestress_enabled = (self.prestress_inputs['enabled'].currentText() == "启用")
        prestress_force = self.prestress_inputs['force'].value()
        duct_diameter = self.prestress_inputs['duct_diameter'].value()
        method_text = str(self.prestress_inputs.get('method').currentText() if self.prestress_inputs.get('method') else "后张法(post_tension)")
        prestress_method = "pretension" if ("pretension" in method_text) else "post_tension"
        if prestress_method == "pretension":
            duct_diameter = 0.0
        prestress_rows = [
            {"Parameter": "Enabled", "Value": str(prestress_enabled)},
            {"Parameter": "Method", "Value": prestress_method},
            {"Parameter": "Force", "Value": prestress_force if prestress_enabled else 0},
            {"Parameter": "Duct_Diameter", "Value": duct_diameter if prestress_enabled else 0},
            {"Parameter": "Path_Type", "Value": "straight"},
        ]

        boundary_rows = [
            {"End": "Left", "Dx": "Fixed", "Dy": "Fixed", "Dz": "Fixed", "Rx": "Free", "Ry": "Free", "Rz": "Free", "N": 0, "Vy": 0, "Vz": 0, "Mx": 0, "My": 0, "Mz": 0},
            {"End": "Right", "Dx": "Free", "Dy": "Fixed", "Dz": "Fixed", "Rx": "Free", "Ry": "Free", "Rz": "Free", "N": 0, "Vy": 0, "Vz": 0, "Mx": 0, "My": 0, "Mz": 0},
        ]

        write_table_workbook(
            excel_path,
            {
                "Geometry": geometry_rows,
                "Longitudinal Rebar": rebar_rows,
                "Longitudinal Layout": longitudinal_layout_rows,
                "Stirrups": stirrup_rows,
                "Holes": holes_rows,
                "Loads": loads_rows,
                "Prestress": prestress_rows,
                "Boundary": boundary_rows,
            },
        )
        return excel_path

    def generate_model(self):
        """生成模型 - 真实引擎调用"""
        if not ENGINE_AVAILABLE:
            QMessageBox.critical(self, "错误", "主引擎模块未加载！\n请确保 main.py 和 core/ 模块完整。")
            return

        try:
            self.log_text.clear()
            self.log_text.append("="*50)
            self.log_text.append(">>> 开始生成 PKPM-CAE 叠合梁模型...")
            self.log_text.append("="*50)

            # 1) 优先使用用户选择的 Excel；若未选择，则从 UI 参数生成临时 Excel
            input_excel = None
            self._temp_excel_to_cleanup = None
            # EXE(onefile) 模式下，避免写入 _MEIPASS 临时目录导致用户找不到输出
            output_dir = current_dir
            if hasattr(sys, "_MEIPASS"):
                try:
                    output_dir = os.path.dirname(os.path.abspath(sys.executable))
                except Exception:
                    output_dir = os.getcwd()
            if self.excel_path and os.path.isfile(self.excel_path):
                input_excel = self.excel_path
                self.log_text.append(f">>> 使用 Excel 参数文件: {Path(input_excel).name}")
            else:
                temp_excel = os.path.join(output_dir, "temp_ui_params.xlsx")
                self.log_text.append(f">>> 未选择 Excel，使用 UI 参数生成临时文件: {Path(temp_excel).name}")
                self._save_ui_params_to_excel(temp_excel)
                self._temp_excel_to_cleanup = temp_excel
                input_excel = temp_excel
                self.log_text.append(">>> ✓ 临时参数文件已生成")

            # 创建并启动后台线程
            self.log_text.append(">>> 启动模型生成引擎...")
            output_script = "pkpm_composite_beam_model.py"
            if self._temp_excel_to_cleanup:
                # UI 参数模式：固定输出到 exe 所在目录（或源码目录）
                output_script = os.path.join(output_dir, "pkpm_composite_beam_model.py")
            self.generation_thread = ModelGenerationThread(input_excel, output_script=output_script)
            self.generation_thread.progress.connect(self._on_generation_progress)
            self.generation_thread.finished.connect(self._on_generation_finished)
            self.generation_thread.start()

        except Exception as e:
            import traceback
            self.log_text.append(f">>> ❌ 错误: {str(e)}")
            self.log_text.append(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"模型生成失败:\n{str(e)}")

    def _on_generation_progress(self, message):
        """处理生成进度更新"""
        self.log_text.append(f">>> {message}")

    def _on_generation_finished(self, success, message):
        """处理生成完成"""
        import os

        self.log_text.append("="*50)
        self.log_text.append(f">>> {message}")
        self.log_text.append("="*50)

        # 清理临时文件（仅当本次生成由 UI 参数自动生成）
        temp_excel = self._temp_excel_to_cleanup
        self._temp_excel_to_cleanup = None
        if temp_excel and os.path.exists(temp_excel):
            try:
                os.remove(temp_excel)
                self.log_text.append(f">>> ✓ 已清理临时文件: {temp_excel}")
            except Exception as e:
                self.log_text.append(f">>> ⚠ 临时文件清理失败: {e}")

        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "错误", message)


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序字体
    app_font = QFont("Microsoft YaHei", 10)
    app.setFont(app_font)

    window = CompositeBeamUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
