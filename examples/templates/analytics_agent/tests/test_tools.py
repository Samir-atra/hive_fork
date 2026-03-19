import os
import sys
import json

# Add parent dir to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools import analyze_data, generate_visualization

def test_analyze_data(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("A,B\n1,2\n3,4\n5,6\n")

    result = analyze_data(str(csv_file))
    data = json.loads(result)

    assert "columns" in data
    assert "rows" in data
    assert data["rows"] == 3
    assert data["columns"] == ["A", "B"]

def test_generate_visualization(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("A,B\n1,2\n3,4\n5,6\n")

    # We change directory to tmp_path so 'outputs' dir is created there
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = generate_visualization(str(csv_file), column_x="A", plot_type="hist")
        assert "Plot successfully generated" in result
        assert os.path.exists("outputs/hist_A.png")
    finally:
        os.chdir(original_cwd)
