from flask import Flask, render_template, request, redirect, url_for, flash, session
from supabase_client import supabase

app = Flask(__name__)
app.secret_key = "super-secret-key"


# =========================
# INDEX
# =========================
@app.route("/")
def index():
    return render_template("index.html")


# =========================
# PLACE ADMIN LOGIN
# =========================
@app.route("/place/login", methods=["GET", "POST"])
def place_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        admins = (
            supabase.table("place_admins")
            .select("*")
            .eq("email", email)
            .execute()
            .data
        )

        if not admins:
            flash("Invalid credentials")
            return render_template("place/login.html")

        admin = admins[0]

        if admin["password"] != password:
            flash("Invalid credentials")
            return render_template("place/login.html")

        # ✅ LOGIN SUCCESS
        session.clear()
        session["admin_id"] = admin["id"]
        session["place_id"] = admin["place_id"]
        session["constituency_id"] = admin["constituency_id"]
        session["district_id"] = admin["district_id"]

        return redirect(url_for("admin_dashboard"))

    return render_template("place/login.html")


# =========================
# ADMIN DASHBOARD
# =========================
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_id"):
        return redirect(url_for("place_login"))

    return render_template("place/dashboard.html")

@app.route("/admin/dashboards")
def admin_dashboards():
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    # 🔹 get escalated problem ids
    escalated = (
        supabase.table("escalated_issues")
        .select("problem_id")
        .execute()
        .data
    )

    escalated_ids = [e["problem_id"] for e in escalated]

    query = supabase.table("problems").select("""
        issue_token,
        description,
        address,
        priority,
        status,
        media_urls,
        created_at
    """).order("created_at", desc=True)

    # 🔹 exclude escalated issues
    if escalated_ids:
        query = query.not_.in_("id", escalated_ids)

    issues = query.execute().data

    return render_template("place/hello.html", issues=issues)
@app.route("/place/escalate-by-token", methods=["GET", "POST"])
def place_escalate_by_token():

    if request.method == "POST":
        issue_token = request.form.get("issue_token")

        if not issue_token:
            flash("Please select issue token")
            return redirect(url_for("place_escalate_by_token"))

        problem = (
            supabase.table("problems")
            .select("id, places_id, constituencies_id")
            .eq("issue_token", issue_token)
            .execute()
            .data
        )

        if not problem:
            flash("Invalid issue token")
            return redirect(url_for("place_escalate_by_token"))

        problem = problem[0]

        # 🔹 insert escalation
        supabase.table("escalated_issues").insert({
            "problem_id": problem["id"],
            "place_id": problem["places_id"],
            "constituency_id": problem["constituencies_id"],
            "escalated_to": "constituency"
        }).execute()

        flash("Issue escalated successfully")
        return redirect(url_for("place_escalate_by_token"))

    # =========================
    # 🔹 GET REQUEST (DROPDOWN)
    # =========================

    escalated = (
        supabase.table("escalated_issues")
        .select("problem_id")
        .execute()
        .data
    )

    escalated_ids = [e["problem_id"] for e in escalated]

    query = supabase.table("problems").select(
        "id, issue_token, description"
    )

    # 🔹 exclude already escalated issues
    if escalated_ids:
        query = query.not_.in_("id", escalated_ids)

    issues = query.execute().data

    return render_template(
        "place/escalate.html",
        issues=issues
    )


@app.route("/place/update-status", methods=["GET", "POST"])
def place_update_status():

    if request.method == "POST":
        issue_token = request.form.get("issue_token")
        new_status = request.form.get("status")

        if not issue_token or not new_status:
            flash("Please select issue token and status")
            return redirect(url_for("place_update_status"))

        # 🔹 Get problem
        problem = (
            supabase.table("problems")
            .select("id")
            .eq("issue_token", issue_token)
            .execute()
            .data
        )

        if not problem:
            flash("Invalid issue token")
            return redirect(url_for("place_update_status"))

        problem_id = problem[0]["id"]

        # 🔒 CHECK: Is issue escalated?
        escalated = (
            supabase.table("escalated_issues")
            .select("id")
            .eq("problem_id", problem_id)
            .execute()
            .data
        )

        if escalated:
            flash("This issue is escalated. Status cannot be changed.")
            return redirect(url_for("place_update_status"))

        # ✅ UPDATE STATUS
        supabase.table("problems").update({
            "status": new_status
        }).eq("id", problem_id).execute()

        flash("Status updated successfully")
        return redirect(url_for("place_update_status"))

    # =========================
    # 🔹 GET: Show ONLY NON-ESCALATED ISSUES
    # =========================
    escalated_ids = (
        supabase.table("escalated_issues")
        .select("problem_id")
        .execute()
        .data
    )

    escalated_problem_ids = [e["problem_id"] for e in escalated_ids]

    query = supabase.table("problems").select("issue_token")

    if escalated_problem_ids:
        query = query.not_.in_("id", escalated_problem_ids)

    issues = query.execute().data

    return render_template(
        "place/status.html",
        issues=issues
    )

# =========================
# CONSTITUENCY ADMIN LOGIN
# =========================
@app.route("/constituency/login", methods=["GET", "POST"])
def constituency_login():

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required")
            return render_template("place/login2.html")

        result = (
            supabase.table("constituency_admins")
            .select("id, email, password, constituency_id")
            .eq("email", email)
            .execute()
            .data
        )

        if not result or result[0]["password"] != password:
            flash("Invalid credentials")
            return render_template("place/login2.html")

        admin = result[0]

        # ✅ STORE constituency_id
        session.clear()
        session["constituency_id"] = admin["constituency_id"]

        return redirect(url_for("admin_dashboardss"))

    return render_template("place/login2.html")
@app.route("/admin/dashboardses")
def admin_dashboardss():
    if not session.get("constituency_id"):
        return redirect(url_for("constituency_login"))

    return render_template("place/dashboards.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/constituency/escalated-issues/<int:constituency_id>")
def constituency_escalated_issues(constituency_id):

    # 1️⃣ Get problem_ids already escalated to department
    dept_escalated = (
        supabase.table("department_escalated_issues")
        .select("problem_id")
        .execute()
        .data
    )

    dept_problem_ids = [d["problem_id"] for d in dept_escalated]

    # 2️⃣ Get place ➝ constituency escalated issues
    query = (
        supabase.table("escalated_issues")
        .select("""
            id,
            problem_id,

            problems (
                issue_token,
                description,
                address,
                priority,
                status,
                media_urls,
                created_at
            ),

            places (
                name
            )
        """)
        .eq("constituency_id", constituency_id)
        .order("id", desc=True)
    )

    # 3️⃣ REMOVE issues already escalated to department
    if dept_problem_ids:
        query = query.not_.in_("problem_id", dept_problem_ids)

    issues = query.execute().data

    return render_template(
        "place/escalated_issues.html",
        issues=issues,
        constituency_id=constituency_id
    )



@app.route("/constituency/escalate-to-department", methods=["GET", "POST"])
def constituency_escalate_to_department():

    if request.method == "POST":
        issue_token = request.form.get("issue_token")
        department_id = request.form.get("department_id")

        if not issue_token or not department_id:
            flash("Issue token and department are required")
            return redirect(url_for("constituency_escalate_to_department"))

        # 🔹 Get problem id
        problem = (
            supabase.table("problems")
            .select("id, constituencies_id, districts_id")
            .eq("issue_token", issue_token)
            .execute()
            .data
        )

        if not problem:
            flash("Invalid issue token")
            return redirect(url_for("constituency_escalate_to_department"))

        problem = problem[0]

        # 🔹 Check already escalated to department
        already = (
            supabase.table("department_escalated_issues")
            .select("id")
            .eq("problem_id", problem["id"])
            .execute()
            .data
        )

        if already:
            flash("Issue already escalated to department")
            return redirect(url_for("constituency_escalate_to_department"))

        # 🔹 Insert escalation
        supabase.table("department_escalated_issues").insert({
            "problem_id": problem["id"],
            "constituency_id": problem["constituencies_id"],
            "district_id": problem["districts_id"],
            "department_id": department_id
        }).execute()

        flash("Issue escalated to department successfully")
        return redirect(url_for("constituency_escalate_to_department"))

    # ==================================================
    # GET REQUEST → DROPDOWNS
    # ==================================================

    # 1️⃣ Problems already escalated to department
    dept_escalated = (
        supabase.table("department_escalated_issues")
        .select("problem_id")
        .execute()
        .data
    )
    dept_problem_ids = [d["problem_id"] for d in dept_escalated]

    # 2️⃣ Problems escalated from PLACE → CONSTITUENCY
    query = (
        supabase.table("escalated_issues")
        .select("""
            problem_id,
            problems (
                issue_token
            )
        """)
    )

    # 3️⃣ Exclude department-escalated issues
    if dept_problem_ids:
        query = query.not_.in_("problem_id", dept_problem_ids)

    escalated_issues = query.execute().data

    # 🔹 Prepare tokens list
    issues = [
        {
            "issue_token": e["problems"]["issue_token"]
        }
        for e in escalated_issues
    ]

    # 4️⃣ Departments dropdown
    departments = (
        supabase.table("departments")
        .select("id, name")
        .order("name")
        .execute()
        .data
    )

    return render_template(
        "place/escalate_department.html",
        issues=issues,
        departments=departments
    )



@app.route("/constituency/update-status", methods=["GET", "POST"])
def constituency_update_status():

    if request.method == "POST":
        issue_token = request.form.get("issue_token")
        new_status = request.form.get("status")

        if not issue_token or not new_status:
            flash("Issue token and status are required")
            return redirect(url_for("constituency_update_status"))

        # 🔍 Get problem ID
        problem = (
            supabase.table("problems")
            .select("id")
            .eq("issue_token", issue_token)
            .execute()
            .data
        )

        if not problem:
            flash("Invalid issue token")
            return redirect(url_for("constituency_update_status"))

        problem_id = problem[0]["id"]

        # ❌ Check if escalated to department
        dept_check = (
            supabase.table("department_escalated_issues")
            .select("id")
            .eq("problem_id", problem_id)
            .execute()
            .data
        )

        if dept_check:
            flash("This issue is escalated to department. Status cannot be changed here.")
            return redirect(url_for("constituency_update_status"))

        # ✅ Update status
        supabase.table("problems").update({
            "status": new_status
        }).eq("id", problem_id).execute()

        flash("Status updated successfully")
        return redirect(url_for("constituency_update_status"))

    # =========================
    # GET → Load ONLY valid issues
    # =========================

    # 1️⃣ Issues escalated to constituency
    esc = (
        supabase.table("escalated_issues")
        .select("problem_id, problems(issue_token)")
        .execute()
        .data
    )

    # 2️⃣ Issues escalated to department
    dept = (
        supabase.table("department_escalated_issues")
        .select("problem_id")
        .execute()
        .data
    )

    dept_ids = [d["problem_id"] for d in dept]

    # 3️⃣ Filter issues (constituency-level ONLY)
    valid_issues = [
        e["problems"]
        for e in esc
        if e["problem_id"] not in dept_ids
    ]

    return render_template(
        "place/update_status.html",
        issues=valid_issues
    )
  








@app.route("/department/login", methods=["GET", "POST"])
def department_login():

    message = None
    success = False

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            message = "Email and password are required"
        else:
            admin = (
                supabase.table("department_admins")
                .select("id, email, password, department_id")
                .eq("email", email)
                .execute()
                .data
            )

            if not admin or admin[0]["password"] != password:
                message = "Invalid credentials"
            else:
                # ✅ STORE IN SESSION
                session["department_id"] = admin[0]["department_id"]
                success = True

                # 🔀 GO DIRECTLY TO DASHBOARD
                return redirect(url_for("department_dashboardss"))

    return render_template(
        "place/login3.html",
        message=message,
        success=success
    )

@app.route("/department/dashboard")
def department_dashboardss():

    department_id = session.get("department_id")

    if not department_id:
        return redirect(url_for("department_login"))

    return render_template("place/dashboardss.html")



@app.route("/department/issues")
def department_issues():

    department_id = session.get("department_id")

    if not department_id:
        return redirect(url_for("department_login"))

    issues = (
        supabase.table("department_escalated_issues")
        .select("""
            id,
            problem_id,

            problems (
                issue_token,
                description,
                address,
                priority,
                status,
                media_urls,
                created_at,

                places ( name ),
                constituencies ( name )
            )
        """)
        .eq("department_id", department_id)
        .order("id", desc=True)
        .execute()
        .data
    )

    return render_template(
        "place/issues.html",
        issues=issues
    )


if __name__ == "__main__":
    app.run(debug=True)