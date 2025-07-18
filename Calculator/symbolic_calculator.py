from mcp.server.fastmcp import FastMCP
import sys
from loguru import logger
import sympy as sp
from sympy import symbols, sympify, latex, simplify, expand, factor, solve, diff, integrate, limit, series
from sympy.printing import pretty, pprint

# Configure loguru logger to output to stderr
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | SymbolicCalc | {message}", level="INFO")

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

# Create an MCP server
mcp = FastMCP("SymbolicCalculator")

def format_math_result(result, show_steps=False):
    """
    Format mathematical result in multiple formats for better display
    
    Args:
        result: SymPy expression result
        show_steps: Whether to show step-by-step formatting
    
    Returns:
        Dictionary with multiple format options
    """
    try:
        # Basic string representation
        result_str = str(result)
        
        # Pretty print (ASCII art style)
        pretty_str = pretty(result, use_unicode=True)
        
        # LaTeX format
        latex_str = latex(result)
        
        # Mathematical notation using Unicode
        unicode_str = sp.pretty(result, use_unicode=True)
        
        # Simplified readable format
        readable_str = str(result).replace('**', '^').replace('*', '·')
        
        return {
            "standard": result_str,
            "pretty": pretty_str,
            "latex": latex_str,
            "unicode": unicode_str,
            "readable": readable_str
        }
    except Exception as e:
        logger.warning(f"Error formatting result: {e}")
        return {
            "standard": str(result),
            "pretty": str(result),
            "latex": str(result),
            "unicode": str(result),
            "readable": str(result)
        }

@mcp.tool()
def symbolic_calculate(expression: str, operation: str = "simplify", show_steps: bool = False) -> dict:
    """
    Perform symbolic mathematical calculations using SymPy.
    
    Args:
        expression: Mathematical expression as string (e.g., "x**2 + 2*x + 1", "sin(x)*cos(x)")
        operation: Type of operation to perform (simplify, expand, factor, solve, diff, integrate)
        show_steps: Whether to show step-by-step calculation
    
    Returns:
        Dictionary containing the result of symbolic calculation in multiple formats
    """
    try:
        # Parse the expression
        expr = sympify(expression)
        
        # Show original expression in pretty format
        original_formats = format_math_result(expr)
        
        # Perform the requested operation
        if operation == "simplify":
            result = simplify(expr)
        elif operation == "expand":
            result = expand(expr)
        elif operation == "factor":
            result = factor(expr)
        elif operation == "solve":
            # Try to find free symbols and solve for the first one
            free_vars = list(expr.free_symbols)
            if free_vars:
                result = solve(expr, free_vars[0])
            else:
                result = "No variables to solve for"
        elif operation == "diff":
            # Differentiate with respect to the first free symbol
            free_vars = list(expr.free_symbols)
            if free_vars:
                result = diff(expr, free_vars[0])
            else:
                result = "No variables to differentiate"
        elif operation == "integrate":
            # Integrate with respect to the first free symbol
            free_vars = list(expr.free_symbols)
            if free_vars:
                result = integrate(expr, free_vars[0])
            else:
                result = "No variables to integrate"
        else:
            result = simplify(expr)  # Default to simplify
        
        # Format result in multiple ways
        result_formats = format_math_result(result)
        
        # Create a readable summary
        summary = f"""
Mathematical Expression: {original_formats['readable']}
Operation: {operation}
Result: {result_formats['readable']}

Pretty Format:
{result_formats['pretty']}
        """.strip()
        
        logger.info(f"Symbolic calculation: {operation}({expression}) = {result_formats['standard']}")
        
        return {
            "success": True,
            "operation": operation,
            "expression": expression,
            "original_formats": original_formats,
            "result_formats": result_formats,
            "summary": summary,
            "free_symbols": [str(sym) for sym in expr.free_symbols]
        }
        
    except Exception as e:
        error_msg = f"Symbolic calculation error: {str(e)}"
        logger.error(f"Error in '{expression}' with operation '{operation}': {error_msg}")
        
        return {
            "success": False,
            "error": error_msg,
            "expression": expression,
            "operation": operation
        }

@mcp.tool()
def solve_equation(equation: str, variable: str = None) -> dict:
    """
    Solve equations symbolically with enhanced formatting.
    
    Args:
        equation: Equation to solve (e.g., "x**2 - 4 = 0", "2*x + 3*y = 6")
        variable: Variable to solve for (optional, will use first free symbol if not specified)
    
    Returns:
        Dictionary containing the solutions in multiple formats
    """
    try:
        # Parse the equation
        if "=" in equation:
            left, right = equation.split("=", 1)
            expr = sympify(left) - sympify(right)
        else:
            expr = sympify(equation)
        
        # Determine variable to solve for
        if variable:
            var = symbols(variable)
        else:
            free_vars = list(expr.free_symbols)
            if free_vars:
                var = free_vars[0]
            else:
                return {"success": False, "error": "No variables found in equation"}
        
        # Solve the equation
        solutions = solve(expr, var)
        
        # Format solutions in multiple ways
        formatted_solutions = []
        for i, sol in enumerate(solutions):
            sol_formats = format_math_result(sol)
            formatted_solutions.append({
                "index": i + 1,
                "formats": sol_formats
            })
        
        # Create readable summary
        if solutions:
            solutions_text = "\n".join([f"  {var} = {format_math_result(sol)['readable']}" for sol in solutions])
            summary = f"""
Equation: {equation}
Variable: {var}
Number of solutions: {len(solutions)}

Solutions:
{solutions_text}
            """.strip()
        else:
            summary = f"Equation: {equation}\nVariable: {var}\nNo solutions found."
        
        logger.info(f"Solved equation: {equation} for {var}, found {len(solutions)} solutions")
        
        return {
            "success": True,
            "equation": equation,
            "variable": str(var),
            "solutions": formatted_solutions,
            "num_solutions": len(solutions),
            "summary": summary
        }
        
    except Exception as e:
        error_msg = f"Equation solving error: {str(e)}"
        logger.error(f"Error solving '{equation}': {error_msg}")
        
        return {
            "success": False,
            "error": error_msg,
            "equation": equation
        }

@mcp.tool()
def calculus_operation(expression: str, operation: str, variable: str = None, **kwargs) -> dict:
    """
    Perform calculus operations with enhanced formatting.
    
    Args:
        expression: Mathematical expression
        operation: Calculus operation (diff, integrate, limit, series)
        variable: Variable for the operation (optional)
        **kwargs: Additional parameters (e.g., point for limit, n for series order)
    
    Returns:
        Dictionary containing the result of calculus operation in multiple formats
    """
    try:
        expr = sympify(expression)
        
        # Determine variable
        if variable:
            var = symbols(variable)
        else:
            free_vars = list(expr.free_symbols)
            if free_vars:
                var = free_vars[0]
            else:
                return {"success": False, "error": "No variables found in expression"}
        
        # Perform calculus operation
        if operation == "diff":
            order = kwargs.get("order", 1)
            result = diff(expr, var, order)
            op_desc = f"d^{order}/d{var}^{order}" if order > 1 else f"d/d{var}"
        elif operation == "integrate":
            if "limits" in kwargs:
                limits = kwargs["limits"]
                result = integrate(expr, (var, limits[0], limits[1]))
                op_desc = f"∫[{limits[0]} to {limits[1]}] ... d{var}"
            else:
                result = integrate(expr, var)
                op_desc = f"∫ ... d{var}"
        elif operation == "limit":
            point = kwargs.get("point", 0)
            direction = kwargs.get("direction", "+-")
            result = limit(expr, var, point, direction)
            op_desc = f"lim({var} → {point})"
        elif operation == "series":
            point = kwargs.get("point", 0)
            n = kwargs.get("n", 6)
            result = series(expr, var, point, n)
            op_desc = f"series expansion around {var} = {point}"
        else:
            return {"success": False, "error": f"Unknown calculus operation: {operation}"}
        
        # Format results
        original_formats = format_math_result(expr)
        result_formats = format_math_result(result)
        
        # Create summary
        summary = f"""
Expression: {original_formats['readable']}
Operation: {op_desc}
Variable: {var}
Result: {result_formats['readable']}

Pretty Format:
{result_formats['pretty']}
        """.strip()
        
        logger.info(f"Calculus operation: {operation}({expression}) = {result_formats['standard']}")
        
        return {
            "success": True,
            "operation": operation,
            "expression": expression,
            "variable": str(var),
            "original_formats": original_formats,
            "result_formats": result_formats,
            "summary": summary,
            "parameters": kwargs
        }
        
    except Exception as e:
        error_msg = f"Calculus operation error: {str(e)}"
        logger.error(f"Error in {operation}('{expression}'): {error_msg}")
        
        return {
            "success": False,
            "error": error_msg,
            "expression": expression,
            "operation": operation
        }

@mcp.tool()
def matrix_operations(matrix_data: str, operation: str = "det") -> dict:
    """
    Perform matrix operations with enhanced formatting.
    
    Args:
        matrix_data: Matrix data as string (e.g., "[[1,2],[3,4]]" or "Matrix([[1,2],[3,4]])")
        operation: Matrix operation (det, inv, eigenvals, eigenvects, transpose, rref)
    
    Returns:
        Dictionary containing the result of matrix operation in multiple formats
    """
    try:
        # Parse matrix data
        if matrix_data.startswith("Matrix"):
            matrix = sympify(matrix_data)
        else:
            # Try to parse as list of lists
            matrix_list = eval(matrix_data)
            matrix = sp.Matrix(matrix_list)
        
        # Format original matrix
        matrix_formats = format_math_result(matrix)
        
        # Perform matrix operation
        if operation == "det":
            result = matrix.det()
        elif operation == "inv":
            result = matrix.inv()
        elif operation == "transpose":
            result = matrix.T
        elif operation == "eigenvals":
            result = matrix.eigenvals()
        elif operation == "eigenvects":
            result = matrix.eigenvects()
        elif operation == "rref":
            result = matrix.rref()
        else:
            return {"success": False, "error": f"Unknown matrix operation: {operation}"}
        
        # Format result
        result_formats = format_math_result(result)
        
        # Create summary
        summary = f"""
Matrix ({matrix.rows}×{matrix.cols}):
{matrix_formats['pretty']}

Operation: {operation}
Result:
{result_formats['pretty']}
        """.strip()
        
        logger.info(f"Matrix operation: {operation} on {matrix.shape} matrix")
        
        return {
            "success": True,
            "operation": operation,
            "matrix_shape": matrix.shape,
            "matrix_formats": matrix_formats,
            "result_formats": result_formats,
            "summary": summary
        }
        
    except Exception as e:
        error_msg = f"Matrix operation error: {str(e)}"
        logger.error(f"Error in matrix {operation}: {error_msg}")
        
        return {
            "success": False,
            "error": error_msg,
            "operation": operation
        }

@mcp.tool()
def display_formula(expression: str) -> dict:
    """
    Display mathematical formula in multiple readable formats.
    
    Args:
        expression: Mathematical expression to display
    
    Returns:
        Dictionary containing the expression in various formats
    """
    try:
        expr = sympify(expression)
        formats = format_math_result(expr)
        
        # Create a comprehensive display
        display_text = f"""
Mathematical Expression Display
==============================

Standard Format: {formats['standard']}
Readable Format: {formats['readable']}

Pretty Print (ASCII Art):
{formats['pretty']}

Unicode Format:
{formats['unicode']}

LaTeX Format: {formats['latex']}

Variables: {', '.join(str(sym) for sym in expr.free_symbols) if expr.free_symbols else 'None'}
        """.strip()
        
        logger.info(f"Displayed formula: {expression}")
        
        return {
            "success": True,
            "expression": expression,
            "formats": formats,
            "display_text": display_text,
            "free_symbols": [str(sym) for sym in expr.free_symbols]
        }
        
    except Exception as e:
        error_msg = f"Display error: {str(e)}"
        logger.error(f"Error displaying '{expression}': {error_msg}")
        
        return {
            "success": False,
            "error": error_msg,
            "expression": expression
        }

# Start the server
if __name__ == "__main__":
    logger.info("Symbolic Calculator MCP Server starting...")
    mcp.run(transport="stdio")