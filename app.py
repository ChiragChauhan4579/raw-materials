import streamlit as st
import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, value


# -----------------------------
# SAMPLE DATA
# -----------------------------
def create_sample_data():
    nutrition = pd.DataFrame({
        "Protein": [0.10, 0.20, 0.15, 0.00, 0.04, 0.033, 0.258],
        "Fat": [0.08, 0.10, 0.11, 0.01, 0.01, 0.013, 0.492],
        "Fibre": [0.001, 0.005, 0.003, 0.10, 0.15, 0.028, 0.085],
        "Salt": [0.002, 0.005, 0.007, 0.002, 0.008, 0.000, 0.001],
        "Sugar": [0.000, 0.000, 0.000, 0.000, 0.000, 0.045, 0.047],
    }, index=["Chicken", "Beef", "Mutton", "Rice", "Wheat bran", "Corn", "Peanuts"])

    dict_costs = {
        "Chicken": 0.095,
        "Beef": 0.150,
        "Mutton": 0.100,
        "Rice": 0.002,
        "Wheat bran": 0.005,
        "Corn": 0.012,
        "Peanuts": 0.013,
    }

    return nutrition, dict_costs


# -----------------------------
# OPTIMIZATION
# -----------------------------
def optimize_recipe(nutrition, dict_costs, bar_weight, constraints):

    ingredients = list(nutrition.index)

    model = LpProblem("Meal_Bar_Recipe", LpMinimize)

    x = LpVariable.dicts("qty", ingredients, lowBound=0)

    model += lpSum([dict_costs[i] * x[i] for i in ingredients])

    model += lpSum([x[i] for i in ingredients]) == bar_weight

    for nutrient, (op, limit) in constraints.items():

        nutrient_sum = lpSum([
            x[i] * nutrition.loc[i, nutrient] for i in ingredients
        ])

        if op == ">=":
            model += nutrient_sum >= limit
        else:
            model += nutrient_sum <= limit

    model.solve()

    return model, x


# -----------------------------
# STREAMLIT UI
# -----------------------------
st.title("Food Manufacturing Raw Material Optimizer")

st.write(
"""
This tool uses **Linear Programming** to find the cheapest ingredient mix
while meeting nutritional constraints.
"""
)

# -----------------------------
# FILE UPLOAD
# -----------------------------
st.sidebar.header("Upload Data")

nutrition_file = st.sidebar.file_uploader(
    "Upload Nutrition Excel", type=["xlsx"]
)

cost_file = st.sidebar.file_uploader(
    "Upload Cost Excel", type=["xlsx"]
)


if nutrition_file and cost_file:

    nutrition = pd.read_excel(nutrition_file, index_col=0)
    costs = pd.read_excel(cost_file)

    dict_costs = dict(zip(costs["Ingredients"], costs["Costs"]))

    st.success("Data loaded from Excel")

else:

    st.warning("Using sample dataset")
    nutrition, dict_costs = create_sample_data()


# -----------------------------
# DISPLAY INPUT DATA
# -----------------------------
st.subheader("Nutrition Data (per gram)")
st.dataframe(nutrition.astype(str))

cost_df = pd.DataFrame(dict_costs.items(), columns=["Ingredient", "Cost"])
st.subheader("Ingredient Costs ($/gram)")
st.dataframe(cost_df.astype(str))


# -----------------------------
# USER CONTROLS
# -----------------------------
st.sidebar.header("Optimization Settings")

bar_weight = st.sidebar.slider("Bar Weight (grams)", 50, 200, 100)

protein = st.sidebar.slider("Minimum Protein (g)", 0, 50, 22)
fat = st.sidebar.slider("Maximum Fat (g)", 0, 50, 22)
fibre = st.sidebar.slider("Minimum Fibre (g)", 0, 20, 6)
salt = st.sidebar.slider("Maximum Salt (g)", 0, 10, 3)
sugar = st.sidebar.slider("Maximum Sugar (g)", 0, 50, 20)

constraints = {
    "Protein": (">=", protein),
    "Fat": ("<=", fat),
    "Fibre": (">=", fibre),
    "Salt": ("<=", salt),
    "Sugar": ("<=", sugar),
}


# -----------------------------
# RUN OPTIMIZATION
# -----------------------------
if st.button("Run Optimization"):

    model, x = optimize_recipe(nutrition, dict_costs, bar_weight, constraints)

    st.subheader("Optimization Status")

    status = LpStatus[model.status]
    st.write(status)

    if model.status != 1:
        st.error("No feasible solution. Try relaxing constraints.")
    else:

        cost = value(model.objective)

        st.success(f"Optimal Cost per Bar: ${cost:.2f}")

        # Recipe table
        results = []

        for ingredient in nutrition.index:
            qty = x[ingredient].varValue
            if qty and qty > 0.01:
                results.append({
                    "Ingredient": ingredient,
                    "Quantity (g)": round(qty, 2),
                    "Cost ($)": round(qty * dict_costs[ingredient], 4)
                })

        results_df = pd.DataFrame(results)

        st.subheader("Optimal Recipe")
        st.dataframe(results_df.astype(str))

        # -----------------------------
        # Nutrition Profile
        # -----------------------------
        st.subheader("Nutritional Profile")

        nutrition_totals = {}

        for nutrient in nutrition.columns:

            total = sum(
                (x[i].varValue or 0) * nutrition.loc[i, nutrient]
                for i in nutrition.index
            )

            nutrition_totals[nutrient] = round(total, 2)

        nutrition_df = pd.DataFrame(
            nutrition_totals.items(),
            columns=["Nutrient", "Total (g)"]
        )

        st.dataframe(nutrition_df.astype(str))


# -----------------------------
# SENSITIVITY ANALYSIS
# -----------------------------
st.subheader("Protein Sensitivity Analysis")

if st.button("Run Sensitivity Analysis"):

    protein_levels = [15, 18, 20, 22, 25, 28, 30]

    results = []

    for p in protein_levels:

        constraints = {
            "Protein": (">=", p),
            "Fat": ("<=", 25),
            "Fibre": (">=", 5),
            "Salt": ("<=", 3),
            "Sugar": ("<=", 20),
        }

        model, x = optimize_recipe(nutrition, dict_costs, 100, constraints)

        status = LpStatus[model.status]

        cost = value(model.objective) if model.status == 1 else None

        results.append({
            "Protein Requirement": p,
            "Cost": cost,
            "Status": status
        })

    sensitivity_df = pd.DataFrame(results)

    st.dataframe(sensitivity_df.astype(str))
