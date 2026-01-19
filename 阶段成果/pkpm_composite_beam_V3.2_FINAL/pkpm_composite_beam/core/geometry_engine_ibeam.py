"""
I-Beam Geometry Engine for PKPM Composite Beam

This module provides dedicated I-beam cross-section generation with:
- Asymmetric upper/lower flange support (V3.0 protocol)
- Boolean union composition for unified solid objects
- Web centerline offset calculation for non-symmetric sections

Author: Claude (Opus 4.5)
Date: 2025-12-31
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass


@dataclass
class IBeamComponent:
    """Represents a single I-beam component (web or flange)"""
    name: str  # "web_pre", "flange_ll", etc.
    center_x: float
    center_y: float
    center_z: float
    width_x: float  # Length along beam axis
    width_y: float  # Width (transverse)
    height_z: float  # Height (vertical)


class IBeamGeometryEngine:
    """
    Dedicated engine for generating I-beam cross-sections with boolean_union composition.

    Supports V3.0 protocol with asymmetric flanges:
    - Upper flanges: bf_lu, tf_lu (left), bf_ru, tf_ru (right)
    - Lower flanges: bf_ll, tf_ll (left), bf_rl, tf_rl (right)
    - Web: Tw (width), H (total height)

    Output: Unified Solid objects via Solid.boolean_union([components])
    """

    def __init__(self, geometry_params):
        """
        Initialize I-beam geometry engine

        Args:
            geometry_params: GeometryParams object with flange dimensions
        """
        self.params = geometry_params
        self.web_offset_y = self.params.get_web_centerline_offset()

    def create_ibeam_section(self) -> Dict[str, Any]:
        """
        Creates complete I-beam cross-section with boolean_union composition

        Returns:
            dict: {
                'precast_components': List[IBeamComponent],  # Components for precast layer
                'cast_components': List[IBeamComponent],     # Components for cast layer
                'web_offset_y': float,                       # Web centerline offset
                'success': bool,
                'message': str
            }
        """
        try:
            # Create precast layer components (web + lower flanges)
            precast_components = []

            # 1. Web (precast portion)
            web_pre = self._create_web(height=self.params.h_pre)
            precast_components.append(web_pre)

            # 2. Lower flanges
            lower_flanges = self._create_lower_flanges()
            precast_components.extend(lower_flanges)

            # Create cast layer components (web extension + upper flanges)
            cast_components = []

            # 3. Web (cast portion - extends upward from precast)
            web_cast = self._create_web_extension()
            cast_components.append(web_cast)

            # 4. Upper flanges
            upper_flanges = self._create_upper_flanges()
            cast_components.extend(upper_flanges)

            return {
                'precast_components': precast_components,
                'cast_components': cast_components,
                'web_offset_y': self.web_offset_y,
                'success': True,
                'message': f'I-beam created: {len(precast_components)} precast + {len(cast_components)} cast components'
            }

        except Exception as e:
            return {
                'precast_components': [],
                'cast_components': [],
                'web_offset_y': self.web_offset_y,
                'success': False,
                'message': f'I-beam creation failed: {str(e)}'
            }

    def _create_web(self, height: float) -> IBeamComponent:
        """
        Creates web box solid for precast layer

        Args:
            height: Web height (h_pre for precast layer)

        Returns:
            IBeamComponent for web
        """
        g = self.params

        return IBeamComponent(
            name='web_pre',
            center_x=g.L / 2,
            center_y=self.web_offset_y,  # Apply offset for asymmetric sections
            center_z=height / 2,
            width_x=g.L,
            width_y=g.Tw,
            height_z=height
        )

    def _create_web_extension(self) -> IBeamComponent:
        """
        Creates web extension for cast layer (continues upward from precast)

        Returns:
            IBeamComponent for cast layer web
        """
        g = self.params
        h_cast = g.H - g.h_pre  # Calculate cast height

        return IBeamComponent(
            name='web_cast',
            center_x=g.L / 2,
            center_y=self.web_offset_y,
            center_z=g.h_pre + h_cast / 2,  # Positioned above precast layer
            width_x=g.L,
            width_y=g.Tw,
            height_z=h_cast
        )

    def _create_lower_flanges(self) -> List[IBeamComponent]:
        """
        Creates lower left and right flange box solids

        Returns:
            List of IBeamComponent (0-2 flanges depending on tf values)
        """
        g = self.params
        flanges = []

        # Lower left flange (if thickness > 0)
        if g.tf_ll > 0 and g.bf_ll > 0:
            y_center = -g.Tw/2 - g.bf_ll/2 + self.web_offset_y

            flanges.append(IBeamComponent(
                name='flange_ll',
                center_x=g.L / 2,
                center_y=y_center,
                center_z=g.tf_ll / 2,
                width_x=g.L,
                width_y=g.bf_ll,
                height_z=g.tf_ll
            ))

        # Lower right flange (if thickness > 0)
        if g.tf_rl > 0 and g.bf_rl > 0:
            y_center = g.Tw/2 + g.bf_rl/2 + self.web_offset_y

            flanges.append(IBeamComponent(
                name='flange_rl',
                center_x=g.L / 2,
                center_y=y_center,
                center_z=g.tf_rl / 2,
                width_x=g.L,
                width_y=g.bf_rl,
                height_z=g.tf_rl
            ))

        return flanges

    def _create_upper_flanges(self) -> List[IBeamComponent]:
        """
        Creates upper left and right flange box solids

        Returns:
            List of IBeamComponent (0-2 flanges depending on tf values)
        """
        g = self.params
        flanges = []
        H_total = g.H

        # Upper left flange (if thickness > 0)
        if g.tf_lu > 0 and g.bf_lu > 0:
            y_center = -g.Tw/2 - g.bf_lu/2 + self.web_offset_y
            z_center = H_total - g.tf_lu / 2

            flanges.append(IBeamComponent(
                name='flange_lu',
                center_x=g.L / 2,
                center_y=y_center,
                center_z=z_center,
                width_x=g.L,
                width_y=g.bf_lu,
                height_z=g.tf_lu
            ))

        # Upper right flange (if thickness > 0)
        if g.tf_ru > 0 and g.bf_ru > 0:
            y_center = g.Tw/2 + g.bf_ru/2 + self.web_offset_y
            z_center = H_total - g.tf_ru / 2

            flanges.append(IBeamComponent(
                name='flange_ru',
                center_x=g.L / 2,
                center_y=y_center,
                center_z=z_center,
                width_x=g.L,
                width_y=g.bf_ru,
                height_z=g.tf_ru
            ))

        return flanges

    def generate_pkpm_creation_code(self, components: List[IBeamComponent],
                                   material_name: str = 'concrete') -> List[str]:
        """
        Generates PKPM-CAE Python API code for creating component solids

        Args:
            components: List of IBeamComponent objects
            material_name: Material variable name (e.g., 'concrete')

        Returns:
            List of code lines (without indentation)
        """
        code_lines = []

        for comp in components:
            code_lines.append(f'# {comp.name.replace("_", " ").title()}')
            code_lines.append(f'{comp.name} = Solid.create_box(')
            code_lines.append(f'    length={comp.width_x:.1f},')
            code_lines.append(f'    width={comp.width_y:.1f},')
            code_lines.append(f'    height={comp.height_z:.1f},')
            code_lines.append(f'    center=({comp.center_x:.1f}, {comp.center_y:.1f}, {comp.center_z:.1f}),')
            code_lines.append(f'    material={material_name}')
            code_lines.append(')')
            code_lines.append('')

        return code_lines

    def generate_pkpm_composition_code(self, components: List[IBeamComponent],
                                      result_var_name: str = 'solid') -> List[str]:
        """
        Generates PKPM-CAE boolean_union code for composing components

        Args:
            components: List of IBeamComponent objects to compose
            result_var_name: Name for the resulting solid variable

        Returns:
            List of code lines (without indentation)
        """
        if len(components) == 0:
            return [f'{result_var_name} = None  # No components to compose']

        elif len(components) == 1:
            # Single component - no boolean needed
            return [f'{result_var_name} = {components[0].name}']

        else:
            # Multiple components - use boolean_union
            component_names = [comp.name for comp in components]
            code_lines = [
                f'# Compose {len(components)} components via boolean union',
                f'{result_var_name} = Solid.boolean_union([',
                f'    {", ".join(component_names)}',
                '])'
            ]
            return code_lines

    def validate_geometry(self) -> Dict[str, Any]:
        """
        Validates I-beam geometry parameters

        Returns:
            dict: {'valid': bool, 'errors': List[str], 'warnings': List[str]}
        """
        errors = []
        warnings = []
        g = self.params

        # Check basic dimensions
        if g.L <= 0:
            errors.append(f'Beam length L={g.L} must be > 0')
        if g.Tw <= 0:
            errors.append(f'Web thickness Tw={g.Tw} must be > 0')
        if g.H <= 0:
            errors.append(f'Total height H={g.H} must be > 0')
        if g.h_pre <= 0:
            errors.append(f'Precast height h_pre={g.h_pre} must be > 0')

        h_cast = g.H - g.h_pre
        if h_cast < 0:
            errors.append(f'Cast height h_cast={h_cast} cannot be negative (H={g.H}, h_pre={g.h_pre})')

        # Check flange consistency
        if g.bf_ll > 0 and g.tf_ll <= 0:
            warnings.append('Lower left flange has width but no thickness')
        if g.bf_rl > 0 and g.tf_rl <= 0:
            warnings.append('Lower right flange has width but no thickness')
        if g.bf_lu > 0 and g.tf_lu <= 0:
            warnings.append('Upper left flange has width but no thickness')
        if g.bf_ru > 0 and g.tf_ru <= 0:
            warnings.append('Upper right flange has width but no thickness')

        # Check for realistic asymmetry
        asymmetry = abs(g.bf_rl - g.bf_ll)
        if asymmetry > g.Tw * 2:
            warnings.append(f'Large flange asymmetry: {asymmetry:.1f}mm (may indicate data error)')

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


# Test function for development
def _test_ibeam_engine():
    """Test I-beam geometry engine with sample parameters"""
    from core.parameters import GeometryParams

    # Test case 1: Symmetric I-beam
    params_symmetric = GeometryParams(
        L=10000, Tw=250, H=800, h_pre=600,  # h_cast = H - h_pre = 200
        bf_ll=125, tf_ll=80, bf_rl=125, tf_rl=80,  # Symmetric lower flanges
        bf_lu=125, tf_lu=100, bf_ru=125, tf_ru=100  # Symmetric upper flanges
    )

    engine = IBeamGeometryEngine(params_symmetric)
    result = engine.create_ibeam_section()

    print("=== Test Case 1: Symmetric I-Beam ===")
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Web offset: {result['web_offset_y']:.1f} mm")
    print(f"Precast components: {[c.name for c in result['precast_components']]}")
    print(f"Cast components: {[c.name for c in result['cast_components']]}")

    # Test case 2: Asymmetric T-beam
    params_asymmetric = GeometryParams(
        L=10000, Tw=250, H=800, h_pre=600,  # h_cast = H - h_pre = 200
        bf_ll=100, tf_ll=80, bf_rl=150, tf_rl=80,  # Asymmetric lower
        bf_lu=0, tf_lu=0, bf_ru=0, tf_ru=0  # No upper flanges
    )

    engine2 = IBeamGeometryEngine(params_asymmetric)
    result2 = engine2.create_ibeam_section()

    print("\n=== Test Case 2: Asymmetric T-Beam ===")
    print(f"Success: {result2['success']}")
    print(f"Message: {result2['message']}")
    print(f"Web offset: {result2['web_offset_y']:.1f} mm (should be 25mm)")
    print(f"Precast components: {[c.name for c in result2['precast_components']]}")

    # Generate code sample
    print("\n=== Generated PKPM Code (Precast) ===")
    code = engine.generate_pkpm_creation_code(result['precast_components'])
    for line in code[:10]:  # Show first 10 lines
        print(f'    {line}')
    print('    ...')


if __name__ == '__main__':
    _test_ibeam_engine()
