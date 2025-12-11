from typing import Tuple, Optional
from .ecu_definition import EcuTable

class MapTracer:
    """
    Logic for 'Map Tracing' - determining the active cell in a map
    based on current sensor values.
    """
    
    @staticmethod
    def get_active_cell(table: EcuTable, x_val: float, y_val: float) -> Tuple[int, int]:
        """
        Returns the (row_index, col_index) of the active cell.
        Uses simple nearest-neighbor or lower-bound logic.
        """
        col_idx = MapTracer._find_nearest_index(table.x_breakpoints, x_val)
        row_idx = MapTracer._find_nearest_index(table.y_breakpoints, y_val)
        
        return row_idx, col_idx

    @staticmethod
    def _find_nearest_index(breakpoints: list[float], value: float) -> int:
        """
        Finds the index of the breakpoint closest to the value.
        """
        if not breakpoints:
            return 0
            
        # Simple implementation: find closest
        closest_idx = 0
        min_diff = float('inf')
        
        for i, bp in enumerate(breakpoints):
            diff = abs(value - bp)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
                
        return closest_idx

    @staticmethod
    def format_trace_output(table: EcuTable, active_row: int, active_col: int) -> str:
        """
        Creates a simple text visualization of the map with the active cell highlighted.
        """
        output = [f"Map: {table.name} (X: {table.x_axis_param}, Y: {table.y_axis_param})"]
        
        # Header (X-axis breakpoints)
        header = "      | " + " | ".join(f"{bp:^6}" for bp in table.x_breakpoints)
        output.append(header)
        output.append("-" * len(header))
        
        # Rows
        for r_idx, y_bp in enumerate(table.y_breakpoints):
            row_str = f"{y_bp:>5} | "
            for c_idx, val in enumerate(table.data[r_idx]):
                cell_text = f"{val:^6}"
                if r_idx == active_row and c_idx == active_col:
                    cell_text = f"[{val:^4}]" # Highlight active cell
                row_str += cell_text + " | "
            output.append(row_str)
            
        return "\n".join(output)