# -*- coding: utf-8 -*-
"""
创建测试数据Excel文件
支持多种截面类型：矩形、T型、倒T型、工字型
"""

import pandas as pd

def create_test_excel(output_path: str, section_type: str = "inverted_T"):
    """创建测试Excel文件

    Args:
        output_path: 输出文件路径
        section_type: 截面类型 - "rect", "T", "inverted_T", "I"
    """
    # 根据截面类型设置翼缘参数
    if section_type == "rect":
        # 矩形截面：无翼缘
        bf_lu, tf_lu, bf_ru, tf_ru = 0, 0, 0, 0
        bf_ll, tf_ll, bf_rl, tf_rl = 0, 0, 0, 0
        desc = "矩形截面"
    elif section_type == "T":
        # T型截面：仅上翼缘
        bf_lu, tf_lu, bf_ru, tf_ru = 100, 150, 100, 150
        bf_ll, tf_ll, bf_rl, tf_rl = 0, 0, 0, 0
        desc = "T型截面"
    elif section_type == "inverted_T":
        # 倒T型截面：仅下翼缘
        bf_lu, tf_lu, bf_ru, tf_ru = 0, 0, 0, 0
        bf_ll, tf_ll, bf_rl, tf_rl = 100, 150, 100, 150
        desc = "倒T型截面"
    elif section_type == "I":
        # 工字型截面：上下翼缘
        bf_lu, tf_lu, bf_ru, tf_ru = 100, 150, 100, 150
        bf_ll, tf_ll, bf_rl, tf_rl = 100, 150, 100, 150
        desc = "工字型截面"
    else:
        raise ValueError(f"未知截面类型: {section_type}")

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: Geometry
        geom_data = {
            'L': [7800],           # 梁长 7.8m
            'H': [1100],           # 总高 1100mm
            'Tw': [500],           # 腹板宽 500mm
            'bf_lu': [bf_lu],      # 左上翼缘宽
            'tf_lu': [tf_lu],      # 左上翼缘厚
            'bf_ru': [bf_ru],      # 右上翼缘宽
            'tf_ru': [tf_ru],      # 右上翼缘厚
            'bf_ll': [bf_ll],      # 左下翼缘伸出宽
            'tf_ll': [tf_ll],      # 左下翼缘厚
            'bf_rl': [bf_rl],      # 右下翼缘伸出宽
            'tf_rl': [tf_rl],      # 右下翼缘厚
            'h_pre': [900]         # 预制层高 900mm
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
            'X': [3900],
            'Z': [500],
            'Width': [2500],
            'Height': [400],
            'Fillet_Radius': [0],
            'SmallBeam_Long_Diameter': [16],
            'SmallBeam_Long_Count': [2],
            'SmallBeam_Stirrup_Diameter': [8],
            'SmallBeam_Stirrup_Spacing': [150],
            'Left_Reinf_Length': [500],
            'Right_Reinf_Length': [500],
            'Side_Stirrup_Spacing': [100],
            'Side_Stirrup_Diameter': [10],
            'Side_Stirrup_Legs': [2],
            'Reinf_Extend_Length': [300]
        }
        pd.DataFrame(holes_data).to_excel(writer, sheet_name='Holes', index=False)

        # Sheet 5: Loads
        loads_data = {
            'Case': ['Dead Load', 'Live Load'],
            'Stage': ['Construction', 'Service'],
            'Type': ['Distributed', 'Distributed'],
            'X': [None, None],
            'X1': [0, 0],
            'X2': [7800, 7800],
            'Direction': ['Z', 'Z'],
            'Magnitude': [-15.0, -20.0]
        }
        pd.DataFrame(loads_data).to_excel(writer, sheet_name='Loads', index=False)

        # Sheet 6: Boundary
        boundary_data = {
            'End': ['Left', 'Right'],
            'Dx': ['Fixed', 'Fixed'],
            'Dy': ['Fixed', 'Fixed'],
            'Dz': ['Fixed', 'Free'],
            'Rx': ['Fixed', 'Free'],
            'Ry': ['Fixed', 'Free'],
            'Rz': ['Fixed', 'Free'],
            'N': [0, 0],
            'Vy': [0, 0],
            'Vz': [0, 0],
            'Mx': [0, 0],
            'My': [0, 0],
            'Mz': [0, 0]
        }
        pd.DataFrame(boundary_data).to_excel(writer, sheet_name='Boundary', index=False)

        # Sheet 7: Prestress
        prestress_data = {
            'Parameter': ['Enabled', 'Force', 'Duct_Diameter', 'Path_Type'],
            'Value': ['True', 1395, 60, 'straight']
        }
        pd.DataFrame(prestress_data).to_excel(writer, sheet_name='Prestress', index=False)

    print(f">>> 测试Excel文件已创建: {output_path}")
    print(f">>> 截面类型: {desc}")
    print(f">>> 上翼缘: 伸出{bf_lu}mm, 厚{tf_lu}mm")
    print(f">>> 下翼缘: 伸出{bf_ll}mm, 厚{tf_ll}mm")


if __name__ == "__main__":
    import sys

    # 默认创建倒T型，也可以通过命令行指定
    section = sys.argv[1] if len(sys.argv) > 1 else "inverted_T"
    output = f"test_beam_{section}.xlsx"
    create_test_excel(output, section)
