"""
PKPM-CAE 叠合梁参数化建模 - 参数数据类定义
定义所有建模所需的参数数据结构
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple


@dataclass
class GeometryParams:
    """几何截面参数 (Excel Sheet 1: Geometry)"""
    L: float              # 梁总长度 (mm)
    H: float              # 梁总高度 (mm)
    Tw: float             # 腹板厚度 (mm)

    # 上翼缘（左右可不对称）
    bf_lu: float          # 左上翼缘宽 (mm)
    tf_lu: float          # 左上翼缘厚 (mm)
    bf_ru: float          # 右上翼缘宽 (mm)
    tf_ru: float          # 右上翼缘厚 (mm)

    # 下翼缘（左右可不对称）
    bf_ll: float          # 左下翼缘宽 (mm)
    tf_ll: float          # 左下翼缘厚 (mm)
    bf_rl: float          # 右下翼缘宽 (mm)
    tf_rl: float          # 右下翼缘厚 (mm)

    # 叠合层
    h_pre: float          # 预制层高度 (mm)
    # 现浇顶盖厚度 (mm)：0=自动/不强制；>0 则在上翼缘内部切分叠合面（推荐用于“叠合面在上翼缘范围”）
    t_cast_cap: float = 0.0

    def __post_init__(self):
        """参数校验"""
        if self.L <= 0:
            raise ValueError(f"梁长度必须大于0，当前值: {self.L}")
        if self.H <= 0:
            raise ValueError(f"梁高度必须大于0，当前值: {self.H}")
        if self.h_pre < 0:
            raise ValueError(f"预制层高度不能为负，当前值: {self.h_pre}")
        if self.Tw <= 0:
            raise ValueError(f"腹板厚度必须大于0，当前值: {self.Tw}")
        if self.t_cast_cap < 0:
            raise ValueError(f"现浇顶盖厚度不能为负，当前值: {self.t_cast_cap}")

        tf_upper = max(float(self.tf_lu or 0.0), float(self.tf_ru or 0.0))
        if self.t_cast_cap > 0:
            if tf_upper <= 1e-6:
                raise ValueError("仅当存在上翼缘时可设置现浇顶盖厚度(t_cast_cap)")
            if self.t_cast_cap >= tf_upper:
                raise ValueError(f"现浇顶盖厚度必须小于上翼缘厚度 {tf_upper} mm，当前值: {self.t_cast_cap}")
            if self.t_cast_cap >= self.H:
                raise ValueError(f"现浇顶盖厚度必须小于梁高 {self.H} mm，当前值: {self.t_cast_cap}")
        else:
            if self.h_pre <= 0 or self.h_pre >= self.H:
                raise ValueError(f"预制层高度必须在 (0, {self.H}) 范围内，当前值: {self.h_pre}")

    def is_symmetric_top(self) -> bool:
        """判断上翼缘是否对称"""
        return (abs(self.bf_lu - self.bf_ru) < 1e-6 and
                abs(self.tf_lu - self.tf_ru) < 1e-6)

    def is_symmetric_bottom(self) -> bool:
        """判断下翼缘是否对称"""
        return (abs(self.bf_ll - self.bf_rl) < 1e-6 and
                abs(self.tf_ll - self.tf_rl) < 1e-6)

    def is_rectangular(self) -> bool:
        """判断是否退化为矩形截面"""
        return (abs(self.bf_lu - self.Tw / 2) < 1e-6 and
                abs(self.bf_ru - self.Tw / 2) < 1e-6 and
                abs(self.bf_ll - self.Tw / 2) < 1e-6 and
                abs(self.bf_rl - self.Tw / 2) < 1e-6)

    def is_t_shaped(self) -> bool:
        """判断是否为T形截面"""
        return (self.is_rectangular() == False and
                abs(self.bf_ll - self.Tw / 2) < 1e-6 and
                abs(self.bf_rl - self.Tw / 2) < 1e-6)

    def get_web_centerline_offset(self) -> float:
        """
        计算腹板中心线的y方向偏移量

        对于非对称截面（如非对称T梁），腹板可能不在y=0位置
        腹板从 -bf_ll 延伸到 +bf_rl，中心线位于 (bf_rl - bf_ll) / 2

        Returns:
            float: 腹板中心线的y坐标偏移 (mm)

        Examples:
            对称截面: bf_ll=125, bf_rl=125 → offset=0 (居中)
            非对称截面: bf_ll=100, bf_rl=150 → offset=25 (偏右25mm)
        """
        return (self.bf_rl - self.bf_ll) / 2.0


@dataclass
class RebarSpec:
    """钢筋规格"""
    diameter: float       # 直径 (mm)
    count: int           # 根数
    extend_length: float = 0.0  # 延伸长度 (mm)，对于附加筋有效

    def __post_init__(self):
        if self.diameter <= 0:
            raise ValueError(f"钢筋直径必须大于0，当前值: {self.diameter}")
        if self.count <= 0:
            raise ValueError(f"钢筋根数必须大于0，当前值: {self.count}")
        if self.extend_length < 0:
            raise ValueError(f"延伸长度不能为负，当前值: {self.extend_length}")

    def area(self) -> float:
        """计算单根钢筋截面积 (mm²)"""
        import math
        return math.pi * (self.diameter / 2) ** 2


@dataclass
class LongitudinalRebar:
    """纵向配筋参数 (Excel Sheet 2: Longitudinal Rebar)

    支持"主筋 + 附加筋"模式，处理 L/3 截断逻辑
    """
    # 必填字段（没有默认值）
    # 顶部通长筋（全跨）：优先读取 Position="Top Through"，否则兼容旧模板的 "Mid Span Top"
    mid_span_top: RebarSpec
    bottom_through_A: RebarSpec

    # 可选：支座附加筋（左右可不同），用于在支座区叠加配筋便于理解/验收
    left_support_top_A: Optional[RebarSpec] = None
    right_support_top_A: Optional[RebarSpec] = None

    # 可选字段（有默认值）
    left_support_top_B: Optional[RebarSpec] = None
    left_support_length: float = 0.0  # 左支座区长度，默认 L/3
    right_support_top_B: Optional[RebarSpec] = None
    right_support_length: float = 0.0  # 右支座区长度，默认 L/3
    bottom_through_B: Optional[RebarSpec] = None

    # 多排纵筋（沿 Z 方向叠排）
    # 说明：
    # - 该功能用于满足“2排/3排纵筋 + 竖向间距可输入”的需求
    # - 当前策略：对顶部/底部纵筋整体叠排（支座区/跨中区都应用），每排的直径/根数沿用该区的既有设置
    top_rows: int = 1
    top_row_spacing: float = 0.0  # mm，净距（中心距按 dia + spacing 处理）
    bottom_rows: int = 1
    bottom_row_spacing: float = 0.0  # mm，净距（中心距按 dia + spacing 处理）

    def __post_init__(self):
        if self.top_rows < 1:
            raise ValueError(f"顶部纵筋排数必须>=1，当前值: {self.top_rows}")
        if self.bottom_rows < 1:
            raise ValueError(f"底部纵筋排数必须>=1，当前值: {self.bottom_rows}")
        if self.top_row_spacing < 0:
            raise ValueError(f"顶部纵筋竖向间距不能为负，当前值: {self.top_row_spacing}")
        if self.bottom_row_spacing < 0:
            raise ValueError(f"底部纵筋竖向间距不能为负，当前值: {self.bottom_row_spacing}")


@dataclass
class StirrupParams:
    """箍筋参数 (Excel Sheet 3: Stirrups)"""
    # 加密区（梁端）
    dense_zone_length: float    # 加密区长度 (mm)
    dense_spacing: float        # 加密区间距 (mm)
    dense_legs: int            # 加密区肢数（必须为偶数）
    dense_diameter: float      # 加密区箍筋直径 (mm)

    # 非加密区（跨中）
    normal_spacing: float      # 非加密区间距 (mm)
    normal_legs: int           # 非加密区肢数（必须为偶数）
    normal_diameter: float     # 非加密区箍筋直径 (mm)

    # 保护层厚度
    cover: float = 25.0        # 保护层厚度 (mm)

    def __post_init__(self):
        if self.dense_legs % 2 != 0:
            raise ValueError(f"加密区箍筋肢数必须为偶数，当前值: {self.dense_legs}")
        if self.normal_legs % 2 != 0:
            raise ValueError(f"非加密区箍筋肢数必须为偶数，当前值: {self.normal_legs}")
        if self.dense_spacing <= 0 or self.normal_spacing <= 0:
            raise ValueError("箍筋间距必须大于0")
        if self.dense_diameter <= 0 or self.normal_diameter <= 0:
            raise ValueError("箍筋直径必须大于0")


@dataclass
class HoleParams:
    """洞口参数 (Excel Sheet 4: Holes & Patch)"""
    # 洞口几何
    x: float                   # X 坐标 (相对梁起点, mm)
    z: float                   # Z 坐标 (相对梁底, mm)
    width: float               # 宽度 (mm)
    height: float              # 高度 (mm)
    fillet_radius: float = 0.0 # 倒角半径 (mm) - T+3预留，T+7实现

    # 小梁配筋（洞口上下形成的微型梁）
    # 兼容旧字段：不区分洞口顶/底时，使用该直径/数量（新字段为 0 时回退）
    small_beam_long_diameter: float = 0.0  # 纵筋直径 (mm)
    small_beam_long_count: int = 0         # 纵筋根数
    # 新字段：洞口顶部/底部加强纵筋分别配置（客户20260127反馈）
    small_beam_long_top_diameter: float = 0.0
    small_beam_long_top_count: int = 0
    small_beam_long_bottom_diameter: float = 0.0
    small_beam_long_bottom_count: int = 0
    small_beam_stirrup_diameter: float = 0.0  # 箍筋直径 (mm)
    small_beam_stirrup_spacing: float = 0.0   # 箍筋间距 (mm)
    small_beam_stirrup_legs: int = 0          # 小梁箍筋肢数（0=自动，建议4）

    # 洞侧补强箍筋
    left_reinf_length: float = 0.0      # 左侧补强区长度 (mm)
    right_reinf_length: float = 0.0     # 右侧补强区长度 (mm)
    side_stirrup_spacing: float = 0.0   # 侧边箍筋间距 (mm)
    side_stirrup_diameter: float = 0.0  # 侧边箍筋直径 (mm)
    side_stirrup_legs: int = 2          # 侧边箍筋肢数

    # 补强筋伸出长度
    reinf_extend_length: float = 0.0    # 补强纵筋锚固伸出长度 (mm)

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("洞口尺寸必须大于0")
        if self.fillet_radius < 0:
            raise ValueError("倒角半径不能为负")
        if self.fillet_radius > min(self.width, self.height) / 2:
            raise ValueError("倒角半径不能超过洞口边长的一半")

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """获取洞口边界 (x_min, x_max, z_min, z_max)"""
        x_min = self.x - self.width / 2
        x_max = self.x + self.width / 2
        z_min = self.z - self.height / 2
        z_max = self.z + self.height / 2
        return x_min, x_max, z_min, z_max

    def check_overlap(self, other: 'HoleParams') -> bool:
        """检查与另一个洞口是否重叠"""
        x1_min, x1_max, z1_min, z1_max = self.get_bounds()
        x2_min, x2_max, z2_min, z2_max = other.get_bounds()

        # 检查X方向和Z方向是否都有重叠
        x_overlap = not (x1_max <= x2_min or x2_max <= x1_min)
        z_overlap = not (z1_max <= z2_min or z2_max <= z1_min)

        return x_overlap and z_overlap


@dataclass
class LoadCase:
    """荷载工况 (Excel Sheet 5: Steps & Boundary)"""
    name: str                  # 工况名称
    stage: str                 # "Construction" 或 "Service"

    # 集中力 [(x位置, 方向, 大小)]
    # 方向: "X", "Y", "Z", "MX", "MY", "MZ"
    concentrated_loads: List[Tuple[float, str, float]] = field(default_factory=list)

    # 均布力 [(起点x, 终点x, 方向, 大小)]
    distributed_loads: List[Tuple[float, float, str, float]] = field(default_factory=list)

    def __post_init__(self):
        if self.stage not in ["Construction", "Service"]:
            raise ValueError(f"荷载阶段必须为 'Construction' 或 'Service'，当前值: {self.stage}")


@dataclass
class BoundaryCondition:
    """边界条件 (Excel Sheet 5: Steps & Boundary)"""
    # 端部约束
    # 格式: {"Dx": "Fixed", "Dy": "Fixed", "Dz": "Fixed", "Rx": "Free", "Ry": "Free", "Rz": "Free"}
    left_end: Dict[str, str] = field(default_factory=dict)
    right_end: Dict[str, str] = field(default_factory=dict)

    # 端部内力
    # 格式: {"N": 0, "Vy": 0, "Vz": 0, "Mx": 0, "My": 0, "Mz": 0}
    left_end_forces: Dict[str, float] = field(default_factory=dict)
    right_end_forces: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        # 设置默认值（如果未提供）
        default_constraint = {"Dx": "Fixed", "Dy": "Fixed", "Dz": "Fixed",
                            "Rx": "Free", "Ry": "Free", "Rz": "Free"}
        default_forces = {"N": 0.0, "Vy": 0.0, "Vz": 0.0, "Mx": 0.0, "My": 0.0, "Mz": 0.0}

        if not self.left_end:
            self.left_end = default_constraint.copy()
        if not self.right_end:
            self.right_end = default_constraint.copy()
        if not self.left_end_forces:
            self.left_end_forces = default_forces.copy()
        if not self.right_end_forces:
            self.right_end_forces = default_forces.copy()


@dataclass
class PrestressParams:
    """预应力参数 (Excel Sheet 6: Prestress)

    后张法逻辑：
    - 几何层面：在预制层 Solid 中通过布尔运算挖掉直径为 duct_diameter 的孔道
    - 分析层面：Step 1（施工）不激活；Step 2（使用）激活并施加 PreStress
    """
    enabled: bool = False       # 是否启用预应力
    # 预应力方式：
    # - post_tension(后张法)：需要波纹管孔道(duct_diameter>0)
    # - pretension(先张法)：不挖孔道，直接对预应力筋/钢筋施加 PreStress
    method: str = 'post_tension'
    force: float = 0.0          # 张拉力 (N)
    duct_diameter: float = 0.0  # 波纹管直径 (mm)
    path_type: str = 'straight' # 路径类型: 'straight' 或 'parabolic'

    # 孔道路径（三维坐标列表）
    # 典型情况：抛物线路径，或简化为直线路径
    # 注意：此字段由 main.py 根据 path_type 和梁几何自动计算
    duct_path: List[Tuple[float, float, float]] = field(default_factory=list)

    def __post_init__(self):
        if self.enabled:
            if self.force <= 0:
                raise ValueError("预应力张拉力必须大于0")
            m = str(self.method or 'post_tension').strip().lower()
            if m not in ('post_tension', 'pretension'):
                m = 'post_tension'
            self.method = m
            if self.method == 'post_tension':
                if self.duct_diameter <= 0:
                    raise ValueError("后张法：波纹管直径必须大于0")
            else:
                # 先张法：不要求孔道，可为0
                if self.duct_diameter < 0:
                    raise ValueError("先张法：波纹管直径不能为负")
            # 注意：duct_path 由 main.py 根据梁几何自动计算，Excel 解析时为空列表


@dataclass
class BeamParameters:
    """完整梁参数集合 - 所有建模所需参数的顶层容器"""
    geometry: GeometryParams
    long_rebar: LongitudinalRebar
    stirrup: StirrupParams
    holes: List[HoleParams] = field(default_factory=list)
    loads: List[LoadCase] = field(default_factory=list)
    boundary: BoundaryCondition = field(default_factory=BoundaryCondition)
    prestress: Optional[PrestressParams] = None

    def validate(self) -> Tuple[bool, List[str]]:
        """
        全面参数校验

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # 1. 洞口合法性检查
        for i, hole in enumerate(self.holes):
            x_min, x_max, z_min, z_max = hole.get_bounds()

            # 洞口不能超出梁体范围
            if x_min < 0 or x_max > self.geometry.L:
                errors.append(f"洞口 {i+1} 超出梁长范围: x 范围 ({x_min:.1f}, {x_max:.1f}) 不在 (0, {self.geometry.L})")

            if z_min < 0 or z_max > self.geometry.H:
                errors.append(f"洞口 {i+1} 超出梁高范围: z 范围 ({z_min:.1f}, {z_max:.1f}) 不在 (0, {self.geometry.H})")

            # 洞口距端部至少 200mm
            if x_min < 200 or x_max > self.geometry.L - 200:
                errors.append(f"洞口 {i+1} 距端部过近（建议至少 200mm）")

            # 检查与其他洞口的重叠
            for j in range(i + 1, len(self.holes)):
                if hole.check_overlap(self.holes[j]):
                    errors.append(f"洞口 {i+1} 与洞口 {j+1} 重叠")

        # 2. 支座区长度默认值处理
        if self.long_rebar.left_support_length == 0:
            self.long_rebar.left_support_length = self.geometry.L / 3
        if self.long_rebar.right_support_length == 0:
            self.long_rebar.right_support_length = self.geometry.L / 3

        # 3. 荷载作用位置检查
        for load_case in self.loads:
            for x, _, _ in load_case.concentrated_loads:
                if x < 0 or x > self.geometry.L:
                    errors.append(f"荷载工况 '{load_case.name}' 中的集中力位置 {x} 超出梁长范围")

            for x1, x2, _, _ in load_case.distributed_loads:
                if x1 < 0 or x2 > self.geometry.L or x1 >= x2:
                    errors.append(f"荷载工况 '{load_case.name}' 中的均布力范围 ({x1}, {x2}) 不合法")

        return len(errors) == 0, errors

    def summary(self) -> str:
        """生成参数摘要信息"""
        summary_lines = [
            "=" * 60,
            "叠合梁参数摘要",
            "=" * 60,
            f"梁长: {self.geometry.L} mm",
            f"梁高: {self.geometry.H} mm (预制层: {self.geometry.h_pre} mm, 现浇顶盖: {getattr(self.geometry,'t_cast_cap',0.0)} mm)",
            f"腹板厚度: {self.geometry.Tw} mm",
            f"截面类型: {'矩形' if self.geometry.is_rectangular() else ('T形' if self.geometry.is_t_shaped() else '工字形')}",
            f"洞口数量: {len(self.holes)}",
            f"荷载工况数: {len(self.loads)}",
            f"预应力: {'启用' if self.prestress and self.prestress.enabled else '未启用'}",
            "=" * 60,
        ]
        return "\n".join(summary_lines)


if __name__ == "__main__":
    # 测试代码
    geom = GeometryParams(
        L=10000, H=800, Tw=250,
        bf_lu=400, tf_lu=150, bf_ru=400, tf_ru=150,
        bf_ll=400, tf_ll=150, bf_rl=400, tf_rl=150,
        h_pre=500,
        t_cast_cap=0.0
    )

    print(f"是否对称: 上翼缘={geom.is_symmetric_top()}, 下翼缘={geom.is_symmetric_bottom()}")
    print(f"是否矩形: {geom.is_rectangular()}")
    print(f"是否T形: {geom.is_t_shaped()}")
