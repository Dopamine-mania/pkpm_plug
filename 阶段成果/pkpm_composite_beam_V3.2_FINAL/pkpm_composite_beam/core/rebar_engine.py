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

    @staticmethod
    def _tag_elements_diameter(elements: List, diameter: float) -> None:
        try:
            d = float(diameter)
        except Exception:
            return
        for e in elements or []:
            try:
                setattr(e, "diameter", d)
            except Exception:
                pass

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
                                   cover: float = 25.0,
                                   holes: List[HoleParams] = None) -> Dict[str, List]:
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
            long_rebar, L, H, top_width, cover, left_len, right_len, holes=holes
        )
        all_nodes.extend(top_rebars_result['nodes'])
        all_elements.extend(top_rebars_result['elements'])
        top_rebars.extend(top_rebars_result['elements'])
        top_through = list(top_rebars_result.get('through', []) or [])
        top_left_support_A = list(top_rebars_result.get('left_A', []) or [])
        top_left_support_B = list(top_rebars_result.get('left_B', []) or [])
        top_right_support_A = list(top_rebars_result.get('right_A', []) or [])
        top_right_support_B = list(top_rebars_result.get('right_B', []) or [])

        # 1B. 上翼缘角部纵筋自动补齐（至少两根角筋，避免只在腹板范围布筋）
        top_corner_auto = []
        try:
            y_corner = top_width / 2 - cover
            if y_corner > 1e-6 and getattr(long_rebar, "mid_span_top", None):
                corner_nodes, corner_elems = self._create_rebar_line(
                    x_start=0, x_end=L,
                    z=H - cover,
                    y_positions=[-y_corner, y_corner],
                    diameter=float(long_rebar.mid_span_top.diameter),
                    holes=holes
                )
                all_nodes.extend(corner_nodes)
                all_elements.extend(corner_elems)
                top_rebars.extend(corner_elems)
                top_corner_auto.extend(corner_elems)
        except Exception:
            pass

        # 2. 创建底部通长筋 (考虑翼缘厚度tf)
        bottom_rebars_result = self._create_bottom_rebars(
            long_rebar, L, H, Tw, cover, tf, holes=holes
        )
        all_nodes.extend(bottom_rebars_result['nodes'])
        all_elements.extend(bottom_rebars_result['elements'])
        bottom_rebars.extend(bottom_rebars_result['elements'])
        bottom_through_A = list(bottom_rebars_result.get('through_A', []) or [])
        bottom_through_B = list(bottom_rebars_result.get('through_B', []) or [])

        # 2B. 底部翼缘顶部角部纵筋（z=tf_lower-cover）：角点至少有钢筋（客户反馈）
        # 2B. 底部翼缘顶部角部纵筋仅适用于存在下翼缘的截面
        bottom_corner_auto = []
        try:
            if bf_lower > 1e-6:
                y_corner = bottom_width / 2 - cover
                z_flange_top = max(cover, float(tf) - cover)
                if y_corner > 1e-6 and z_flange_top > cover + 1e-6 and getattr(long_rebar, "bottom_through_A", None):
                    corner_nodes, corner_elems = self._create_rebar_line(
                        x_start=0, x_end=L,
                        z=z_flange_top,
                        y_positions=[-y_corner, y_corner],
                        diameter=float(long_rebar.bottom_through_A.diameter),
                        holes=holes
                    )
                    all_nodes.extend(corner_nodes)
                    all_elements.extend(corner_elems)
                    bottom_rebars.extend(corner_elems)
                    bottom_corner_auto.extend(corner_elems)
        except Exception:
            pass

        return {
            'top_rebars': top_rebars,
            'bottom_rebars': bottom_rebars,
            'all_nodes': all_nodes,
            'all_elements': all_elements,
            # 纵筋分组证据（不含自动角筋）
            'top_through': top_through,
            'top_left_support_A': top_left_support_A,
            'top_left_support_B': top_left_support_B,
            'top_right_support_A': top_right_support_A,
            'top_right_support_B': top_right_support_B,
            'bottom_through_A': bottom_through_A,
            'bottom_through_B': bottom_through_B,
            # 自动角筋（不纳入“通长筋/支座筋”验收计数，避免掩盖缺筋）
            'top_corner_auto': top_corner_auto,
            'bottom_corner_auto': bottom_corner_auto,
        }

    @staticmethod
    def _stacked_zs(base_z: float, rows: int, spacing: float, diameter: float, direction: int) -> List[float]:
        """
        计算多排纵筋的 Z 坐标列表（按中心距叠排）。

        Args:
            base_z: 第1排的Z坐标
            rows: 排数（>=1）
            spacing: 净距(mm)，中心距采用 (dia + spacing)
            diameter: 钢筋直径(mm)
            direction: +1 向上叠排；-1 向下叠排
        """
        try:
            n = max(1, int(rows))
        except Exception:
            n = 1
        try:
            sp = max(0.0, float(spacing))
        except Exception:
            sp = 0.0
        try:
            d = max(0.0, float(diameter))
        except Exception:
            d = 0.0
        step = (d + sp) if d > 1e-6 else sp
        return [float(base_z) + float(direction) * float(i) * float(step) for i in range(n)]

    def _create_top_rebars(self, long_rebar: LongitudinalRebar,
                          L: float, H: float, section_width: float, cover: float,
                          left_len: float, right_len: float,
                          holes: List[HoleParams] = None) -> Dict:
        """
        创建顶部纵向钢筋（支座区 + 跨中区）

        逻辑：
        - 顶部通长筋：0 ~ L（由 long_rebar.mid_span_top 提供；兼容旧模板“Mid Span Top”命名）
        - 左支座附加筋：0 ~ left_len（由 left_support_top_A/B 提供）
        - 右支座附加筋：(L - right_len) ~ L（由 right_support_top_A/B 提供）

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
        # 证据化分组（用于验收：通长筋 vs 支座附加筋独立）
        through = []
        left_A = []
        left_B = []
        right_A = []
        right_B = []

        # 顶部钢筋 Z 坐标（距顶面 cover）；支持多排叠排（向下）
        z_top_base = H - cover

        # 1) 顶部通长筋（全跨）
        z_top_list_through = self._stacked_zs(
            base_z=z_top_base,
            rows=getattr(long_rebar, "top_rows", 1),
            spacing=getattr(long_rebar, "top_row_spacing", 0.0),
            diameter=float(long_rebar.mid_span_top.diameter),
            direction=-1,
        )
        for z_top in z_top_list_through:
            through_nodes, through_elems = self._create_rebar_line(
                x_start=0, x_end=L,
                z=z_top, y_positions=self._calculate_rebar_y_positions(
                    section_width, long_rebar.mid_span_top.count, cover
                ),
                diameter=long_rebar.mid_span_top.diameter,
                holes=holes
            )
            nodes.extend(through_nodes)
            elements.extend(through_elems)
            through.extend(through_elems)

        # 2) 左支座附加筋
        if getattr(long_rebar, "left_support_top_A", None):
            z_top_list_la = self._stacked_zs(
                base_z=z_top_base,
                rows=getattr(long_rebar, "top_rows", 1),
                spacing=getattr(long_rebar, "top_row_spacing", 0.0),
                diameter=float(long_rebar.left_support_top_A.diameter),
                direction=-1,
            )
            for z_top in z_top_list_la:
                left_a_nodes, left_a_elems = self._create_rebar_line(
                    x_start=0, x_end=left_len,
                    z=z_top, y_positions=self._calculate_rebar_y_positions(
                        section_width, long_rebar.left_support_top_A.count, cover
                    ),
                    diameter=long_rebar.left_support_top_A.diameter,
                    holes=holes
                )
                nodes.extend(left_a_nodes)
                elements.extend(left_a_elems)
                left_A.extend(left_a_elems)

        # 左支座 B 组（附加筋，如果有）
        if long_rebar.left_support_top_B:
            extend_len = long_rebar.left_support_top_B.extend_length
            z_top_list_b = self._stacked_zs(
                base_z=z_top_base,
                rows=getattr(long_rebar, "top_rows", 1),
                spacing=getattr(long_rebar, "top_row_spacing", 0.0),
                diameter=float(long_rebar.left_support_top_B.diameter),
                direction=-1,
            )
            for z_top in z_top_list_b:
                left_b_nodes, left_b_elems = self._create_rebar_line(
                    x_start=0, x_end=min(left_len + extend_len, L),
                    z=z_top, y_positions=self._calculate_rebar_y_positions(
                        section_width, long_rebar.left_support_top_B.count, cover,
                        offset=(long_rebar.left_support_top_A.count if getattr(long_rebar, "left_support_top_A", None) else 0)
                    ),
                    diameter=long_rebar.left_support_top_B.diameter,
                    holes=holes
                )
                nodes.extend(left_b_nodes)
                elements.extend(left_b_elems)
                left_B.extend(left_b_elems)

        # 3) 右支座附加筋
        if getattr(long_rebar, "right_support_top_A", None):
            z_top_list_ra = self._stacked_zs(
                base_z=z_top_base,
                rows=getattr(long_rebar, "top_rows", 1),
                spacing=getattr(long_rebar, "top_row_spacing", 0.0),
                diameter=float(long_rebar.right_support_top_A.diameter),
                direction=-1,
            )
            for z_top in z_top_list_ra:
                right_a_nodes, right_a_elems = self._create_rebar_line(
                    x_start=L - right_len, x_end=L,
                    z=z_top, y_positions=self._calculate_rebar_y_positions(
                        section_width, long_rebar.right_support_top_A.count, cover
                    ),
                    diameter=long_rebar.right_support_top_A.diameter,
                    holes=holes
                )
                nodes.extend(right_a_nodes)
                elements.extend(right_a_elems)
                right_A.extend(right_a_elems)

        # 右支座 B 组（附加筋，如果有）
        if long_rebar.right_support_top_B:
            extend_len = long_rebar.right_support_top_B.extend_length
            z_top_list_rb = self._stacked_zs(
                base_z=z_top_base,
                rows=getattr(long_rebar, "top_rows", 1),
                spacing=getattr(long_rebar, "top_row_spacing", 0.0),
                diameter=float(long_rebar.right_support_top_B.diameter),
                direction=-1,
            )
            for z_top in z_top_list_rb:
                right_b_nodes, right_b_elems = self._create_rebar_line(
                    x_start=max(L - right_len - extend_len, 0), x_end=L,
                    z=z_top, y_positions=self._calculate_rebar_y_positions(
                        section_width, long_rebar.right_support_top_B.count, cover,
                        offset=(long_rebar.right_support_top_A.count if getattr(long_rebar, "right_support_top_A", None) else 0)
                    ),
                    diameter=long_rebar.right_support_top_B.diameter,
                    holes=holes
                )
                nodes.extend(right_b_nodes)
                elements.extend(right_b_elems)
                right_B.extend(right_b_elems)

        return {
            'nodes': nodes,
            'elements': elements,
            'through': through,
            'left_A': left_A,
            'left_B': left_B,
            'right_A': right_A,
            'right_B': right_B,
        }

    def _create_bottom_rebars(self, long_rebar: LongitudinalRebar,
                             L: float, H: float, Tw: float, cover: float, tf: float,
                             holes: List[HoleParams] = None) -> Dict:
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
        through_A = []
        through_B = []

        # 底部受拉主筋：第1排Z坐标 = 底部保护层厚度；支持多排叠排（向上）
        z_bottom_base = cover  # 25~30mm，在翼缘实体内

        # 【关键修正】底筋分布在翼缘总宽内，不是腹板宽
        # 翼缘总宽 = Tw + 2*bf
        # 翼缘伸出宽度：必须使用几何参数本身，不能用“200mm 默认值”覆盖（否则会把底筋放到混凝土外）
        bf = max(self.geometry.bf_ll, self.geometry.bf_rl, 0.0)
        flange_width = Tw + 2 * bf  # 翼缘总宽（如 250+2*200=650mm）

        # 底部 A 组（通长，从0到L，Y分布在翼缘总宽内）
        z_bottom_list_a = self._stacked_zs(
            base_z=z_bottom_base,
            rows=getattr(long_rebar, "bottom_rows", 1),
            spacing=getattr(long_rebar, "bottom_row_spacing", 0.0),
            diameter=float(long_rebar.bottom_through_A.diameter),
            direction=+1,
        )
        for z_bottom in z_bottom_list_a:
            bottom_a_nodes, bottom_a_elems = self._create_rebar_line(
                x_start=0, x_end=L,
                z=z_bottom, y_positions=self._calculate_rebar_y_positions(
                    flange_width, long_rebar.bottom_through_A.count, cover
                ),
                diameter=long_rebar.bottom_through_A.diameter,
                holes=holes
            )
            nodes.extend(bottom_a_nodes)
            elements.extend(bottom_a_elems)
            through_A.extend(bottom_a_elems)

        # 底部 B 组（如果有，也是通长，Y分布在翼缘总宽内）
        if long_rebar.bottom_through_B and long_rebar.bottom_through_B.count > 0:
            z_bottom_list_b = self._stacked_zs(
                base_z=z_bottom_base,
                rows=getattr(long_rebar, "bottom_rows", 1),
                spacing=getattr(long_rebar, "bottom_row_spacing", 0.0),
                diameter=float(long_rebar.bottom_through_B.diameter),
                direction=+1,
            )
            for z_bottom in z_bottom_list_b:
                bottom_b_nodes, bottom_b_elems = self._create_rebar_line(
                    x_start=0, x_end=L,
                    z=z_bottom, y_positions=self._calculate_rebar_y_positions(
                        flange_width, long_rebar.bottom_through_B.count, cover,
                        offset=long_rebar.bottom_through_A.count
                    ),
                    diameter=long_rebar.bottom_through_B.diameter,
                    holes=holes
                )
                nodes.extend(bottom_b_nodes)
                elements.extend(bottom_b_elems)
                through_B.extend(bottom_b_elems)

        return {'nodes': nodes, 'elements': elements, 'through_A': through_A, 'through_B': through_B}

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

        # 多根钢筋等间距分布（默认：端点落在保护层内侧）
        spacing = effective_width / (count - 1)
        y_positions = [-effective_width / 2 + i * spacing for i in range(count)]

        # 附加筋避开主筋：用“合并后的等分序列”选取未被主筋占用的位置（保持对称、且不突破保护层）
        if offset > 0:
            total = int(count) + int(offset)
            if total >= 2 and offset >= 2:
                all_spacing = effective_width / (total - 1)
                all_pos = [-effective_width / 2 + i * all_spacing for i in range(total)]
                used = {
                    int(round(i * (total - 1) / (offset - 1)))
                    for i in range(offset)
                }
                cand = [all_pos[i] for i in range(total) if i not in used]
                if len(cand) == count:
                    y_positions = cand

        return y_positions

    def _create_rebar_line(self, x_start: float, x_end: float,
                          z: float, y_positions: List[float],
                          diameter: float, num_segments: int = 30,
                          holes: List[HoleParams] = None) -> Tuple[List, List]:
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

        # 洞口避让：钢筋不得穿过洞口真空区域（hole_void 内不允许出现任何钢筋线段）
        Tw = float(getattr(self.geometry, "Tw", 0.0) or 0.0)
        hole_pad = float(getattr(self, "HOLE_EDGE_CLEARANCE", 2.0) or 2.0)
        hole_spans = []
        if holes:
            for h in holes:
                try:
                    x0, x1, z0, z1 = h.get_bounds()
                    hole_spans.append((float(x0) - hole_pad, float(x1) + hole_pad,
                                       float(z0) - hole_pad, float(z1) + hole_pad))
                except Exception:
                    continue

        def _seg_hits_hole(xa: float, xb: float, yv: float, zv: float) -> bool:
            if not hole_spans:
                return False
            # 洞口贯通腹板厚度（Y方向），仅需判断该筋是否落在腹板厚度范围内
            if Tw <= 1e-6 or abs(float(yv)) > (Tw / 2.0 - 1e-6):
                return False
            for hx0, hx1, hz0, hz1 in hole_spans:
                # 纵筋为常Z线：只要其 z 落在洞口高度范围内，即视为穿洞
                if float(zv) <= hz0 + 1e-6 or float(zv) >= hz1 - 1e-6:
                    continue
                lo = min(float(xa), float(xb))
                hi = max(float(xa), float(xb))
                if hi > hx0 + 1e-6 and lo < hx1 - 1e-6:
                    return True
            return False

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
                xa = float(rebar_nodes[i].x)
                xb = float(rebar_nodes[i + 1].x)
                if _seg_hits_hole(xa, xb, float(y), float(z)):
                    continue
                elem = Element([rebar_nodes[i].id, rebar_nodes[i+1].id], etype=EleType.Link)
                try:
                    elem.diameter = float(diameter)
                except Exception:
                    pass
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

        # 【关键】下翼缘参数（左右独立，用于自适应箍筋“外侧短肢”高度）
        bf_ll = float(getattr(self.geometry, "bf_ll", 0.0) or 0.0)
        bf_rl = float(getattr(self.geometry, "bf_rl", 0.0) or 0.0)
        tf_ll = float(getattr(self.geometry, "tf_ll", 0.0) or 0.0)
        tf_rl = float(getattr(self.geometry, "tf_rl", 0.0) or 0.0)
        bf_lower = max(bf_ll, bf_rl, 0.0)
        # 下翼缘总宽（用于“下翼缘外侧短肢”）
        flange_width_lower = Tw + 2.0 * bf_lower

        # 【关键修正】箍筋Y坐标分布
        # - 若存在下翼缘：外侧肢 Y = ±(下翼缘宽/2 - cover)
        # - 若不存在下翼缘（T梁等）：退化为腹板矩形箍筋（y_outer=y_inner），避免出现“外肢跑到混凝土外面”
        y_outer = flange_width_lower / 2.0 - cover if bf_lower > 1e-6 else (Tw / 2.0 - cover)
        y_inner = Tw / 2 - cover            # 100mm (内侧肢Y坐标)

        # 箍筋Z坐标 - 自适应高度
        z_bottom = cover                           # 底部Z=25mm
        # 外侧短肢仅在“下翼缘厚度范围”内存在；没有下翼缘则高度退化到 z_bottom
        z_flange_top_left = (tf_ll - cover) if (bf_ll > 1e-6 and tf_ll > cover + 1e-6) else z_bottom
        z_flange_top_right = (tf_rl - cover) if (bf_rl > 1e-6 and tf_rl > cover + 1e-6) else z_bottom
        z_top = H - cover                          # 顶部Z=775mm

        # 箍筋高度分段（用于调试输出）
        print(f">>> 【箍筋参数】Y外侧={y_outer:.1f}mm, Y内侧={y_inner:.1f}mm")
        print(f">>> 【箍筋参数】Z底={z_bottom:.1f}mm, Z翼缘顶左={z_flange_top_left:.1f}mm, Z翼缘顶右={z_flange_top_right:.1f}mm, Z顶={z_top:.1f}mm")

        all_nodes = []
        all_elements = []
        dense_stirrups = []
        normal_stirrups = []

        # 洞口避让：洞宽范围内屏蔽全局箍筋（仅允许洞口补强筋出现）
        # 额外扩大 2mm：避免箍筋恰好落在洞口边界线上（客户反馈：洞口中心不允许钢筋穿过）
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

        # 2肢箍筋：按腹板矩形闭合（不引入外侧短肢/中间横筋）
        # 无下翼缘（T梁等）：同样退化为腹板矩形闭合箍筋，避免“外侧短肢”越界
        if int(legs) <= 2 or abs(float(y_outer) - float(y_inner)) <= 1e-6:
            n1 = Node(x, -y_inner, z_bottom)
            n2 = Node(x,  y_inner, z_bottom)
            n3 = Node(x,  y_inner, z_top)
            n4 = Node(x, -y_inner, z_top)
            nodes.extend([n1, n2, n3, n4])
            elements.extend([
                Element([n1.id, n2.id], etype=EleType.Link),
                Element([n2.id, n3.id], etype=EleType.Link),
                Element([n3.id, n4.id], etype=EleType.Link),
                Element([n4.id, n1.id], etype=EleType.Link),
            ])
            self._tag_elements_diameter(elements, diameter)

            # 4肢及以上：添加中间内拉筋（贯通全高）
            if int(legs) >= 4:
                inner_leg_count = legs - 2
                if inner_leg_count > 0:
                    inner_spacing = (2 * y_inner) / (inner_leg_count + 1)
                    for i in range(1, inner_leg_count + 1):
                        y_mid = -y_inner + i * inner_spacing
                        n_mid_bottom = Node(x, y_mid, z_bottom)
                        n_mid_top = Node(x, y_mid, z_top)
                        nodes.extend([n_mid_bottom, n_mid_top])
                        e_mid = Element([n_mid_bottom.id, n_mid_top.id], etype=EleType.Link)
                        try:
                            e_mid.diameter = float(diameter)
                        except Exception:
                            pass
                        elements.append(e_mid)

            # 20260203 客户反馈：非加密区缺少翼缘箍筋
            # - 即使按“2肢/腹板矩形”退化，也需要在下翼缘范围补一个闭合环，保证洞口范围外翼缘箍筋不缺失。
            # - 仅在确实存在下翼缘高度（z_flange_top > z_bottom）且 y_outer != y_inner 时启用。
            try:
                if abs(float(y_outer) - float(y_inner)) > 1e-6:
                    zf = min(float(z_flange_top_left), float(z_flange_top_right))
                    if zf > float(z_bottom) + 1e-6:
                        f1 = Node(x, -float(y_outer), float(z_bottom))
                        f2 = Node(x, float(y_outer), float(z_bottom))
                        f3 = Node(x, float(y_outer), float(zf))
                        f4 = Node(x, -float(y_outer), float(zf))
                        nodes.extend([f1, f2, f3, f4])
                        flange_elems = [
                            Element([f1.id, f2.id], etype=EleType.Link),
                            Element([f2.id, f3.id], etype=EleType.Link),
                            Element([f3.id, f4.id], etype=EleType.Link),
                            Element([f4.id, f1.id], etype=EleType.Link),
                        ]
                        self._tag_elements_diameter(flange_elems, diameter)
                        elements.extend(flange_elems)
            except Exception:
                pass

            # 上翼缘闭合环：仍按原逻辑补齐（若存在上翼缘）
            try:
                g = self.geometry
                H = float(getattr(g, "H", 0.0) or 0.0)
                Tw = float(getattr(g, "Tw", 0.0) or 0.0)
                cover_est = Tw / 2.0 - float(y_inner)
                bf_upper = max(float(getattr(g, "bf_lu", 0.0) or 0.0), float(getattr(g, "bf_ru", 0.0) or 0.0))
                tf_upper = max(float(getattr(g, "tf_lu", 0.0) or 0.0), float(getattr(g, "tf_ru", 0.0) or 0.0))
                if bf_upper > 1e-6 and tf_upper > 1e-6 and cover_est > 0:
                    top_width = (Tw + 2.0 * bf_upper) if bf_upper > 1e-6 else Tw
                    y_outer_upper = top_width / 2.0 - cover_est
                    z_upper_bottom = H - tf_upper + cover_est
                    if y_outer_upper > float(y_inner) + 1e-6 and (z_top - z_upper_bottom) > 1e-6:
                        u1 = Node(x, -y_outer_upper, z_upper_bottom)
                        u2 = Node(x, y_outer_upper, z_upper_bottom)
                        u3 = Node(x, -y_outer_upper, z_top)
                        u4 = Node(x, y_outer_upper, z_top)
                        nodes.extend([u1, u2, u3, u4])
                        _up_elems = [
                            Element([u1.id, u2.id], etype=EleType.Link),
                            Element([u2.id, u4.id], etype=EleType.Link),
                            Element([u4.id, u3.id], etype=EleType.Link),
                            Element([u3.id, u1.id], etype=EleType.Link),
                        ]
                        self._tag_elements_diameter(_up_elems, diameter)
                        elements.extend(_up_elems)
            except Exception:
                pass

            return nodes, elements

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

        # 20260203 客户反馈：加密区翼缘顶部在腹板范围未闭合
        # - 对“左右下翼缘顶标高一致”的情况，在 z=z_flange_top 处补一段贯通翼缘宽度的顶边（E->F），保证翼缘箍筋闭合观感。
        # - 若左右翼缘顶高度不一致（非对称截面），不补这条斜边，避免生成穿越实体外的斜杆。
        e13 = None
        try:
            if abs(float(z_flange_top_left) - float(z_flange_top_right)) <= 1e-6:
                e13 = Element([n5.id, n6.id], etype=EleType.Link)  # 翼缘顶贯通边
        except Exception:
            e13 = None

        # 顶部横向边（腹板宽度）
        e10 = Element([n9.id, n10.id], etype=EleType.Link)  # 顶边

        # 注：不在 z=z_flange_top 处额外添加横向连筋，避免出现“多一条水平钢筋/中间横线”的观感与肢数歧义
        base_elems = [e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12]
        if e13 is not None:
            base_elems.append(e13)
        elements.extend(base_elems)
        self._tag_elements_diameter(elements, diameter)

        # === 多肢箍筋：添加中间内肢（避免把 4 肢误生成成 6 肢）===
        # 约定：
        # - 工字/倒T等存在下翼缘外肢时，基础肢数=4（±y_outer 外肢 + ±y_inner 内肢）
        # - 无下翼缘时退化为腹板矩形，基础肢数=2（±y_inner）
        # legs 表示“目标总肢数”，不足基础肢数时按基础肢数处理。
        try:
            legs_req = int(legs)
        except Exception:
            legs_req = 0
        base_legs = 4 if abs(float(y_outer) - float(y_inner)) > 1e-6 else 2
        legs_eff = max(base_legs, legs_req)
        inner_leg_count = max(0, int(legs_eff) - int(base_legs))
        if inner_leg_count > 0 and float(y_inner) > 1e-6:
            inner_spacing = (2.0 * float(y_inner)) / float(inner_leg_count + 1)
            for i in range(1, inner_leg_count + 1):
                y_mid = -float(y_inner) + float(i) * float(inner_spacing)
                # 中间内肢：从底部贯通到顶部（不添加任何中间横向连杆）
                n_mid_bottom = Node(x, y_mid, z_bottom)
                n_mid_top = Node(x, y_mid, z_top)
                nodes.extend([n_mid_bottom, n_mid_top])
                e_mid = Element([n_mid_bottom.id, n_mid_top.id], etype=EleType.Link)
                try:
                    e_mid.diameter = float(diameter)
                except Exception:
                    pass
                elements.append(e_mid)

        # === 20260119 客户反馈：补齐“上部箍筋”（上翼缘范围的闭合环）===
        # 说明：原 ring13 的外侧短肢仅在下翼缘范围内；此处为上翼缘补一个“闭合矩形环”，
        # 仅位于上翼缘厚度范围内（不影响原 ring13 13段自检）。
        try:
            g = self.geometry
            H = float(getattr(g, "H", 0.0) or 0.0)
            Tw = float(getattr(g, "Tw", 0.0) or 0.0)
            # 由 y_inner 反推 cover（y_inner = Tw/2 - cover）
            cover_est = Tw / 2.0 - float(y_inner)
            bf_upper = max(float(getattr(g, "bf_lu", 0.0) or 0.0), float(getattr(g, "bf_ru", 0.0) or 0.0))
            tf_upper = max(float(getattr(g, "tf_lu", 0.0) or 0.0), float(getattr(g, "tf_ru", 0.0) or 0.0))
            if bf_upper > 1e-6 and tf_upper > 1e-6 and cover_est > 0:
                top_width = (Tw + 2.0 * bf_upper) if bf_upper > 1e-6 else Tw
                y_outer_upper = top_width / 2.0 - cover_est
                z_upper_bottom = H - tf_upper + cover_est
                # 需要至少留出 2*cover 的实体厚度
                if y_outer_upper > float(y_inner) + 1e-6 and (z_top - z_upper_bottom) > 1e-6:
                    u1 = Node(x, -y_outer_upper, z_upper_bottom)
                    u2 = Node(x, y_outer_upper, z_upper_bottom)
                    u3 = Node(x, -y_outer_upper, z_top)
                    u4 = Node(x, y_outer_upper, z_top)
                    nodes.extend([u1, u2, u3, u4])
                    _up_elems = [
                        Element([u1.id, u2.id], etype=EleType.Link),  # 上翼缘底边
                        Element([u2.id, u4.id], etype=EleType.Link),  # 右竖边
                        Element([u4.id, u3.id], etype=EleType.Link),  # 上翼缘顶边
                        Element([u3.id, u1.id], etype=EleType.Link),  # 左竖边
                    ]
                    self._tag_elements_diameter(_up_elems, diameter)
                    elements.extend(_up_elems)
        except Exception:
            pass

        return nodes, elements

    # ========== 洞口加强筋 ==========
    def create_hole_reinforcement(self, hole, tf_lower: float, cover: float = 25.0) -> Dict:
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
        try:
            cover = float(cover)
        except Exception:
            cover = 25.0
        cover = max(0.0, cover)

        # 洞口几何
        hx = hole.x                    # 洞口中心X
        hz = hole.z                    # 洞口中心Z
        hw = hole.width                # 洞口宽度
        hh = hole.height               # 洞口高度

        # 洞口边界
        x_left = hx - hw / 2           # 洞口左边
        x_right = hx + hw / 2          # 洞口右边
        z_bottom_raw = hz - hh / 2     # 洞口底(原始)
        z_top_raw = hz + hh / 2        # 洞口顶(原始)
        # 与几何开孔保持一致：洞口底边不得低于下翼缘顶(tf_lower)，无下翼缘时至少不贴到底面(>=cover+1mm)
        try:
            tf_lower = float(tf_lower)
        except Exception:
            tf_lower = 0.0
        z_bottom = max(float(z_bottom_raw), float(tf_lower), float(cover) + 1.0)
        if abs(float(z_bottom) - float(tf_lower)) <= 1e-6 and float(tf_lower) > (float(cover) + 1.0 + 1e-6):
            z_bottom = float(z_bottom) + 1.0
        z_top = float(z_top_raw)
        edge_clear = float(self.HOLE_EDGE_CLEARANCE)

        # 1. 创建洞口顶底纵筋（小梁纵筋）：支持顶/底分别配置（新字段为0则回退旧字段）
        top_long_dia = float(getattr(hole, "small_beam_long_top_diameter", 0.0) or 0.0)
        top_long_cnt = int(getattr(hole, "small_beam_long_top_count", 0) or 0)
        bot_long_dia = float(getattr(hole, "small_beam_long_bottom_diameter", 0.0) or 0.0)
        bot_long_cnt = int(getattr(hole, "small_beam_long_bottom_count", 0) or 0)
        legacy_dia = float(getattr(hole, "small_beam_long_diameter", 0.0) or 0.0)
        legacy_cnt = int(getattr(hole, "small_beam_long_count", 0) or 0)
        if top_long_cnt <= 0 or top_long_dia <= 0:
            top_long_cnt, top_long_dia = legacy_cnt, legacy_dia
        if bot_long_cnt <= 0 or bot_long_dia <= 0:
            bot_long_cnt, bot_long_dia = legacy_cnt, legacy_dia

        if (top_long_cnt > 0 and top_long_dia > 0) or (bot_long_cnt > 0 and bot_long_dia > 0):
            extend = hole.reinf_extend_length if hole.reinf_extend_length > 0 else 300  # 默认锚固300mm

            # 防呆：洞口靠近梁顶/梁底时，纵筋标高不能越出混凝土外表面
            # 顶部纵筋：理想位置=洞口顶面上方 cover；若超出梁顶保护层位置，则下压到 H-cover
            z_top_bar_raw = float(z_top) + float(cover)
            z_top_bar_max = float(H) - float(cover)
            z_top_bar = min(z_top_bar_raw, z_top_bar_max)
            # 底部纵筋：理想位置=洞口底面下方 cover；若低于梁底保护层位置，则上抬到 cover
            z_bot_bar_raw = float(z_bottom) - float(cover)
            z_bot_bar_min = float(cover)
            z_bot_bar = max(z_bot_bar_raw, z_bot_bar_min)
            if abs(z_top_bar - z_top_bar_raw) > 1e-6:
                print(f">>> 警告: 洞口顶纵筋标高超出梁顶，已调整: raw={z_top_bar_raw:.1f} -> {z_top_bar:.1f} (H={H:.1f}, cover={cover:.1f})")
            if abs(z_bot_bar - z_bot_bar_raw) > 1e-6:
                print(f">>> 警告: 洞口底纵筋标高低于梁底，已调整: raw={z_bot_bar_raw:.1f} -> {z_bot_bar:.1f} (cover={cover:.1f})")

            if top_long_cnt > 0 and top_long_dia > 0:
                top_result = self._create_hole_longitudinal_rebars(
                    x_start=x_left - extend,
                    x_end=x_right + extend,
                    z=z_top_bar,  # 洞口顶面上方（必要时下压到梁顶保护层）
                    y_width=Tw,
                    count=top_long_cnt,
                    diameter=top_long_dia,
                    cover=cover,
                    holes=[hole]
                )
                all_nodes.extend(top_result['nodes'])
                all_elements.extend(top_result['elements'])
                top_long_rebars.extend(top_result['elements'])

            if bot_long_cnt > 0 and bot_long_dia > 0:
                bottom_result = self._create_hole_longitudinal_rebars(
                    x_start=x_left - extend,
                    x_end=x_right + extend,
                    z=z_bot_bar,  # 洞口底面下方（必要时上抬到梁底保护层）
                    y_width=Tw,
                    count=bot_long_cnt,
                    diameter=bot_long_dia,
                    cover=cover,
                    holes=[hole]
                )
                all_nodes.extend(bottom_result['nodes'])
                all_elements.extend(bottom_result['elements'])
                bottom_long_rebars.extend(bottom_result['elements'])

            print(f">>> 【洞口补强】顶纵筋: {top_long_cnt}根 x Φ{top_long_dia}, 底纵筋: {bot_long_cnt}根 x Φ{bot_long_dia}, 锚固{extend}mm")

        # 2. 创建洞口侧边加强箍筋
        if hole.side_stirrup_spacing > 0 and hole.side_stirrup_diameter > 0:
            # 【客户反馈】洞口两侧加强箍筋的高度应与全局箍筋一致：贯通梁顶/梁底
            # 这里采用工字型 ring13 形状（与全局箍筋同形同高），仅在洞口两侧加密范围内生成。
            bf_ll = float(getattr(self.geometry, "bf_ll", 0.0) or 0.0)
            bf_rl = float(getattr(self.geometry, "bf_rl", 0.0) or 0.0)
            bf_lower = max(bf_ll, bf_rl, 0.0)
            flange_width_lower = Tw + 2.0 * bf_lower
            y_outer = flange_width_lower / 2.0 - cover if bf_lower > 1e-6 else (Tw / 2.0 - cover)
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
            try:
                sb_legs = int(getattr(hole, "small_beam_stirrup_legs", 0) or 0)
            except Exception:
                sb_legs = 0
            if sb_legs <= 0:
                sb_legs = 4
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
                legs=int(sb_legs),
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
                                        legs: int = 4,
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

        # 洞顶/洞底“小梁箍筋”：
        # - 作为洞口上下两个“独立小梁”的箍筋笼，禁止任何钢筋线段穿过洞口真空区
        # - 顶部带：洞顶 + cover -> 梁顶 - cover
        # - 底部带：梁底 + cover -> 洞底 - cover（贯通到梁底，并包住下翼缘混凝土）
        try:
            legs_req = int(legs)
        except Exception:
            legs_req = 4
        legs_eff = max(2, legs_req)

        y_web = float(self.geometry.Tw) / 2.0 - float(cover)
        # 底部带外包宽度：若存在下翼缘，外包到下翼缘外侧；否则外包到腹板
        bf_ll = float(getattr(self.geometry, "bf_ll", 0.0) or 0.0)
        bf_rl = float(getattr(self.geometry, "bf_rl", 0.0) or 0.0)
        bf_lower = max(bf_ll, bf_rl, 0.0)
        y_outer_bot = (float(self.geometry.Tw) + 2.0 * float(bf_lower)) / 2.0 - float(cover) if bf_lower > 1e-6 else float(y_web)

        top_z2 = float(H) - float(cover)
        top_z1_raw = float(z_top) + float(cover)
        top_z1 = max(float(cover), min(top_z1_raw, top_z2))
        top_enabled = (top_z2 > top_z1 + 1e-6)

        bot_z1 = float(cover)
        bot_z2_raw = float(z_bottom) - float(cover)
        bot_z2 = max(bot_z1 + 1.0, min(float(H) - float(cover), bot_z2_raw))
        bot_enabled = (bot_z2 > bot_z1 + 1e-6)

        def _y_positions_for_top() -> List[float]:
            if legs_eff <= 2 or y_web <= 1e-6:
                return [-y_web, y_web]
            k = legs_eff - 2
            step = (2.0 * y_web) / float(k + 1)
            mids = [(-y_web + float(i) * step) for i in range(1, k + 1)]
            return [float(-y_web)] + [float(round(v, 6)) for v in mids] + [float(y_web)]

        def _y_positions_for_bottom() -> List[float]:
            # 无下翼缘或要求<=2肢：外包到 y_outer_bot（此时 y_outer_bot==y_web 或退化）
            if legs_eff <= 2 or y_outer_bot <= 1e-6:
                return [-y_outer_bot, y_outer_bot]
            k = legs_eff - 2
            step = (2.0 * y_outer_bot) / float(k + 1)
            mids = [(-y_outer_bot + float(i) * step) for i in range(1, k + 1)]
            return [float(-y_outer_bot)] + [float(round(v, 6)) for v in mids] + [float(y_outer_bot)]

        def _y_positions_inner_web(nlegs: int) -> List[float]:
            nlegs = max(2, int(nlegs))
            if nlegs <= 2 or y_web <= 1e-6:
                return [-y_web, y_web]
            k = nlegs - 2
            step = (2.0 * y_web) / float(k + 1)
            mids = [(-y_web + float(i) * step) for i in range(1, k + 1)]
            return [float(-y_web)] + [float(round(v, 6)) for v in mids] + [float(y_web)]

        def _multi_leg_ring_at(xv: float, z1: float, z2: float, y_positions: List[float]) -> Tuple[List, List]:
            ys = [float(v) for v in (y_positions or [])]
            ys = sorted(set(round(v, 6) for v in ys))
            if len(ys) < 2:
                ys = [-y_web, y_web]

            nb = [Node(xv, float(yv), float(z1)) for yv in ys]
            nt = [Node(xv, float(yv), float(z2)) for yv in ys]
            _nodes = nb + nt
            _elems: List = []

            # 底部横向：分段连接，内部节点用于“内肢落点”
            for i in range(len(nb) - 1):
                _elems.append(Element([nb[i].id, nb[i + 1].id], etype=EleType.Link))
            # 顶部横向：分段连接
            for i in range(len(nt) - 1):
                _elems.append(Element([nt[i].id, nt[i + 1].id], etype=EleType.Link))
            # 竖向肢：每个 y 一个竖向单元
            for i in range(len(nb)):
                _elems.append(Element([nb[i].id, nt[i].id], etype=EleType.Link))

            self._tag_elements_diameter(_elems, diameter)
            return _nodes, _elems

        for xv in x_positions:
            # 顶部带（无空间则跳过）
            if top_enabled:
                ns, es = _multi_leg_ring_at(float(xv), float(top_z1), float(top_z2), _y_positions_for_top())
                nodes.extend(ns); elems_top.extend(es)
            # 底部带
            if bot_enabled:
                # 关键：下翼缘外肢（±y_outer_bot）仅应出现在下翼缘高度范围内；
                # 若直接把外肢贯通到 bot_z2（通常 > tf_lower-cover），会在“上部腹板窄区”越出混凝土，触发 PKPM: rebar.within_concrete.y_by_z。
                tf_ll = float(getattr(self.geometry, "tf_ll", 0.0) or 0.0)
                tf_rl = float(getattr(self.geometry, "tf_rl", 0.0) or 0.0)
                tf_lower = max(tf_ll, tf_rl, 0.0)
                z_step = max(float(bot_z1) + 1.0, min(float(bot_z2), float(tf_lower) - float(cover))) if tf_lower > 1e-6 else float(bot_z1)

                stepped = (y_outer_bot > y_web + 1e-6) and (legs_eff >= 4) and (z_step > float(bot_z1) + 1e-6) and (z_step < float(bot_z2) - 1e-6)
                if stepped:
                    # “总肢数(含外肢)”口径：外肢 2 根（仅在下翼缘范围），其余肢为腹板内肢（贯通到 bot_z2）
                    inner_legs = max(2, int(legs_eff) - 2)
                    ns1, es1 = _multi_leg_ring_at(float(xv), float(bot_z1), float(bot_z2), _y_positions_inner_web(inner_legs))
                    ns2, es2 = _multi_leg_ring_at(float(xv), float(bot_z1), float(z_step), [-float(y_outer_bot), float(y_outer_bot)])
                    nodes.extend(ns1 + ns2)
                    elems_bot.extend(es1 + es2)
                else:
                    ns, es = _multi_leg_ring_at(float(xv), float(bot_z1), float(bot_z2), _y_positions_for_bottom())
                    nodes.extend(ns); elems_bot.extend(es)

        return nodes, elems_top, elems_bot

    def _create_hole_longitudinal_rebars(self, x_start: float, x_end: float,
                                          z: float, y_width: float, count: int,
                                          diameter: float, cover: float,
                                          holes: List[HoleParams] = None) -> Dict:
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
        # 计算Y方向位置
        y_positions = self._calculate_rebar_y_positions(y_width, count, cover)

        # 复用通用纵筋生成（含洞口真空区避让）
        nodes, elements = self._create_rebar_line(
            x_start=float(x_start),
            x_end=float(x_end),
            z=float(z),
            y_positions=[float(v) for v in (y_positions or [])],
            diameter=float(diameter),
            num_segments=10,
            holes=holes
        )
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
            self._tag_elements_diameter([e1, e2, e3, e4], diameter)

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
                    try:
                        e_mid.diameter = float(diameter)
                    except Exception:
                        pass
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
