"""
圆弧倒角（Fillet）几何切削处理器
T+7 新增功能 - 对洞口四角进行圆弧倒角处理

功能说明:
- 接收矩形洞口参数和倒角半径
- 生成四角圆弧切削的几何命令
- 确保倒角半径不超过洞口尺寸限制
- 生成符合 PKPM-CAE Python API 的 Fillet 命令
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class FilletConfig:
    """圆弧倒角配置参数"""
    enabled: bool = False
    radius: float = 50.0  # 默认倒角半径 50mm

    def validate(self, hole_width: float, hole_height: float) -> bool:
        """
        验证倒角半径是否合理

        Args:
            hole_width: 洞口宽度
            hole_height: 洞口高度

        Returns:
            True 如果参数合法，否则 False
        """
        if not self.enabled:
            return True

        if self.radius <= 0:
            return False

        # 倒角半径不能超过洞口尺寸的一半
        max_radius = min(hole_width, hole_height) / 2
        if self.radius > max_radius:
            return False

        return True


class FilletProcessor:
    """圆弧倒角处理器

    对矩形洞口的四个直角进行圆弧倒角处理
    """

    def __init__(self, config: FilletConfig):
        """
        初始化倒角处理器

        Args:
            config: 倒角配置参数
        """
        self.config = config

    def calculate_fillet_points(
        self,
        x: float,
        z: float,
        width: float,
        height: float
    ) -> Dict[str, List[Tuple[float, float]]]:
        """
        计算四角圆弧倒角的关键点坐标

        Args:
            x: 洞口左下角 X 坐标
            z: 洞口左下角 Z 坐标
            width: 洞口宽度
            height: 洞口高度

        Returns:
            包含四个角的圆弧关键点字典
            {
                'bottom_left': [(x1, z1), (x2, z2), ...],
                'bottom_right': [...],
                'top_left': [...],
                'top_right': [...]
            }
        """
        if not self.config.enabled:
            return {}

        r = self.config.radius

        # 四个角的圆心坐标
        corners = {
            'bottom_left': (x + r, z + r),
            'bottom_right': (x + width - r, z + r),
            'top_left': (x + r, z + height - r),
            'top_right': (x + width - r, z + height - r)
        }

        # 生成圆弧离散点（每个角 9 个点，包括起点和终点）
        fillet_points = {}
        num_points = 9

        for corner_name, (cx, cz) in corners.items():
            points = []

            # 根据角的位置确定起始角度和终止角度
            if corner_name == 'bottom_left':
                start_angle = math.pi  # 180°
                end_angle = 3 * math.pi / 2  # 270°
            elif corner_name == 'bottom_right':
                start_angle = 3 * math.pi / 2  # 270°
                end_angle = 2 * math.pi  # 360°
            elif corner_name == 'top_left':
                start_angle = math.pi / 2  # 90°
                end_angle = math.pi  # 180°
            else:  # top_right
                start_angle = 0  # 0°
                end_angle = math.pi / 2  # 90°

            # 生成圆弧上的离散点
            for i in range(num_points):
                t = i / (num_points - 1)
                angle = start_angle + t * (end_angle - start_angle)
                px = cx + r * math.cos(angle)
                pz = cz + r * math.sin(angle)
                points.append((px, pz))

            fillet_points[corner_name] = points

        return fillet_points

    def generate_fillet_boundary(
        self,
        x: float,
        z: float,
        width: float,
        height: float
    ) -> List[Tuple[float, float]]:
        """
        生成带圆角的洞口边界点序列（逆时针）

        Args:
            x: 洞口左下角 X 坐标
            z: 洞口左下角 Z 坐标
            width: 洞口宽度
            height: 洞口高度

        Returns:
            边界点坐标列表 [(x1, z1), (x2, z2), ...]
        """
        if not self.config.enabled:
            # 无倒角时返回矩形四个角点
            return [
                (x, z),
                (x + width, z),
                (x + width, z + height),
                (x, z + height)
            ]

        r = self.config.radius
        boundary = []

        # 获取四角圆弧点
        fillet_points = self.calculate_fillet_points(x, z, width, height)

        # 按逆时针顺序组装边界
        # 1. 底边左端 → 左下角圆弧 → 底边右端
        boundary.append((x + r, z))  # 底边左端
        boundary.extend(fillet_points['bottom_left'])  # 左下角圆弧
        boundary.append((x + width - r, z))  # 底边右端

        # 2. 右下角圆弧 → 右边
        boundary.extend(fillet_points['bottom_right'])  # 右下角圆弧
        boundary.append((x + width, z + height - r))  # 右边下端

        # 3. 右上角圆弧 → 顶边
        boundary.extend(fillet_points['top_right'])  # 右上角圆弧
        boundary.append((x + width - r, z + height))  # 顶边右端

        # 4. 左上角圆弧 → 左边
        boundary.extend(fillet_points['top_left'])  # 左上角圆弧
        boundary.append((x, z + height - r))  # 左边上端

        return boundary

    def generate_pkpm_fillet_commands(
        self,
        hole_solid_id: int,
        x: float,
        z: float,
        width: float,
        height: float
    ) -> List[str]:
        """
        生成 PKPM-CAE Python API 的 Fillet 命令

        Args:
            hole_solid_id: 洞口实体 ID
            x: 洞口左下角 X 坐标
            z: 洞口左下角 Z 坐标
            width: 洞口宽度
            height: 洞口高度

        Returns:
            Python 代码命令列表
        """
        if not self.config.enabled:
            return []

        commands = []
        r = self.config.radius

        # 生成倒角命令注释
        commands.append(f"# 对洞口实体 {hole_solid_id} 进行圆弧倒角 (R={r}mm)")

        # PKPM-CAE 中的 Fillet 命令示例（根据实际 API 调整）
        # 假设 API 格式: solid.fillet(edge_id, radius)

        # 四条边的 ID（需要根据实际 API 获取边 ID 的方式）
        # 这里采用伪代码形式，实际使用时需要查询 PKPM-CAE API 文档
        commands.append(f"""
# 获取洞口四条边
edges = model.get_edges_of_solid({hole_solid_id})

# 对四个角进行倒角
for edge in edges:
    if edge.is_corner_edge():  # 判断是否为角边
        model.fillet(edge.id, radius={r})
""")

        # 备选方案：如果 API 不支持 Fillet，则通过布尔运算实现
        commands.append(f"""
# 备选方案：通过圆柱布尔运算实现倒角
# 在四个角创建 1/4 圆柱并进行布尔减运算
fillet_cylinders = []

# 左下角
cyl1 = model.create_cylinder(center=({x + r}, 0, {z + r}),
                             radius={r}, height={width},
                             axis='Y')
fillet_cylinders.append(cyl1)

# 右下角
cyl2 = model.create_cylinder(center=({x + width - r}, 0, {z + r}),
                             radius={r}, height={width},
                             axis='Y')
fillet_cylinders.append(cyl2)

# 左上角
cyl3 = model.create_cylinder(center=({x + r}, 0, {z + height - r}),
                             radius={r}, height={width},
                             axis='Y')
fillet_cylinders.append(cyl3)

# 右上角
cyl4 = model.create_cylinder(center=({x + width - r}, 0, {z + height - r}),
                             radius={r}, height={width},
                             axis='Y')
fillet_cylinders.append(cyl4)

# 对洞口实体进行布尔加运算
for cyl in fillet_cylinders:
    hole_solid_{hole_solid_id} = model.boolean_union(hole_solid_{hole_solid_id}, cyl)
""")

        return commands

    def apply_fillet_to_hole(
        self,
        hole_params: Dict[str, float],
        beam_solid_id: int
    ) -> Dict[str, any]:
        """
        对洞口应用圆弧倒角，并返回处理结果

        Args:
            hole_params: 洞口参数字典 {'x', 'z', 'width', 'height'}
            beam_solid_id: 梁实体 ID

        Returns:
            处理结果字典
            {
                'success': bool,
                'boundary': List[Tuple[float, float]],
                'commands': List[str],
                'message': str
            }
        """
        x = hole_params['x']
        z = hole_params['z']
        width = hole_params['width']
        height = hole_params['height']

        # 验证参数
        if not self.config.validate(width, height):
            return {
                'success': False,
                'boundary': [],
                'commands': [],
                'message': f'倒角半径 {self.config.radius}mm 超过洞口尺寸限制'
            }

        # 生成倒角边界
        boundary = self.generate_fillet_boundary(x, z, width, height)

        # 生成 PKPM 命令（预留）
        commands = []  # self.generate_pkpm_fillet_commands(hole_id, x, z, width, height)

        return {
            'success': True,
            'boundary': boundary,
            'commands': commands,
            'message': f'✓ 圆弧倒角已应用 (R={self.config.radius}mm)'
        }


def demo_fillet_usage():
    """演示圆弧倒角功能的使用"""
    print("="*60)
    print("圆弧倒角（Fillet）处理器 - 功能演示")
    print("="*60)

    # 创建倒角配置
    config = FilletConfig(enabled=True, radius=50.0)

    # 创建处理器
    processor = FilletProcessor(config)

    # 洞口参数
    hole_params = {
        'x': 2000,
        'z': 100,
        'width': 800,
        'height': 300
    }

    # 应用倒角
    result = processor.apply_fillet_to_hole(hole_params, beam_solid_id=1)

    print(f"\n处理结果: {result['message']}")
    print(f"边界点数: {len(result['boundary'])}")

    # 输出边界点（前5个和后5个）
    print("\n边界点坐标（示例）:")
    for i, (px, pz) in enumerate(result['boundary'][:5]):
        print(f"  点 {i+1}: ({px:.2f}, {pz:.2f})")
    print("  ...")
    for i, (px, pz) in enumerate(result['boundary'][-5:]):
        print(f"  点 {len(result['boundary'])-4+i}: ({px:.2f}, {pz:.2f})")

    print("\n" + "="*60)


if __name__ == "__main__":
    demo_fillet_usage()
