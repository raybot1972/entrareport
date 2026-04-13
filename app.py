import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib_venn import venn2

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="Entra – Weekly Risk Dashboard",
    layout="wide"
)

st.title("🔐 Entra Interactive Sign‑Ins – Dashboard")
st.caption("Weekly identity risk view based on Entra InteractiveSignIns export")

# --------------------------------------------------
# File upload
# --------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload InteractiveSignIns CSV",
    type=["csv"]
)

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # --------------------------------------------------
    # Auto-detect user column
    # --------------------------------------------------
    possible_user_cols = [
        "User principal name",
        "UserPrincipalName",
        "userPrincipalName",
        "User"
    ]

    user_col = next((c for c in possible_user_cols if c in df.columns), None)

    if not user_col:
        st.error(
            "Could not find a user identifier column. "
            f"Expected one of: {', '.join(possible_user_cols)}"
        )
        st.stop()

    # --------------------------------------------------
    # Authentication requirement column
    # --------------------------------------------------
    auth_col = "Authentication requirement"
    if auth_col not in df.columns:
        st.error(f"Missing required column: {auth_col}")
        st.stop()

    # --------------------------------------------------
    # Normalise authentication values (IMPORTANT FIX)
    # --------------------------------------------------
    df[auth_col] = (
        df[auth_col]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    def is_mfa(val):
        return "multi" in val or val == "mfa"

    def is_sfa(val):
        return "single" in val or val == "sfa"

    # --------------------------------------------------
    # EVENT-BASED FILTERING (corrected)
    # --------------------------------------------------
    mfa_attempts_df = df[df[auth_col].apply(is_mfa)]
    sfa_attempts_df = df[df[auth_col].apply(is_sfa)]

    # --------------------------------------------------
    # USER-BASED SETS (logic unchanged)
    # --------------------------------------------------
    mfa_users = set(mfa_attempts_df[user_col])
    sfa_users = set(sfa_attempts_df[user_col])
    overlap_users = mfa_users & sfa_users

    # --------------------------------------------------
    # Attempt counts
    # --------------------------------------------------
    mfa_attempt_count = len(mfa_attempts_df)
    sfa_attempt_count = len(sfa_attempts_df)

    # --------------------------------------------------
    # User-based metrics
    # --------------------------------------------------
    st.subheader("User‑Based Metrics")

    u1, u2, u3 = st.columns(3)
    u1.metric("MFA Users", len(mfa_users))
    u2.metric("SFA Users", len(sfa_users))
    u3.metric("MFA ∩ SFA Users", len(overlap_users))

    # --------------------------------------------------
    # Event-based metrics
    # --------------------------------------------------
    st.subheader("Sign‑In Attempt Counts (Event‑Based)")

    a1, a2 = st.columns(2)
    a1.metric("MFA Attempts", mfa_attempt_count)
    a2.metric("SFA Attempts", sfa_attempt_count)

    # --------------------------------------------------
    # Venn Diagram
    # --------------------------------------------------
    st.subheader("MFA vs SFA User Overlap")

    # Create a centered column to constrain the diagram width
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4), dpi=80)
        venn2(
            subsets=(
                len(mfa_users - sfa_users),
                len(sfa_users - mfa_users),
                len(overlap_users)
            ),
            set_labels=("MFA", "SFA"),
            ax=ax
        )
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True, clear_figure=True)

    # --------------------------------------------------
    # Top 10 MFA attempts
    # --------------------------------------------------
    st.subheader("Top 10 MFA Sign‑In Attempt Sources")

    top_mfa = (
        mfa_attempts_df
        .groupby(user_col)
        .size()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="MFA Attempts")
    )

    st.dataframe(top_mfa, use_container_width=True)

    # --------------------------------------------------
    # Top 10 SFA attempts
    # --------------------------------------------------
    st.subheader("Top 10 SFA Sign‑In Attempt Sources")

    top_sfa = (
        sfa_attempts_df
        .groupby(user_col)
        .size()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="SFA Attempts")
    )

    st.dataframe(top_sfa, use_container_width=True)

    # --------------------------------------------------
    # Overlap users table
    # --------------------------------------------------
    st.subheader("⚠ Users Authenticating with BOTH MFA and SFA")

    if overlap_users:
        overlap_df = pd.DataFrame(
            sorted(overlap_users),
            columns=[user_col]
        )
        st.dataframe(overlap_df, use_container_width=True)
    else:
        st.success("No overlapping MFA/SFA users detected for this period.")

    # --------------------------------------------------
    # Country-based login analysis
    # --------------------------------------------------
    st.subheader("🌍 Login Activity by Country")

    # Check for location column
    possible_location_cols = ["Location", "location", "Country", "Sign-in location"]
    location_col = next((c for c in possible_location_cols if c in df.columns), None)

    if location_col:
        # Clean and process location data
        df_clean = df.dropna(subset=[location_col])
        df_clean = df_clean[df_clean[location_col].astype(str).str.strip() != '']
        
        if len(df_clean) > 0:
            # Extract country information (assuming format like "City, Country" or just "Country")
            df_clean['Country'] = df_clean[location_col].astype(str).apply(
                lambda x: x.split(',')[-1].strip() if ',' in x else x.strip()
            )
            
            # Count logins per country
            country_counts = (
                df_clean
                .groupby('Country')
                .size()
                .sort_values(ascending=False)
                .reset_index(name='Login Count')
            )
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Countries", len(country_counts))
            col2.metric("Total Located Logins", len(df_clean))
            col3.metric("Top Country", f"{country_counts.iloc[0]['Country']}" if len(country_counts) > 0 else "N/A")
            
            # Display country table
            st.dataframe(country_counts, use_container_width=True)
            
            # Highlight potential risks
            if len(country_counts) > 1:
                st.warning(f"⚠ **Security Notice**: Logins detected from {len(country_counts)} different countries. Review for potential unauthorized access.")
            
        else:
            st.info("No location data available for analysis.")
    else:
        st.info(f"Location column not found. Expected one of: {', '.join(possible_location_cols)}")

    # --------------------------------------------------
    # Executive summary
    # --------------------------------------------------
    st.subheader("Executive Summary (Weekly Feed)")

    # Prepare country summary
    if location_col and len(df_clean) > 0:
        total_countries = len(country_counts)
        top_country = country_counts.iloc[0]['Country'] if len(country_counts) > 0 else "Unknown"
        country_summary = f"""

**Geographic perspective:**  
Sign-in activity was observed from **{total_countries} countries**, with **{top_country}** being the most frequent location.  
{"Multiple-country activity requires monitoring for potential credential compromise or unauthorized access." if total_countries > 1 else "Single-country activity detected - geographically consistent."}"""
    else:
        country_summary = ""

    st.markdown(
        f"""
**User perspective:**  
The environment recorded **{len(mfa_users)} MFA users** and **{len(sfa_users)} SFA users**.  
**{len(overlap_users)} users authenticated using both MFA and SFA**, indicating inconsistent enforcement of strong authentication controls.

**Activity perspective:**  
A total of **{mfa_attempt_count} MFA sign‑in attempts** and **{sfa_attempt_count} SFA sign‑in attempts** were observed.  
Sustained SFA usage remains a key exposure area for credential‑based and authentication‑downgrade attacks.{country_summary}
        """
    )

else:
    st.info("Upload an InteractiveSignIns CSV file to begin.")