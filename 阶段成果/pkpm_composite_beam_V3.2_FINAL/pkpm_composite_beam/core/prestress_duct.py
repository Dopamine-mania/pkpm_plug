"""
预应力波纹管孔道生成模块
实现后张法预应力波纹管在预制层中的几何切削

核心功能：
1. 根据孔道路径生成圆柱体（波纹管）
2. 通过布尔减运算从预制层中挖除波纹管孔道
3. 支持直线路径和抛物线路径
"""

import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from core.parameters import PrestressParams


@dataclass
class DuctSegment:
    """波纹管孔道段（圆柱体）"""
    center: Tuple[float, float, float]  # 圆心坐标 (x, y, z)
    radius: float                        # 半径 (mm)
    height: float                        # 高度/长度 (mm)
    direction: Tuple[float, float, float]  # 方向向量


class PrestressDuctGenerator:
    """预应力波纹管孔道生成器

    后张法逻辑：
    - 施工阶段（Step 1）：波纹管孔道已预留，但预应力筋未张拉
    - 使用阶段（Step 2）：预应力筋张拉，施加预应力
    """

    def __init__(self, prestress_params: PrestressParams):
        """
        初始化波纹管生成器

        Args:
            prestress_params: 预应力参数
        """
        self.params = prestress_params
        self.duct_segments: List[DuctSegment] = []

    def generate_straight_duct_path(
        self,
        start_point: Tuple[float, float, float],
        end_point: Tuple[float, float, float],
        num_segments: int = 10
    ) -> List[Tuple[float, float, float]]:
        """
        生成直线孔道路径

        Args:
            start_point: 起点坐标 (x, y, z)
            end_point: 终点坐标 (x, y, z)
            num_segments: 分段数

        Returns:
            路径点坐标列表
        """
        path = []
        for i in range(num_segments + 1):
            t = i / num_segments
            x = start_point[0] + t * (end_point[0] - start_point[0])
            y = start_point[1] + t * (end_point[1] - start_point[1])
            z = start_point[2] + t * (end_point[2] - start_point[2])
            path.append((x, y, z))
        return path

    def generate_parabolic_duct_path(
        self,
        start_point: Tuple[float, float, float],
        end_point: Tuple[float, float, float],
        sag: float,
        num_segments: int = 20
    ) -> List[Tuple[float, float, float]]:
        """
        生成抛物线孔道路径（适用于连续梁）

        Args:
            start_point: 起点坐标 (x, y, z)
            end_point: 终点坐标 (x, y, z)
            sag: 垂度/矢高 (mm) - 中点相对于起终点连线的偏移
            num_segments: 分段数

        Returns:
            路径点坐标列表
        """
        path = []
        L = end_point[0] - start_point[0]  # 跨度

        for i in range(num_segments + 1):
            t = i / num_segments
            x = start_point[0] + t * L

            # 抛物线方程: y = 4*sag/L^2 * x * (L-x)
            # 归一化到 [0, 1]
            local_x = t * L
            z_offset = 4 * sag / (L ** 2) * local_x * (L - local_x)

            y = start_point[1] + t * (end_point[1] - start_point[1])
            z = start_point[2] + t * (end_point[2] - start_point[2]) + z_offset

            path.append((x, y, z))

        return path

    def create_duct_cylinders_from_path(
        self,
        path: List[Tuple[float, float, float]]
    ) -> List[DuctSegment]:
        """
        根据孔道路径创建圆柱体段列表

        Args:
            path: 孔道路径点列表

        Returns:
            波纹管孔道段列表
        """
        if len(path) < 2:
            raise ValueError("孔道路径至少需要2个点")

        segments = []
        radius = self.params.duct_diameter / 2

        for i in range(len(path) - 1):
            p1 = path[i]
            p2 = path[i + 1]

            # 计算段中心点
            center_x = (p1[0] + p2[0]) / 2
            center_y = (p1[1] + p2[1]) / 2
            center_z = (p1[2] + p2[2]) / 2

            # 计算段长度
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dz = p2[2] - p1[2]
            length = math.sqrt(dx**2 + dy**2 + dz**2)

            # 计算方向向量（单位化）
            if length > 1e-6:
                direction = (dx/length, dy/length, dz/length)
            else:
                direction = (1, 0, 0)  # 默认X方向

            segment = DuctSegment(
                center=(center_x, center_y, center_z),
                radius=radius,
                height=length,
                direction=direction
            )
            segments.append(segment)

        self.duct_segments = segments
        return segments

    def generate_pkpm_duct_commands(
        self,
        precast_solid_id: int,
        path: Optional[List[Tuple[float, float, float]]] = None
    ) -> List[str]:
        """
        生成 PKPM-CAE Python API 的波纹管孔道切削命令

        Args:
            precast_solid_id: 预制层实体 ID
            path: 孔道路径（如不提供则使用 params.duct_path）

        Returns:
            Python 代码命令列表
        """
        if not self.params.enabled:
            return []

        if path is None:
            path = self.params.duct_path

        if not path or len(path) < 2:
            return ["# 警告：预应力孔道路径为空，跳过波纹管生成"]

        # 创建孔道段
        segments = self.create_duct_cylinders_from_path(path)

        commands = []
        commands.append(f"# ========== 预应力波纹管孔道生成 ==========")
        commands.append(f"# 波纹管直径: {self.params.duct_diameter} mm")
        commands.append(f"# 孔道路径点数: {len(path)}")
        commands.append(f"# 孔道分段数: {len(segments)}")
        commands.append("")

        # 生成圆柱体创建命令
        commands.append("# 创建波纹管孔道圆柱体")
        commands.append("duct_cylinders = []")

        for i, seg in enumerate(segments):
            cx, cy, cz = seg.center
            dx, dy, dz = seg.direction

            # PKPM-CAE API 示例（实际使用时需根据真实API调整）
            commands.append(f"""
# 孔道段 {i+1}
cyl_{i} = model.create_cylinder(
    center=({cx:.2f}, {cy:.2f}, {cz:.2f}),
    radius={seg.radius:.2f},
    height={seg.height:.2f},
    direction=({dx:.4f}, {dy:.4f}, {dz:.4f})
)
duct_cylinders.append(cyl_{i})
""")

        # 生成布尔减运算命令
        commands.append("")
        commands.append("# 从预制层中挖除波纹管孔道（布尔减运算）")
        commands.append(f"precast_solid_with_duct = precast_solid_{precast_solid_id}")
        commands.append("for cyl in duct_cylinders:")
        commands.append("    precast_solid_with_duct = model.boolean_subtract(")
        commands.append("        precast_solid_with_duct, cyl")
        commands.append("    )")

        commands.append("")
        commands.append(f"# 更新预制层实体 ID")
        commands.append(f"precast_solid_{precast_solid_id} = precast_solid_with_duct")

        return commands

    def validate_duct_path(
        self,
        path: List[Tuple[float, float, float]],
        beam_geometry: Dict
    ) -> Dict[str, any]:
        """
        验证孔道路径是否合理

        Args:
            path: 孔道路径
            beam_geometry: 梁几何参数字典 {'L', 'H', 'h_pre'}

        Returns:
            验证结果字典
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        errors = []
        warnings = []

        # 检查路径点数
        if len(path) < 2:
            errors.append("孔道路径至少需要2个点")

        # 检查是否超出梁长范围
        for i, (x, y, z) in enumerate(path):
            if x < 0 or x > beam_geometry['L']:
                errors.append(f"路径点 {i+1} X 坐标 {x} 超出梁长范围 [0, {beam_geometry['L']}]")

            # 检查Z坐标是否在预制层内
            if z < 0 or z > beam_geometry['h_pre']:
                warnings.append(f"路径点 {i+1} Z 坐标 {z} 超出预制层范围 [0, {beam_geometry['h_pre']}]")

        # 检查波纹管直径
        min_spacing = 50  # 最小边距 50mm
        if self.params.duct_diameter > beam_geometry['h_pre'] - 2 * min_spacing:
            errors.append(f"波纹管直径 {self.params.duct_diameter} 过大，预制层高度仅 {beam_geometry['h_pre']} mm")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


def demo_prestress_duct():
    """演示预应力波纹管功能"""
    print("="*60)
    print("预应力波纹管孔道生成器 - 功能演示")
    print("="*60)

    # 创建预应力参数
    from core.parameters import PrestressParams

    # 先禁用状态创建参数，稍后启用
    params = PrestressParams(
        enabled=False,  # 先禁用，生成路径后再启用
        force=1000000,  # 1000 kN
        duct_diameter=90,  # 90mm 波纹管
        duct_path=[]
    )

    # 创建生成器
    generator = PrestressDuctGenerator(params)

    # 生成直线孔道路径
    print("\n[1] 生成直线孔道路径")
    start = (500, 0, 250)  # 距左端500mm, Y方向中心, Z方向250mm
    end = (9500, 0, 250)   # 距右端500mm
    path_straight = generator.generate_straight_duct_path(start, end, num_segments=10)
    print(f"  ✓ 直线路径: {len(path_straight)} 个点")
    print(f"  起点: {start}")
    print(f"  终点: {end}")

    # 更新参数启用预应力
    params.enabled = True
    params.duct_path = path_straight

    # 生成抛物线孔道路径
    print("\n[2] 生成抛物线孔道路径")
    path_parabolic = generator.generate_parabolic_duct_path(
        start, end, sag=200, num_segments=20
    )
    print(f"  ✓ 抛物线路径: {len(path_parabolic)} 个点")
    print(f"  垂度: 200 mm")

    # 创建孔道圆柱体段
    print("\n[3] 创建孔道圆柱体段")
    segments = generator.create_duct_cylinders_from_path(path_straight)
    print(f"  ✓ 圆柱体段数: {len(segments)}")
    print(f"  波纹管直径: {params.duct_diameter} mm")

    # 验证孔道路径
    print("\n[4] 验证孔道路径")
    beam_geom = {'L': 10000, 'H': 800, 'h_pre': 500}
    result = generator.validate_duct_path(path_straight, beam_geom)
    print(f"  验证结果: {'✓ 通过' if result['valid'] else '✗ 失败'}")
    if result['errors']:
        print(f"  错误: {result['errors']}")
    if result['warnings']:
        print(f"  警告: {result['warnings']}")

    # 生成 PKPM 命令
    print("\n[5] 生成 PKPM-CAE 命令")
    commands = generator.generate_pkpm_duct_commands(
        precast_solid_id=1,
        path=path_straight
    )
    print(f"  ✓ 生成命令行数: {len(commands)}")
    print("\n  命令示例（前10行）:")
    for cmd in commands[:10]:
        print(f"    {cmd}")

    print("\n" + "="*60)


if __name__ == "__main__":
    demo_prestress_duct()
