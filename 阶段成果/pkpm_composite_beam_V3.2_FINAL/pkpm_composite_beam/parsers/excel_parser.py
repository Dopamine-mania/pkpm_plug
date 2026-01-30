"""
PKPM-CAE 叠合梁参数化建模 - Excel 参数解析模块
从 Excel 模板 V3.0 中读取参数并转换为参数对象
"""

import importlib
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
        # 读取策略：
        # - 优先 pandas + openpyxl（若环境已安装依赖）
        # - 若 openpyxl 缺失或读取失败，则回退到 stdlib-only 的最小 XLSX 读取器（仅支持本项目表格型sheet）
        self._pd = None
        self._use_minimal = True
        self.excel_file = None

        # 读取策略（尽量减少依赖与打包复杂度）：
        # - 默认使用 stdlib-only 最小 XLSX 读取器（支持本项目模板的“表格型sheet”）
        # - 若环境已安装 pandas 且 ExcelFile 可用，则自动切换为 pandas 读取（更宽容）
        try:
            self._pd = importlib.import_module("pandas")
        except Exception:
            self._pd = None

        if self._pd is not None:
            try:
                # 不显式指定 openpyxl，避免在无 openpyxl 环境下直接 ImportError
                self.excel_file = self._pd.ExcelFile(self.excel_path)
                self._use_minimal = False
            except FileNotFoundError:
                raise FileNotFoundError(f"Excel 文件不存在: {self.excel_path}")
            except Exception:
                self.excel_file = None
                self._use_minimal = True

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

    def _is_na(self, v: Any) -> bool:
        if v is None:
            return True
        try:
            pd = getattr(self, "_pd", None)
            if pd is not None and pd.isna(v):
                return True
        except Exception:
            pass
        return False

    def _read_rows(self, sheet_name: str) -> List[Dict[str, Any]]:
        if getattr(self, "_use_minimal", False):
            from parsers.xlsx_minimal import read_table_rows
            return read_table_rows(self.excel_path, sheet_name)
        pd = self._pd
        df = pd.read_excel(self.excel_file, sheet_name=sheet_name, header=0)
        return [row.to_dict() for _, row in df.iterrows()]

    def _parse_geometry(self) -> GeometryParams:
        """解析 Sheet 1: Geometry"""
        rows = self._read_rows('Geometry')
        if not rows:
            raise ValueError("Geometry sheet 为空或不存在")
        data = rows[0]

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
        rows = self._read_rows('Longitudinal Rebar')

        def _spec(dia, cnt, extend) -> Optional[RebarSpec]:
            if self._is_na(dia) or self._is_na(cnt):
                return None
            try:
                d = float(dia)
                c = int(float(cnt))
                e = float(extend or 0.0)
            except Exception:
                return None
            if d <= 1e-6 or c <= 0:
                return None
            return RebarSpec(diameter=d, count=c, extend_length=e)

        # 解析各位置的配筋
        rebars = {}
        support_len = {}
        for row in rows:
            position = row.get('Position', '')
            if position is None:
                continue
            position = str(position).strip()
            if not position:
                continue
            dia_a = row.get('Diameter_A', 0)
            count_a = row.get('Count_A', 0)
            dia_b = row.get('Diameter_B', None)
            count_b = row.get('Count_B', None)
            extend = row.get('Extend_Length', 0)

            rebar_a = _spec(dia_a, count_a, extend)

            rebar_b = None
            rebar_b = _spec(dia_b, count_b, extend)

            # 兼容：将“Top Through”映射为顶部通长筋（内部仍使用 mid_span_top 字段）
            key = "Mid Span Top" if position in ["Top Through", "顶部通长", "TopThrough"] else position
            rebars[key] = (rebar_a, rebar_b)
            if key in ["Left Support Top", "Right Support Top"]:
                try:
                    support_len[key] = float(extend or 0.0)
                except Exception:
                    pass

        # 构建 LongitudinalRebar 对象
        left_a, left_b = rebars.get('Left Support Top', (None, None))
        mid_a, _ = rebars.get('Mid Span Top', (None, None))
        right_a, right_b = rebars.get('Right Support Top', (None, None))
        bottom_a, bottom_b = rebars.get('Bottom Through', (None, None))

        if mid_a is None:
            raise ValueError("Longitudinal Rebar 缺少顶部通长筋：请提供 Position='Top Through' 或 'Mid Span Top' 的 Diameter_A/Count_A")
        if bottom_a is None:
            raise ValueError("Longitudinal Rebar 缺少底部通长筋：请提供 Position='Bottom Through' 的 Diameter_A/Count_A")

        lr = LongitudinalRebar(
            left_support_top_B=left_b,
            mid_span_top=mid_a,
            right_support_top_B=right_b,
            bottom_through_A=bottom_a,
            bottom_through_B=bottom_b
        )
        # 支座附加筋（可选）
        lr.left_support_top_A = left_a
        lr.right_support_top_A = right_a
        # 支座区长度：复用 Left/Right Support Top 行的 Extend_Length（更符合客户输入习惯）
        try:
            lr.left_support_length = float(support_len.get("Left Support Top", 0.0) or 0.0)
        except Exception:
            lr.left_support_length = 0.0
        try:
            lr.right_support_length = float(support_len.get("Right Support Top", 0.0) or 0.0)
        except Exception:
            lr.right_support_length = 0.0

        # 多排纵筋参数（可选 Sheet: Longitudinal Layout）
        # 表格格式：
        # | Group | Rows | RowSpacing |
        # | Top   | 2    | 40         |
        # | Bottom| 2    | 40         |
        try:
            layout_rows = self._read_rows('Longitudinal Layout')
        except Exception:
            layout_rows = []
        for r in layout_rows or []:
            group = str(r.get('Group', '') or '').strip().lower()
            if not group:
                continue
            try:
                rows_n = int(float(r.get('Rows', 1) or 1))
            except Exception:
                rows_n = 1
            try:
                sp = float(r.get('RowSpacing', 0.0) or 0.0)
            except Exception:
                sp = 0.0

            if group in ['top', '顶部', 'upper']:
                lr.top_rows = max(1, rows_n)
                lr.top_row_spacing = max(0.0, sp)
            elif group in ['bottom', '底部', 'lower']:
                lr.bottom_rows = max(1, rows_n)
                lr.bottom_row_spacing = max(0.0, sp)

        return lr

    def _parse_stirrup(self) -> StirrupParams:
        """解析 Sheet 3: Stirrups"""
        rows = self._read_rows('Stirrups')
        if not rows:
            raise ValueError("Stirrups sheet 为空或不存在")

        # 假设数据格式：
        # | Zone | Spacing | Legs | Diameter |
        # | Dense | ... | ... | ... |
        # | Normal | ... | ... | ... |

        dense_row = next((r for r in rows if str(r.get('Zone', '')).strip() == 'Dense'), None)
        normal_row = next((r for r in rows if str(r.get('Zone', '')).strip() == 'Normal'), None)
        if dense_row is None or normal_row is None:
            raise ValueError("Stirrups sheet 缺少 Dense/Normal 行")

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
        rows = self._read_rows('Holes')

        holes = []
        for row in rows:
            # 跳过空行
            if self._is_na(row.get('X', None)):
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
                small_beam_long_top_diameter=float(row.get('SmallBeam_Long_Top_Diameter', 0.0)),
                small_beam_long_top_count=int(row.get('SmallBeam_Long_Top_Count', 0)),
                small_beam_long_bottom_diameter=float(row.get('SmallBeam_Long_Bottom_Diameter', 0.0)),
                small_beam_long_bottom_count=int(row.get('SmallBeam_Long_Bottom_Count', 0)),
                small_beam_stirrup_diameter=float(row.get('SmallBeam_Stirrup_Diameter', 0.0)),
                small_beam_stirrup_spacing=float(row.get('SmallBeam_Stirrup_Spacing', 0.0)),
                small_beam_stirrup_legs=int(row.get('SmallBeam_Stirrup_Legs', 0) or 0),

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
        rows = self._read_rows('Loads')

        # 按工况名称分组
        load_cases = {}
        for row in rows:
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
            rows = self._read_rows('Boundary')
        except Exception:
            return BoundaryCondition()
        if not rows:
            return BoundaryCondition()

        # 假设格式：
        # | End | Dx | Dy | Dz | Rx | Ry | Rz | N | Vy | Vz | Mx | My | Mz |
        # | Left | ... | ... | ... |
        # | Right | ... | ... | ... |

        left_row = next((r for r in rows if str(r.get('End', '')).strip() == 'Left'), None)
        right_row = next((r for r in rows if str(r.get('End', '')).strip() == 'Right'), None)
        if left_row is None or right_row is None:
            return BoundaryCondition()

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
            rows = self._read_rows('Prestress')
        except Exception:
            return None
        if not rows:
            return None

        def _get_value(param_name: str, default=None):
            for r in rows:
                if str(r.get('Parameter', '')).strip() == param_name:
                    return r.get('Value', default)
            return default

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
