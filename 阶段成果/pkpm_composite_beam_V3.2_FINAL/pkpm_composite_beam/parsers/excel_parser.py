"""
PKPM-CAE 叠合梁参数化建模 - Excel 参数解析模块
从 Excel 模板 V3.0 中读取参数并转换为参数对象
"""

import pandas as pd
from typing import Dict, Any, List, Optional
import sys
import os

# 添加父目录到路径以便导入 core 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parameters import (
    BeamParameters, GeometryParams, LongitudinalRebar, RebarSpec,
    StirrupParams, HoleParams, LoadCase, BoundaryCondition, PrestressParams
)


class ExcelParser:
    """Excel 参数解析器

    解析 Excel 模板 V3.0，支持 6 个 Sheet:
    - Sheet 1: Geometry (几何截面)
    - Sheet 2: Longitudinal Rebar (纵向配筋)
    - Sheet 3: Stirrups (箍筋)
    - Sheet 4: Holes (洞口与补强)
    - Sheet 5: Loads & Boundary (荷载与边界)
    - Sheet 6: Prestress (预应力)
    """

    def __init__(self, excel_path: str):
        """
        初始化解析器

        Args:
            excel_path: Excel 文件路径
        """
        self.excel_path = excel_path
        self.excel_file = None

    def parse(self) -> BeamParameters:
        """
        解析 Excel 文件，返回完整参数对象

        Returns:
            BeamParameters 对象

        Raises:
            ValueError: 参数解析失败
            FileNotFoundError: Excel 文件不存在
        """
        try:
            self.excel_file = pd.ExcelFile(self.excel_path, engine='openpyxl')
        except FileNotFoundError:
            raise FileNotFoundError(f"Excel 文件不存在: {self.excel_path}")
        except Exception as e:
            raise ValueError(f"无法打开 Excel 文件: {e}")

        # 解析各个 Sheet
        geometry = self._parse_geometry()
        long_rebar = self._parse_longitudinal_rebar()
        stirrup = self._parse_stirrup()
        holes = self._parse_holes()
        loads = self._parse_loads()
        boundary = self._parse_boundary()
        prestress = self._parse_prestress()

        # 构建完整参数对象
        params = BeamParameters(
            geometry=geometry,
            long_rebar=long_rebar,
            stirrup=stirrup,
            holes=holes,
            loads=loads,
            boundary=boundary,
            prestress=prestress
        )

        return params

    def _parse_geometry(self) -> GeometryParams:
        """解析 Sheet 1: Geometry"""
        df = pd.read_excel(self.excel_file, sheet_name='Geometry', header=0)

        # 提取参数（假设数据在第一行）
        data = df.iloc[0].to_dict()

        return GeometryParams(
            L=float(data.get('L', 0)),
            H=float(data.get('H', 0)),
            Tw=float(data.get('Tw', 0)),
            bf_lu=float(data.get('bf_lu', 0)),
            tf_lu=float(data.get('tf_lu', 0)),
            bf_ru=float(data.get('bf_ru', 0)),
            tf_ru=float(data.get('tf_ru', 0)),
            bf_ll=float(data.get('bf_ll', 0)),
            tf_ll=float(data.get('tf_ll', 0)),
            bf_rl=float(data.get('bf_rl', 0)),
            tf_rl=float(data.get('tf_rl', 0)),
            h_pre=float(data.get('h_pre', 0)),
            # 现浇顶盖厚度（进入上翼缘内部的叠合面切分）：老模板可缺省，默认0=自动/不强制
            t_cast_cap=float(data.get('t_cast_cap', data.get('t_cast', 0)) or 0)
        )

    def _parse_longitudinal_rebar(self) -> LongitudinalRebar:
        """解析 Sheet 2: Longitudinal Rebar"""
        df = pd.read_excel(self.excel_file, sheet_name='Longitudinal Rebar', header=0)

        # 解析各位置的配筋
        rebars = {}
        for _, row in df.iterrows():
            position = row.get('Position', '')
            dia_a = row.get('Diameter_A', 0)
            count_a = row.get('Count_A', 0)
            dia_b = row.get('Diameter_B', None)
            count_b = row.get('Count_B', None)
            extend = row.get('Extend_Length', 0)

            rebar_a = RebarSpec(diameter=float(dia_a), count=int(count_a), extend_length=float(extend))

            rebar_b = None
            if dia_b and count_b and not pd.isna(dia_b) and not pd.isna(count_b):
                rebar_b = RebarSpec(diameter=float(dia_b), count=int(count_b), extend_length=float(extend))

            rebars[position] = (rebar_a, rebar_b)

        # 构建 LongitudinalRebar 对象
        left_a, left_b = rebars.get('Left Support Top', (None, None))
        mid_a, _ = rebars.get('Mid Span Top', (None, None))
        right_a, right_b = rebars.get('Right Support Top', (None, None))
        bottom_a, bottom_b = rebars.get('Bottom Through', (None, None))

        return LongitudinalRebar(
            left_support_top_A=left_a,
            left_support_top_B=left_b,
            mid_span_top=mid_a,
            right_support_top_A=right_a,
            right_support_top_B=right_b,
            bottom_through_A=bottom_a,
            bottom_through_B=bottom_b
        )

    def _parse_stirrup(self) -> StirrupParams:
        """解析 Sheet 3: Stirrups"""
        df = pd.read_excel(self.excel_file, sheet_name='Stirrups', header=0)

        # 假设数据格式：
        # | Zone | Spacing | Legs | Diameter |
        # | Dense | ... | ... | ... |
        # | Normal | ... | ... | ... |

        dense_row = df[df['Zone'] == 'Dense'].iloc[0]
        normal_row = df[df['Zone'] == 'Normal'].iloc[0]

        # 加密区长度（从另一个字段读取或使用默认值）
        dense_length = dense_row.get('Length', 1500.0)

        return StirrupParams(
            dense_zone_length=float(dense_length),
            dense_spacing=float(dense_row['Spacing']),
            dense_legs=int(dense_row['Legs']),
            dense_diameter=float(dense_row['Diameter']),
            normal_spacing=float(normal_row['Spacing']),
            normal_legs=int(normal_row['Legs']),
            normal_diameter=float(normal_row['Diameter']),
            cover=float(dense_row.get('Cover', 25.0))
        )

    def _parse_holes(self) -> List[HoleParams]:
        """解析 Sheet 4: Holes"""
        df = pd.read_excel(self.excel_file, sheet_name='Holes', header=0)

        holes = []
        for _, row in df.iterrows():
            # 跳过空行
            if pd.isna(row.get('X', None)):
                continue

            hole = HoleParams(
                x=float(row['X']),
                z=float(row['Z']),
                width=float(row['Width']),
                height=float(row['Height']),
                fillet_radius=float(row.get('Fillet_Radius', 0.0)),

                # 小梁配筋
                small_beam_long_diameter=float(row.get('SmallBeam_Long_Diameter', 0.0)),
                small_beam_long_count=int(row.get('SmallBeam_Long_Count', 0)),
                small_beam_stirrup_diameter=float(row.get('SmallBeam_Stirrup_Diameter', 0.0)),
                small_beam_stirrup_spacing=float(row.get('SmallBeam_Stirrup_Spacing', 0.0)),

                # 洞侧补强
                left_reinf_length=float(row.get('Left_Reinf_Length', 0.0)),
                right_reinf_length=float(row.get('Right_Reinf_Length', 0.0)),
                side_stirrup_spacing=float(row.get('Side_Stirrup_Spacing', 0.0)),
                side_stirrup_diameter=float(row.get('Side_Stirrup_Diameter', 0.0)),
                side_stirrup_legs=int(row.get('Side_Stirrup_Legs', 2)),
                reinf_extend_length=float(row.get('Reinf_Extend_Length', 0.0))
            )
            holes.append(hole)

        return holes

    def _parse_loads(self) -> List[LoadCase]:
        """解析 Sheet 5: Loads"""
        df = pd.read_excel(self.excel_file, sheet_name='Loads', header=0)

        # 按工况名称分组
        load_cases = {}
        for _, row in df.iterrows():
            case_name = row.get('Case', '')
            stage = row.get('Stage', 'Service')

            if case_name not in load_cases:
                load_cases[case_name] = LoadCase(name=case_name, stage=stage)

            # 解析荷载
            load_type = row.get('Type', '')
            if load_type == 'Concentrated':
                x = float(row['X'])
                direction = row['Direction']
                magnitude = float(row['Magnitude'])
                load_cases[case_name].concentrated_loads.append((x, direction, magnitude))

            elif load_type == 'Distributed':
                x1 = float(row['X1'])
                x2 = float(row['X2'])
                direction = row['Direction']
                magnitude = float(row['Magnitude'])
                load_cases[case_name].distributed_loads.append((x1, x2, direction, magnitude))

        return list(load_cases.values())

    def _parse_boundary(self) -> BoundaryCondition:
        """解析 Sheet 5: Boundary"""
        try:
            df = pd.read_excel(self.excel_file, sheet_name='Boundary', header=0)
        except ValueError:
            # 如果没有 Boundary sheet，使用默认值
            return BoundaryCondition()

        # 假设格式：
        # | End | Dx | Dy | Dz | Rx | Ry | Rz | N | Vy | Vz | Mx | My | Mz |
        # | Left | ... | ... | ... |
        # | Right | ... | ... | ... |

        left_row = df[df['End'] == 'Left'].iloc[0]
        right_row = df[df['End'] == 'Right'].iloc[0]

        def parse_constraint(row):
            return {
                'Dx': row.get('Dx', 'Fixed'),
                'Dy': row.get('Dy', 'Fixed'),
                'Dz': row.get('Dz', 'Fixed'),
                'Rx': row.get('Rx', 'Free'),
                'Ry': row.get('Ry', 'Free'),
                'Rz': row.get('Rz', 'Free')
            }

        def parse_forces(row):
            return {
                'N': float(row.get('N', 0)),
                'Vy': float(row.get('Vy', 0)),
                'Vz': float(row.get('Vz', 0)),
                'Mx': float(row.get('Mx', 0)),
                'My': float(row.get('My', 0)),
                'Mz': float(row.get('Mz', 0))
            }

        return BoundaryCondition(
            left_end=parse_constraint(left_row),
            right_end=parse_constraint(right_row),
            left_end_forces=parse_forces(left_row),
            right_end_forces=parse_forces(right_row)
        )

    def _parse_prestress(self) -> Optional[PrestressParams]:
        """解析 Sheet 6: Prestress"""
        try:
            df = pd.read_excel(self.excel_file, sheet_name='Prestress', header=0)
        except ValueError:
            # 如果没有 Prestress sheet，返回 None
            return None

        def _get_value(param_name: str, default=None):
            rows = df[df['Parameter'] == param_name]
            if rows.empty:
                return default
            return rows.iloc[0].get('Value', default)

        enabled_raw = _get_value('Enabled', 'False')
        enabled = str(enabled_raw).lower() in ['true', 'yes', '1', 'enabled']

        # 预应力方式：post_tension / pretension（可选，缺省=post_tension）
        method = str(_get_value('Method', 'post_tension') or 'post_tension').strip().lower()
        if method in ['pre_tension', 'pretension', '先张', '先张法']:
            method = 'pretension'
        if method not in ['post_tension', 'pretension']:
            method = 'post_tension'

        # 几何层面：即使未启用预应力，也允许预留孔道（例如客户验收需要看到波纹管孔道）
        duct_diameter = float(_get_value('Duct_Diameter', 0.0) or 0.0)

        # 路径类型（可选，默认 straight）
        path_type = str(_get_value('Path_Type', 'straight') or 'straight').lower()
        if path_type not in ['straight', 'parabolic']:
            path_type = 'straight'

        # 预应力力学层面：仅 enabled=True 时才读取 Force 并在后续步骤施加
        force = float(_get_value('Force', 0.0) or 0.0) if enabled else 0.0

        return PrestressParams(
            enabled=enabled,
            method=method,
            force=force,
            duct_diameter=duct_diameter,
            path_type=path_type
            # duct_path 将由 main.py 根据几何自动计算
        )


def create_example_excel(output_path: str):
    """
    创建一个示例 Excel 模板文件，用于测试

    Args:
        output_path: 输出文件路径
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: Geometry
        geom_data = {
            'L': [10000],
            'H': [800],
            'Tw': [250],
            'bf_lu': [400],
            'tf_lu': [150],
            'bf_ru': [400],
            'tf_ru': [150],
            'bf_ll': [400],
            'tf_ll': [150],
            'bf_rl': [400],
            'tf_rl': [150],
            'h_pre': [500],
            't_cast_cap': [0]
        }
        pd.DataFrame(geom_data).to_excel(writer, sheet_name='Geometry', index=False)

        # Sheet 2: Longitudinal Rebar
        rebar_data = {
            'Position': ['Left Support Top', 'Mid Span Top', 'Right Support Top', 'Bottom Through'],
            'Diameter_A': [25, 25, 25, 25],
            'Count_A': [2, 2, 2, 4],
            'Diameter_B': [22, None, 20, 22],
            'Count_B': [3, None, 2, 2],
            'Extend_Length': [3333, 0, 3333, 0]
        }
        pd.DataFrame(rebar_data).to_excel(writer, sheet_name='Longitudinal Rebar', index=False)

        # Sheet 3: Stirrups
        stirrup_data = {
            'Zone': ['Dense', 'Normal'],
            'Length': [1500, 0],
            'Spacing': [100, 200],
            'Legs': [4, 2],
            'Diameter': [10, 8],
            'Cover': [25, 25]
        }
        pd.DataFrame(stirrup_data).to_excel(writer, sheet_name='Stirrups', index=False)

        # Sheet 4: Holes
        holes_data = {
            'X': [3000, 7000],
            'Z': [400, 400],
            'Width': [800, 1000],
            'Height': [400, 400],
            'Fillet_Radius': [0, 0],
            'SmallBeam_Long_Diameter': [16, 16],
            'SmallBeam_Long_Count': [2, 2],
            'SmallBeam_Stirrup_Diameter': [8, 8],
            'SmallBeam_Stirrup_Spacing': [150, 150],
            'Left_Reinf_Length': [500, 500],
            'Right_Reinf_Length': [500, 500],
            'Side_Stirrup_Spacing': [100, 100],
            'Side_Stirrup_Diameter': [10, 10],
            'Side_Stirrup_Legs': [2, 2],
            'Reinf_Extend_Length': [300, 300]
        }
        pd.DataFrame(holes_data).to_excel(writer, sheet_name='Holes', index=False)

        # Sheet 5: Loads
        loads_data = {
            'Case': ['Dead Load', 'Dead Load', 'Live Load'],
            'Stage': ['Construction', 'Construction', 'Service'],
            'Type': ['Distributed', 'Concentrated', 'Distributed'],
            'X': [None, 5000, None],
            'X1': [0, None, 0],
            'X2': [10000, None, 10000],
            'Direction': ['Z', 'Z', 'Z'],
            'Magnitude': [-10.0, -5000.0, -15.0]
        }
        pd.DataFrame(loads_data).to_excel(writer, sheet_name='Loads', index=False)

        # Sheet 5 (另一个 tab): Boundary
        boundary_data = {
            'End': ['Left', 'Right'],
            'Dx': ['Fixed', 'Fixed'],
            'Dy': ['Fixed', 'Fixed'],
            'Dz': ['Fixed', 'Free'],
            'Rx': ['Free', 'Free'],
            'Ry': ['Free', 'Free'],
            'Rz': ['Free', 'Free'],
            'N': [0, 0],
            'Vy': [0, 0],
            'Vz': [0, 0],
            'Mx': [0, 0],
            'My': [0, 0],
            'Mz': [0, 0]
        }
        pd.DataFrame(boundary_data).to_excel(writer, sheet_name='Boundary', index=False)

        # Sheet 6: Prestress (示例：不启用；method 默认后张法)
        prestress_data = {
            'Parameter': ['Enabled', 'Method', 'Force', 'Duct_Diameter', 'Path_Type'],
            'Value': ['False', 'post_tension', 0, 0, 'straight']
        }
        pd.DataFrame(prestress_data).to_excel(writer, sheet_name='Prestress', index=False)

    print(f"示例 Excel 文件已创建: {output_path}")


if __name__ == "__main__":
    # 测试代码：创建示例 Excel 文件
    example_path = "example_beam_parameters.xlsx"
    create_example_excel(example_path)

    # 测试解析
    parser = ExcelParser(example_path)
    params = parser.parse()

    # 验证并打印摘要
    is_valid, errors = params.validate()
    print(params.summary())

    if not is_valid:
        print("\n参数校验失败:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n参数校验通过!")
