import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
import io
import os
from typing import Optional

def analyze_data(file_path: str) -> str:
    """
    Perform automated EDA and statistical summaries on a given dataset (CSV).

    Args:
        file_path: The path to the CSV file to analyze.

    Returns:
        A JSON string containing basic statistics and insights.
    """
    try:
        df = pd.read_csv(file_path)

        summary = {
            "columns": list(df.columns),
            "rows": len(df),
            "missing_values": df.isnull().sum().to_dict(),
            "describe": df.describe().to_dict()
        }

        return json.dumps(summary, indent=2)
    except Exception as e:
        return f"Error analyzing data: {str(e)}"

def generate_visualization(file_path: str, column_x: str, column_y: Optional[str] = None, plot_type: str = "bar") -> str:
    """
    Generate a basic visualization for the dataset.

    Args:
        file_path: The path to the CSV file.
        column_x: The primary column for the X-axis.
        column_y: The optional column for the Y-axis.
        plot_type: The type of plot to generate ('bar', 'scatter', 'hist').

    Returns:
        A message indicating success and where the plot was saved.
    """
    try:
        df = pd.read_csv(file_path)
        plt.figure(figsize=(10, 6))

        if plot_type == "bar":
            if column_y:
                sns.barplot(data=df, x=column_x, y=column_y)
            else:
                df[column_x].value_counts().plot(kind='bar')
        elif plot_type == "scatter":
            if not column_y:
                return "Scatter plot requires both column_x and column_y."
            sns.scatterplot(data=df, x=column_x, y=column_y)
        elif plot_type == "hist":
            sns.histplot(data=df, x=column_x, kde=True)
        else:
            return f"Unsupported plot type: {plot_type}"

        plt.title(f"{plot_type.capitalize()} Plot of {column_x}" + (f" vs {column_y}" if column_y else ""))
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()

        os.makedirs("outputs", exist_ok=True)
        output_file = f"outputs/{plot_type}_{column_x}.png"
        with open(output_file, "wb") as f:
            f.write(buf.getvalue())

        return f"Plot successfully generated and saved to {output_file}"

    except Exception as e:
        return f"Error generating visualization: {str(e)}"
