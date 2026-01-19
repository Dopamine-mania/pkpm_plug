"""
PKPM-CAE 叠合梁参数化建模 - 分析步配置模块
实现两阶段分析（施工阶段 + 使用阶段）
"""

from typing import List, Dict, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pypcae.stru import Step, Change, LoadCaseCombine, Embeded
    from pypcae.enums import ChangeType, LoadType, ConstraintType
    from pypcae.load import LoadCase, ConcentratedLoad, DistributedLoad
except ImportError:
    print("警告: PyPCAE 模块未安装，使用模拟模式")

    class ChangeType:
        Add = "Add"
        Remove = "Remove"
        Modify = "Modify"

    class LoadType:
        Concentrated = "Concentrated"
        Distributed = "Distributed"

    class ConstraintType:
        Fixed = "Fixed"
        Free = "Free"

    class Change:
        def __init__(self, type, geids):
            self.type = type
            self.geids = geids

    class LoadCaseCombine:
        def __init__(self, lid, coef=1.0):
            self.lid = lid
            self.coef = coef

    class Step:
        _id_counter = 1
        def __init__(self, name, changes=None, loadCases=None):
            self.name = name
            self.changes = changes or []
            self.loadCases = loadCases or []
            self.id = Step._id_counter
            Step._id_counter += 1

    class LoadCase:
        _id_counter = 100
        def __init__(self, name, loadType=None):
            self.name = name
            self.loadType = loadType
            self.id = LoadCase._id_counter
            LoadCase._id_counter += 1

    class ConcentratedLoad:
        def __init__(self, node_id, direction, magnitude):
            self.node_id = node_id
            self.direction = direction
            self.magnitude = magnitude

    class DistributedLoad:
        def __init__(self, element_ids, direction, magnitude):
            self.element_ids = element_ids
            self.direction = direction
            self.magnitude = magnitude

    class Embeded:
        _id_counter = 500
        def __init__(self, link_ids, solid_ids, tol=5.0):
            self.link_ids = link_ids
            self.solid_ids = solid_ids
            self.tol = tol
            self.id = Embeded._id_counter
            Embeded._id_counter += 1

from core.parameters import LoadCase as ParamLoadCase, BoundaryCondition


class AnalysisConfigurator:
    """分析配置器

    功能：
    1. 创建两阶段分析步（施工 + 使用）
    2. 配置荷载工况
    3. 配置边界条件
    4. 配置钢筋嵌入
    """

    def __init__(self):
        """初始化分析配置器"""
        pass

    def create_two_stage_analysis(self,
                                  precast_solid_ids: List[int],
                                  cast_solid_ids: List[int],
                                  precast_rebar_ids: List[int],
                                  all_rebar_ids: List[int],
                                  construction_load_ids: List[int],
                                  service_load_ids: List[int]) -> Dict:
        """
        创建两阶段分析步配置

        Args:
            precast_solid_ids: 预制层实体 ID 列表
            cast_solid_ids: 后浇层实体 ID 列表
            precast_rebar_ids: 预制层内钢筋 ID 列表
            all_rebar_ids: 全部钢筋 ID 列表
            construction_load_ids: 施工阶段荷载工况 ID 列表
            service_load_ids: 使用阶段荷载工况 ID 列表

        Returns:
            {
                'step1': Step 对象（施工阶段）,
                'step2': Step 对象（使用阶段）,
                'all_steps': [Step 列表]
            }
        """
        # Step 1: 施工阶段
        # 只激活预制层实体和预制层内的钢筋
        step1_changes = [
            Change(type=ChangeType.Add, geids=precast_solid_ids),
            Change(type=ChangeType.Add, geids=precast_rebar_ids)
        ]

        step1_load_combines = [
            LoadCaseCombine(lid=lid, coef=1.0)
            for lid in construction_load_ids
        ]

        step1 = Step(
            name="Construction Stage",
            changes=step1_changes,
            loadCases=step1_load_combines
        )

        # Step 2: 使用阶段
        # 激活后浇层和剩余钢筋，继承 Step 1 的内力
        remaining_rebar_ids = [rid for rid in all_rebar_ids
                               if rid not in precast_rebar_ids]

        step2_changes = [
            Change(type=ChangeType.Add, geids=cast_solid_ids),
            Change(type=ChangeType.Add, geids=remaining_rebar_ids)
        ]

        step2_load_combines = [
            LoadCaseCombine(lid=lid, coef=1.0)
            for lid in service_load_ids
        ]

        step2 = Step(
            name="Service Stage",
            changes=step2_changes,
            loadCases=step2_load_combines
        )

        return {
            'step1': step1,
            'step2': step2,
            'all_steps': [step1, step2]
        }

    def create_load_cases(self, load_params: List[ParamLoadCase],
                         node_map: Dict = None,
                         element_map: Dict = None) -> Dict:
        """
        创建荷载工况

        Args:
            load_params: 荷载参数列表
            node_map: 节点映射（用于集中力）
            element_map: 单元映射（用于均布力）

        Returns:
            {
                'construction_loads': [LoadCase 列表],
                'service_loads': [LoadCase 列表],
                'all_loads': [LoadCase 列表],
                'construction_ids': [ID 列表],
                'service_ids': [ID 列表]
            }
        """
        construction_loads = []
        service_loads = []
        construction_ids = []
        service_ids = []

        for load_param in load_params:
            load_case = LoadCase(name=load_param.name)

            # 添加集中力
            for x_pos, direction, magnitude in load_param.concentrated_loads:
                # 在真实环境中，需要找到对应位置的节点
                # 这里简化处理
                conc_load = ConcentratedLoad(
                    node_id=1,  # 简化：需要根据 x_pos 查找节点
                    direction=direction,
                    magnitude=magnitude
                )
                # load_case.add_load(conc_load)  # 实际 API 调用

            # 添加均布力
            for x1, x2, direction, magnitude in load_param.distributed_loads:
                # 在真实环境中，需要找到对应范围的单元
                dist_load = DistributedLoad(
                    element_ids=[1, 2, 3],  # 简化：需要根据 x1, x2 查找单元
                    direction=direction,
                    magnitude=magnitude
                )
                # load_case.add_load(dist_load)  # 实际 API 调用

            # 根据阶段分类
            if load_param.stage == "Construction":
                construction_loads.append(load_case)
                construction_ids.append(load_case.id)
            else:
                service_loads.append(load_case)
                service_ids.append(load_case.id)

        return {
            'construction_loads': construction_loads,
            'service_loads': service_loads,
            'all_loads': construction_loads + service_loads,
            'construction_ids': construction_ids,
            'service_ids': service_ids
        }

    def create_boundary_conditions(self, boundary: BoundaryCondition,
                                   left_node_id: int,
                                   right_node_id: int) -> Dict:
        """
        创建边界条件

        Args:
            boundary: 边界条件参数
            left_node_id: 左端节点 ID
            right_node_id: 右端节点 ID

        Returns:
            {
                'left_constraints': {约束字典},
                'right_constraints': {约束字典},
                'left_forces': {内力字典},
                'right_forces': {内力字典}
            }
        """
        # 在真实环境中，需要调用 PyPCAE API 设置节点约束
        # 例如: Node(left_node_id).set_constraint(Dx=Fixed, Dy=Fixed, ...)

        return {
            'left_constraints': boundary.left_end,
            'right_constraints': boundary.right_end,
            'left_forces': boundary.left_end_forces,
            'right_forces': boundary.right_end_forces
        }

    def create_rebar_embedment(self,
                              rebar_element_ids: List[int],
                              concrete_solid_ids: List[int],
                              tolerance: float = 5.0) -> Embeded:
        """
        创建钢筋嵌入

        关键参数：
        - tolerance: 嵌入容差（mm），建议 5.0
          - 太小：可能导致嵌入失败
          - 太大：影响精度

        Args:
            rebar_element_ids: 钢筋 Link 单元 ID 列表
            concrete_solid_ids: 混凝土 Solid 单元 ID 列表
            tolerance: 嵌入容差

        Returns:
            Embeded 对象
        """
        # 创建嵌入关系
        # 确保：
        # 1. 钢筋节点距离混凝土表面至少保护层厚度（通常 25mm）
        # 2. 容差设置合理（5mm 是经验值）
        # 3. 钢筋单元类型为 Link

        embeded = Embeded(
            link_ids=rebar_element_ids,
            solid_ids=concrete_solid_ids,
            tol=tolerance
        )

        return embeded

    def separate_rebars_by_layer(self,
                                 all_rebar_nodes: List,
                                 h_pre: float) -> Dict:
        """
        根据 Z 坐标将钢筋分配到预制层或后浇层

        判断规则：
        - 钢筋节点 Z < h_pre: 属于预制层
        - 钢筋节点 Z >= h_pre: 属于后浇层
        - 如果钢筋跨越分界面：根据节点数量多数原则

        Args:
            all_rebar_nodes: 所有钢筋节点列表
            h_pre: 预制层高度

        Returns:
            {
                'precast_rebar_ids': [预制层钢筋 ID],
                'cast_rebar_ids': [后浇层钢筋 ID]
            }
        """
        precast_rebar_ids = []
        cast_rebar_ids = []

        # 简化实现：需要根据实际节点坐标判断
        # 在真实环境中，需要遍历每个 Link 单元的两个节点
        # 如果两个节点的平均 Z 坐标 < h_pre，则属于预制层

        for node in all_rebar_nodes:
            if hasattr(node, 'z') and node.z < h_pre:
                if hasattr(node, 'id'):
                    precast_rebar_ids.append(node.id)
            else:
                if hasattr(node, 'id'):
                    cast_rebar_ids.append(node.id)

        return {
            'precast_rebar_ids': precast_rebar_ids,
            'cast_rebar_ids': cast_rebar_ids
        }


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("分析配置模块测试")
    print("=" * 60)

    configurator = AnalysisConfigurator()

    # 模拟数据
    precast_solid_ids = [1]
    cast_solid_ids = [2]
    precast_rebar_ids = [101, 102, 103]
    all_rebar_ids = [101, 102, 103, 104, 105, 106]
    construction_load_ids = [201]
    service_load_ids = [202, 203]

    # 创建两阶段分析
    analysis = configurator.create_two_stage_analysis(
        precast_solid_ids=precast_solid_ids,
        cast_solid_ids=cast_solid_ids,
        precast_rebar_ids=precast_rebar_ids,
        all_rebar_ids=all_rebar_ids,
        construction_load_ids=construction_load_ids,
        service_load_ids=service_load_ids
    )

    print(f"\n✓ Step 1 (施工阶段) 创建成功:")
    print(f"  - 名称: {analysis['step1'].name}")
    print(f"  - 激活单元数: {len(analysis['step1'].changes)} 组")
    print(f"  - 荷载工况数: {len(analysis['step1'].loadCases)}")

    print(f"\n✓ Step 2 (使用阶段) 创建成功:")
    print(f"  - 名称: {analysis['step2'].name}")
    print(f"  - 激活单元数: {len(analysis['step2'].changes)} 组")
    print(f"  - 荷载工况数: {len(analysis['step2'].loadCases)}")

    # 创建钢筋嵌入
    embeded = configurator.create_rebar_embedment(
        rebar_element_ids=all_rebar_ids,
        concrete_solid_ids=precast_solid_ids + cast_solid_ids,
        tolerance=5.0
    )

    print(f"\n✓ 钢筋嵌入创建成功:")
    print(f"  - 嵌入 ID: {embeded.id}")
    print(f"  - 钢筋单元数: {len(embeded.link_ids)}")
    print(f"  - 混凝土实体数: {len(embeded.solid_ids)}")
    print(f"  - 容差: {embeded.tol} mm")

    print("\n" + "=" * 60)
    print("分析配置模块测试完成!")
    print("=" * 60)
    print("\n关键提示:")
    print("  ✓ 两阶段分析实现内力继承")
    print("  ✓ 钢筋嵌入容差设置为 5mm（经验值）")
    print("  ✓ 确保钢筋节点距混凝土表面 >= 保护层厚度")
    print("  ✓ 网格划分时，嵌入的钢筋会自动与混凝土单元关联")
