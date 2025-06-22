import pandas as pd
import streamlit as st
from math import isclose
from itertools import combinations
import io
from datetime import datetime
import time

# --- Progress Tracking ---
class ProgressTracker:
    def __init__(self, total_steps):
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.current_step = 0
        self.total_steps = total_steps

    def update(self, message):
        self.current_step += 1
        progress = min(self.current_step / self.total_steps, 1.0)
        self.progress_bar.progress(progress)
        self.status_text.text(f"{message} ({self.current_step}/{self.total_steps})")

# --- Core Functions with Progress ---
def find_subsets(data, targets, operation, tolerance=0, progress=None):
    results = []
    for i, target in enumerate(targets):
        if progress:
            progress.update(f"Searching for {target}")

        if operation == "sum":
            subset = find_subset_sum(data, target, tolerance, progress)
        elif operation == "product":
            subset = find_subset_product(data, target, tolerance, progress)
        elif operation == "difference":
            subset = find_subset_difference(data, target, tolerance, progress)
        elif operation == "quotient":
            subset = find_subset_quotient(data, target, tolerance, progress)

        if subset:
            results.append((target, subset))
    return results

def find_subset_sum(data, target, tolerance, progress=None):
    dp = {0: []}
    for i, item in enumerate(data):
        if progress and i % 100 == 0:  # Update every 100 items
            progress.update(f"Checking sum combinations")

        for s in list(dp.keys()):
            new_sum = s + item["value"]
            if abs(new_sum - target) <= tolerance:
                return dp[s] + [item]
            if new_sum not in dp:
                dp[new_sum] = dp[s] + [item]
    return None


def find_subset_difference(data, target, tolerance, progress=None):
    """
    Finds two numbers where |a - b| ≈ target (±tolerance)
    Returns list of items with column/row info
    """
    values = [item["value"] for item in data]  # Extract numerical values

    # Check all unique pairs
    for (a, b) in combinations(values, 2):
        if progress:
            progress.update("Checking difference combinations")

        if abs(abs(a - b) - target) <= tolerance:
            # Find and return the original items with metadata
            return reconstruct_items(data, [a, b])

    return None


def find_subset_product(data, target, tolerance, progress=None):
    """
    Finds subset where product ≈ target (±tolerance%)
    Checks pairs and triplets
    """
    values = [item["value"] for item in data if item["value"] != 0]  # Exclude zeros

    # Check pairs first (most common case)
    for subset in combinations(values, 2):
        if progress:
            progress.update("Checking product pairs")

        product = subset[0] * subset[1]
        if abs(product - target) <= tolerance * target:
            return reconstruct_items(data, subset)

    # Check triplets if no pair found
    for subset in combinations(values, 3):
        if progress:
            progress.update("Checking product triplets")

        product = subset[0] * subset[1] * subset[2]
        if abs(product - target) <= tolerance * target:
            return reconstruct_items(data, subset)

    return None


def find_subset_quotient(data, target, tolerance, progress=None):
    """
    Finds pair where a/b ≈ target (±tolerance%)
    or b/a ≈ target
    """
    data = [item for item in data if item["value"] != 0]  # Exclude division by zero
    values = [item["value"] for item in data]

    for (a, b) in combinations(values, 2):
        if progress:
            progress.update("Checking quotient pairs")

        if (isclose(a / b, target, rel_tol=tolerance) or
                isclose(b / a, target, rel_tol=tolerance)):
            return reconstruct_items(data, [a, b])

    return None


def reconstruct_items(full_data, values):
    """
    Helper: Maps values back to original items with metadata
    """
    result = []
    remaining = list(values)

    for item in full_data:
        if item["value"] in remaining:
            result.append(item)
            remaining.remove(item["value"])
            if not remaining:
                return result
    return None

# ... [keep other functions unchanged but add progress param] ...

# --- UI Setup ---
def main():
    st.set_page_config(page_title="Target Value Finder", layout="wide")

    # App Header
    st.title("🎯 Advanced Target Value Finder")
    st.markdown("""
    *Find number combinations matching targets with real-time progress tracking*
    """)

    # Configuration Panel
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        match_mode = st.radio(
            "Search mode:",
            ["Single target", "Multiple targets", "Approximate match"]
        )

        if match_mode == "Multiple targets":
            target_input = st.text_input("Targets (comma-separated):", "25, 50, 100")
            targets = [float(x.strip()) for x in target_input.split(",")]
        else:
            target = st.number_input("Target value:", value=25.0)
            targets = [target]

        if match_mode == "Approximate match":
            tolerance = st.slider("Tolerance (%):", 0.0, 20.0, 5.0) / 100
        else:
            tolerance = 0

        operation = st.selectbox(
            "Operation:",
            ["sum", "difference", "product", "quotient"]
        )

    # Main Content
    uploaded_file = st.file_uploader("📤 Upload Excel/CSV", type=["xlsx", "csv"])

    if uploaded_file and st.button("🔍 Find Matches", type="primary"):
        try:
            # Data Loading
            if uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            else:
                df = pd.read_csv(uploaded_file)

            numeric_cols = df.select_dtypes(include=['number']).columns
            selected_cols = st.multiselect("Select columns:", numeric_cols, default=list(numeric_cols))

            if not selected_cols:
                st.warning("Please select columns")
                st.stop()

            # Prepare data
            data = []
            for col in selected_cols:
                for idx, value in df[col].dropna().items():
                    data.append({
                        "value": value,
                        "column": col,
                        "row": idx + 2
                    })

            # Estimate progress steps
            progress_steps = len(targets) * len(data)  # Rough estimate
            progress = ProgressTracker(progress_steps)

            # Run search
            with st.spinner("Starting search..."):
                start_time = time.time()
                results = find_subsets(data, targets, operation, tolerance, progress)
                duration = time.time() - start_time

            # Display results
            st.success(f"Search completed in {duration:.1f} seconds")
            display_results(results, operation)

        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.stop()

def display_results(results, operation):
    if not results:
        st.error("No matches found")
        return

    st.success(f"Found {len(results)} match(es)")
    for target, subset in results:
        with st.expander(f"Target: {target}", expanded=True):
            # Generate formula
            if operation == "sum":
                formula = " + ".join(str(item["value"]) for item in subset)
            elif operation == "product":
                formula = " × ".join(str(item["value"]) for item in subset)
            elif operation == "difference":
                formula = f"{subset[0]['value']} − {subset[1]['value']}"
            elif operation == "quotient":
                formula = f"{subset[0]['value']} ÷ {subset[1]['value']}"

            st.markdown(f"**Solution:** {formula} = {target}")

            # Detailed table
            result_df = pd.DataFrame([{
                "Value": item["value"],
                "Column": item["column"],
                "Row": item["row"]
            } for item in subset])

            st.dataframe(result_df)

if __name__ == "__main__":
    main()