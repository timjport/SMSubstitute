import streamlit as st
import pandas as pd

st.set_page_config(page_title="Cast Substitution Tool v4.2", layout="centered")

st.title("🎭 Cast Substitution Tool (v4.2) — Printable & Notes Ready")

# --- Upload Section ---
st.header("📂 Step 1: Upload Cast & Skills Files")

cast_file = st.file_uploader("Upload Cast Assignment Spreadsheet (CSV or XLSX)", type=["csv", "xlsx"])
skills_file = st.file_uploader("Upload Actor Skills Spreadsheet (CSV or XLSX)", type=["csv", "xlsx"])

if cast_file and skills_file:
    cast_df = pd.read_excel(cast_file) if cast_file.name.endswith("xlsx") else pd.read_csv(cast_file)
    skills_df = pd.read_excel(skills_file) if skills_file.name.endswith("xlsx") else pd.read_csv(skills_file)

    st.success("✅ Files loaded!")

    with st.expander("🔍 View Cast Assignments"):
        st.dataframe(cast_df)

    with st.expander("🔍 View Actor Skills"):
        st.dataframe(skills_df)

    # --- Optional Role Notes ---
    st.header("📝 Step 1.5: (Optional) Add Notes for Roles")
    role_notes = {}
    for role in cast_df[cast_df.columns[0]]:
        role_notes[role] = st.text_input(f"Note for {role}", "")

    # --- Select Unavailable Actors ---
    st.header("😷 Step 2: Select Sick / Unavailable Actors")
    all_actors = list(skills_df.columns[1:])
    sick_actors = st.multiselect("Select actor(s) who are unavailable", all_actors)

    if sick_actors:
        st.subheader("⚠️ Roles Needing Coverage")
        roles_to_cover = []
        for actor in sick_actors:
            actor_roles = cast_df[cast_df.eq(actor).any(axis=1)]
            for _, row in actor_roles.iterrows():
                role = row.iloc[0]
                if role not in roles_to_cover:
                    roles_to_cover.append(role)

        st.info(f"Roles affected: {', '.join(roles_to_cover)}")

        # --- Substitution Solver ---
        st.header("🔄 Step 3: Suggested Substitutions (Max 1-level Chain)")

        current_assignments = cast_df.set_index(cast_df.columns[0])[cast_df.columns[1]].to_dict()
        used_subs = set()
        swap_log = []
        suggestions = {}

        for role in roles_to_cover:
            substitute = None

            # Find direct substitute
            for actor in all_actors:
                if actor in sick_actors or actor in used_subs:
                    continue
                if role in skills_df[skills_df[actor] == 1]['Role'].values:
                    if actor not in current_assignments.values():
                        substitute = actor
                        swap_log.append(f"{actor} directly covers {role}")
                        break

            # Try 1-level chain
            if not substitute:
                for actor in all_actors:
                    if actor in sick_actors or actor in used_subs:
                        continue
                    if role in skills_df[skills_df[actor] == 1]['Role'].values:
                        their_current_role = [r for r, a in current_assignments.items() if a == actor]
                        if their_current_role:
                            vacant_role = their_current_role[0]
                            for actor2 in all_actors:
                                if actor2 in sick_actors or actor2 in used_subs or actor2 == actor:
                                    continue
                                if vacant_role in skills_df[skills_df[actor2] == 1]['Role'].values:
                                    substitute = actor
                                    suggestions[vacant_role] = actor2
                                    used_subs.add(actor2)
                                    swap_log.append(f"{actor2} covers {vacant_role} (chain swap)")
                                    swap_log.append(f"{actor} moves from {vacant_role} to {role} (chain swap)")
                                    break
                            if substitute:
                                break

            if substitute:
                used_subs.add(substitute)
                suggestions[role] = substitute
            else:
                suggestions[role] = "❌ No available substitute"
                swap_log.append(f"⚠️ No available substitute for {role}")

        # --- Swap Log ---
        st.header("📝 Swap Log")
        for log in swap_log:
            st.write(log)

        # --- Substitution Report ---
        st.header("📄 Substitution Report (Printable)")

        report_df = pd.DataFrame([
            {"Role": role, "Assigned Substitute": suggestions[role], "Note": role_notes[role]} for role in roles_to_cover
        ])

        st.dataframe(
            report_df.style.set_table_styles(
                [{"selector": "th", "props": [("background-color", "#333"), ("color", "white")]},
                 {"selector": "td", "props": [("border", "1px solid black")]},
                 {"selector": "tr:nth-child(even)", "props": [("background-color", "#f2f2f2")]},
                 {"selector": "tr:nth-child(odd)", "props": [("background-color", "#ffffff")]},
                 ]
            ).set_properties(**{'text-align': 'left'})
        )

        st.info("Tip: Right-click the table and 'Print to PDF' for a clean, printable report.")
