"""
PKPM-CAE 叠合梁参数化建模 - 简化几何引擎 (T+3 版本)
先实现矩形截面，验证叠合层切分逻辑
"""

from typing import List, Dict
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pypcae.comp import Node, Line, Surf, Solid
    from pypcae.stru import StruModel
    from pypcae.enums import *
except ImportError:
    print("警告: PyPCAE 模块未安装，使用模拟模式")
    # 模拟类用于开发测试
    class Node:
        _id_counter = 1
        def __init__(self, x, y, z):
            self.x, self.y, self.z = x, y, z
            self.id = Node._id_counter
            Node._id_counter += 1

    class Line:
        _id_counter = 1
        def __init__(self, n1, n2):
            self.n1, self.n2 = n1, n2
            self.id = Line._id_counter
            Line._id_counter += 1

    class Surf:
        _id_counter = 1
        def __init__(self, lines, inners=None):
            self.lines = lines
            self.inners = inners or []
            self.id = Surf._id_counter
            Surf._id_counter += 1

    class Solid:
        _id_counter = 1
        def __init__(self, surfaces):
            self.surfaces = surfaces
            self.id = Solid._id_counter
            Solid._id_counter += 1

    class StruModel:
        @staticmethod
        def toViewer():
            print("StruModel.toViewer() 调用（模拟模式）")

from core.parameters import GeometryParams, HoleParams


class GeometryEngineSimple:
    """简化几何引擎 - T+3 版本

    策略：
    1. 先实现矩形截面（退化的工字型）
    2. 验证叠合层切分逻辑
    3. 验证洞口切削逻辑
    4. 为后续扩展预留接口
    """

    def __init__(self, params: GeometryParams):
        self.params = params

    def build_composite_beam(self, holes: List[HoleParams] = None) -> Dict:
        """
        构建叠合梁模型

        Returns:
            {
                'precast_solid': Solid 对象,
                'cast_in_situ_solid': Solid 对象,
                'all_solids': [Solid 对象列表]
            }
        """
        if holes is None:
            holes = []

        L = self.params.L
        H = self.params.H
        Tw = self.params.Tw
        h_pre = self.params.h_pre

        # 简化为矩形截面：宽度 = Tw
        width = Tw

        # 1. 创建预制层实体 (Z: 0 -> h_pre)
        precast_solid = self._create_box_solid(
            x_start=0, x_end=L,
            y_start=-width/2, y_end=width/2,
            z_start=0, z_end=h_pre,
            holes=holes
        )

        # 2. 创建后浇层实体 (Z: h_pre -> H)
        cast_solid = self._create_box_solid(
            x_start=0, x_end=L,
            y_start=-width/2, y_end=width/2,
            z_start=h_pre, z_end=H,
            holes=holes
        )

        return {
            'precast_solid': precast_solid,
            'cast_in_situ_solid': cast_solid,
            'all_solids': [precast_solid, cast_solid]
        }

    def _create_box_solid(self, x_start: float, x_end: float,
                         y_start: float, y_end: float,
                         z_start: float, z_end: float,
                         holes: List[HoleParams]) -> Solid:
        """
        创建矩形box实体（参考开洞实体梁.py）

        Args:
            x_start, x_end: X 方向范围
            y_start, y_end: Y 方向范围
            z_start, z_end: Z 方向范围
            holes: 洞口列表

        Returns:
            Solid 对象
        """
        # 创建8个角点
        nbox = [
            Node(x_start, y_start, z_start),
            Node(x_end, y_start, z_start),
            Node(x_end, y_end, z_start),
            Node(x_start, y_end, z_start),
            Node(x_start, y_start, z_end),
            Node(x_end, y_start, z_end),
            Node(x_end, y_end, z_end),
            Node(x_start, y_end, z_end),
        ]

        # 创建12条边
        wbox = [
            Line(nbox[0].id, nbox[1].id),  # 底面4条边
            Line(nbox[1].id, nbox[2].id),
            Line(nbox[2].id, nbox[3].id),
            Line(nbox[3].id, nbox[0].id),

            Line(nbox[4].id, nbox[5].id),  # 顶面4条边
            Line(nbox[5].id, nbox[6].id),
            Line(nbox[6].id, nbox[7].id),
            Line(nbox[7].id, nbox[4].id),

            Line(nbox[1].id, nbox[5].id),  # 竖边4条
            Line(nbox[2].id, nbox[6].id),
            Line(nbox[3].id, nbox[7].id),
            Line(nbox[0].id, nbox[4].id)
        ]

        # 过滤当前层内的洞口
        layer_holes = self._filter_holes_in_layer(holes, z_start, z_end)

        # 创建洞口的节点和线（在前后面上）
        hole_inners_front = []  # 前面 (x=x_start)
        hole_inners_back = []   # 后面 (x=x_end)

        for hole in layer_holes:
            # 计算洞口在当前层的有效范围
            hole_z_min = max(hole.z - hole.height/2, z_start)
            hole_z_max = min(hole.z + hole.height/2, z_end)
            hole_y_min = hole.z - hole.width/2  # 注意：这里width是Y方向，height是Z方向
            hole_y_max = hole.z + hole.width/2

            # 前面洞口 (x = x_start)
            nhole_front = [
                Node(x_start, hole_y_min, hole_z_min),
                Node(x_start, hole_y_max, hole_z_min),
                Node(x_start, hole_y_max, hole_z_max),
                Node(x_start, hole_y_min, hole_z_max),
            ]
            whole_front = [
                Line(nhole_front[0].id, nhole_front[1].id).id,
                Line(nhole_front[1].id, nhole_front[2].id).id,
                Line(nhole_front[2].id, nhole_front[3].id).id,
                Line(nhole_front[3].id, nhole_front[0].id).id,
            ]
            hole_inners_front.append(whole_front)

            # 后面洞口 (x = x_end)
            nhole_back = [
                Node(x_end, hole_y_min, hole_z_min),
                Node(x_end, hole_y_max, hole_z_min),
                Node(x_end, hole_y_max, hole_z_max),
                Node(x_end, hole_y_min, hole_z_max),
            ]
            whole_back = [
                Line(nhole_back[0].id, nhole_back[1].id).id,
                Line(nhole_back[1].id, nhole_back[2].id).id,
                Line(nhole_back[2].id, nhole_back[3].id).id,
                Line(nhole_back[3].id, nhole_back[0].id).id,
            ]
            hole_inners_back.append(whole_back)

        # 创建6个面
        sbottom = Surf([wbox[0].id, wbox[1].id, wbox[2].id, wbox[3].id])
        stop = Surf([wbox[4].id, wbox[5].id, wbox[6].id, wbox[7].id])

        # 前面（x = x_start），包含洞口
        s_front = Surf(
            [wbox[0].id, wbox[8].id, wbox[4].id, wbox[11].id],
            inners=hole_inners_front if len(hole_inners_front) > 0 else None
        )

        # 后面（x = x_end），包含洞口
        s_back = Surf(
            [wbox[2].id, wbox[10].id, wbox[6].id, wbox[9].id],
            inners=hole_inners_back if len(hole_inners_back) > 0 else None
        )

        # 左右两侧面
        s_left = Surf([wbox[1].id, wbox[9].id, wbox[5].id, wbox[8].id])
        s_right = Surf([wbox[3].id, wbox[11].id, wbox[7].id, wbox[10].id])

        # 创建实体
        solid = Solid([sbottom.id, stop.id, s_front.id, s_back.id, s_left.id, s_right.id])

        return solid

    def _filter_holes_in_layer(self, holes: List[HoleParams],
                               z_start: float, z_end: float) -> List[HoleParams]:
        """
        过滤出与当前层有交集的洞口

        Args:
            holes: 洞口列表
            z_start: 层底部 Z 坐标
            z_end: 层顶部 Z 坐标

        Returns:
            在当前层范围内的洞口列表
        """
        layer_holes = []
        for hole in holes:
            x_min, x_max, z_min, z_max = hole.get_bounds()
            # 检查 Z 方向是否有交集
            if z_max > z_start and z_min < z_end:
                layer_holes.append(hole)
        return layer_holes


if __name__ == "__main__":
    # 测试代码
    from core.parameters import GeometryParams, HoleParams

    print("=" * 60)
    print("简化几何引擎测试")
    print("=" * 60)

    # 创建几何参数（矩形截面）
    geom = GeometryParams(
        L=5400, H=500, Tw=250,
        bf_lu=125, tf_lu=100, bf_ru=125, tf_ru=100,
        bf_ll=125, tf_ll=100, bf_rl=125, tf_rl=100,
        h_pre=300
    )

    # 创建洞口参数
    hole1 = HoleParams(
        x=2000, z=250, width=800, height=200,
        fillet_radius=0,
        small_beam_long_diameter=16, small_beam_long_count=2,
        small_beam_stirrup_diameter=8, small_beam_stirrup_spacing=150,
        left_reinf_length=500, right_reinf_length=500,
        side_stirrup_spacing=100, side_stirrup_diameter=10,
        side_stirrup_legs=2, reinf_extend_length=300
    )

    # 创建几何引擎
    engine = GeometryEngineSimple(geom)

    # 构建叠合梁
    result = engine.build_composite_beam(holes=[hole1])

    print(f"\n✓ 预制层实体创建成功: ID = {result['precast_solid'].id}")
    print(f"✓ 后浇层实体创建成功: ID = {result['cast_in_situ_solid'].id}")
    print(f"✓ 总实体数: {len(result['all_solids'])}")

    print("\n" + "=" * 60)
    print("几何引擎测试完成!")
    print("=" * 60)

    # 如果有真实 PyPCAE 环境，可视化模型
    try:
        StruModel.toViewer()
    except Exception as e:
        print(f"\n注意: 无法启动可视化 ({e})")
