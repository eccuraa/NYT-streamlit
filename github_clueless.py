import streamlit as st
import pandas as pd
import numpy as np
import math
import plotly.graph_objects as go
import random

# Page configuration
st.set_page_config(
    page_title="HR1 Tax Impact Dashboard",
    page_icon="🏠",
    layout="wide"
)

# Load data
@st.cache_data
def load_data():
    return pd.read_csv("retrial.csv")

# Main app
def main():
    st.title("🏠 HR1 Tax Bill - Household Impact Dashboard")
    st.markdown("*Explore how the HR1 tax bill affects individual American households compared to current policy*")
    
    # Load the data
    df = load_data()
    
    # Sidebar for household selection
    st.sidebar.header("Select Household")
    
    # Initialize filtered dataframe
    df_filtered = df.copy()
    
    ### ALL FILTERS
    with st.sidebar.expander("🔍 Filters"):
        # Filter 1: Household Weight
        weight_options = {
            "All Households": 0,
            "Weight 1,000+": 1000,
            "Weight 5,000+": 5000,
            "Weight 10,000+": 10000,
            "Weight 25,000+": 25000,
            "Weight 50,000+": 50000
        }
        selected_weight = st.selectbox("Minimum Household Weight:", list(weight_options.keys()))  # Removed .sidebar
        min_weight = weight_options[selected_weight]
        if min_weight > 0:
            df_filtered = df_filtered[df_filtered['Household Weight'] >= min_weight]
        
        # Filter 2: Net Income
        income_ranges = {
            "All Income Levels": (0, float('inf')),
            "Under $25k": (0, 25000),
            "$25k - $50k": (25000, 50000),
            "$50k - $100k": (50000, 100000),
            "$100k - $200k": (100000, 200000),
            "$200k+": (200000, float('inf'))
        }
        selected_income = st.selectbox("Net Income:", list(income_ranges.keys()))  # Removed .sidebar
        min_income, max_income = income_ranges[selected_income]
        if min_income > 0 or max_income < float('inf'):
            df_filtered = df_filtered[
                (df_filtered['Baseline Net Income'] >= min_income) & 
                (df_filtered['Baseline Net Income'] <= max_income)
            ]
        
        # Filter 3: State
        states = ["All States"] + sorted(df['State'].unique().tolist())
        selected_state = st.selectbox("State:", states)  # Removed .sidebar
        if selected_state != "All States":
            df_filtered = df_filtered[df_filtered['State'] == selected_state]
        
        # Filter 4: Marital Status
        marital_options = ["All", "Married", "Single"]
        selected_marital = st.selectbox("Marital Status:", marital_options)  # Removed .sidebar
        if selected_marital != "All":
            is_married = selected_marital == "Married"
            df_filtered = df_filtered[df_filtered['Is Married'] == is_married]
        
        # Filter 5: Number of Dependents
        dependent_options = ["All", "0", "1", "2", "3+"]
        selected_dependents = st.selectbox("Number of Dependents:", dependent_options)  # Removed .sidebar
        if selected_dependents != "All":
            if selected_dependents == "3+":
                df_filtered = df_filtered[df_filtered['Number of Dependents'] >= 3]
            else:
                df_filtered = df_filtered[df_filtered['Number of Dependents'] == int(selected_dependents)]

        # Filter 6: Age of Head of Household
        age_ranges = {
            "All Ages": (0, 200),
            "Under 30": (0, 30),
            "30-40": (30, 40),
            "40-50": (40, 50),
            "50-60": (50, 60),
            "60-70": (60, 70),
            "70-80": (70, 80),
            "80+": (80, 200)
        }
        selected_age = st.selectbox("Head of Household Age:", list(age_ranges.keys()))
        min_age, max_age = age_ranges[selected_age]
        if selected_age != "All Ages":
            df_filtered = df_filtered[
                (df_filtered['Age of Head'] >= min_age) & 
                (df_filtered['Age of Head'] < max_age)
            ]
        
        # Show filter results  
        st.caption(f"📊 Showing {len(df_filtered):,} of {len(df):,} households")  # Removed .sidebar
        if len(df_filtered) == 0:
            st.error("No households match your filters!")  # Removed .sidebar
            st.stop()

    # Use df_filtered everywhere below this point

    
    selection_method = st.sidebar.radio(
        "Selection Method:",
        ["By Household ID", "Find Interesting Cases", "Random Shuffle"]
    )
    
    if selection_method == "By Household ID":
        household_id = st.sidebar.selectbox(
            "Choose Household ID:",
            df_filtered['Household ID'].unique()
        )
    
    elif selection_method == "Random Shuffle":
        if st.sidebar.button("🎲 Get Random Household"):
            # Store random selection in session state to persist across reruns
            st.session_state.random_household = df_filtered['Household ID'].sample(1).iloc[0]
        
        # Show the selected random household or pick initial one
        if 'random_household' not in st.session_state:
            st.session_state.random_household = df_filtered['Household ID'].sample(1).iloc[0]
        
        household_id = st.session_state.random_household
        st.sidebar.info(f"Random Household ID: {household_id}")
    else:
        # Pre-filter for interesting cases with top 20 rankings
        case_type = st.sidebar.selectbox("Select Case Type:", [
            "Largest % Federal Tax Increase",
            "Largest % Federal Tax Decrease", 
            "Largest Federal Tax Increase",
            "Largest Federal Tax Decrease",
            "Largest % Income Increase",
            "Largest % Income Decrease",
            "Largest Income Increase",
            "Largest Income Decrease"
        ])
        
        # Get top 20 households for selected category
        categories = {
            "Largest % Federal Tax Increase": ('nlargest', 'Percentage Change in Federal Tax Liability'),
            "Largest % Federal Tax Decrease": ('nsmallest', 'Percentage Change in Federal Tax Liability'),
            "Largest Federal Tax Increase": ('nlargest', 'Total Change in Federal Tax Liability'),
            "Largest Federal Tax Decrease": ('nsmallest', 'Total Change in Federal Tax Liability'),
            "Largest % Income Increase": ('nlargest', 'Percentage Change in Net Income'),
            "Largest % Income Decrease": ('nsmallest', 'Percentage Change in Net Income'),
            "Largest Income Increase": ('nlargest', 'Total Change in Net Income'),
            "Largest Income Decrease": ('nsmallest', 'Total Change in Net Income')
        }
        
        method, column = categories[case_type]
        top_households = getattr(df_filtered, method)(20, column)
                
        # Create ranked list for selection
        ranked_options = []
        household_ids = []  # Keep track of household IDs separately, sorry that this is not concise
        
        for i, (idx, row) in enumerate(top_households.iterrows(), 1):
            household_ids.append(row['Household ID'])  # Store the household ID
            
            if "%" in case_type:
                if "Tax" in case_type:
                    value = row['Percentage Change in Federal Tax Liability']
                    ranked_options.append(f"#{i}: {value:+.1f}%")
                else:  # Income
                    value = row['Percentage Change in Net Income']
                    ranked_options.append(f"#{i}: {value:+.1f}%")
            else:  # Dollar amounts
                if "Tax" in case_type:
                    value = row['Total Change in Federal Tax Liability']
                    ranked_options.append(f"#{i}: ${value:+,.0f}")
                else:  # Income
                    value = row['Total Change in Net Income']
                    ranked_options.append(f"#{i}: ${value:+,.0f}")
        
        # Let user select from ranked list
        selected_option = st.sidebar.selectbox(f"Top 20 for {case_type}:", ranked_options)
        
        # Get household ID using the index
        selected_index = ranked_options.index(selected_option)
        household_id = household_ids[selected_index]
        # Show it in a card
        st.sidebar.info(f"Selected Household ID: {household_id}")

    
    
    # Get household data
    household = df_filtered[df_filtered['Household ID'] == household_id].iloc[0]

    # Baseline Attributes in Sidebar
    st.sidebar.subheader("Baseline Household Attributes")
        
    st.sidebar.markdown(f"""
    **State:** {household['State']}  
    **Head of Household Age:** {household['Age of Head']:.0f} years  
    **Number of Dependents:** {household['Number of Dependents']:.0f}""")
    # Add children's ages if there are dependents
    if household['Number of Dependents'] > 0:
        dependent_ages = []
        for i in range(1, 12):  # Check dependents 1-11
            age_col = f'Age of Dependent {i}'
            if pd.notna(household[age_col]) and household[age_col] > 0:
                dependent_ages.append(f"{household[age_col]:.0f}")
        
        if dependent_ages:
            st.sidebar.markdown(f"**Children's Ages:** {', '.join(dependent_ages)} years")
    

    if household['Is Married']:
        st.sidebar.markdown(f"""**Marital Status:** Married  
    **Spouse Age:** {household['Age of Spouse']:.0f} years""")
    else:
        st.sidebar.markdown("**Marital Status:** Single")

    st.sidebar.markdown("**Income Sources:**")
    income_sources = [
        ("Employment Income", household['Employment Income']),
        ("Self-Employment Income", household['Self-Employment Income']),
        ("Tip Income", household['Tip Income']),
        ("Overtime Income", household['Overtime Income']),
        ("Capital Gains", household['Capital Gains'])
    ]

    for source, amount in income_sources:
        if amount > 0:
            st.sidebar.markdown(f"• {source}: ${amount:,.2f}")


    # Collapsible DF row
    with st.sidebar.expander("Full Dataframe Row"):
        # Get the row index (position in the CSV)
        row_index = df_filtered[df_filtered['Household ID'] == household_id].index[0]
        st.dataframe(household.to_frame().T, use_container_width=True)


    # Implementing the Federal vs. State Tax Checkboxes
    st.sidebar.markdown("---")
    st.sidebar.subheader("Show Effects for")
    show_federal = st.sidebar.checkbox("Federal Taxes", value=True)
    show_state = st.sidebar.checkbox("State Taxes", value=False)

    if not show_federal and not show_state:
        st.sidebar.error("Please select at least one tax type")
        st.stop()
    
    # Display household information in cards
    col1, col2 = st.columns(2)
    
    with col1:
        # Baseline Calculated Values Card
        st.subheader("Baseline Federal Tax and Net Income")
        with st.container():
            st.metric(
                "Federal Tax Liability", 
                f"${household['Baseline Federal Tax Liability']:,.2f}"
            )
            st.metric(
                "Net Income", 
                f"${household['Baseline Net Income']:,.2f}"
            )
            
            # Show other current expenses
            if household['State Income Tax'] > 0:
                st.markdown(f"**State Income Tax:** ${household['State Income Tax']:,.2f}")    
            if household['Property Taxes'] > 0:
                st.markdown(f"**Property Taxes:** ${household['Property Taxes']:,.2f}")
      
    
    with col2:
        st.subheader("🔄 HR1 Bill Impact Summary")
        with st.container():
            # Define income variables first (these don't change based on tax selection)
            income_change = household['Total Change in Net Income']
            income_pct_change = household['Percentage Change in Net Income']
            
            # Calculate tax changes based on selection
            federal_tax_change = household['Total Change in Federal Tax Liability'] if show_federal else 0
            state_tax_change = household['Total Change in State Tax Liability'] if show_state else 0
            total_tax_change = federal_tax_change + state_tax_change
            
            # Calculate percentage changes
            federal_tax_pct_change = household['Percentage Change in Federal Tax Liability'] if show_federal else 0
            state_tax_pct_change = household['Percentage Change in State Tax Liability'] if show_state else 0
            
            # For combined percentage, show separately when both selected
            if show_federal and show_state:
                tax_display = f"Federal: ${federal_tax_change:,.2f} ({federal_tax_pct_change:+.1f}%), State: ${state_tax_change:,.2f} ({state_tax_pct_change:+.1f}%)"
            elif show_federal:
                tax_display = f"${federal_tax_change:,.2f} ({federal_tax_pct_change:+.1f}%)"
            else:  # show_state
                tax_display = f"${state_tax_change:,.2f} ({state_tax_pct_change:+.1f}%)"
            
            # Color coding for positive/negative changes
            tax_color = "red" if total_tax_change > 0 else "green"
            income_color = "green" if income_change > 0 else "red"
            
            st.markdown(f"""
            <div style="padding: 10px; border-radius: 5px; background-color: #f0f2f6;">
            <h4>Overall Impact</h4>
            <p style="color: {tax_color}; font-size: 18px; font-weight: bold;">
            Tax Change: {tax_display}
            </p>
            <p style="color: {income_color}; font-size: 18px; font-weight: bold;">
            Net Income Change: ${income_change:,.2f} ({income_pct_change:+.1f}%)
            </p>
            </div>
            """, unsafe_allow_html=True)

        
        # Statistical Weight Card
        st.subheader("📈 Statistical Weight")
        with st.container():
            weight = household['Household Weight']
            st.metric("Population Weight", f"{math.ceil(weight):,}")
            st.caption("This household represents approximately this many similar households in the U.S.")
    
    # Create reform components data based on selection
    reform_components = []
    reform_configs = [
        ("Tax Rate Reform", "Tax Rate Reform", "Net income change after Tax Rate Reform"),
        ("Standard Deduction Reform", "Standard Deduction Reform", "Net income change after Standard Deduction Reform"),
        ("Exemption Reform", "Exemption Reform", "Net income change after Exemption Reform"),
        ("Child Tax Credit Reform", "CTC Reform", "Net income change after CTC Reform"),
        ("QBID Reform", "QBID Reform", "Net income change after QBID Reform"),
        ("AMT Reform", "AMT Reform", "Net income change after AMT Reform"),
        ("SALT Reform", "SALT Reform", "Net income change after SALT Reform"),
        ("Tip Income Exemption", "Tip Income Exempt", "Net income change after Tip Income Exempt"),
        ("Overtime Income Exemption", "Overtime Income Exempt", "Net income change after Overtime Income Exempt"),
        ("Auto Loan Interest Deduction", "Auto Loan Interest ALD", "Net income change after Auto Loan Interest ALD"),
        ("Miscellaneous Reform", "Miscellaneous Reform", "Net income change after Miscellaneous Reform"),
        ("Other Itemized Deductions Reform", "Other Itemized Deductions Reform", "Net income change after Other Itemized Deductions Reform"),
        ("Pease Reform", "Pease Reform", "Net income change after Pease Reform")
    ]
    
    for display_name, col_name, income_col in reform_configs:
        federal_tax = household[f'Federal tax liability after {col_name}'] if show_federal else 0
        state_tax = household[f'State tax liability after {col_name}'] if show_state else 0
        combined_tax = federal_tax + state_tax
        income_change = household[income_col]
        reform_components.append((display_name, combined_tax, income_change)) 
    
    # Filter out components with no change
    active_components = [(name, tax_after, income_change) for name, tax_after, income_change in reform_components if abs(income_change) > 0.01]

    # Detailed Reform Breakdown
    st.subheader("🔍 Detailed Reform Component Analysis")
    
    if active_components:
        cols = st.columns(min(3, len(active_components)))
        for i, (name, tax_after, income_change) in enumerate(active_components):
            with cols[i % 3]:
                color = "green" if income_change > 0 else "red"
                st.markdown(f"""
                <div style="padding: 8px; border-radius: 5px; background-color: #f9f9f9; margin: 5px 0;">
                <h5>{name}</h5>
                <p style="color: {color}; font-weight: bold;">
                Net Income Change: ${income_change:,.2f} 
                </p>
                </div>
                """, unsafe_allow_html=True)
    

        
        # Waterfall Chart
        chart_title = []
        if show_federal: chart_title.append("Federal")
        if show_state: chart_title.append("State")
        chart_type = " & ".join(chart_title) + " Tax"
        
        st.subheader(f"📊 {chart_type} Impact Waterfall Chart")
        
        # Calculate baseline
        baseline_federal = household['Baseline Federal Tax Liability'] if show_federal else 0
        baseline_state = household.get('Baseline State Tax Liability', 0) if show_state else 0  # Add if column exists
        baseline_total = baseline_federal + baseline_state
        
        # Prepare waterfall data
        waterfall_data = [(f"Baseline {chart_type}", baseline_total, baseline_total)]
        running_total = baseline_total
        
        for name, combined_tax, income_change in active_components:
            tax_change = -income_change
            running_total += tax_change
            waterfall_data.append((name, tax_change, running_total))
        
        # Final total
        final_total = baseline_total + total_tax_change
        waterfall_data.append((f"Final {chart_type}", final_total, final_total))  

                
        # Create FEDERAL INCOME TAX waterfall chart (state option still needed, etc.)
        fig = go.Figure() 
        
        # Add baseline
        fig.add_trace(go.Waterfall(
            name=f"{chart_type} Impact",  # Dynamic name based on selection
            orientation="v",
            measure=["absolute"] + ["relative"] * len(active_components) + ["total"],
            x=[item[0] for item in waterfall_data],
            y=[item[1] for item in waterfall_data],
            text=[f"${item[1]:,.0f}" for item in waterfall_data],
            textposition="outside",
            connector={"line":{"color":"rgb(63, 63, 63)"}},
            increasing={"marker":{"color":"red"}},  # Tax increases in red
            decreasing={"marker":{"color":"green"}},  # Tax decreases in green
            totals={"marker":{"color":"blue"}}
        ))
        
        # Update chart title
        fig.update_layout(
            title=f"{chart_type} Liability Changes: ${baseline_total:,.0f} → ${final_total:,.0f}",
            xaxis_title="Reform Components",
            yaxis_title="Tax Liability ($)",
            showlegend=False,
            height=500,
            xaxis={'tickangle': -45}
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Verification
        total_calculated_change = sum([item[1] for item in waterfall_data[1:-1]])
        # Changed this from taxes, to overall change from all reforms!! Must change title accordingly
        # And negated the change in income so it would match the change in taxes
        actual_change = -household['Total Change in Net Income']

        # Check if calculated change is within $3 of other Tax Change calculation
        if abs(total_calculated_change - actual_change) < 3:
            pass
        else:
            st.error(f"Discrepancy detected: Calculated change ${total_calculated_change:,.2f} vs Actual change ${actual_change:,.2f}")

    else:
        st.info("This household is not significantly affected by any specific reform components.")
    
    # Summary for journalists
    st.subheader("📝 Story Summary")
    impact_level = "significantly" if abs(income_change) > 1000 else "moderately" if abs(income_change) > 100 else "minimally"
    direction = "benefits from" if income_change > 0 else "is burdened by"

    
    # Find the reform with the greatest absolute impact
    if active_components:
        biggest_impact_reform = max(active_components, key=lambda x: abs(x[2]))
        biggest_reform_name = biggest_impact_reform[0]
        biggest_reform_change = biggest_impact_reform[2]
        biggest_reform_text = f"The biggest change comes from the {biggest_reform_name} (${biggest_reform_change:+,.2f})."
    else:
        biggest_reform_text = "No single reform has a major impact."

    
    st.info(f"""
    **Quick Story Angle:** This {household['State']} household {impact_level} {direction} the HR1 bill, 
    with a net income change of {household['Total Change in Net Income']:,.2f} ({income_pct_change:+.1f}%). 
    {biggest_reform_text}
    The household represents approximately {f"{math.ceil(weight):,}"} similar American families.
    """)
    
if __name__ == "__main__":
    main()
