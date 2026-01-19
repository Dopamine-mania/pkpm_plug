# -*- coding: utf-8 -*-
"""
创建最终验收测试用例 - 涵盖客户张工8个痛点的复杂工况
"""

import pandas as pd

def create_final_acceptance_test():
    """创建最终验收测试Excel

    参数要求：
    - 几何: 梁长7.8m, 总高1100mm, 工字型截面(翼缘宽500厚150, 腹板厚250)
    - 叠合: 叠合面在上翼缘范围（通过“现浇顶盖厚度 t_cast_cap”控制）
    - 洞口: X=3900mm, 2500x400mm
    - 洞口补强: 小梁纵筋2D16, 小梁箍筋D8@150, 侧箍D10@100/4肢/各500mm
    - 边界: 左端固端, 右端简支
    - 荷载: 均布15kN/m, 集中50kN@X=2000
    """

    output_path = "test_final_acceptance.xlsx"

    # 翼缘伸出宽度计算: (翼缘总宽500 - 腹板宽250) / 2 = 125mm
    bf_extend = 125
    tf = 150  # 翼缘厚度

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: Geometry - 工字型截面
        geom_data = {
            'L': [7800],           # 梁长 7.8m
            'H': [1100],           # 总高 1100mm
            'Tw': [250],           # 腹板宽 250mm
            'bf_lu': [bf_extend],  # 左上翼缘伸出 125mm
            'tf_lu': [tf],         # 左上翼缘厚 150mm
            'bf_ru': [bf_extend],  # 右上翼缘伸出 125mm
            'tf_ru': [tf],         # 右上翼缘厚 150mm
            'bf_ll': [bf_extend],  # 左下翼缘伸出 125mm
            'tf_ll': [tf],         # 左下翼缘厚 150mm
            'bf_rl': [bf_extend],  # 右下翼缘伸出 125mm
            'tf_rl': [tf],         # 右下翼缘厚 150mm
            'h_pre': [400],        # 预制层高（保留字段；当 t_cast_cap>0 时以 t_cast_cap 优先切分叠合面）
            't_cast_cap': [75]     # 现浇顶盖厚度 75mm：叠合面进入上翼缘内部
        }
        pd.DataFrame(geom_data).to_excel(writer, sheet_name='Geometry', index=False)

        # Sheet 2: Longitudinal Rebar
        rebar_data = {
            'Position': ['Left Support Top', 'Mid Span Top', 'Right Support Top', 'Bottom Through'],
            'Diameter_A': [25, 25, 25, 25],
            'Count_A': [3, 2, 3, 4],
            'Diameter_B': [22, None, 22, 22],
            'Count_B': [2, None, 2, 2],
            'Extend_Length': [2600, 0, 2600, 0]
        }
        pd.DataFrame(rebar_data).to_excel(writer, sheet_name='Longitudinal Rebar', index=False)

        # Sheet 3: Stirrups - 工字型闭合箍筋
        stirrup_data = {
            'Zone': ['Dense', 'Normal'],
            'Length': [1500, 0],
            'Spacing': [100, 200],
            'Legs': [4, 2],
            'Diameter': [10, 8],
            'Cover': [25, 25]
        }
        pd.DataFrame(stirrup_data).to_excel(writer, sheet_name='Stirrups', index=False)

        # Sheet 4: Holes - 中心大洞口 + 完整补强参数
        holes_data = {
            'X': [3900],                        # 中心位置
            'Z': [350],                         # 洞口中心Z (在腹板中间)
            'Width': [2500],                    # 洞宽 2500mm
            'Height': [400],                    # 洞高 400mm
            'Fillet_Radius': [0],               # 无倒角
            'SmallBeam_Long_Diameter': [16],    # 小梁纵筋 D16
            'SmallBeam_Long_Count': [2],        # 2根
            'SmallBeam_Stirrup_Diameter': [8],  # 小梁箍筋 D8
            'SmallBeam_Stirrup_Spacing': [150], # @150
            'Left_Reinf_Length': [500],         # 左侧加强区 500mm
            'Right_Reinf_Length': [500],        # 右侧加强区 500mm
            'Side_Stirrup_Spacing': [100],      # 侧箍 @100
            'Side_Stirrup_Diameter': [10],      # 侧箍 D10
            'Side_Stirrup_Legs': [4],           # 4肢
            'Reinf_Extend_Length': [300]        # 纵筋锚固延伸 300mm
        }
        pd.DataFrame(holes_data).to_excel(writer, sheet_name='Holes', index=False)

        # Sheet 5: Loads - 均布荷载 + 集中荷载
        loads_data = {
            'Case': ['Dead Load', 'Concentrated'],
            'Stage': ['Construction', 'Construction'],
            'Type': ['Distributed', 'Concentrated'],
            'X': [None, 2000],                  # 集中荷载位置 X=2000
            'X1': [0, None],
            'X2': [7800, None],
            'Direction': ['Z', 'Z'],
            'Magnitude': [-15.0, -50.0]         # 均布15kN/m, 集中50kN
        }
        pd.DataFrame(loads_data).to_excel(writer, sheet_name='Loads', index=False)

        # Sheet 6: Boundary - 左固端 + 右简支
        boundary_data = {
            'End': ['Left', 'Right'],
            'Type': ['Fixed', 'Simple'],        # 明确标识
            'Dx': ['Fixed', 'Fixed'],
            'Dy': ['Fixed', 'Fixed'],
            'Dz': ['Fixed', 'Free'],            # 简支: Dz自由
            'Rx': ['Fixed', 'Free'],
            'Ry': ['Fixed', 'Free'],
            'Rz': ['Fixed', 'Free']
        }
        pd.DataFrame(boundary_data).to_excel(writer, sheet_name='Boundary', index=False)

        # Sheet 7: Prestress - 默认关闭预应力（可在 UI/Excel 中切换 method）
        prestress_data = {
            'Parameter': ['Enabled', 'Method', 'Force', 'Duct_Diameter', 'Path_Type'],
            'Value': ['False', 'post_tension', 0, 60, 'straight']
        }
        pd.DataFrame(prestress_data).to_excel(writer, sheet_name='Prestress', index=False)

    print(f"=" * 60)
    print(f"最终验收测试Excel已创建: {output_path}")
    print(f"=" * 60)
    print(f"几何参数:")
    print(f"  - 梁长: 7800mm")
    print(f"  - 总高: 1100mm")
    print(f"  - 截面: 工字型 (翼缘总宽500mm, 腹板宽250mm)")
    print(f"  - 预制层高: 400mm")
    print(f"洞口参数:")
    print(f"  - 位置: X=3900mm (中心)")
    print(f"  - 尺寸: 2500x400mm")
    print(f"  - 小梁纵筋: 2D16")
    print(f"  - 小梁箍筋: D8@150")
    print(f"  - 侧箍: D10@100, 4肢, 各500mm")
    print(f"边界条件:")
    print(f"  - 左端: 固端 (Coupling)")
    print(f"  - 右端: 简支 (线约束Dz)")
    print(f"荷载:")
    print(f"  - 均布: 15kN/m")
    print(f"  - 集中: 50kN @ X=2000mm")
    print(f"=" * 60)

    return output_path

if __name__ == "__main__":
    create_final_acceptance_test()
