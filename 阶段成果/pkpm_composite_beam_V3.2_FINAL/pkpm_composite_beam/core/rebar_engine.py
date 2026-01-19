"""
PKPM-CAE 叠合梁参数化建模 - 钢筋布置引擎
"""

from typing import List, Dict, Tuple
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pypcae.comp import Node, Element
    from pypcae.enums import EleType
except ImportError:
    print("警告: PyPCAE 模块未安装，使用模拟模式")

    class Node:
        _id_counter = 10000
        def __init__(self, x, y, z):
            self.x, self.y, self.z = x, y, z
            self.id = Node._id_counter
            Node._id_counter += 1

    class Element:
        _id_counter = 20000
        def __init__(self, nodes, etype=None):
            self.nodes = nodes
            self.etype = etype
            self.id = Element._id_counter
            Element._id_counter += 1

    class EleType:
        Link = "Link"

from core.parameters import GeometryParams, LongitudinalRebar, StirrupParams, HoleParams


class RebarEngine:
    # 为避免钢筋与洞口/几何边界“完全重合”导致网格/拾取异常，给洞口相关钢筋做最小偏移
    HOLE_EDGE_CLEARANCE = 2.0  # mm
    """钢筋布置引擎

    功能：
    1. 纵向钢筋布置（主筋 + 附加筋 + L/3 截断）
    2. 箍筋肢数自动布置算法
    3. 洞口补强配筋
    4. 钢筋 Embeded 嵌入
    """

    def __init__(self, geometry: GeometryParams):
        """
        初始化钢筋引擎

        Args:
            geometry: 几何参数
        """
        self.geometry = geometry

    def _effective_hp(self) -> float:
        """
        叠合面有效高度 hp (mm)

        当存在上翼缘且设置了 t_cast_cap>0 时，hp = H - t_cast_cap；
        否则回退到 Excel 的 h_pre。
        """
        g = self.geometry
        try:
            H = float(g.H)
            bf_upper = max(float(getattr(g, "bf_lu", 0.0) or 0.0), float(getattr(g, "bf_ru", 0.0) or 0.0))
            tf_upper = max(float(getattr(g, "tf_lu", 0.0) or 0.0), float(getattr(g, "tf_ru", 0.0) or 0.0))
            if bf_upper > 1e-6 and tf_upper > 1e-6:
                t_cast_cap = float(getattr(g, "t_cast_cap", 0.0) or 0.0)
                if t_cast_cap > 1e-6:
                    t_cast_cap = max(1.0, t_cast_cap)
                    t_cast_cap = min(t_cast_cap, tf_upper - 1.0)
                    return H - t_cast_cap
        except Exception:
            pass
        return float(getattr(g, "h_pre", 0.0) or 0.0)

    def create_longitudinal_rebars(self, long_rebar: LongitudinalRebar,
                                   cover: float = 25.0) -> Dict[str, List]:
        """
        创建纵向配筋

        Args:
            long_rebar: 纵向配筋参数
            cover: 保护层厚度 (mm)

        Returns:
            {
                'top_rebars': [Element列表],
                'bottom_rebars': [Element列表],
                'all_nodes': [Node列表],
                'all_elements': [Element列表]
            }
        """
        L = self.geometry.L
        H = self.geometry.H
        Tw = self.geometry.Tw

        # 【关键】翼缘厚度，底筋要在翼缘以上
        tf = max(self.geometry.tf_ll, self.geometry.tf_rl, 100.0)  # 默认100mm
        bf_upper = max(float(getattr(self.geometry, "bf_lu", 0.0) or 0.0), float(getattr(self.geometry, "bf_ru", 0.0) or 0.0))
        bf_lower = max(float(getattr(self.geometry, "bf_ll", 0.0) or 0.0), float(getattr(self.geometry, "bf_rl", 0.0) or 0.0))
        top_width = (Tw + 2 * bf_upper) if bf_upper > 1e-6 else Tw
        bottom_width = (Tw + 2 * bf_lower) if bf_lower > 1e-6 else Tw

        # 设置默认支座区长度
        left_len = long_rebar.left_support_length if long_rebar.left_support_length > 0 else L / 3
        right_len = long_rebar.right_support_length if long_rebar.right_support_length > 0 else L / 3

        all_nodes = []
        all_elements = []
        top_rebars = []
        bottom_rebars = []

        # 1. 创建顶部钢筋
        top_rebars_result = self._create_top_rebars(
            long_rebar, L, H, top_width, cover, left_len, right_len
        )
        all_nodes.extend(top_rebars_result['nodes'])
        all_elements.extend(top_rebars_result['elements'])
        top_rebars.extend(top_rebars_result['elements'])

        # 1B. 上翼缘角部纵筋自动补齐（至少两根角筋，避免只在腹板范围布筋）
        try:
            y_corner = top_width / 2 - cover
            if y_corner > 1e-6 and getattr(long_rebar, "left_support_top_A", None):
                corner_nodes, corner_elems = self._create_rebar_line(
                    x_start=0, x_end=L,
                    z=H - cover,
                    y_positions=[-y_corner, y_corner],
                    diameter=float(long_rebar.left_support_top_A.diameter)
                )
                all_nodes.extend(corner_nodes)
                all_elements.extend(corner_elems)
                top_rebars.extend(corner_elems)
        except Exception:
            pass

        # 2. 创建底部通长筋 (考虑翼缘厚度tf)
        bottom_rebars_result = self._create_bottom_rebars(
            long_rebar, L, H, Tw, cover, tf
        )
        all_nodes.extend(bottom_rebars_result['nodes'])
        all_elements.extend(bottom_rebars_result['elements'])
        bottom_rebars.extend(bottom_rebars_result['elements'])

        # 2B. 底部翼缘顶部角部纵筋（z=tf_lower-cover）：角点至少有钢筋（张工反馈）
        try:
            y_corner = bottom_width / 2 - cover
            z_flange_top = max(cover, float(tf) - cover)
            if y_corner > 1e-6 and z_flange_top > cover + 1e-6 and getattr(long_rebar, "bottom_through_A", None):
                corner_nodes, corner_elems = self._create_rebar_line(
                    x_start=0, x_end=L,
                    z=z_flange_top,
                    y_positions=[-y_corner, y_corner],
                    diameter=float(long_rebar.bottom_through_A.diameter)
                )
                all_nodes.extend(corner_nodes)
                all_elements.extend(corner_elems)
                bottom_rebars.extend(corner_elems)
        except Exception:
            pass

        return {
            'top_rebars': top_rebars,
            'bottom_rebars': bottom_rebars,
            'all_nodes': all_nodes,
            'all_elements': all_elements
        }

    def _create_top_rebars(self, long_rebar: LongitudinalRebar,
                          L: float, H: float, section_width: float, cover: float,
                          left_len: float, right_len: float) -> Dict:
        """
        创建顶部纵向钢筋（支座区 + 跨中区）

        逻辑：
        - 左支座区：0 ~ left_len，布置 A组 + B组
        - 跨中区：left_len ~ (L - right_len)，布置跨中钢筋
        - 右支座区：(L - right_len) ~ L，布置 A组 + B组

        Args:
            long_rebar: 纵向配筋参数
            L, H, section_width: 几何尺寸
            cover: 保护层
            left_len, right_len: 左右支座区长度

        Returns:
            {'nodes': [], 'elements': []}
        """
        nodes = []
        elements = []

        # 顶部钢筋 Z 坐标（距顶面 cover）
        z_top = H - cover

        # 左支座 A 组（通长）
        left_a_nodes, left_a_elems = self._create_rebar_line(
            x_start=0, x_end=left_len,
            z=z_top, y_positions=self._calculate_rebar_y_positions(
                section_width, long_rebar.left_support_top_A.count, cover
            ),
            diameter=long_rebar.left_support_top_A.diameter
        )
        nodes.extend(left_a_nodes)
        elements.extend(left_a_elems)

        # 左支座 B 组（附加筋，如果有）
        if long_rebar.left_support_top_B:
            extend_len = long_rebar.left_support_top_B.extend_length
            left_b_nodes, left_b_elems = self._create_rebar_line(
                x_start=0, x_end=min(left_len + extend_len, L),
                z=z_top, y_positions=self._calculate_rebar_y_positions(
                    section_width, long_rebar.left_support_top_B.count, cover,
                    offset=long_rebar.left_support_top_A.count
                ),
                diameter=long_rebar.left_support_top_B.diameter
            )
            nodes.extend(left_b_nodes)
            elements.extend(left_b_elems)

        # 跨中区钢筋
        mid_start = left_len
        mid_end = L - right_len
        mid_nodes, mid_elems = self._create_rebar_line(
            x_start=mid_start, x_end=mid_end,
            z=z_top, y_positions=self._calculate_rebar_y_positions(
                section_width, long_rebar.mid_span_top.count, cover
            ),
            diameter=long_rebar.mid_span_top.diameter
        )
        nodes.extend(mid_nodes)
        elements.extend(mid_elems)

        # 右支座 A 组（通长）
        right_a_nodes, right_a_elems = self._create_rebar_line(
            x_start=L - right_len, x_end=L,
            z=z_top, y_positions=self._calculate_rebar_y_positions(
                section_width, long_rebar.right_support_top_A.count, cover
            ),
            diameter=long_rebar.right_support_top_A.diameter
        )
        nodes.extend(right_a_nodes)
        elements.extend(right_a_elems)

        # 右支座 B 组（附加筋，如果有）
        if long_rebar.right_support_top_B:
            extend_len = long_rebar.right_support_top_B.extend_length
            right_b_nodes, right_b_elems = self._create_rebar_line(
                x_start=max(L - right_len - extend_len, 0), x_end=L,
                z=z_top, y_positions=self._calculate_rebar_y_positions(
                    section_width, long_rebar.right_support_top_B.count, cover,
                    offset=long_rebar.right_support_top_A.count
                ),
                diameter=long_rebar.right_support_top_B.diameter
            )
            nodes.extend(right_b_nodes)
            elements.extend(right_b_elems)

        return {'nodes': nodes, 'elements': elements}

    def _create_bottom_rebars(self, long_rebar: LongitudinalRebar,
                             L: float, H: float, Tw: float, cover: float, tf: float) -> Dict:
        """
        创建底部通长筋

        Args:
            long_rebar: 纵向配筋参数
            L, H, Tw: 几何尺寸
            cover: 保护层
            tf: 翼缘厚度

        Returns:
            {'nodes': [], 'elements': []}
        """
        nodes = []
        elements = []

        # 【关键修正】底部受拉主筋必须放在翼缘（翅膀）内部，不是腹板！
        # Z坐标 = 底部保护层厚度（约30mm），钢筋铺在最底下的大翼缘板内
        z_bottom = cover  # 25~30mm，在翼缘实体内

        # 【关键修正】底筋分布在翼缘总宽内，不是腹板宽
        # 翼缘总宽 = Tw + 2*bf
        # 翼缘伸出宽度：必须使用几何参数本身，不能用“200mm 默认值”覆盖（否则会把底筋放到混凝土外）
        bf = max(self.geometry.bf_ll, self.geometry.bf_rl, 0.0)
        flange_width = Tw + 2 * bf  # 翼缘总宽（如 250+2*200=650mm）

        # 底部 A 组（通长，从0到L，Y分布在翼缘总宽内）
        bottom_a_nodes, bottom_a_elems = self._create_rebar_line(
            x_start=0, x_end=L,
            z=z_bottom, y_positions=self._calculate_rebar_y_positions(
                flange_width, long_rebar.bottom_through_A.count, cover
            ),
            diameter=long_rebar.bottom_through_A.diameter
        )
        nodes.extend(bottom_a_nodes)
        elements.extend(bottom_a_elems)

        # 底部 B 组（如果有，也是通长，Y分布在翼缘总宽内）
        if long_rebar.bottom_through_B and long_rebar.bottom_through_B.count > 0:
            bottom_b_nodes, bottom_b_elems = self._create_rebar_line(
                x_start=0, x_end=L,
                z=z_bottom, y_positions=self._calculate_rebar_y_positions(
                    flange_width, long_rebar.bottom_through_B.count, cover,
                    offset=long_rebar.bottom_through_A.count
                ),
                diameter=long_rebar.bottom_through_B.diameter
            )
            nodes.extend(bottom_b_nodes)
            elements.extend(bottom_b_elems)

        return {'nodes': nodes, 'elements': elements}

    def _calculate_rebar_y_positions(self, section_width: float, count: int,
                                     cover: float, offset: int = 0) -> List[float]:
        """
        计算钢筋在 Y 方向的位置

        Args:
            section_width: 截面宽度
            count: 钢筋根数
            cover: 保护层厚度
            offset: 偏移根数（用于附加筋避开主筋位置）

        Returns:
            [Y 坐标列表]
        """
        if count <= 0:
            return []

        # 有效宽度（扣除保护层）
        effective_width = section_width - 2 * cover

        if count == 1:
            return [0.0]  # 单根钢筋居中

        # 多根钢筋等间距分布
        spacing = effective_width / (count - 1)
        y_positions = []

        for i in range(count):
            y = -effective_width / 2 + i * spacing
            y_positions.append(y)

        # 如果有偏移，微调位置避免重合
        if offset > 0:
            y_positions = [y + cover * 0.5 for y in y_positions]

        return y_positions

    def _create_rebar_line(self, x_start: float, x_end: float,
                          z: float, y_positions: List[float],
                          diameter: float, num_segments: int = 30) -> Tuple[List, List]:
        """
        创建一组平行钢筋（沿 X 方向）

        Args:
            x_start, x_end: X 方向起止点
            z: Z 坐标
            y_positions: Y 坐标列表
            diameter: 钢筋直径
            num_segments: 每根钢筋分段数（满血版用30段确保精度）

        Returns:
            ([Node列表], [Element列表])
        """
        nodes = []
        elements = []

        # 计算X方向分段点
        x_points = [x_start + i * (x_end - x_start) / num_segments
                   for i in range(num_segments + 1)]

        for y in y_positions:
            # 为每根钢筋创建节点
            rebar_nodes = []
            for x in x_points:
                node = Node(x, y, z)
                nodes.append(node)
                rebar_nodes.append(node)

            # 创建 Link 单元连接节点
            for i in range(len(rebar_nodes) - 1):
                elem = Element([rebar_nodes[i].id, rebar_nodes[i+1].id], etype=EleType.Link)
                elements.append(elem)

        return nodes, elements

    def create_stirrups(self, stirrup: StirrupParams, holes: List[HoleParams] = None) -> Dict:
        """
        创建箍筋

        Args:
            stirrup: 箍筋参数

        Returns:
            {
                'dense_stirrups': [Element列表],
                'normal_stirrups': [Element列表],
                'all_nodes': [Node列表],
                'all_elements': [Element列表]
            }
        """
        L = self.geometry.L
        H = self.geometry.H
        Tw = self.geometry.Tw
        cover = stirrup.cover

        # 【关键】翼缘厚度 - 左右独立，用于自适应箍筋高度
        tf_ll = max(self.geometry.tf_ll, 100.0)  # 左下翼缘厚度，默认100mm
        tf_rl = max(self.geometry.tf_rl, 100.0)  # 右下翼缘厚度，默认100mm
        # 翼缘伸出宽度：取上下翼缘最大值（避免上翼缘更宽时箍筋仍按下翼缘宽度生成）
        bf = max(
            float(getattr(self.geometry, "bf_ll", 0.0) or 0.0),
            float(getattr(self.geometry, "bf_rl", 0.0) or 0.0),
            float(getattr(self.geometry, "bf_lu", 0.0) or 0.0),
            float(getattr(self.geometry, "bf_ru", 0.0) or 0.0),
            0.0
        )
        flange_width = Tw + 2 * bf  # 翼缘总宽 650mm

        # 【关键修正】箍筋Y坐标分布
        # 外侧肢 Y = ±(flange_width/2 - cover) = ±300mm
        # 内侧肢 Y = ±(Tw/2 - cover) = ±100mm
        y_outer = flange_width / 2 - cover  # 300mm (外侧肢Y坐标)
        y_inner = Tw / 2 - cover            # 100mm (内侧肢Y坐标)

        # 箍筋Z坐标 - 自适应高度
        z_bottom = cover                           # 底部Z=25mm
        z_flange_top_left = tf_ll - cover          # 左翼缘顶Z（自适应）
        z_flange_top_right = tf_rl - cover         # 右翼缘顶Z（自适应）
        z_top = H - cover                          # 顶部Z=775mm

        # 箍筋高度分段（用于调试输出）
        print(f">>> 【箍筋参数】Y外侧={y_outer:.1f}mm, Y内侧={y_inner:.1f}mm")
        print(f">>> 【箍筋参数】Z底={z_bottom:.1f}mm, Z翼缘顶左={z_flange_top_left:.1f}mm, Z翼缘顶右={z_flange_top_right:.1f}mm, Z顶={z_top:.1f}mm")

        all_nodes = []
        all_elements = []
        dense_stirrups = []
        normal_stirrups = []

        # 洞口避让：洞宽范围内屏蔽全局箍筋（仅允许洞口补强筋出现）
        # 额外扩大 2mm：避免箍筋恰好落在洞口边界线上（张工反馈：洞口中心不允许钢筋穿过）
        skip_ranges = []
        if holes:
            for h in holes:
                try:
                    x_min, x_max, _z0, _z1 = h.get_bounds()
                    pad = float(self.HOLE_EDGE_CLEARANCE)
                    skip_ranges.append((float(x_min) - pad, float(x_max) + pad))
                except Exception:
                    continue

        # 1. 创建加密区箍筋（两端）- 工字型
        # 左端加密区
        left_dense_result = self._create_i_shaped_stirrup_zone(
            x_start=cover,
            x_end=stirrup.dense_zone_length,
            spacing=stirrup.dense_spacing,
            y_outer=y_outer,                        # 外侧肢Y=300mm
            y_inner=y_inner,                        # 内侧肢Y=100mm
            z_bottom=z_bottom,                      # 25mm
            z_flange_top_left=z_flange_top_left,    # 左翼缘顶（自适应）
            z_flange_top_right=z_flange_top_right,  # 右翼缘顶（自适应）
            z_top=z_top,                            # 775mm
            legs=stirrup.dense_legs,
            diameter=stirrup.dense_diameter,
            skip_ranges=skip_ranges
        )
        all_nodes.extend(left_dense_result['nodes'])
        all_elements.extend(left_dense_result['elements'])
        dense_stirrups.extend(left_dense_result['elements'])

        # 右端加密区
        right_dense_result = self._create_i_shaped_stirrup_zone(
            x_start=L - stirrup.dense_zone_length,
            x_end=L - cover,
            spacing=stirrup.dense_spacing,
            y_outer=y_outer,
            y_inner=y_inner,
            z_bottom=z_bottom,
            z_flange_top_left=z_flange_top_left,
            z_flange_top_right=z_flange_top_right,
            z_top=z_top,
            legs=stirrup.dense_legs,
            diameter=stirrup.dense_diameter,
            skip_ranges=skip_ranges
        )
        all_nodes.extend(right_dense_result['nodes'])
        all_elements.extend(right_dense_result['elements'])
        dense_stirrups.extend(right_dense_result['elements'])

        # 2. 创建非加密区箍筋（跨中）- 工字型
        normal_result = self._create_i_shaped_stirrup_zone(
            x_start=stirrup.dense_zone_length,
            x_end=L - stirrup.dense_zone_length,
            spacing=stirrup.normal_spacing,
            y_outer=y_outer,
            y_inner=y_inner,
            z_bottom=z_bottom,
            z_flange_top_left=z_flange_top_left,
            z_flange_top_right=z_flange_top_right,
            z_top=z_top,
            legs=stirrup.normal_legs,
            diameter=stirrup.normal_diameter,
            skip_ranges=skip_ranges
        )
        all_nodes.extend(normal_result['nodes'])
        all_elements.extend(normal_result['elements'])
        normal_stirrups.extend(normal_result['elements'])

        return {
            'dense_stirrups': dense_stirrups,
            'normal_stirrups': normal_stirrups,
            'all_nodes': all_nodes,
            'all_elements': all_elements
        }

    def _create_i_shaped_stirrup_zone(self, x_start: float, x_end: float,
                                       spacing: float, y_outer: float, y_inner: float,
                                       z_bottom: float, z_flange_top_left: float,
                                       z_flange_top_right: float, z_top: float,
                                       legs: int, diameter: float,
                                       skip_ranges: List[Tuple[float, float]] = None) -> Dict:
        """
        创建一个区域内的工字型箍筋

        Args:
            x_start, x_end: X坐标范围
            spacing: 箍筋间距
            y_outer: 外侧肢Y坐标（绝对值）= 300mm
            y_inner: 内侧肢Y坐标（绝对值）= 100mm
            z_bottom: 底部Z坐标 = cover
            z_flange_top_left: 左翼缘顶Z = tf_ll - cover（自适应）
            z_flange_top_right: 右翼缘顶Z = tf_rl - cover（自适应）
            z_top: 顶部Z坐标 = H - cover
            legs: 肢数
            diameter: 直径
        """
        nodes = []
        elements = []

        # 计算箍筋X位置
        num_stirrups = int((x_end - x_start) / spacing) + 1
        x_positions = [x_start + i * spacing for i in range(num_stirrups)
                      if x_start + i * spacing <= x_end]

        def _in_skip(xv: float) -> bool:
            if not skip_ranges:
                return False
            for a, b in skip_ranges:
                if xv >= a - 1e-6 and xv <= b + 1e-6:
                    return True
            return False

        for x_pos in x_positions:
            if _in_skip(x_pos):
                continue
            stirrup_nodes, stirrup_elems = self._create_single_i_shaped_stirrup(
                x=x_pos,
                y_outer=y_outer,
                y_inner=y_inner,
                z_bottom=z_bottom,
                z_flange_top_left=z_flange_top_left,
                z_flange_top_right=z_flange_top_right,
                z_top=z_top,
                legs=legs,
                diameter=diameter
            )
            nodes.extend(stirrup_nodes)
            elements.extend(stirrup_elems)

        return {'nodes': nodes, 'elements': elements}

    def _create_single_i_shaped_stirrup(self, x: float, y_outer: float, y_inner: float,
                                         z_bottom: float, z_flange_top_left: float,
                                         z_flange_top_right: float, z_top: float,
                                         legs: int, diameter: float) -> Tuple[List, List]:
        """
        创建单个工字型箍筋（自适应高度版本）

        形状示意（从X轴正向看）：

                    ┌───────┐           Z=z_top (775mm)
                    │       │
                    │ 内侧肢│  Y=±100mm，贯通全高
                    │ (长)  │
           ┌────────┤       ├────────┐  Z=z_flange_top (左右可不同)
           │ 外侧肢 │       │ 外侧肢 │
           │ (短)   │       │ (短)   │  Y=±300mm，只在翼缘内
           └────────┴───────┴────────┘  Z=z_bottom (25mm)
            Y=-300  Y=-100 Y=+100 Y=+300

        关键逻辑：
        - 外侧肢（Y=±300）：短，高度 = z_flange_top - z_bottom（翼缘内）
        - 内侧肢（Y=±100）：长，高度 = z_top - z_bottom（贯通全高）
        - 左右翼缘高度可不同（tf_ll vs tf_rl），实现自适应
        """
        nodes = []
        elements = []

        # === 创建10个关键节点 ===
        # 外侧4个底角（在翼缘底部 Z=z_bottom）
        n1 = Node(x, -y_outer, z_bottom)    # 左外底 Y=-300
        n2 = Node(x, -y_inner, z_bottom)    # 左内底 Y=-100
        n3 = Node(x, y_inner, z_bottom)     # 右内底 Y=+100
        n4 = Node(x, y_outer, z_bottom)     # 右外底 Y=+300

        # 外侧短肢顶点（左右翼缘顶，高度自适应）
        n5 = Node(x, -y_outer, z_flange_top_left)   # 左外顶（自适应tf_ll）
        n6 = Node(x, y_outer, z_flange_top_right)   # 右外顶（自适应tf_rl）

        # 内侧长肢的翼缘顶点（用于水平连接）
        n7 = Node(x, -y_inner, z_flange_top_left)   # 左内翼缘顶
        n8 = Node(x, y_inner, z_flange_top_right)   # 右内翼缘顶

        # 内侧长肢顶点（贯通到梁顶）
        n9 = Node(x, -y_inner, z_top)    # 左内顶 Y=-100
        n10 = Node(x, y_inner, z_top)    # 右内顶 Y=+100

        nodes.extend([n1, n2, n3, n4, n5, n6, n7, n8, n9, n10])

        # === 创建箍筋边 ===
        # 底部横向边（翼缘宽度，从左外到右外）
        e1 = Element([n1.id, n2.id], etype=EleType.Link)  # 左段底边
        e2 = Element([n2.id, n3.id], etype=EleType.Link)  # 中段底边
        e3 = Element([n3.id, n4.id], etype=EleType.Link)  # 右段底边

        # 外侧短肢（竖向，只在翼缘内）
        e4 = Element([n1.id, n5.id], etype=EleType.Link)  # 左外竖边（短）
        e5 = Element([n4.id, n6.id], etype=EleType.Link)  # 右外竖边（短）

        # 【修正】内侧长肢改为分段，确保闭合
        # 左内侧肢：下段(n2→n7) + 上段(n7→n9)
        e6 = Element([n2.id, n7.id], etype=EleType.Link)   # 左内竖边（下段，翼缘内）
        e11 = Element([n7.id, n9.id], etype=EleType.Link)  # 左内竖边（上段，腹板内）

        # 右内侧肢：下段(n3→n8) + 上段(n8→n10)
        e7 = Element([n3.id, n8.id], etype=EleType.Link)   # 右内竖边（下段，翼缘内）
        e12 = Element([n8.id, n10.id], etype=EleType.Link) # 右内竖边（上段，腹板内）

        # 翼缘顶横向连接（外侧短肢顶连接到内侧肢）
        e8 = Element([n5.id, n7.id], etype=EleType.Link)  # 左翼缘顶横边
        e9 = Element([n8.id, n6.id], etype=EleType.Link)  # 右翼缘顶横边

        # 顶部横向边（腹板宽度）
        e10 = Element([n9.id, n10.id], etype=EleType.Link)  # 顶边

        # 【张工反馈#7-封口】预制层顶部（腹板与底翼缘交接面）增加一根横向封口筋：
        # 在 z=z_flange_top 位置连接两根内侧肢，形成“预制段闭合矩形框”
        e13 = Element([n7.id, n8.id], etype=EleType.Link)   # 封口横筋（+1段）

        elements.extend([e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12, e13])

        # === 4肢及以上：添加中间内拉筋 ===
        if legs >= 4:
            inner_leg_count = legs - 2
            if inner_leg_count > 0:
                inner_spacing = (2 * y_inner) / (inner_leg_count + 1)
                for i in range(1, inner_leg_count + 1):
                    y_mid = -y_inner + i * inner_spacing
                    # 中间内拉筋：从底部贯通到顶部
                    n_mid_bottom = Node(x, y_mid, z_bottom)
                    n_mid_top = Node(x, y_mid, z_top)
                    nodes.extend([n_mid_bottom, n_mid_top])
                    e_mid = Element([n_mid_bottom.id, n_mid_top.id], etype=EleType.Link)
                    elements.append(e_mid)

        return nodes, elements

    # ========== 洞口加强筋 ==========
    def create_hole_reinforcement(self, hole, tf_lower: float) -> Dict:
        """
        创建洞口加强配筋

        Args:
            hole: HoleParams 洞口参数对象
            tf_lower: 下翼缘厚度 (用于确定箍筋高度范围)

        Returns:
            {
                'top_long_rebars': [Element列表],    # 洞口顶部纵筋
                'bottom_long_rebars': [Element列表], # 洞口底部纵筋
                'left_stirrups': [Element列表],      # 左侧加强箍筋
                'right_stirrups': [Element列表],     # 右侧加强箍筋
                'all_nodes': [Node列表],
                'all_elements': [Element列表]
            }
        """
        all_nodes = []
        all_elements = []
        top_long_rebars = []
        bottom_long_rebars = []
        left_stirrups = []
        right_stirrups = []
        top_beam_stirrups = []
        bottom_beam_stirrups = []

        Tw = self.geometry.Tw
        hp = self._effective_hp()
        H = self.geometry.H
        cover = 25.0  # 保护层

        # 洞口几何
        hx = hole.x                    # 洞口中心X
        hz = hole.z                    # 洞口中心Z
        hw = hole.width                # 洞口宽度
        hh = hole.height               # 洞口高度

        # 洞口边界
        x_left = hx - hw / 2           # 洞口左边
        x_right = hx + hw / 2          # 洞口右边
        z_bottom = hz - hh / 2         # 洞口底
        z_top = hz + hh / 2            # 洞口顶
        edge_clear = float(self.HOLE_EDGE_CLEARANCE)

        # 1. 创建洞口顶底纵筋（小梁纵筋）
        if hole.small_beam_long_count > 0 and hole.small_beam_long_diameter > 0:
            extend = hole.reinf_extend_length if hole.reinf_extend_length > 0 else 300  # 默认锚固300mm

            # 顶部纵筋
            top_result = self._create_hole_longitudinal_rebars(
                x_start=x_left - extend,
                x_end=x_right + extend,
                z=z_top + cover,  # 洞口顶面上方
                y_width=Tw,
                count=hole.small_beam_long_count,
                diameter=hole.small_beam_long_diameter,
                cover=cover
            )
            all_nodes.extend(top_result['nodes'])
            all_elements.extend(top_result['elements'])
            top_long_rebars.extend(top_result['elements'])

            # 底部纵筋
            bottom_result = self._create_hole_longitudinal_rebars(
                x_start=x_left - extend,
                x_end=x_right + extend,
                z=z_bottom - cover,  # 洞口底面下方
                y_width=Tw,
                count=hole.small_beam_long_count,
                diameter=hole.small_beam_long_diameter,
                cover=cover
            )
            all_nodes.extend(bottom_result['nodes'])
            all_elements.extend(bottom_result['elements'])
            bottom_long_rebars.extend(bottom_result['elements'])

            print(f">>> 【洞口补强】顶底纵筋: {hole.small_beam_long_count}根 x Φ{hole.small_beam_long_diameter}, 锚固{extend}mm")

        # 2. 创建洞口侧边加强箍筋
        if hole.side_stirrup_spacing > 0 and hole.side_stirrup_diameter > 0:
            # 【张工反馈】洞口两侧加强箍筋的高度应与全局箍筋一致：贯通梁顶/梁底
            # 这里采用工字型 ring13 形状（与全局箍筋同形同高），仅在洞口两侧加密范围内生成。
            bf = max(
                float(getattr(self.geometry, "bf_ll", 0.0) or 0.0),
                float(getattr(self.geometry, "bf_rl", 0.0) or 0.0),
                float(getattr(self.geometry, "bf_lu", 0.0) or 0.0),
                float(getattr(self.geometry, "bf_ru", 0.0) or 0.0),
            )
            flange_width = Tw + 2 * bf
            y_outer = flange_width / 2 - cover
            y_inner = Tw / 2 - cover
            z_full_bottom = cover
            z_flange_top_left = max(cover, float(tf_lower) - cover)
            z_flange_top_right = z_flange_top_left
            z_full_top = H - cover

            # 左侧补强区
            if hole.left_reinf_length > 0:
                left_result = self._create_hole_side_i_stirrups(
                    x_start=x_left - hole.left_reinf_length,
                    x_end=x_left - edge_clear,  # 避免与洞口边界重合
                    spacing=hole.side_stirrup_spacing,
                    y_outer=y_outer,
                    y_inner=y_inner,
                    z_bottom=z_full_bottom,
                    z_flange_top_left=z_flange_top_left,
                    z_flange_top_right=z_flange_top_right,
                    z_top=z_full_top,
                    legs=hole.side_stirrup_legs,
                    diameter=hole.side_stirrup_diameter
                )
                all_nodes.extend(left_result['nodes'])
                all_elements.extend(left_result['elements'])
                left_stirrups.extend(left_result['elements'])

            # 右侧补强区
            if hole.right_reinf_length > 0:
                right_result = self._create_hole_side_i_stirrups(
                    x_start=x_right + edge_clear,  # 避免与洞口边界重合
                    x_end=x_right + hole.right_reinf_length,
                    spacing=hole.side_stirrup_spacing,
                    y_outer=y_outer,
                    y_inner=y_inner,
                    z_bottom=z_full_bottom,
                    z_flange_top_left=z_flange_top_left,
                    z_flange_top_right=z_flange_top_right,
                    z_top=z_full_top,
                    legs=hole.side_stirrup_legs,
                    diameter=hole.side_stirrup_diameter
                )
                all_nodes.extend(right_result['nodes'])
                all_elements.extend(right_result['elements'])
                right_stirrups.extend(right_result['elements'])

            print(f">>> 【洞口补强】侧边箍筋: 左{hole.left_reinf_length}mm + 右{hole.right_reinf_length}mm, 间距{hole.side_stirrup_spacing}mm")

        # 3. 洞顶/洞底小梁箍筋（沿 X 方向 @spacing，补齐洞口两端）
        if hole.small_beam_stirrup_spacing > 0 and hole.small_beam_stirrup_diameter > 0:
            sb_nodes, sb_elems_top, sb_elems_bot = self._create_hole_small_beam_stirrups(
                x_left=x_left,
                x_right=x_right,
                z_top=z_top,
                z_bottom=z_bottom,
                y_width=Tw,
                spacing=float(hole.small_beam_stirrup_spacing),
                diameter=float(hole.small_beam_stirrup_diameter),
                cover=cover,
                H=float(H),
                edge_clear=edge_clear
            )
            all_nodes.extend(sb_nodes)
            all_elements.extend(sb_elems_top + sb_elems_bot)
            top_beam_stirrups.extend(sb_elems_top)
            bottom_beam_stirrups.extend(sb_elems_bot)

        return {
            'top_long_rebars': top_long_rebars,
            'bottom_long_rebars': bottom_long_rebars,
            'left_stirrups': left_stirrups,
            'right_stirrups': right_stirrups,
            'top_beam_stirrups': top_beam_stirrups,
            'bottom_beam_stirrups': bottom_beam_stirrups,
            'all_nodes': all_nodes,
            'all_elements': all_elements
        }

    def _create_hole_small_beam_stirrups(self,
                                        x_left: float, x_right: float,
                                        z_top: float, z_bottom: float,
                                        y_width: float,
                                        spacing: float,
                                        diameter: float,
                                        cover: float,
                                        H: float,
                                        edge_clear: float = 0.0) -> Tuple[List, List, List]:
        """
        洞顶/洞底小梁箍筋（D@spacing）：在洞口范围内生成若干道矩形箍筋（YZ平面闭合环），并确保包含洞口两端。

        说明：此处箍筋的“高度带宽”采用固定带宽，围绕洞口顶/底纵筋所在标高形成闭合环，便于验收与网格稳定。
        """
        nodes: List = []
        elems_top: List = []
        elems_bot: List = []

        if spacing <= 0:
            return nodes, elems_top, elems_bot

        # 生成 X 位置（含两端）
        x_positions = []
        x0_raw = float(min(x_left, x_right))
        x1_raw = float(max(x_left, x_right))
        x0 = x0_raw + float(edge_clear)
        x1 = x1_raw - float(edge_clear)
        if x1 <= x0 + 1e-6:
            # 洞口过窄或 edge_clear 过大：退化为洞口中心
            mid = 0.5 * (x0_raw + x1_raw)
            x0 = mid
            x1 = mid
        n = max(1, int((x1 - x0) / spacing) + 1)
        for i in range(n):
            xv = x0 + i * spacing
            if xv <= x1 + 1e-6:
                x_positions.append(float(xv))
        x_positions.extend([float(x0), float(x1)])
        x_positions = sorted(set(round(v, 6) for v in x_positions))

        # 洞顶/洞底“小梁箍筋”采用 ring13（工字型闭合），但严格限制在局部高度带内：
        # - 顶部带：完全位于洞顶之上（z >= z_top + cover）
        # - 底部带：完全位于洞底之下（z <= z_bottom - cover）
        #
        # ring13 需要 y_outer/y_inner。洞顶位置在腹板区时，外肢不能跑到翼缘宽度外，
        # 这里按“所在截面区域”自适应：
        # - 若带宽位于下翼缘厚度范围内：外肢取翼缘外侧（更符合“外箍筋”要求）
        # - 否则：外肢收敛到腹板附近（避免钢筋跑出混凝土）
        band = 80.0  # mm：固定带宽，便于验收/自检
        bf = max(
            float(getattr(self.geometry, "bf_ll", 0.0) or 0.0),
            float(getattr(self.geometry, "bf_rl", 0.0) or 0.0),
            float(getattr(self.geometry, "bf_lu", 0.0) or 0.0),
            float(getattr(self.geometry, "bf_ru", 0.0) or 0.0),
        )
        flange_width = float(self.geometry.Tw) + 2.0 * bf
        y_inner = float(self.geometry.Tw) / 2.0 - float(cover)
        y_outer_full = flange_width / 2.0 - float(cover)

        top_z1 = float(z_top) + float(cover)
        top_z2 = top_z1 + band
        top_z1 = max(float(cover), top_z1)
        top_z2 = min(float(H) - float(cover), top_z2)
        if top_z2 <= top_z1 + 1e-6:
            top_z2 = top_z1 + 1.0

        bot_z2 = float(z_bottom) - float(cover)
        bot_z1 = bot_z2 - band
        bot_z1 = max(float(cover), bot_z1)
        bot_z2 = min(float(H) - float(cover), bot_z2)
        if bot_z2 <= bot_z1 + 1e-6:
            bot_z2 = bot_z1 + 1.0

        def _ring13_at(xv: float, z1: float, z2: float) -> Tuple[List, List]:
            # 用 band 中点判定是否处于下翼缘范围：下翼缘厚度取 geometry.tf_ll/tf_rl 的最大
            tf_lower = max(float(getattr(self.geometry, "tf_ll", 0.0) or 0.0),
                           float(getattr(self.geometry, "tf_rl", 0.0) or 0.0))
            zmid_band = 0.5 * (float(z1) + float(z2))
            if zmid_band <= (tf_lower - float(cover) + 1e-6):
                y_outer = y_outer_full
            else:
                # 腹板区：外肢靠近腹板，避免跑出混凝土；留 1mm 防止退化为零长度
                y_outer = max(y_inner + 1.0, y_inner)

            # ring13 的“翼缘顶”在局部带内取中点，确保外肢为短肢、内肢贯通带宽
            z_fl = 0.5 * (float(z1) + float(z2))

            # === 创建10个关键节点（与全局 ring13 拓扑一致）===
            n1 = Node(xv, -y_outer, z1)
            n2 = Node(xv, -y_inner, z1)
            n3 = Node(xv,  y_inner, z1)
            n4 = Node(xv,  y_outer, z1)
            n5 = Node(xv, -y_outer, z_fl)
            n6 = Node(xv,  y_outer, z_fl)
            n7 = Node(xv, -y_inner, z_fl)
            n8 = Node(xv,  y_inner, z_fl)
            n9 = Node(xv, -y_inner, z2)
            n10= Node(xv,  y_inner, z2)
            _nodes = [n1,n2,n3,n4,n5,n6,n7,n8,n9,n10]

            # === 13 段闭合（与全局 ring13 一致）===
            _elems = [
                Element([n1.id, n2.id], etype=EleType.Link),
                Element([n2.id, n3.id], etype=EleType.Link),
                Element([n3.id, n4.id], etype=EleType.Link),
                Element([n1.id, n5.id], etype=EleType.Link),
                Element([n4.id, n6.id], etype=EleType.Link),
                Element([n2.id, n7.id], etype=EleType.Link),
                Element([n3.id, n8.id], etype=EleType.Link),
                Element([n5.id, n7.id], etype=EleType.Link),
                Element([n8.id, n6.id], etype=EleType.Link),
                Element([n7.id, n9.id], etype=EleType.Link),
                Element([n8.id, n10.id], etype=EleType.Link),
                Element([n9.id, n10.id], etype=EleType.Link),
                Element([n7.id, n8.id], etype=EleType.Link),  # 封口横筋
            ]
            return _nodes, _elems

        for xv in x_positions:
            # 顶部带 ring13
            ns, es = _ring13_at(float(xv), float(top_z1), float(top_z2))
            nodes.extend(ns); elems_top.extend(es)
            # 底部带 ring13
            ns, es = _ring13_at(float(xv), float(bot_z1), float(bot_z2))
            nodes.extend(ns); elems_bot.extend(es)

        return nodes, elems_top, elems_bot

    def _create_hole_longitudinal_rebars(self, x_start: float, x_end: float,
                                          z: float, y_width: float, count: int,
                                          diameter: float, cover: float) -> Dict:
        """
        创建洞口顶/底的水平补强纵筋

        Args:
            x_start, x_end: X方向范围 (含锚固长度)
            z: Z坐标
            y_width: Y方向宽度 (腹板宽)
            count: 钢筋根数
            diameter: 钢筋直径
            cover: 保护层

        Returns:
            {'nodes': [], 'elements': []}
        """
        nodes = []
        elements = []

        # 计算Y方向位置
        y_positions = self._calculate_rebar_y_positions(y_width, count, cover)

        # 为每根钢筋创建节点和单元
        num_segments = 10  # 分段数
        x_points = [x_start + i * (x_end - x_start) / num_segments for i in range(num_segments + 1)]

        for y in y_positions:
            rebar_nodes = []
            for x in x_points:
                node = Node(x, y, z)
                nodes.append(node)
                rebar_nodes.append(node)

            # 创建Link单元
            for i in range(len(rebar_nodes) - 1):
                elem = Element([rebar_nodes[i].id, rebar_nodes[i+1].id], etype=EleType.Link)
                elements.append(elem)

        return {'nodes': nodes, 'elements': elements}

    def _create_hole_side_i_stirrups(self, x_start: float, x_end: float,
                                     spacing: float,
                                     y_outer: float, y_inner: float,
                                     z_bottom: float,
                                     z_flange_top_left: float, z_flange_top_right: float,
                                     z_top: float,
                                     legs: int, diameter: float) -> Dict:
        """
        洞口两侧加强箍筋：使用与全局一致的工字型 ring13（同高同形）
        """
        nodes = []
        elements = []

        if spacing <= 0:
            return {'nodes': nodes, 'elements': elements}

        x_min = min(x_start, x_end)
        x_max = max(x_start, x_end)
        n = max(1, int((x_max - x_min) / spacing) + 1)
        x_positions = [x_min + i * spacing for i in range(n) if (x_min + i * spacing) <= x_max + 1e-6]

        for x in x_positions:
            ring_nodes, ring_elements = self._create_single_i_shaped_stirrup(
                x=x,
                y_outer=y_outer,
                y_inner=y_inner,
                z_bottom=z_bottom,
                z_flange_top_left=z_flange_top_left,
                z_flange_top_right=z_flange_top_right,
                z_top=z_top,
                legs=legs,
                diameter=diameter
            )
            nodes.extend(ring_nodes)
            elements.extend(ring_elements)

        return {'nodes': nodes, 'elements': elements}

    def _create_hole_side_stirrups(self, x_start: float, x_end: float,
                                    spacing: float, y_width: float,
                                    z_bottom: float, z_top: float,
                                    legs: int, diameter: float, cover: float) -> Dict:
        """
        创建洞口侧边的加强箍筋 (简化矩形箍筋)

        Args:
            x_start, x_end: X方向范围
            spacing: 箍筋间距
            y_width: Y方向宽度 (腹板宽)
            z_bottom, z_top: Z方向范围
            legs: 肢数
            diameter: 直径
            cover: 保护层

        Returns:
            {'nodes': [], 'elements': []}
        """
        nodes = []
        elements = []

        # 计算箍筋X位置
        num_stirrups = max(1, int((x_end - x_start) / spacing) + 1)
        x_positions = [x_start + i * spacing for i in range(num_stirrups) if x_start + i * spacing <= x_end]

        # Y范围
        y_min = -y_width / 2 + cover
        y_max = y_width / 2 - cover

        for x in x_positions:
            # 创建矩形箍筋 (4个角点)
            n1 = Node(x, y_min, z_bottom + cover)  # 左下
            n2 = Node(x, y_max, z_bottom + cover)  # 右下
            n3 = Node(x, y_max, z_top - cover)     # 右上
            n4 = Node(x, y_min, z_top - cover)     # 左上
            nodes.extend([n1, n2, n3, n4])

            # 4条边
            e1 = Element([n1.id, n2.id], etype=EleType.Link)  # 底边
            e2 = Element([n2.id, n3.id], etype=EleType.Link)  # 右边
            e3 = Element([n3.id, n4.id], etype=EleType.Link)  # 顶边
            e4 = Element([n4.id, n1.id], etype=EleType.Link)  # 左边
            elements.extend([e1, e2, e3, e4])

            # 多肢箍筋：添加中间拉筋
            if legs >= 4:
                inner_count = legs - 2
                y_spacing = (y_max - y_min) / (inner_count + 1)
                for j in range(1, inner_count + 1):
                    y_mid = y_min + j * y_spacing
                    n_bot = Node(x, y_mid, z_bottom + cover)
                    n_top = Node(x, y_mid, z_top - cover)
                    nodes.extend([n_bot, n_top])
                    e_mid = Element([n_bot.id, n_top.id], etype=EleType.Link)
                    elements.append(e_mid)

        return {'nodes': nodes, 'elements': elements}


if __name__ == "__main__":
    # 测试代码
    from core.parameters import GeometryParams, LongitudinalRebar, RebarSpec, StirrupParams

    print("=" * 60)
    print("钢筋引擎测试")
    print("=" * 60)

    # 创建几何参数
    geom = GeometryParams(
        L=10000, H=800, Tw=250,
        bf_lu=125, tf_lu=150, bf_ru=125, tf_ru=150,
        bf_ll=125, tf_ll=150, bf_rl=125, tf_rl=150,
        h_pre=500
    )

    # 创建纵向配筋参数
    long_rebar = LongitudinalRebar(
        left_support_top_A=RebarSpec(diameter=25, count=2, extend_length=0),
        left_support_top_B=RebarSpec(diameter=22, count=3, extend_length=3333),
        mid_span_top=RebarSpec(diameter=25, count=2, extend_length=0),
        right_support_top_A=RebarSpec(diameter=25, count=2, extend_length=0),
        right_support_top_B=RebarSpec(diameter=20, count=2, extend_length=3333),
        bottom_through_A=RebarSpec(diameter=25, count=4, extend_length=0),
        bottom_through_B=RebarSpec(diameter=22, count=2, extend_length=0)
    )

    # 创建箍筋参数
    stirrup = StirrupParams(
        dense_zone_length=1500,
        dense_spacing=100,
        dense_legs=4,
        dense_diameter=10,
        normal_spacing=200,
        normal_legs=2,
        normal_diameter=8,
        cover=25
    )

    # 创建钢筋引擎
    engine = RebarEngine(geom)

    # 创建纵向钢筋
    long_result = engine.create_longitudinal_rebars(long_rebar)
    print(f"\n纵向钢筋:")
    print(f"  顶部钢筋单元数: {len(long_result['top_rebars'])}")
    print(f"  底部钢筋单元数: {len(long_result['bottom_rebars'])}")
    print(f"  总节点数: {len(long_result['all_nodes'])}")
    print(f"  总单元数: {len(long_result['all_elements'])}")

    # 创建箍筋
    stirrup_result = engine.create_stirrups(stirrup)
    print(f"\n箍筋:")
    print(f"  加密区箍筋单元数: {len(stirrup_result['dense_stirrups'])}")
    print(f"  非加密区箍筋单元数: {len(stirrup_result['normal_stirrups'])}")
    print(f"  总节点数: {len(stirrup_result['all_nodes'])}")
    print(f"  总单元数: {len(stirrup_result['all_elements'])}")

    print("\n" + "=" * 60)
    print("钢筋引擎测试完成!")
    print("=" * 60)
