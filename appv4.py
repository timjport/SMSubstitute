import streamlit as st
import pandas as pd

st.set_page_config(page_title="Cast Substitution Tool v4.5", layout="centered")

st.title("🎭 Cast Substitution Tool (v4.5) — Conflict Warnings")

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

    with st.expander("🔍 View Actor Skills (0 = can't cover, 1 = partial, 2 = full)"):
        st.dataframe(skills_df)

    # --- Optional Role Notes ---
    st.header("📝 Step 1.5: (Optional) Add Notes for Roles")
    role_notes = {}
    for role in cast_df[cast_df.columns[0]]:
        role_notes[role] = st.text_input(f"Note for {role}", "")

    # --- Allow Partial Setting ---
    allow_partial = st.checkbox("Allow actors who are partially prepared to cover roles", value=True)

    # --- Max Partials Limit ---
    max_partials = st.number_input("Maximum Allowed Partial Covers Tonight", min_value=0, max_value=20, value=2, step=1)

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
        partial_count = 0

        for role in roles_to_cover:
            substitute = None
            for skill_level in ([2, 1] if allow_partial else [2]):
                if substitute:
                    break
                for actor in all_actors:
                    if actor in sick_actors or actor in used_subs:
                        continue
                    actor_skill = skills_df.loc[skills_df['Role'] == role, actor].values[0]
                    if actor_skill >= skill_level and actor not in current_assignments.values():
                        if actor_skill == 1 and partial_count >= max_partials:
                            continue
                        substitute = actor
                        if actor_skill == 1:
                            partial_count += 1
                        swap_log.append(f"{actor} directly covers {role} ({'Partial' if actor_skill==1 else 'Full'})")
                        break

            if not substitute:
                for skill_level in ([2, 1] if allow_partial else [2]):
                    if substitute:
                        break
                    for actor in all_actors:
                        if actor in sick_actors or actor in used_subs:
                            continue
                        actor_skill = skills_df.loc[skills_df['Role'] == role, actor].values[0]
                        if actor_skill >= skill_level:
                            their_current_role = [r for r, a in current_assignments.items() if a == actor]
                            if their_current_role:
                                vacant_role = their_current_role[0]
                                for actor2 in all_actors:
                                    if actor2 in sick_actors or actor2 in used_subs or actor2 == actor:
                                        continue
                                    actor2_skill = skills_df.loc[skills_df['Role'] == vacant_role, actor2].values[0]
                                    if actor2_skill >= (1 if allow_partial else 2):
                                        if actor2_skill == 1 and partial_count >= max_partials:
                                            continue
                                        substitute = actor
                                        if actor2_skill == 1:
                                            partial_count +=1
                                        suggestions[vacant_role] = actor2 + (" [Partial]" if actor2_skill==1 else "")
                                        used_subs.add(actor2)
                                        swap_log.append(f"{actor2} covers {vacant_role} ({'Partial' if actor2_skill==1 else 'Full'})")
                                        swap_log.append(f"{actor} moves from {vacant_role} to {role} ({'Partial' if actor_skill==1 else 'Full'})")
                                        break
                                if substitute:
                                    break

            if substitute:
                used_subs.add(substitute)
                skill_display = skills_df.loc[skills_df['Role'] == role, substitute].values[0]
                if skill_display == 1:
                    partial_count += 1
                suggestions[role] = substitute + (" [Partial]" if skill_display==1 else "")
            else:
                suggestions[role] = "❌ No available substitute"
                swap_log.append(f"⚠️ No available substitute for {role}")

        # --- Swap Log ---
        st.header("📝 Swap Log")
        for log in swap_log:
            st.write(log)

        if partial_count > max_partials:
            st.warning(f"Partial limit exceeded! {partial_count} partials used but limit is {max_partials}")

        # --- Actor Conflict Check ---
        st.header("🚨 Conflict Checker")
        assigned_actors = [s.split(" ")[0] for s in suggestions.values() if not s.startswith("❌")]
        conflict_df = pd.Series(assigned_actors).value_counts()
        conflicts = conflict_df[conflict_df > 1]

        if not conflicts.empty:
            st.error("❗ Conflict Detected! The following actor(s) are assigned to multiple roles:")
            for actor, count in conflicts.items():
                st.write(f"- {actor}: assigned {count} times")
        else:
            st.success("✅ No actor conflicts detected.")

        # --- Substitution Report ---
        st.header("📄 Substitution Report (Printable)")

        def highlight_sub(val):
            if "[Partial]" in val:
                return "background-color: orange"
            elif "No available" in val:
                return "background-color: red; color: white"
            else:
                return "background-color: lightgreen"

        report_df = pd.DataFrame([
            {"Role": role, "Assigned Substitute": suggestions[role], "Note": role_notes[role]} for role in roles_to_cover
        ])

        st.dataframe(report_df.style.applymap(highlight_sub, subset=["Assigned Substitute"]))

        st.info("Tip: Right-click the table and 'Print to PDF' for a clean, printable report.")
