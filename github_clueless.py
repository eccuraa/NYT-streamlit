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
    return pd.read_csv("16.50pr.csv")

# Main app
def main():
    st.title("🏠 HR1 Tax Bill - Household Impact Dashboard")
    st.markdown("*Explore how the HR1 tax bill affects individual American households compared to current policy*")
    
    # Load the data
    df = load_data()
    
    # Sidebar for household selection
    st.sidebar.header("Select Household")
    
    # Option to select by household ID or find interesting cases
    selection_method = st.sidebar.radio(
        "Selection Method:",
        ["Random Shuffle", "By Household ID", "Find Interesting Cases"]
    )
    
    if selection_method == "By Household ID":
        household_id = st.sidebar.selectbox(
            "Choose Household ID:",
            df['Household ID'].unique()
        )
    
    elif selection_method == "Random Shuffle":
        if st.sidebar.button("🎲 Get Random Household"):
            # Store random selection in session state to persist across reruns
            st.session_state.random_household = df['Household ID'].sample(1).iloc[0]
        
        # Show the selected random household or pick initial one
        if 'random_household' not in st.session_state:
            st.session_state.random_household = df['Household ID'].sample(1).iloc[0]
        
        household_id = st.session_state.random_household
        st.sidebar.info(f"Random Household ID: {household_id}")
    else:
        # Pre-filter for interesting cases
        interesting_options = {
            "Biggest Tax Increase": df.loc[df['Total Change in Federal Tax Liability'].idxmax(), 'Household ID'],
            "Biggest Tax Decrease": df.loc[df['Total Change in Federal Tax Liability'].idxmin(), 'Household ID'],
            "Highest Income Impact": df.loc[df['Total Change in Net Income'].abs().idxmax(), 'Household ID'],
            "Largest Percentage Change": df.loc[df['Percentage Change in Federal Tax Liability'].abs().idxmax(), 'Household ID']
        }
        
        case_type = st.sidebar.selectbox("Select Case Type:", list(interesting_options.keys()))
        household_id = interesting_options[case_type]
        st.sidebar.info(f"Selected Household ID: {household_id}")
    
    # Get household data
    household = df[df['Household ID'] == household_id].iloc[0]

    # Baseline Attributes in Sidebar
    st.sidebar.subheader("Baseline Household Attributes")
    # Add this after your existing Baseline Household Attributes section
    with st.sidebar.expander("Dataframe Row Index", expanded = True):
        # Get the row index (position in the CSV)
        row_index = df[df['Household ID'] == household_id].index[0]
        st.write(f"**Dataframe Row Number:** {row_index + 1}")  # +1 because CSV rows start at 1 (including header)
        st.dataframe(household.to_frame().T, use_container_width=True)
        
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
            if household['Property Taxes'] > 0:
                st.markdown(f"**Property Taxes:** ${household['Property Taxes']:,.2f}")
            if household['State Income Tax'] > 0:
                st.markdown(f"**State Income Tax:** ${household['State Income Tax']:,.2f}")        
    
    with col2:
        # Reform Impact Card
        st.subheader("🔄 HR1 Bill Impact Summary")
        with st.container():
            tax_change = household['Total Change in Federal Tax Liability']
            income_change = household['Total Change in Net Income']
            tax_pct_change = household['Percentage Change in Federal Tax Liability']
            income_pct_change = household['Percentage Change in Net Income']
            
            # Color coding for positive/negative changes
            tax_color = "red" if tax_change > 0 else "green"
            income_color = "green" if income_change > 0 else "red"
            
            st.markdown(f"""
            <div style="padding: 10px; border-radius: 5px; background-color: #f0f2f6;">
            <h4>Overall Impact</h4>
            <p style="color: {tax_color}; font-size: 18px; font-weight: bold;">
            Tax Change: ${tax_change:,.2f} ({tax_pct_change:+.1f}%)
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
    
    # Create reform components data
    reform_components = [
        ("Tax Rate Reform", household['Federal tax liability after Tax Rate Reform'], household['Net income change after Tax Rate Reform']),
        ("Standard Deduction Reform", household['Federal tax liability after Standard Deduction Reform'], household['Net income change after Standard Deduction Reform']),
        ("Exemption Reform", household['Federal tax liability after Exemption Reform'], household['Net income change after Exemption Reform']),
        ("Child Tax Credit Reform", household['Federal tax liability after CTC Reform'], household['Net income change after CTC Reform']),
        ("QBID Reform", household['Federal tax liability after QBID Reform'], household['Net income change after QBID Reform']),
        ("Estate Tax Reform", household['Federal tax liability after Estate Tax Reform'], household['Net income change after Estate Tax Reform']),
        ("AMT Reform", household['Federal tax liability after AMT Reform'], household['Net income change after AMT Reform']),
        ("SALT Reform", household['Federal tax liability after SALT Reform'], household['Net income change after SALT Reform']),
        ("Tip Income Exemption", household['Federal tax liability after Tip Income Exempt'], household['Net income change after Tip Income Exempt']),
        ("Overtime Income Exemption", household['Federal tax liability after Overtime Income Exempt'], household['Net income change after Overtime Income Exempt']),
        ("Auto Loan Interest Deduction", household['Federal tax liability after Auto Loan Interest ALD'], household['Net income change after Auto Loan Interest ALD']),
        ("Miscellaneous Reform", household['Federal tax liability after Miscellaneous Reform'], household['Net income change after Miscellaneous Reform']),
        ("Other Itemized Deductions Reform", household['Federal tax liability after Other Itemized Deductions Reform'], household['Net income change after Other Itemized Deductions Reform']),
        ("Pease Reform", household['Federal tax liability after Pease Reform'], household['Net income change after Pease Reform'])
    ]
    
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
        st.subheader("📊 Financial Impact Waterfall Chart")
        
        # Prepare data for waterfall chart
        baseline_tax = household['Baseline Federal Tax Liability']
        
        # Get tax liability changes (not net income changes)
        waterfall_data = []
        waterfall_data.append(("Baseline Federal Income Tax", baseline_tax, baseline_tax))
        
        running_total = baseline_tax
        
        for name, tax_after, income_change in active_components:
            # Calculate the tax change (negative income change = positive tax change)
            tax_change = -income_change
            running_total += tax_change
            waterfall_data.append((name, tax_change, running_total))
        
        # Final total
        final_tax = baseline_tax + household['Total Change in Federal Tax Liability']
        waterfall_data.append(("Final Federal Income Tax", final_tax, final_tax))
        
        # Create FEDERAL INCOME TAX waterfall chart (state option still needed, etc.)
        fig = go.Figure() 
        
        # Add baseline
        fig.add_trace(go.Waterfall(
            name="Federal Income Tax Impact",
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
        
        fig.update_layout(
            title=f"Federal Income Tax Liability Changes: ${baseline_tax:,.0f} → ${final_tax:,.0f}",
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
        biggest_reform_text = f"The biggest driver is {biggest_reform_name} (${biggest_reform_change:+,.2f})."
    else:
        biggest_reform_text = "No single reform has a major impact."

    
    st.info(f"""
    **Quick Story Angle:** This {household['State']} household (ID: {household_id}) {impact_level} {direction} the HR1 bill, 
    with a net income change of ${household['Total Change in Net Income']:,.2f} ({income_pct_change:+.1f}%). The biggest driver is {biggest_reform_name} (${biggest_reform_change:+,.2f}).
    The household represents approximately {f"{math.ceil(weight):,}"} similar American families.
    """)
    
if __name__ == "__main__":
    main()
