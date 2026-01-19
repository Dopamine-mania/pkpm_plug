"""
PyInstaller 一键打包脚本 - 生成免安装绿色版可执行文件
"""
import os
import sys
import shutil

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 60)
print("  PKPM-CAE 叠合梁建模工具 - PyInstaller 打包")
print("=" * 60)
print()

# 检查 PyInstaller 是否安装
try:
    import PyInstaller
    print("✓ PyInstaller 已安装")
except ImportError:
    print("❌ PyInstaller 未安装！")
    print()
    print("正在安装 PyInstaller...")
    os.system("pip install pyinstaller")
    print()

# 清理旧的打包文件
def safe_rmtree(path):
    """安全删除目录，处理文件占用情况"""
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            print(f"清理旧的 {path}/ 目录...")
        except PermissionError:
            print(f"⚠ 无法删除 {path}/（文件可能被占用），将覆盖打包...")

safe_rmtree("build")
safe_rmtree("dist")

for spec_file in ["ui_main_pro.spec", "PKPM叠合梁工具.spec"]:
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
            print(f"清理旧的 {spec_file} 文件...")
        except:
            pass

print()
print("=" * 60)
print("  开始打包...")
print("=" * 60)
print()

# PyInstaller 打包命令
# --onefile: 打包成单个可执行文件
# --windowed: 不显示控制台窗口（GUI程序）
# --name: 可执行文件名称
# --hidden-import: 显式包含动态导入的模块

# 构建隐藏导入参数（PyInstaller无法自动检测的动态导入模块）
hidden_imports = [
    "main",
    "core",
    "core.geometry_engine_ibeam",
    "core.geometry_engine_simple",
    "core.rebar_engine",
    "core.analysis_config",
    "core.prestress_duct",
    "core.fillet_processor",
    "core.parameters",
    "parsers",
    "parsers.excel_parser",
]

hidden_import_args = " ".join([f'--hidden-import="{m}"' for m in hidden_imports])

# 添加数据目录（core/ 和 parsers/ 目录需要包含在打包中）
add_data_args = '--add-data="core;core" --add-data="parsers;parsers" --add-data="main.py;."'

cmd = f'pyinstaller --onefile --windowed --name="PKPM叠合梁工具" {hidden_import_args} {add_data_args} ui_main_pro.py'

print(f"执行命令: {cmd}")
print()

result = os.system(cmd)

print()
print("=" * 60)

if result == 0:
    print("  ✅ 打包成功！")
    print("=" * 60)
    print()
    print("可执行文件位置:")
    print("  dist/PKPM叠合梁工具.exe")
    print()
    print("使用方式:")
    print("  1. 将 dist/PKPM叠合梁工具.exe 复制到任意电脑")
    print("  2. 双击运行，无需安装 Python 环境")
    print("  3. 可执行文件大小约 50-80 MB")
    print()
else:
    print("  ❌ 打包失败！")
    print("=" * 60)
    print()
    print("常见问题:")
    print("  1. 检查 Python 环境是否正确配置")
    print("  2. 确保所有依赖库已安装（运行 安装依赖.bat）")
    print("  3. 检查 ui_main_pro.py 文件是否存在")
    print()

print("=" * 60)
