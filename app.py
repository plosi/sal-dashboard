from shiny import App, render, ui, reactive, session
from shinywidgets import output_widget, render_widget
from utils import db, excel_io
from great_tables import GT

import faicons as fa
import polars as pl
from datetime import datetime, timedelta, date

import re
import json
import os
import plotly.express as px
import plotly.io as pio
pio.templates.default = "ggplot2"

# Initialize the database
db.initialize_db()

# Create a reactive value that acts as a data validation trigger
data_trigger = reactive.Value(0)

# Load credentials from .secrets.json
SECRETS = False
try:
    with open(".secrets.json", "r") as secrets_file:
        SECRETS = json.load(secrets_file)
except:
    print("No 'secrets' file found")
    PWD = os.getenv("PWD")
    print(PWD)

# Reactive values to track login state and session expiration
is_logged_in = reactive.Value(False)
last_login = reactive.Value(None)

# Get departments dynamically
def get_departments():
    conn = db.get_db_connection()
    return [row for row in conn.execute("SELECT code, icon FROM departments ORDER BY code DESC").fetchall()]

# ---- UI builders ----
def login_ui():
    return ui.page_fluid(
        ui.card(
            ui.input_text("username", "Username"),
            ui.input_password("password", "Password"),
            ui.input_action_button("login_btn", "Login", class_="btn btn-primary", width="130px"),
            title="Login",
            style="max-width: 400px; margin: auto; margin-top: 100px;"
        )
    )


def calendar_panel(dept):
    return ui.nav_panel(
        "Calendar",
        ui.navset_card_tab(
            ui.nav_panel(
                "Dashboard",
                ui.card(
                    output_widget(f"calendar_{dept}_plot"),
                    full_screen=True
                ),

                ui.card(
                    ui.row(
                        ui.column(3, ui.output_ui(f"calendar_{dept}_insights_year_filter")),
                        ui.column(3, ui.output_ui(f"calendar_{dept}_insights_advisor_filter"))
                    ),
                    ui.row(
                        ui.column(4, ui.output_ui(f"calendar_{dept}_insights_table")),
                        ui.column(8, output_widget(f"calendar_{dept}_insights_plot"))
                    )
                ),
                icon=fa.icon_svg("chart-pie")
            ),
            ui.nav_panel(
                "Data",
                ui.row(
                    ui.column(2,
                        ui.row(ui.output_ui(f"add_calendar_{dept}_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui(f"edit_calendar_{dept}_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui(f"delete_calendar_{dept}_btn"))
                    ),
                    ui.column(10, ui.output_data_frame(f"calendar_{dept}_table"))
                ),
                icon=fa.icon_svg("table")
            )
        ),
        icon=fa.icon_svg("calendar-day")
    )

def support_panel(dept):
    return ui.nav_panel(
        "Country Support",
        ui.navset_card_tab(
            ui.nav_panel(
                "Dashboard",
                ui.card(
                    ui.output_ui(f"support_{dept}_overall_year_filter"),
                    output_widget(f"support_{dept}_plot"),
                    full_screen=True
                ),

                ui.card(
                    ui.row(
                        ui.column(3, ui.output_ui(f"support_{dept}_insights_year_filter")),
                        ui.column(3, ui.output_ui(f"support_{dept}_insights_country_filter"))
                    ),
                    ui.row(
                        ui.column(7, output_widget(f"support_{dept}_insights_timeline")),
                        ui.column(5, output_widget(f"support_{dept}_insights_pie_chart"))
                    ),
                    ui.row(
                        ui.column(12, output_widget(f"support_{dept}_insights_advisors_plot"))
                    )
                ),
                icon=fa.icon_svg("chart-pie")
            ),
            ui.nav_panel(
                "Data",
                ui.row(
                    ui.column(2,
                        ui.row(ui.output_ui(f"add_timesheet_{dept}_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui(f"edit_timesheet_{dept}_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui(f"delete_timesheet_{dept}_btn"))
                    ),
                    ui.column(10, ui.output_data_frame(f"timesheet_{dept}_table"))
                ),
                icon=fa.icon_svg("table")
            )
        ),
        icon=fa.icon_svg("handshake-angle")
    )

def countries_panel(dept):
    return ui.nav_panel(
        "Countries",
        ui.navset_card_tab(
            ui.nav_panel(
                "Dashboard",
                ui.card(output_widget(f"allocations_{dept}_map"), full_screen=True),
                ui.card(
                    ui.row(
                        ui.column(2,
                            ui.row(ui.output_ui(f"country_focals_{dept}_country_filter")),
                            ui.row(ui.output_ui(f"make_country_focals_{dept}_btn"))
                        ),
                        ui.column(10, ui.output_ui(f"country_focals_{dept}_table")),
                    ),
                ),
                icon=fa.icon_svg("chart-pie"),
            ),
            ui.nav_panel(
                "Data",
                ui.row(
                    ui.column(2,
                        ui.row(ui.output_ui(f"add_country_focal_{dept}_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui(f"edit_country_focal_{dept}_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui(f"delete_country_focal_{dept}_btn"))
                    ),
                    ui.column(10, ui.output_data_frame(f"country_focals_{dept}_table_editable"))
                ),
                icon=fa.icon_svg("table")
            )
        ), 
        icon=fa.icon_svg("globe")
    )

def proposals_panel(dept):
    return ui.nav_panel(
        "Proposals",
        ui.navset_card_tab(
            ui.nav_panel(
                "Dashboard",
                ui.card(
                    ui.row(
                        ui.column(3, ui.output_ui(f"proposal_{dept}_insights_year_filter")),
                        ui.column(3, ui.output_ui(f"proposal_{dept}_insights_country_filter"))
                    ),
                    ui.row(
                        ui.column(7, output_widget(f"proposal_{dept}_insights_timeline")),
                        ui.column(5, output_widget(f"proposal_{dept}_insights_pie_chart"))
                    ),
                ),
                icon=fa.icon_svg("chart-pie"),
            ),
            ui.nav_panel(
                "Data",
                ui.row(
                    ui.column(2,
                        ui.row(ui.output_ui(f"add_proposal_{dept}_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui(f"edit_proposal_{dept}_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui(f"delete_proposal_{dept}_btn"))
                    ),
                    ui.column(10, ui.output_data_frame(f"proposals_{dept}_table"))
                ),
                icon=fa.icon_svg("table")
            )
        ), 
        icon=fa.icon_svg("file")
    )

def admin_panel():
    return ui.nav_menu(
        "Admin",
        ui.nav_panel(
            "Advisors",
            ui.card(
                ui.row(
                    ui.column(2,
                        ui.row(ui.output_ui("add_advisor_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui("edit_advisor_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui("delete_advisor_btn"))
                    ),
                    ui.column(10, ui.output_data_frame(f"advisors_table"))
                ),
            ),
            icon=fa.icon_svg("users")
        ),
        ui.nav_panel(
            "Departments",
            ui.card(
                ui.row(
                    ui.column(2,
                        ui.row(ui.output_ui("add_department_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui("edit_department_btn")),
                        ui.row(ui.br()),
                        ui.row(ui.output_ui("delete_department_btn"))
                    ),
                    ui.column(10, ui.output_data_frame(f"departments_table"))
                ),
            ),
            icon=fa.icon_svg("building-user")
        ),
        ui.nav_panel(
            "Export / Import",
            ui.card(
                ui.row(
                    ui.column(2, ui.row(ui.output_ui("export_btn"))),
                    ui.column(2, ui.row(ui.output_ui("import_btn")))
                ),
            ),
            icon=fa.icon_svg("database")
        ),
        icon=fa.icon_svg("user-tie")
    )

def logout_panel():
    return ui.nav_menu(
        "Logout",
        ui.nav_panel(
            ui.input_action_button(
                "logout_btn",
                "Logout",
                class_="btn btn-danger btn-sm",
                width="100px",
                icon=fa.icon_svg("door-open")
            ),
        ),
        icon=fa.icon_svg("door-open")
    ),


# Build full department UI
def department_ui(dept, icon):
    return ui.nav_panel(
        dept,
        ui.navset_pill_list(
            calendar_panel(dept),
            support_panel(dept),
            countries_panel(dept),
            proposals_panel(dept),
            widths=(2, 10),
        ),
        icon=fa.icon_svg(icon)
    )

# Base UI with a placeholder for dynamic content
app_ui = ui.page_fluid(
    ui.output_ui("dynamic_navbar")
)

# Server logic
def server(input, output, session):
    # Render the navbar reactively
    @output
    @render.ui
    def dynamic_navbar():
        if is_logged_in():
            departments = get_departments()
            return ui.page_navbar(
                *[department_ui(dept,icon) for dept, icon in departments],
                admin_panel(), # Global admin panel   
                logout_panel(),
                footer=ui.h6(
                    f"Made by Paolo Losi @ {datetime.now().year}",
                    style="color: black !important; text-align: center;"
                ),
                title="SAL TA Dashboard",
            )
        else:
            return login_ui()
    
    @reactive.Effect
    @reactive.event(input.login_btn)
    def handle_login():
        username = input.username()
        password = input.password()

        # Validate credentials
        if SECRETS:
            if username in SECRETS["users"] and SECRETS["users"][username] == password:
                is_logged_in.set(True)
                last_login.set(datetime.now())
                ui.notification_show("Login successful!", type="success")
            else:
                ui.notification_show("Invalid username or password.", type="error")
        else:
            if username == "sal" and password == PWD:
                is_logged_in.set(True)
                last_login.set(datetime.now())
                ui.notification_show("Login successful!", type="success")
            else:
                ui.notification_show("Invalid username or password.", type="error")

    # Optional: Add a session timeout (e.g., 30 days)
    @reactive.Effect
    def session_timeout():
        if is_logged_in():
            # last_login_ = last_login.set(datetime.now())
            if (datetime.now() - last_login.get()).days > 1:
                is_logged_in.set(False)
                ui.notification_show("Session expired. Please log in again.", type="warning")
    
    @reactive.Effect
    @reactive.event(input.logout_btn)
    def handle_logout():
        # session_state["logged_in"] = False
        is_logged_in.set(False)
        ui.notification_show("You have been logged out.", type="info")


    # ----- Admin
    # ----- Advisors
    @output(id=f"add_advisor_btn")
    @render.ui
    def _add_advisor_btn():
        return ui.input_action_button(
            f"add_advisor_btn_",
            "Add row",
            class_="btn btn-success btn-sm",
            width="130px",
            icon=fa.icon_svg("calendar-plus")
        )

    @output(id=f"edit_advisor_btn")
    @render.ui
    def _edit_advisor_btn():
        return ui.input_action_button(
            f"edit_advisor_btn_",
            "Edit row",
            class_="btn btn-warning btn-sm",
            width="130px",
            icon=fa.icon_svg("calendar-day")
        )
    
    @output(id=f"delete_advisor_btn")
    @render.ui
    def _delete_advisor_btn():
        return ui.input_action_button(
            f"delete_advisor_btn_",
            "Delete row",
            class_="btn btn-danger btn-sm",
            width="130px",
            icon=fa.icon_svg("calendar-xmark")
        )
    
    @reactive.Effect
    @reactive.event(input[f"add_advisor_btn_"])
    def _():
        ui.modal_show(
            ui.modal(
                ui.input_selectize("department_code", "Department", choices=dict((db.read_table("departments").select(pl.col("code"), pl.col("name"))).iter_rows())),
                ui.input_text("name", "Full Name"),
                ui.input_text("short_name", "Short Name (i.e., name displayed in dashboards)"),
                ui.input_text("role", "Role/Title"),
                ui.input_text("email", "Email"),
                ui.input_checkbox("active", "Active", value=True),
                ui.input_selectize("country_codes", "Country(ies)", dict((db.read_table("countries").select(pl.col("iso_alpha3_code"), pl.col("name"))).iter_rows()), multiple=True),
                ui.input_text("colour", "Colour (HEX)", value="#000000"),
                ui.modal_button("Cancel"),
                ui.input_action_button(f"add_advisor_submit", "Submit", class_="btn btn-primary"),
                title="Add Advisor",
                easy_close=True,
                fade=True,
                footer=None
            )
        )
    
    @reactive.Effect
    @reactive.event(input[f"add_advisor_submit"])
    def _():
        new_advisor = {
            "department_code": input.department_code(),
            "name": input.name(),
            "short_name": input.short_name(),
            "role": input.role(),
            "email": input.email(),
            "active": input.active(),
            "country_codes": re.sub("[()']", "", ", ".join(map(str, input["country_codes"]()))).strip(","),
            "colour": input.colour()
        }
        try:
            if not re.match(r"^#([A-Fa-f0-9]{6})$", new_advisor["colour"]):
                ui.notification_show(f"Error adding advisor: Colour must be a valid HEX code (e.g., #FF5733).", type="error")
                raise ValueError("Colour must be a valid HEX code (e.g., #FF5733).")
            if not new_advisor["name"] or not new_advisor["short_name"] or not new_advisor["department_code"]:
                ui.notification_show("Error adding advisor: Name, Short Name, and Department are required fields.", type="error")
                raise ValueError("Name, Short Name, and Department are required fields.")
            if not re.match(r"[^@]+@[^@]+\.[^@]+", new_advisor["email"]):
                ui.notification_show(f"Error adding advisor: Email must be a valid email address.", type="error")
                raise ValueError("Email must be a valid email address.")
        except ValueError as ve:
            ui.notification_show(f"Error adding advisor: {ve}", type="error")
            return
        finally:
            ui.modal_remove()
            data_trigger.set(data_trigger.get() + 1)
        
        db.insert("advisors", new_advisor)
    
    @reactive.Effect
    @reactive.event(input[f"edit_advisor_btn_"])
    def _():
        selected_rows = _advisors_table.data_view(selected=True)
        
        if selected_rows.shape[0] == 0:
            ui.notification_show("Please select a row to edit.", type="warning")
            return
        if selected_rows.shape[0] > 1:
            ui.notification_show("Please select only one row to edit.", type="warning")
            return
        try:
            id_to_edit = selected_rows.get_column("id").to_list()[0]
            advisor_data = db.read_table("advisors", where=f"id = {id_to_edit}").to_dicts()[0]
            ui.modal_show(
                ui.modal(
                    ui.input_selectize("edit_department_code", "Department", choices=dict((db.read_table("departments").select(pl.col("code"), pl.col("name"))).iter_rows()), selected=advisor_data["department_code"]),
                    ui.input_text("edit_name", "Full Name", value=advisor_data["name"]),
                    ui.input_text("edit_short_name", "Short Name (i.e., name displayed in dashboards)", value=advisor_data["short_name"]),
                    ui.input_text("edit_role", "Role/Title", value=advisor_data["role"]),
                    ui.input_text("edit_email", "Email", value=advisor_data["email"]),
                    ui.input_checkbox("edit_active", "Active", value=advisor_data["active"]),
                    ui.input_selectize("edit_country_codes", "Country(ies)", choices=dict((db.read_table("countries").select(pl.col("iso_alpha3_code"), pl.col("name"))).iter_rows()), multiple=True, selected=advisor_data["country_codes"]),
                    ui.input_text("edit_colour", "Colour (HEX)", value=advisor_data["colour"]),
                    ui.modal_button("Cancel"),
                    ui.input_action_button(f"edit_advisor_submit", "Submit", class_="btn btn-primary"),
                    title="Edit Advisor",
                    easy_close=True,
                    fade=True,
                    footer=None
                )
            )
        except Exception as e:
            ui.notification_show(f"Error preparing edit modal: {e}", type="error")
            return
    
        @reactive.Effect
        @reactive.event(input[f"edit_advisor_submit"])
        def _():
            updated_advisor = {
                "department_code": input.edit_department_code(),
                "name": input.edit_name(),
                "short_name": input.edit_short_name(),
                "role": input.edit_role(),
                "email": input.edit_email(),
                "active": input.edit_active(),
                "country_codes": re.sub("[()']", "", ", ".join(map(str, input["edit_country_codes"]()))).strip(","),
                "colour": input.edit_colour()
            }
            try:
                if not re.match(r"^#([A-Fa-f0-9]{6})$", updated_advisor["colour"]):
                    ui.notification_show(f"Error updating advisor: Colour must be a valid HEX code (e.g., #FF5733).", type="error")
                    raise ValueError("Colour must be a valid HEX code (e.g., #FF5733).")
                if not updated_advisor["name"] or not updated_advisor["short_name"] or not updated_advisor["department_code"]:
                    ui.notification_show("Error updating advisor: Name, Short Name, and Department are required fields.", type="error")
                    raise ValueError("Name, Short Name, and Department are required fields.")
                if not re.match(r"[^@]+@[^@]+\.[^@]+", updated_advisor["email"]):
                    ui.notification_show(f"Error updating advisor: Email must be a valid email address.", type="error")
                    raise ValueError("Email must be a valid email address.")
                db.update_row("advisors", updates=updated_advisor, where=f"id = {id_to_edit}")
                ui.notification_show("Advisor updated successfully.", type="success")
            except Exception as e:
                ui.notification_show(f"Error updating advisor: {e}", type="error")
            finally:
                ui.modal_remove()
                data_trigger.set(data_trigger.get() + 1)
    
    @reactive.Effect
    @reactive.event(input[f"delete_advisor_btn_"])
    def _():
        selected_rows = _advisors_table.data_view(selected=True)
        
        if selected_rows.shape[0] == 0:
            ui.notification_show("Please select at least one row to delete.", type="warning")
            return
        try:
            ids_to_delete = selected_rows.get_column("id").to_list()
            ui.modal_show(
                ui.modal(
                    ui.h4(f"Are you sure you want to delete the selected {len(ids_to_delete)} advisor(s)? This action cannot be undone."),
                    ui.modal_button("Cancel"),
                    ui.input_action_button(f"delete_advisor_confirm", "Delete", class_="btn btn-danger"),
                    title="Confirm Deletion",
                    easy_close=True,
                    fade=True,
                    footer=None
                )
            )
        except Exception as e:
            ui.notification_show(f"Error preparing delete modal: {e}", type="error")
            return

        @reactive.Effect
        @reactive.event(input[f"delete_advisor_confirm"])
        def _():
            try:
                db.delete_row("advisors", where=f"id IN ({', '.join(map(str, ids_to_delete))})")
                ui.notification_show(f"Deleted {len(ids_to_delete)} advisor(s) successfully.", type="success")
            except Exception as e:
                ui.notification_show(f"Error deleting advisor(s): {e}", type="error")
            finally:
                ui.modal_remove()
                data_trigger.set(data_trigger.get() + 1)

    @output(id=f"advisors_table")
    @render.data_frame
    def _advisors_table():
        # Use data_trigger to refresh the table when it changes
        data_trigger.get()  # Trigger reactivity
        advisors = db.read_table("advisors").sort(by=["department_code"], descending=False)
        return render.DataGrid(
            advisors,
            height="400px",
            selection_mode="rows",
            filters=True
        )


    # ----- Departments
    @output(id=f"add_department_btn")
    @render.ui
    def _add_department_btn():
        return ui.input_action_button(
            f"add_department_btn_",
            "Add row",
            class_="btn btn-success btn-sm",
            width="130px",
            icon=fa.icon_svg("calendar-plus")
        )

    @output(id=f"edit_department_btn")
    @render.ui
    def _edit_department_btn():
        return ui.input_action_button(
            f"edit_department_btn_",
            "Edit row",
            class_="btn btn-warning btn-sm",
            width="130px",
            icon=fa.icon_svg("calendar-day")
        )

    @output(id=f"delete_department_btn")
    @render.ui
    def _delete_department_btn():
        return ui.input_action_button(
            f"delete_department_btn_",
            "Delete row",
            class_="btn btn-danger btn-sm",
            width="130px",
            icon=fa.icon_svg("calendar-xmark")
        )
    
    @reactive.Effect
    @reactive.event(input[f"add_department_btn_"])
    def _():
        ui.modal_show(
            ui.modal(
                ui.input_text("name", "Department Name"),
                ui.input_text("code", "Department Code (short, unique)"),
                ui.input_text("icon", "Icon (FontAwesome icon name, e.g., building-user)"),
                ui.modal_button("Cancel"),
                ui.input_action_button(f"add_department_submit", "Submit", class_="btn btn-primary"),
                title="Add Department",
                easy_close=True,
                fade=True,
                footer=None
            )
        )

    @reactive.Effect
    @reactive.event(input[f"add_department_submit"])
    def _():
        new_department = {
            "name": input.name(),
            "code": input.code(),
            "icon": input.icon()
        }
        try:
            if not new_department["name"] or not new_department["code"]:
                ui.notification_show("Error adding department: Name and Code are required fields.", type="error")
                raise ValueError("Name and Code are required fields.")
            db.insert("departments", new_department)
        except Exception as e:
            ui.notification_show(f"Error adding department: {e}", type="error")
        finally:
            ui.modal_remove()
            data_trigger.set(data_trigger.get() + 1)
    
    @reactive.Effect
    @reactive.event(input[f"edit_department_btn_"])
    def _():
        selected_rows = _departments_table.data_view(selected=True)
        
        if selected_rows.shape[0] == 0:
            ui.notification_show("Please select a row to edit.", type="warning")
            return
        if selected_rows.shape[0] > 1:
            ui.notification_show("Please select only one row to edit.", type="warning")
            return
        try:
            id_to_edit = selected_rows.get_column("id").to_list()[0]
            department_data = db.read_table("departments", where=f"id = {id_to_edit}").to_dicts()[0]
            ui.modal_show(
                ui.modal(
                    ui.input_text("edit_name", "Department Name", value=department_data["name"]),
                    ui.input_text("edit_code", "Department Code (short, unique)", value=department_data["code"]),
                    ui.input_text("edit_icon", "Icon (FontAwesome icon name, e.g., building-user)", value=department_data["icon"]),
                    ui.modal_button("Cancel"),
                    ui.input_action_button(f"edit_department_submit", "Submit", class_="btn btn-primary"),
                    title="Edit Department",
                    easy_close=True,
                    fade=True,
                    footer=None
                )
            )
        except Exception as e:
            ui.notification_show(f"Error preparing edit modal: {e}", type="error")
            return

        @reactive.Effect
        @reactive.event(input[f"edit_department_submit"])
        def _():
            updated_department = {
                "name": input.edit_name(),
                "code": input.edit_code(),
                "icon": input.edit_icon()
            }
            try:
                if not updated_department["name"] or not updated_department["code"]:
                    ui.notification_show("Error updating department: Name and Code are required fields.", type="error")
                    raise ValueError("Name and Code are required fields.")
                db.update_row("departments", updates=updated_department, where=f"id = {id_to_edit}")
                ui.notification_show("Department updated successfully.", type="success")
            except Exception as e:
                ui.notification_show(f"Error updating department: {e}", type="error")
            finally:
                ui.modal_remove()
                data_trigger.set(data_trigger.get() + 1)
    
    @reactive.Effect
    @reactive.event(input[f"delete_department_btn_"])
    def _():
        selected_rows = _departments_table.data_view(selected=True)
        
        if selected_rows.shape[0] == 0:
            ui.notification_show("Please select at least one row to delete.", type="warning")
            return
        try:
            ids_to_delete = selected_rows.get_column("id").to_list()
            ui.modal_show(
                ui.modal(
                    ui.h4(f"Are you sure you want to delete the selected {len(ids_to_delete)} department(s)? This action cannot be undone."),
                    ui.modal_button("Cancel"),
                    ui.input_action_button(f"delete_department_confirm", "Delete", class_="btn btn-danger"),
                    title="Confirm Deletion",
                    easy_close=True,
                    fade=True,
                    footer=None
                )
            )
        except Exception as e:
            ui.notification_show(f"Error preparing delete modal: {e}", type="error")
            return

        @reactive.Effect
        @reactive.event(input[f"delete_department_confirm"])
        def _():
            try:
                db.delete_row("departments", where=f"id IN ({', '.join(map(str, ids_to_delete))})")
                ui.notification_show(f"Deleted {len(ids_to_delete)} department(s) successfully.", type="success")
            except Exception as e:
                ui.notification_show(f"Error deleting department(s): {e}", type="error")
            finally:
                ui.modal_remove()
                data_trigger.set(data_trigger.get() + 1)
    
    @output(id=f"departments_table")
    @render.data_frame
    def _departments_table():
        # Use data_trigger to refresh the table when it changes
        data_trigger.get()  # Trigger reactivity
        departments = db.read_table("departments").sort(by=["code"], descending=False)
        return render.DataGrid(
            departments,
            height="400px",
            selection_mode="rows",
            filters=True
        )
    
    # ----- Export / Import
    @output(id="export_btn")
    @render.ui
    def _export_btn():
        return ui.download_button(
            id="download",
            label="Download Excel",
            class_="btn btn-success",
            icon=fa.icon_svg("file-export")
        )
    
    @render.download()
    def download():
        try:
            now = datetime.now().isoformat("#", "seconds").replace(":", "_")
            excel_io.export_db_to_excel(f"sal_ta_dashboard_export_{now}.xlsx")
            ui.notification_show("Database exported successfully.", type="success")
            return f"sal_ta_dashboard_export_{now}.xlsx"
        except Exception as e:
            ui.notification_show(f"Error exporting database: {e}", type="error")
            return None
    


    # Now define reactive renderers for each department/table combo
    depts = [row[0] for row in get_departments()]

    # Create dictionaries to store renderers
    calendar_table_renderers = {}
    timesheet_table_renderers = {}
    country_focals_table_renderers = {}
    proposal_table_renderers = {}

    for dept in depts:
        # ----- Calendar        
        @output(id=f"calendar_{dept}_plot")
        @render_widget
        def _plot_calendar(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            calendar = db.read_table("calendar", where=f"department_code = '{dept}'")

            # Handle calendar date range
            try:
                range_x_start, range_x_end = [datetime.today() - timedelta(weeks=2), datetime.today() + timedelta(weeks=6)]#input[f"calendar_{dept}_data_range_"]()
                # Transform data range into datetime object
                range_x_start = datetime(range_x_start.year, range_x_start.month, range_x_start.day)
                range_x_end = datetime(range_x_end.year, range_x_end.month, range_x_end.day)
                assert range_x_start is not None and range_x_end is not None
            except (TypeError, AssertionError) as e:
                print(e)
                range_x_start, range_x_end = None, None
            
            # Ensure that single days events are represented with a visible width
            calendar = calendar.with_columns(
                pl.when(pl.col("start_date") == pl.col("end_date"))
                .then(pl.col("end_date") + pl.duration(hours=11, minutes=59))
                .otherwise(pl.col("end_date"))
                .alias("end_date")
            )

            # Get events for color mapping
            events = db.read_table("events")

            fig = px.timeline(
                data_frame=calendar,
                x_start = "start_date",
                x_end = "end_date",
                y="advisor_short_name",
                color="event_name",
                color_discrete_map=dict(zip(events.get_column("name").to_list(), events.get_column("colour").to_list())),
                text="notes",
                labels={"event_name": "", "advisor_short_name": ""},
                range_x=[range_x_start, range_x_end] if range_x_start and range_x_end else None
            )

            fig.update_xaxes(
                tickformat="%d-%b",
                dtick=86400000.0*7,#"D7",
                rangebreaks=[
                    dict(bounds=["sat", "mon"]), # hide weekends
                ],
                rangeslider_visible=True,
            )

            fig.update_traces(textposition='inside')
            fig.add_vline(x=datetime.today(), line_dash='dot', line_width=2, opacity=1, line_color='black')
            return fig

        @output(id=f"calendar_{dept}_insights_year_filter")
        @render.ui
        def _calendar_insights_year_filter(dept=dept):
            calendar = db.read_table("calendar", where=f"department_code = '{dept}'")
            years = calendar.select(pl.col("start_date").dt.year().alias("year")).unique().sort("year").to_series().to_list()
            return ui.input_select(
                f"calendar_{dept}_insights_year_filter_",
                "Select Year",
                choices=years,
                selected=years[-1] if years else None,
                width="150px"
            )
        
        @output(id=f"calendar_{dept}_insights_advisor_filter")
        @render.ui
        def _calendar_insights_advisor_filter(dept=dept):
            calendar = db.read_table("calendar", where=f"department_code = '{dept}'")
            advisors = calendar.select(pl.col("advisor_short_name")).unique().sort("advisor_short_name").to_series().to_list()
            return ui.input_select(
                f"calendar_{dept}_insights_advisor_filter_",
                "Select Advisor",
                choices=["All"] + advisors,
                selected="All",
                width="150px"
            )

        @output(id=f"calendar_{dept}_insights_table")
        @render.ui
        def _calendar_insights_table(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            calendar = db.read_table("calendar", where=f"department_code = '{dept}'")
            # Apply filters
            try:
                selected_year = int(input[f"calendar_{dept}_insights_year_filter_"]())
            except (TypeError, ValueError):
                selected_year = None
            selected_advisor = input[f"calendar_{dept}_insights_advisor_filter_"]()
            if selected_year:
                calendar = calendar.filter(pl.col("start_date").dt.year() == selected_year)
            if selected_advisor and selected_advisor != "All":
                calendar = calendar.filter(pl.col("advisor_short_name") == selected_advisor)
            
            # Aggregate data
            insights = (
                calendar
                .with_columns(
                    pl.business_day_count(pl.col("start_date").dt.date(), pl.col("end_date").dt.date()).alias("total_business_days"),
                    pl.col("start_date").dt.year().alias("year"),
                )
                .group_by(["year", "advisor_short_name", "event_name"])
                .agg([pl.sum("total_business_days").alias("total_days")])
                .sort(["year", "advisor_short_name"])
            ).with_columns(
                (pl.col("total_days") / 260 * 100).round(1).alias("percentage_of_year")# Assuming 260 business days in a year
            )
            insights = insights.select([
                pl.col("advisor_short_name").alias("Advisor"),
                pl.col("event_name").alias("Description"),
                pl.col("total_days").alias("Total Days"),
                pl.col("percentage_of_year").alias("% of Year")
            ])

            return GT(insights).tab_options(container_height="350px")
        
        @output(id=f"calendar_{dept}_insights_plot")
        @render_widget
        def _calendar_insights_plot(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            calendar = db.read_table("calendar", where=f"department_code = '{dept}'")
            # Apply filters
            try:
                selected_year = int(input[f"calendar_{dept}_insights_year_filter_"]())
            except (TypeError, ValueError):
                selected_year = None
            selected_advisor = input[f"calendar_{dept}_insights_advisor_filter_"]()
            if selected_year:
                calendar = calendar.filter(pl.col("start_date").dt.year() == selected_year)
            if selected_advisor and selected_advisor != "All":
                calendar = calendar.filter(pl.col("advisor_short_name") == selected_advisor)
            
            # Aggregate data
            insights = (
                calendar
                .with_columns(
                    pl.business_day_count(pl.col("start_date").dt.date(), pl.col("end_date").dt.date()).alias("total_business_days"),
                    pl.col("start_date").dt.year().alias("year"),
                )
                .group_by(["year", "advisor_short_name", "event_name"])
                .agg([pl.sum("total_business_days").alias("total_days")])
                .sort(["year", "advisor_short_name"])
            ).with_columns(
                (pl.col("total_days") / 260 * 100).round(1).alias("percentage_of_year")# Assuming 260 business days in a year
            )

            # Get advisors for color mapping
            advisors = db.read_table("advisors", where=f"department_code = '{dept}'")
            
            fig = px.bar(
                insights,
                x="total_days",
                y="event_name",
                color="advisor_short_name",
                text="total_days",
                labels={"advisor_short_name": "", "total_days": "Total Days", "event_name": ""},
                # color_discrete_map=dict(zip(insights.get_column("advisor_short_name").unique().to_list(), advisors_palette))
                color_discrete_map=dict(zip(advisors.get_column("short_name").to_list(), advisors.get_column("colour").to_list()))
            )
            fig.update_traces(textposition='inside')
            fig.update_layout(barmode='stack', yaxis={'categoryorder':'total descending'})
            return fig
        
        @output(id=f"add_calendar_{dept}_btn")
        @render.ui
        def _add_calendar_btn(dept=dept):
            return ui.input_action_button(
                f"add_calendar_{dept}_btn_",
                "Add row",
                class_="btn btn-success btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-plus")
            )
        
        @output(id=f"edit_calendar_{dept}_btn")
        @render.ui
        def _edit_calendar_btn(dept=dept):
            return ui.input_action_button(
                f"edit_calendar_{dept}_btn_",
                "Edit row",
                class_="btn btn-warning btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-day")
            )
        
        @output(id=f"delete_calendar_{dept}_btn")
        @render.ui
        def _delete_calendar_btn(dept=dept):
            return ui.input_action_button(
                f"delete_calendar_{dept}_btn_",
                "Delete row",
                class_="btn btn-danger btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-xmark")
            )

        @output(id=f"calendar_{dept}_table")
        @render.data_frame
        def _calendar_table(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            calendar = db.read_table("calendar", where=f"department_code = '{dept}'").sort(by="id", descending=True)
            return render.DataGrid(
                calendar,
                height="400px",
                selection_mode="rows"
            )
        
        # Keep a reference to the calendar table for use in other reactive contexts
        calendar_table_renderers[dept] = _calendar_table
        
        @reactive.Effect
        @reactive.event(input[f"add_calendar_{dept}_btn_"])
        def _(dept=dept):
            ui.modal_show(
                ui.modal(
                    ui.input_selectize("advisor_short_name", "Advisor", choices=db.read_table("advisors", where=f"department_code = '{dept}'").select(pl.col("short_name")).to_series().to_list()),
                    ui.input_date("start_date", "From", value=date.today()),
                    ui.input_date("end_date", "To", value=date.today()),
                    ui.input_selectize("event_name", "Type", choices=db.read_table("events").get_column("name").unique().to_list()),
                    ui.input_text_area("notes", "Notes", placeholder="Additional details, e.g., country name, workshop title, etc."),
                    ui.modal_button("Cancel"),
                    ui.input_action_button(f"add_calendar_{dept}_submit", "Submit", class_="btn btn-primary"),
                    title="Add Calendar Entry",
                    easy_close=True,
                    fade=True,
                    footer=None
                )
            )
        
        @reactive.Effect
        @reactive.event(input[f"add_calendar_{dept}_submit"])
        def _(dept=dept):
            advisor_short_name = input["advisor_short_name"]()
            start_date = input["start_date"]()
            end_date = input["end_date"]()
            event_name = input["event_name"]()
            notes = input["notes"]()

            try:
                db.insert_row(
                    "calendar", {
                        "department_code": dept,
                        "advisor_short_name": advisor_short_name,
                        "start_date": start_date,
                        "end_date": end_date,
                        "event_name": event_name,
                        "notes": notes
                    }
                )
                ui.notification_show(f"Calendar entry added successfully for {advisor_short_name}!", type="success")
            except Exception as e:
                ui.notification_show(f"Error adding calendar entry: {e}", type="error")
            finally:
                data_trigger.set(data_trigger.get() + 1)
        
        @reactive.Effect
        @reactive.event(input[f"edit_calendar_{dept}_btn_"])
        def _(dept=dept):
            selected_rows = calendar_table_renderers[dept].data_view(selected=True)
            
            if selected_rows.shape[0] == 0:
                ui.notification_show("Please select a row to edit.", type="warning")
                return
            if selected_rows.shape[0] > 1:
                ui.notification_show("Please select only one row to edit.", type="warning")
                return
            try:
                id_to_edit = selected_rows.get_column("id").to_list()[0]
                ui.modal_show(
                    ui.modal(
                        ui.input_selectize("edit_advisor_short_name", "Advisor", choices=db.read_table("advisors", where=f"department_code = '{dept}'").select(pl.col("short_name")).to_series().to_list(), selected=selected_rows.get_column("advisor_short_name").to_list()[0]),
                        ui.input_date("edit_start_date", "From", value=selected_rows.get_column("start_date").to_list()[0].date()),
                        ui.input_date("edit_end_date", "To", value=selected_rows.get_column("end_date").to_list()[0].date()),
                        ui.input_selectize("edit_event_name", "Type", choices=db.read_table("events").get_column("name").unique().to_list(), selected=selected_rows.get_column("event_name").to_list()[0]),
                        ui.input_text_area("edit_notes", "Notes", value=selected_rows.get_column("notes").to_list()[0], placeholder="Additional details, e.g., country name, workshop title, etc."),
                        ui.modal_button("Cancel"),
                        ui.input_action_button(f"edit_calendar_{dept}_submit", "Submit", class_="btn btn-primary"),
                        title="Edit Calendar Entry",
                        easy_close=True,
                        fade=True,
                        footer=None
                    )
                )
            except Exception as e:
                ui.notification_show(f"Error preparing edit modal: {e}", type="error")
            @reactive.Effect
            @reactive.event(input[f"edit_calendar_{dept}_submit"])
            def _(id_to_edit=id_to_edit):
                advisor_short_name = input["edit_advisor_short_name"]()
                start_date = input["edit_start_date"]()
                end_date = input["edit_end_date"]()
                event_name = input["edit_event_name"]()
                notes = input["edit_notes"]()

                try:
                    db.update_row(
                        "calendar",
                        {
                            "advisor_short_name": advisor_short_name,
                            "start_date": start_date,
                            "end_date": end_date,
                            "event_name": event_name,
                            "notes": notes
                        },
                        where=f"id = {id_to_edit}"
                    )
                    ui.notification_show(f"Calendar entry updated successfully for {advisor_short_name}!", type="success")
                except Exception as e:
                    ui.notification_show(f"Error updating calendar entry: {e}", type="error")
                finally:
                    data_trigger.set(data_trigger.get() + 1)
        
        @reactive.Effect
        @reactive.event(input[f"delete_calendar_{dept}_btn_"])
        def _(dept=dept):
            selected_rows = calendar_table_renderers[dept].data_view(selected=True)
            
            if selected_rows.shape[0] == 0:
                ui.notification_show("Please select a row to delete.", type="warning")
                return
            if selected_rows.shape[0] > 1:
                ui.notification_show("Please select only one row to delete.", type="warning")
                return
            try:
                id_to_delete = selected_rows.get_column("id").to_list()[0]
                advisor_short_name = selected_rows.get_column("advisor_short_name").to_list()[0]
                ui.modal_show(
                    ui.modal(
                        ui.p(f"Are you sure you want to delete the calendar entry for {advisor_short_name}?"),
                        ui.modal_button("Cancel"),
                        ui.input_action_button(f"delete_calendar_{dept}_submit", "Delete", class_="btn btn-danger"),
                        title="Confirm Deletion",
                        easy_close=True,
                        fade=True,
                        footer=None
                    )
                )
            except Exception as e:
                ui.notification_show(f"Error preparing delete modal: {e}", type="error")
            
            @reactive.Effect
            @reactive.event(input[f"delete_calendar_{dept}_submit"])
            def _(id_to_delete=id_to_delete, advisor_short_name=advisor_short_name):
                ui.modal_remove()
                try:
                    db.delete_row(
                        "calendar",
                        where=f"id = {id_to_delete}"
                    )
                    ui.notification_show(f"Calendar entry deleted successfully for {advisor_short_name}!", type="success")
                except Exception as e:
                    ui.notification_show(f"Error deleting calendar entry: {e}", type="error")
                finally:
                    data_trigger.set(data_trigger.get() + 1)

        # ----- Country Support
        @output(id=f"support_{dept}_overall_year_filter")
        @render.ui
        def _support_overall_year_filter(dept=dept):
            timesheet = db.read_table("timesheet", where=f"department_code = '{dept}'")
            years = timesheet.select(pl.col("date").dt.year().alias("year")).unique().sort("year").to_series().to_list()
            return ui.input_select(
                f"support_{dept}_overall_year_filter_",
                "Select Year",
                choices=years,
                selected=years[-1] if years else None,
                width="150px"
            )

        @output(id=f"support_{dept}_plot")
        @render_widget
        def _plot_support_overview(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            timesheet = db.read_table("timesheet", where=f"department_code = '{dept}'")

            # Apply year filter
            selected_year = int(input[f"support_{dept}_overall_year_filter_"]())
            timesheet = timesheet.filter(pl.col("date").dt.year() == selected_year)

            # Transform country_name to handle multiple countries
            timesheet = (
                timesheet
                .with_columns(pl.col("country_name").str.split(", "))
                .explode("country_name")
            )
            
            # Aggregate data
            aggregated_data = (
                timesheet
                .group_by(["country_name","support_name"])
                .agg(pl.col("hours").sum().alias("total_hours"))
            )

            # Map colors
            support = db.read_table("support")

            fig = px.bar(
                aggregated_data,
                x="country_name",
                y="total_hours",
                text="total_hours",
                color="support_name",
                color_discrete_map=dict(zip(support.get_column("name").to_list(), support.get_column("colour").to_list())),
                labels={"country_name":"", "total_hours":"Total Hours", "support_name":"Type of Support"},
                title=f"Total number of hours of technical support by country ({selected_year})"
            )

            fig.update_layout(xaxis={'categoryorder':'total descending'})

            return fig
        
        @output(id=f"support_{dept}_insights_year_filter")
        @render.ui
        def _support_insights_year_filter(dept=dept):
            timesheet = db.read_table("timesheet", where=f"department_code = '{dept}'")
            years = timesheet.select(pl.col("date").dt.year().alias("year")).unique().sort("year").to_series().to_list()
            return ui.input_select(
                f"support_{dept}_insights_year_filter_",
                "Select Year",
                choices=years,
                selected=years[-1] if years else None,
                width="150px"
            )
        
        @output(id=f"support_{dept}_insights_country_filter")
        @render.ui
        def _support_insights_country_filter(dept=dept):
            timesheet = db.read_table("timesheet", where=f"department_code = '{dept}'")
            countries = timesheet.select(pl.col("country_name").str.split(", ")).explode("country_name").unique().sort("country_name").to_series().to_list()
            
            return ui.input_select(
                f"support_{dept}_insights_country_filter_",
                "Select Country",
                choices=["All"] + countries,
                selected="All",
                width="150px"
            )
        
        @output(id=f"support_{dept}_insights_timeline")
        @render_widget
        def _support_insights_timeline(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            timesheet = db.read_table("timesheet", where=f"department_code = '{dept}'")

            # Apply filters
            selected_year = int(input[f"support_{dept}_insights_year_filter_"]())
            selected_country = input[f"support_{dept}_insights_country_filter_"]()
            if selected_year:
                timesheet = timesheet.filter(pl.col("date").dt.year() == selected_year)
            if selected_country and selected_country != "All":
                # Transform country_name to handle multiple countries
                timesheet = (
                    timesheet
                    .with_columns(pl.col("country_name").str.split(", "))
                    .explode("country_name")
                )
                timesheet = timesheet.filter(pl.col("country_name") == selected_country)

            # Extract month
            timesheet = timesheet.with_columns(pl.col("date").dt.month().alias("month"))
            
            # Aggregate data
            MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            insights = (
                timesheet
                .group_by(["month"])
                .agg(pl.col("hours").sum().alias("total_hours"))
            )            
            
            fig = px.bar(
                insights,
                x="month",
                y="total_hours",
                labels={"month":"", "total_hours":"Total Hours"},
                title=f"Monthly technical support" + (f" for {selected_country}" if selected_country and selected_country != "All" else "") + f" ({selected_year})"
            ).update_xaxes(
                tickvals=insights['month'].unique(),
                ticktext=[MONTHS[i-1] for i in insights['month'].unique()]
            )
            return fig
        
        @output(id=f"support_{dept}_insights_pie_chart")
        @render_widget
        def _support_insights_pie_chart(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            timesheet = db.read_table("timesheet", where=f"department_code = '{dept}'")
            # Apply filters
            selected_year = int(input[f"support_{dept}_insights_year_filter_"]())
            selected_country = input[f"support_{dept}_insights_country_filter_"]()
            if selected_year:
                timesheet = timesheet.filter(pl.col("date").dt.year() == selected_year)
            if selected_country and selected_country != "All":
                # Transform country_name to handle multiple countries
                timesheet = (
                    timesheet
                    .with_columns(pl.col("country_name").str.split(", "))
                    .explode("country_name")
                )
                timesheet = timesheet.filter(pl.col("country_name") == selected_country)            

            # Aggregate data
            insights = (
                timesheet
                .group_by(["support_name"])
                .agg(pl.col("hours").sum().alias("total_hours"))
                .sort("total_hours", descending=True)
            )

            fig = px.pie(
                insights,
                names="support_name",
                values="total_hours",
                color_discrete_sequence=px.colors.sequential.Reds,
                title=f"Technical support by type" + (f" for {selected_country}" if selected_country and selected_country != "All" else "") + f" ({selected_year})"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')

            return fig
        
        @output(id=f"support_{dept}_insights_advisors_plot")
        @render_widget
        def _support_insights_advisors_plot(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            timesheet = db.read_table("timesheet", where=f"department_code = '{dept}'")
            # Apply filters
            selected_year = int(input[f"support_{dept}_insights_year_filter_"]())
            selected_country = input[f"support_{dept}_insights_country_filter_"]()
            if selected_year:
                timesheet = timesheet.filter(pl.col("date").dt.year() == selected_year)
            if selected_country and selected_country != "All":
                # Transform country_name to handle multiple countries
                timesheet = (
                    timesheet
                    .with_columns(pl.col("country_name").str.split(", "))
                    .explode("country_name")
                )
                timesheet = timesheet.filter(pl.col("country_name") == selected_country)            

            # Transform sal_attendees to handle multiple advisors
            timesheet = (
                timesheet
                .with_columns(pl.col("sal_attendees").str.split(", "))
                .explode("sal_attendees")
            )

            # Aggregate data
            insights = (
                timesheet
                .group_by(["sal_attendees"])
                .agg(pl.col("hours").sum().alias("total_hours"))
                # .sort("total_hours", descending=True)
            )

            # Get advisors for color mapping
            advisors = db.read_table("advisors", where=f"department_code = '{dept}'")
            
            fig = px.bar(
                insights,
                x="sal_attendees",
                y="total_hours",
                color="sal_attendees",
                text="total_hours",
                labels={"sal_attendees":"", "total_hours":"Total Hours"},
                title=f"Technical support by advisor" + (f" for {selected_country}" if selected_country and selected_country != "All" else "") + f" ({selected_year})",
                color_discrete_map=dict(zip(advisors.get_column("short_name").to_list(), advisors.get_column("colour").to_list()))
            )
            fig.update_traces(textposition='inside')
            fig.update_layout(showlegend=False, xaxis={'categoryorder':'total descending'})

            return fig

        
        @output(id=f"add_timesheet_{dept}_btn")
        @render.ui
        def _add_timesheet_btn(dept=dept):
            return ui.input_action_button(
                f"add_timesheet_{dept}_btn_",
                "Add row",
                class_="btn btn-success btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-plus")
            )

        @output(id=f"edit_timesheet_{dept}_btn")
        @render.ui
        def _edit_timesheet_btn(dept=dept):
            return ui.input_action_button(
                f"edit_timesheet_{dept}_btn_",
                "Edit row",
                class_="btn btn-warning btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-day")
            )

        @output(id=f"delete_timesheet_{dept}_btn")
        @render.ui
        def _delete_timesheet_btn(dept=dept):
            return ui.input_action_button(
                f"delete_timesheet_{dept}_btn_",
                "Delete row",
                class_="btn btn-danger btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-xmark")
            )

        @output(id=f"timesheet_{dept}_table")
        @render.data_frame
        def _timesheet_table(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            timesheet = db.read_table("timesheet", where=f"department_code = '{dept}'").sort(by="id", descending=True)
            return render.DataGrid(
                timesheet,
                height="400px",
                selection_mode="rows"
            )
        
        # Keep a reference to the timesheet table for use in other reactive contexts
        timesheet_table_renderers[dept] = _timesheet_table

        @reactive.Effect
        @reactive.event(input[f"add_timesheet_{dept}_btn_"])
        def _(dept=dept):
            ui.modal_show(
                ui.modal(
                    ui.input_date("date", "Date", value=date.today()),
                    ui.input_selectize("country_name", "Country(ies)", choices=db.read_table("countries").select(pl.col("name")).to_series().to_list(), multiple=True),
                    ui.input_selectize("sal_attendees", "Advisor(s)", choices=db.read_table("advisors", where=f"department_code = '{dept}' AND active = 'true'").select(pl.col("short_name")).to_series().to_list(), multiple=True),
                    ui.input_text_area("country_attendees", "Country Attendee(s)", placeholder="Comma separated list of names"),
                    ui.input_selectize("support_name", "Type of Support", choices=db.read_table("support").select(pl.col("name")).to_series().to_list()),
                    ui.input_text_area("description", "Description", placeholder="Additional details, e.g., monthly catch-up, training topics, etc."),
                    ui.input_numeric("hours", "Hours", min=0.5, max=8, step=0.5, value=1.0),
                    ui.modal_button("Cancel"),
                    ui.input_action_button(f"add_timesheet_{dept}_submit", "Submit", class_="btn btn-primary"),
                    title="Add Timesheet Entry",
                    easy_close=True,
                    fade=True,
                    footer=None
                )
            )
        
        @reactive.Effect
        @reactive.event(input[f"add_timesheet_{dept}_submit"])
        def _(dept=dept):
            date = input["date"]()
            country_name = re.sub("[()']", "", ", ".join(map(str, input["country_name"]()))).strip(",")
            sal_attendees = re.sub("[()']", "", ", ".join(map(str, input["sal_attendees"]()))).strip(",")
            country_attendees = input["country_attendees"]()
            support_name = input["support_name"]()
            description = input["description"]()
            hours = input["hours"]()

            try:
                db.insert_row(
                    "timesheet", {
                        "department_code": dept,
                        "date": date,
                        "country_name": country_name,
                        "sal_attendees": sal_attendees,
                        "country_attendees": country_attendees,
                        "support_name": support_name,
                        "description": description,
                        "hours": hours
                    }
                )
                ui.notification_show(f"Timesheet entry added successfully for {sal_attendees}!", type="success")
            except Exception as e:
                ui.notification_show(f"Error adding timesheet entry: {e}", type="error")
            finally:
                data_trigger.set(data_trigger.get() + 1)
        
        @reactive.Effect
        @reactive.event(input[f"edit_timesheet_{dept}_btn_"])
        def _(dept=dept):
            selected_rows = timesheet_table_renderers[dept].data_view(selected=True)

            if selected_rows.shape[0] == 0:
                ui.notification_show("Please select a row to edit.", type="warning")
                return
            if selected_rows.shape[0] > 1:
                ui.notification_show("Please select only one row to edit.", type="warning")
                return
            try:
                id_to_edit = selected_rows.get_column("id").to_list()[0]
                ui.modal_show(
                    ui.modal(
                        ui.input_date("edit_date", "Date", value=selected_rows.get_column("date").to_list()[0].date()),
                        ui.input_selectize("edit_country_name", "Country(ies)", choices=db.read_table("countries").select(pl.col("name")).to_series().to_list(), multiple=True, selected=selected_rows.get_column("country_name").to_list()[0].split(", ")),
                        ui.input_selectize("edit_sal_attendees", "Advisor(s)", choices=db.read_table("advisors", where=f"department_code = '{dept}' AND active = 'true'").select(pl.col("short_name")).to_series().to_list(), multiple=True, selected=selected_rows.get_column("sal_attendees").to_list()[0].split(", ")),
                        ui.input_text_area("edit_country_attendees", "Country Attendee(s)", placeholder="Comma separated list of names", value=selected_rows.get_column("country_attendees").to_list()[0]),
                        ui.input_selectize("edit_support_name", "Type of Support", choices=db.read_table("support").select(pl.col("name")).to_series().to_list(), selected=selected_rows.get_column("support_name").to_list()[0]),
                        ui.input_text_area("edit_description", "Description", placeholder="Additional details, e.g., monthly catch-up, training topics, etc.", value=selected_rows.get_column("description").to_list()[0]),
                        ui.input_numeric("edit_hours", "Hours", min=0.5, max=8, step=0.5, value=selected_rows.get_column("hours").to_list()[0]),
                        ui.modal_button("Cancel"),
                        ui.input_action_button(f"edit_timesheet_{dept}_submit", "Submit", class_="btn btn-primary"),
                        title="Edit Timesheet Entry",
                        easy_close=True,
                        fade=True,
                        footer=None
                    )
                )
            except Exception as e:
                ui.notification_show(f"Error preparing edit modal: {e}", type="error")
            
            @reactive.Effect
            @reactive.event(input[f"edit_timesheet_{dept}_submit"])
            def _(id_to_edit=id_to_edit):
                date = input["edit_date"]()
                country_name = re.sub("[()']", "", ", ".join(map(str, input["edit_country_name"]()))).strip(",")#input["country_name"]()
                sal_attendees = re.sub("[()']", "", ", ".join(map(str, input["edit_sal_attendees"]()))).strip(",")#input["sal_attendees"]()
                country_attendees = input["edit_country_attendees"]()
                support_name = input["edit_support_name"]()
                description = input["edit_description"]()
                hours = input["edit_hours"]()

                try:
                    db.update_row(
                        "timesheet",
                        {
                            "date": date,
                            "country_name": country_name,
                            "sal_attendees": sal_attendees,
                            "country_attendees": country_attendees,
                            "support_name": support_name,
                            "description": description,
                            "hours": hours
                        },
                        where=f"id = {id_to_edit}"
                    )
                    ui.notification_show(f"Timesheet entry updated successfully!", type="success")
                except Exception as e:
                    ui.notification_show(f"Error updating timesheet entry: {e}", type="error")
                finally:
                    ui.modal_remove()
                    data_trigger.set(data_trigger.get() + 1)
        
        @reactive.Effect
        @reactive.event(input[f"delete_timesheet_{dept}_btn_"])
        def _(dept=dept):
            selected_rows = timesheet_table_renderers[dept].data_view(selected=True)
            
            if selected_rows.shape[0] == 0:
                ui.notification_show("Please select a row to delete.", type="warning")
                return
            if selected_rows.shape[0] > 1:
                ui.notification_show("Please select only one row to delete.", type="warning")
                return
            try:
                id_to_delete = selected_rows.get_column("id").to_list()[0]
                country_name = selected_rows.get_column("country_name").to_list()[0]
                ui.modal_show(
                    ui.modal(
                        ui.p(f"Are you sure you want to delete the timesheet entry for {country_name}?"),
                        ui.modal_button("Cancel"),
                        ui.input_action_button(f"delete_timesheet_{dept}_submit", "Delete", class_="btn btn-danger"),
                        title="Confirm Deletion",
                        easy_close=True,
                        fade=True,
                        footer=None
                    )
                )
            except Exception as e:
                ui.notification_show(f"Error preparing delete modal: {e}", type="error")
            
            @reactive.Effect
            @reactive.event(input[f"delete_timesheet_{dept}_submit"])
            def _(id_to_delete=id_to_delete, country_name=country_name):
                ui.modal_remove()
                try:
                    db.delete_row(
                        "timesheet",
                        where=f"id = {id_to_delete}"
                    )
                    ui.notification_show(f"Timesheet entry deleted successfully for {country_name}!", type="success")
                except Exception as e:
                    ui.notification_show(f"Error deleting timesheet entry: {e}", type="error")
                finally:
                    data_trigger.set(data_trigger.get() + 1)
        
        # ---- Countries
        @output(id=f"allocations_{dept}_map")
        @render_widget
        def _allocations_map(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            countries = db.read_table("countries")
            advisors = db.read_table("advisors", where=f"department_code = '{dept}' AND active = 'true'")
                        
            allocations = (
                advisors
                .with_columns(pl.col("country_codes").str.split(", "))
                .explode("country_codes")
            ).select(["short_name", "country_codes"])

            allocations = allocations.join(countries, left_on="country_codes", right_on="iso_alpha3_code", how="left").select(["short_name", "name"]).rename({"name":"country_name"})

            fig = px.choropleth(
                allocations,
                locations="country_name",
                locationmode="country names",
                color="short_name",
                hover_name="country_name",
                hover_data={"country_name":False, "short_name":True},
                labels={"short_name":"Advisor"},
                color_discrete_map=dict(zip(advisors.get_column("short_name").to_list(), advisors.get_column("colour").to_list())),
                title=f"Country allocations by advisor (as of {date.today().year})"
            )
            fig.update_geos(showcountries=True, showcoastlines=True, showland=True, fitbounds="locations")
            fig.update_layout(coloraxis_showscale=False)

            return fig
        
        @output(id=f"country_focals_{dept}_country_filter")
        @render.ui
        def _country_focals_country_filter(dept=dept):
            country_focals = db.read_table("country_focals", where=f"department_code = '{dept}'")
            countries = country_focals.select(pl.col("country_name")).unique().sort("country_name").to_series().to_list()
            return ui.input_select(
                f"country_focals_{dept}_country_filter_",
                "Select Country",
                choices=["All"] + countries,
                selected="All",
                width="150px"
            )

        @output(id=f"country_focals_{dept}_table")
        @render.ui
        def _country_focals_table(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity

            country_focals = db.read_table("country_focals", where=f"department_code = '{dept}'")

            # Apply country filter            
            selected_country = input[f"country_focals_{dept}_country_filter_"]()
            if selected_country and selected_country != "All":
                country_focals = country_focals.filter(pl.col("country_name") == selected_country) 

            col_to_show = ["name","country_name","role","email"]
            table = (
                GT(country_focals.select(col_to_show))
                .cols_move_to_start(["country_name"])
                .tab_options(container_height="350px")
            )
            return table
        
        @output(id=f"add_country_focal_{dept}_btn")
        @render.ui
        def _add_country_focal_btn(dept=dept):
            return ui.input_action_button(
                f"add_country_focal_{dept}_btn_",
                "Add row",
                class_="btn btn-success btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-plus")
            )

        @output(id=f"edit_country_focal_{dept}_btn")
        @render.ui
        def _edit_country_focal_btn(dept=dept):
            return ui.input_action_button(
                f"edit_country_focal_{dept}_btn_",
                "Edit row",
                class_="btn btn-warning btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-day")
            )

        @output(id=f"delete_country_focal_{dept}_btn")
        @render.ui
        def _delete_country_focal_btn(dept=dept):
            return ui.input_action_button(
                f"delete_country_focal_{dept}_btn_",
                "Delete row",
                class_="btn btn-danger btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-xmark")
            )

        @output(id=f"country_focals_{dept}_table_editable")
        @render.data_frame
        def _country_focals_table_editable(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            country_focals = db.read_table("country_focals", where=f"department_code = '{dept}'")
            return render.DataGrid(
                country_focals,
                height="400px",
                selection_mode="rows"
            )
        
        # Keep a reference to the country focals table for use in other reactive contexts
        country_focals_table_renderers[dept] = _country_focals_table_editable

        @reactive.Effect
        @reactive.event(input[f"add_country_focal_{dept}_btn_"])
        def _(dept=dept):
            ui.modal_show(
                ui.modal(
                    ui.input_text("name", "Name"),
                    ui.input_selectize("country_name", "Country", choices=db.read_table("countries").select(pl.col("name")).to_series().to_list()),
                    ui.input_text("role", "Role/Title"),
                    ui.input_text("email", "Email"),
                    ui.modal_button("Cancel"),
                    ui.input_action_button(f"add_country_focal_{dept}_submit", "Submit", class_="btn btn-primary"),
                    title="Add Country Focal Entry",
                    easy_close=True,
                    fade=True,
                    footer=None
                )
            )
        
        @reactive.Effect
        @reactive.event(input[f"add_country_focal_{dept}_submit"])
        def _(dept=dept):
            new_focal = {
                "department_code": dept,
                "name": input["name"](),
                "country_name": input["country_name"](),
                "role": input["role"](),
                "email": input["email"]()
            }

            try:
                if not new_focal["name"] or not new_focal["country_name"]:
                    ui.notification_show("Error adding focal point: Name and Country are required fields.", type="error")
                    raise ValueError("Name and Country are required fields.")
                if not re.match(r"[^@]+@[^@]+\.[^@]+", new_focal["email"]):
                    ui.notification_show(f"Error adding focal point: Email must be a valid email address.", type="error")
                    raise ValueError("Email must be a valid email address.")
            except ValueError as ve:
                ui.notification_show(f"Error adding focal point: {ve}", type="error")
                return
            finally:
                ui.modal_remove()
                data_trigger.set(data_trigger.get() + 1)
            
            db.insert("country_focals", new_focal)
        
        @reactive.Effect
        @reactive.event(input[f"edit_country_focal_{dept}_btn_"])
        def _(dept=dept):
            selected_rows = country_focals_table_renderers[dept].data_view(selected=True)

            if selected_rows.shape[0] == 0:
                ui.notification_show("Please select a row to edit.", type="warning")
                return
            if selected_rows.shape[0] > 1:
                ui.notification_show("Please select only one row to edit.", type="warning")
                return
            try:
                id_to_edit = selected_rows.get_column("id").to_list()[0]
                ui.modal_show(
                    ui.modal(
                        ui.input_text("edit_name", "Name", value=selected_rows.get_column("name").to_list()[0]),
                        ui.input_selectize("edit_country_name", "Country", choices=db.read_table("countries").select(pl.col("name")).to_series().to_list(), selected=selected_rows.get_column("country_name").to_list()[0]),
                        ui.input_text("edit_role", "Role/Title", value=selected_rows.get_column("role").to_list()[0]),
                        ui.input_text("edit_email", "Email", value=selected_rows.get_column("email").to_list()[0]),
                        ui.modal_button("Cancel"),
                        ui.input_action_button(f"edit_country_focal_{dept}_submit", "Submit", class_="btn btn-primary"),
                        title="Edit Country Focal Entry",
                        easy_close=True,
                        fade=True,
                        footer=None
                    )
                )
            except Exception as e:
                ui.notification_show(f"Error preparing edit modal: {e}", type="error")
            
            @reactive.Effect
            @reactive.event(input[f"edit_country_focal_{dept}_submit"])
            def _(id_to_edit=id_to_edit):
                updated_focal = {
                    "name": input["edit_name"](),
                    "country_name": input["edit_country_name"](),
                    "role": input["edit_role"](),
                    "email": input["edit_email"]()
                }

                try:
                    if not updated_focal["name"] or not updated_focal["country_name"]:
                        ui.notification_show("Error adding focal point: Name and Country are required fields.", type="error")
                        raise ValueError("Name and Country are required fields.")
                    if not re.match(r"[^@]+@[^@]+\.[^@]+", updated_focal["email"]):
                        ui.notification_show(f"Error adding focal point: Email must be a valid email address.", type="error")
                        raise ValueError("Email must be a valid email address.")          
                    db.update_row("country_focals", updates=updated_focal, where=f"id = {id_to_edit}")
                    ui.notification_show(f"Country focal entry updated successfully!", type="success")
                except Exception as e:
                    ui.notification_show(f"Error updating country focal entry: {e}", type="error")
                finally:
                    ui.modal_remove()
                    data_trigger.set(data_trigger.get() + 1)
        
        @reactive.Effect
        @reactive.event(input[f"delete_country_focal_{dept}_btn_"])
        def _(dept=dept):
            selected_rows = country_focals_table_renderers[dept].data_view(selected=True)
            
            if selected_rows.shape[0] == 0:
                ui.notification_show("Please select a row to delete.", type="warning")
                return
            if selected_rows.shape[0] > 1:
                ui.notification_show("Please select only one row to delete.", type="warning")
                return
            try:
                id_to_delete = selected_rows.get_column("id").to_list()[0]
                country_name = selected_rows.get_column("country_name").to_list()[0]
                ui.modal_show(
                    ui.modal(
                        ui.p(f"Are you sure you want to delete the country focal entry for {country_name}?"),
                        ui.modal_button("Cancel"),
                        ui.input_action_button(f"delete_country_focal_{dept}_submit", "Delete", class_="btn btn-danger"),
                        title="Confirm Deletion",
                        easy_close=True,
                        fade=True,
                        footer=None
                    )
                )
            except Exception as e:
                ui.notification_show(f"Error preparing delete modal: {e}", type="error")
            
            @reactive.Effect
            @reactive.event(input[f"delete_country_focal_{dept}_submit"])
            def _(id_to_delete=id_to_delete, country_name=country_name):
                ui.modal_remove()
                try:
                    db.delete_row(
                        "country_focals",
                        where=f"id = {id_to_delete}"
                    )
                    ui.notification_show(f"Country focal entry deleted successfully for {country_name}!", type="success")
                except Exception as e:
                    ui.notification_show(f"Error deleting country focal entry: {e}", type="error")
                finally:
                    data_trigger.set(data_trigger.get() + 1)

        #  ----- Proposals
        @output(id=f"proposal_{dept}_insights_year_filter")
        @render.ui
        def _proposal_insights_year_filter(dept=dept):
            proposals = db.read_table("proposals", where=f"department_code = '{dept}'")
            years = proposals.select(pl.col("date_submission").dt.year().alias("year")).unique().sort("year").to_series().to_list()
            return ui.input_select(
                f"proposal_{dept}_insights_year_filter_",
                "Select Year",
                choices=years,
                selected=years[-1] if years else None,
                width="150px"
            )
        
        @output(id=f"proposal_{dept}_insights_country_filter")
        @render.ui
        def _proposal_insights_country_filter(dept=dept):
            selected_year = int(input[f"proposal_{dept}_insights_year_filter_"]())
            proposals = db.read_table("proposals", where=f"department_code = '{dept}'")
            countries = proposals.filter(pl.col("date_submission").dt.year() == selected_year).select(pl.col("country_name")).unique().sort("country_name").to_series().to_list()
            
            return ui.input_select(
                f"proposal_{dept}_insights_country_filter_",
                "Select Country",
                choices=["All"] + countries,
                selected="All",
                width="150px"
            )
        
        @output(id=f"proposal_{dept}_insights_timeline")
        @render_widget
        def _proposal_insights_timeline(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            proposals = db.read_table("proposals", where=f"department_code = '{dept}'")

            # Apply filters
            selected_year = int(input[f"proposal_{dept}_insights_year_filter_"]())
            selected_country = input[f"proposal_{dept}_insights_country_filter_"]()
            if selected_year:
                proposals = proposals.filter(pl.col("date_submission").dt.year() == selected_year)
            if selected_country and selected_country != "All":
                # Transform country_name to handle multiple countries
                proposals = proposals.filter(pl.col("country_name") == selected_country)

            # Extract month
            proposals = proposals.with_columns(pl.col("date_submission").dt.month().alias("month"))
            result_map = {True:"win", False:"lost"}
            proposals = proposals.with_columns(
                pl.col("result").replace(result_map)
            ).with_columns(pl.col("result").fill_null("pending"))

            # Aggregate data
            MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            insights = (
                proposals
                .group_by(["month", "result"])
                .agg(pl.col("result").count().alias("total"))
            )        
            
            fig = px.bar(
                insights,
                x="month",
                y="total",
                color="result",
                labels={"month":"", "total":"Total proposals/concept notes"},
                color_discrete_sequence=px.colors.sequential.Reds,
                title=f"Monthly proposals / concept notes" + (f" for {selected_country}" if selected_country and selected_country != "All" else "") + f" ({selected_year})"
            ).update_xaxes(
                tickvals=insights['month'].unique(),
                ticktext=[MONTHS[i-1] for i in insights['month'].unique()]
            )
            return fig
        
        @output(id=f"proposal_{dept}_insights_pie_chart")
        @render_widget
        def _proposal_insights_pie_chart(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            proposals = db.read_table("proposals", where=f"department_code = '{dept}'")
            # Apply filters
            selected_year = int(input[f"proposal_{dept}_insights_year_filter_"]())
            selected_country = input[f"proposal_{dept}_insights_country_filter_"]()
            if selected_year:
                proposals = proposals.filter(pl.col("date_submission").dt.year() == selected_year)
            if selected_country and selected_country != "All":
                proposals = proposals.filter(pl.col("country_name") == selected_country)            

            result_map = {True:"win", False:"lost"}
            proposals = proposals.with_columns(
                pl.col("result").replace(result_map)
            ).with_columns(pl.col("result").fill_null("pending"))

            # Aggregate data
            insights = (
                proposals
                .group_by(["result"])
                .agg(pl.col("result").count().alias("total"))
            )

            fig = px.pie(
                insights,
                names="result",
                values="total",
                color_discrete_sequence=px.colors.sequential.Reds,
                title=f"Proposals / concept notes" + (f" for {selected_country}" if selected_country and selected_country != "All" else "") + f" ({selected_year})"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')

            return fig


        @output(id=f"add_proposal_{dept}_btn")
        @render.ui
        def _add_proposal_btn(dept=dept):
            return ui.input_action_button(
                f"add_proposal_{dept}_btn_",
                "Add row",
                class_="btn btn-success btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-plus")
            )

        @output(id=f"edit_proposal_{dept}_btn")
        @render.ui
        def _edit_proposal_btn(dept=dept):
            return ui.input_action_button(
                f"edit_proposal_{dept}_btn_",
                "Edit row",
                class_="btn btn-warning btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-day")
            )

        @output(id=f"delete_proposal_{dept}_btn")
        @render.ui
        def _delete_proposal_btn(dept=dept):
            return ui.input_action_button(
                f"delete_proposal_{dept}_btn_",
                "Delete row",
                class_="btn btn-danger btn-sm",
                width="130px",
                icon=fa.icon_svg("calendar-xmark")
            )

        @output(id=f"proposals_{dept}_table")
        @render.data_frame
        def _proposals_table(dept=dept):
            # Use data_trigger to refresh the table when it changes
            data_trigger.get()  # Trigger reactivity
            proposals = db.read_table("proposals", where=f"department_code = '{dept}'").sort(by="id", descending=True)
            return render.DataGrid(
                proposals,
                height="400px",
                selection_mode="rows"
            )
        
        # Keep a reference to the proposals table for use in other reactive contexts
        proposal_table_renderers[dept] = _proposals_table

        @reactive.Effect
        @reactive.event(input[f"add_proposal_{dept}_btn_"])
        def _(dept=dept):
            ui.modal_show(
                ui.modal(
                    ui.input_selectize("type", "Type", choices=['proposal', 'concept note']),
                    ui.input_selectize("country_name", "Country", choices=db.read_table("countries").select(pl.col("name")).to_series().to_list()),
                    ui.input_text("donor", "Donor"),
                    ui.input_date("date_submission", "Date submission", value=date.today()),
                    ui.input_switch("result", "Result (tick for win)", value=False),
                    ui.input_selectize("sal_support", "Advisor(s)", choices=db.read_table("advisors", where=f"department_code = '{dept}' AND active = 'true'").select(pl.col("short_name")).to_series().to_list(), multiple=True),
                    ui.input_text("country_focal", "Country focal(s)"),
                    ui.input_text_area("description", "Description", placeholder="Add details and reference to GMS if available"),
                    ui.modal_button("Cancel"),
                    ui.input_action_button(f"add_timesheet_{dept}_submit", "Submit", class_="btn btn-primary"),
                    title="Add Proposal Entry",
                    easy_close=True,
                    fade=True,
                    footer=None
                )
            )
        
        @reactive.Effect
        @reactive.event(input[f"add_proposal_{dept}_submit"])
        def _(dept=dept):
            type = input["type"]()
            country_name = input["country_name"]()
            donor = input["donor"]()
            date_submission = input["date_submission"]()
            result = input["result"]()
            sal_support = re.sub("[()']", "", ", ".join(map(str, input["sal_support"]()))).strip(",")
            country_focal = input["country_focal"]()
            description = input["description"]()

            try:
                db.insert_row(
                    "proposals", {
                        "department_code": dept,
                        "type": type,
                        "country_name": country_name,
                        "donor": donor,
                        "date_submission": date_submission,
                        "result": result,
                        "sal_support": sal_support,
                        "country_focal": country_focal,
                        "description": description
                    }
                )
                ui.notification_show(f"Proposal entry added successfully for {country_name}!", type="success")
            except Exception as e:
                ui.notification_show(f"Error adding proposal entry: {e}", type="error")
            finally:
                data_trigger.set(data_trigger.get() + 1)
        
        @reactive.Effect
        @reactive.event(input[f"edit_proposal_{dept}_btn_"])
        def _(dept=dept):
            selected_rows = proposal_table_renderers[dept].data_view(selected=True)

            if selected_rows.shape[0] == 0:
                ui.notification_show("Please select a row to edit.", type="warning")
                return
            if selected_rows.shape[0] > 1:
                ui.notification_show("Please select only one row to edit.", type="warning")
                return
            try:
                id_to_edit = selected_rows.get_column("id").to_list()[0]
                ui.modal_show(
                    ui.modal(
                        ui.input_selectize("edit_type", "Type", choices=['proposal', 'concept note'], selected=selected_rows.get_column("type").to_list()[0]),
                        ui.input_selectize("edit_country_name", "Country", choices=db.read_table("countries").select(pl.col("name")).to_series().to_list(), selected=selected_rows.get_column("country_name").to_list()[0]),
                        ui.input_text("edit_donor", "Donor", value=selected_rows.get_column("donor").to_list()[0]),
                        ui.input_date("edit_date_submission", "Date submission", value=selected_rows.get_column("date_submission").to_list()[0]),
                        ui.input_switch("edit_result", "Result (tick for win)", value=selected_rows.get_column("result").to_list()[0]),
                        ui.input_selectize("edit_sal_support", "Advisor(s)", choices=db.read_table("advisors", where=f"department_code = '{dept}' AND active = 'true'").select(pl.col("short_name")).to_series().to_list(), multiple=True, selected=selected_rows.get_column("sal_support").to_list()[0].split(", ")),
                        ui.input_text("edit_country_focal", "Country focal(s)", value=selected_rows.get_column("country_focal").to_list()[0]),
                        ui.input_text_area("edit_description", "Description", value=selected_rows.get_column("description").to_list()[0]),
                        ui.modal_button("Cancel"),
                        ui.input_action_button(f"edit_proposal_{dept}_submit", "Submit", class_="btn btn-primary"),
                        title="Edit Proposal Entry",
                        easy_close=True,
                        fade=True,
                        footer=None
                    )
                )
            except Exception as e:
                ui.notification_show(f"Error preparing edit modal: {e}", type="error")
            
            @reactive.Effect
            @reactive.event(input[f"edit_proposal_{dept}_submit"])
            def _(id_to_edit=id_to_edit):
                type = input["edit_type"]()
                country_name = input["edit_country_name"]()
                donor = input["edit_donor"]()
                date_submission = input["edit_date_submission"]()
                result = input["edit_result"]()
                sal_support = re.sub("[()']", "", ", ".join(map(str, input["edit_sal_support"]()))).strip(",")
                country_focal = input["edit_country_focal"]()
                description = input["edit_description"]()

                try:
                    db.update_row(
                        "proposals",
                        {
                            "type": type,
                            "country_name": country_name,
                            "donor": donor,
                            "date_submission": date_submission,
                            "result": result,
                            "sal_support": sal_support,
                            "country_focal": country_focal,
                            "description": description
                        },
                        where=f"id = {id_to_edit}"
                    )
                    ui.notification_show(f"Proposal entry updated successfully!", type="success")
                except Exception as e:
                    ui.notification_show(f"Error updating proposal entry: {e}", type="error")
                finally:
                    ui.modal_remove()
                    data_trigger.set(data_trigger.get() + 1)
        
        @reactive.Effect
        @reactive.event(input[f"delete_proposal_{dept}_btn_"])
        def _(dept=dept):
            selected_rows = proposal_table_renderers[dept].data_view(selected=True)
            
            if selected_rows.shape[0] == 0:
                ui.notification_show("Please select a row to delete.", type="warning")
                return
            if selected_rows.shape[0] > 1:
                ui.notification_show("Please select only one row to delete.", type="warning")
                return
            try:
                id_to_delete = selected_rows.get_column("id").to_list()[0]
                country_name = selected_rows.get_column("country_name").to_list()[0]
                ui.modal_show(
                    ui.modal(
                        ui.p(f"Are you sure you want to delete the proposal entry for {country_name}?"),
                        ui.modal_button("Cancel"),
                        ui.input_action_button(f"delete_proposal_{dept}_submit", "Delete", class_="btn btn-danger"),
                        title="Confirm Deletion",
                        easy_close=True,
                        fade=True,
                        footer=None
                    )
                )
            except Exception as e:
                ui.notification_show(f"Error preparing delete modal: {e}", type="error")
            
            @reactive.Effect
            @reactive.event(input[f"delete_proposal_{dept}_submit"])
            def _(id_to_delete=id_to_delete, country_name=country_name):
                ui.modal_remove()
                try:
                    db.delete_row(
                        "proposals",
                        where=f"id = {id_to_delete}"
                    )
                    ui.notification_show(f"Proposal entry deleted successfully for {country_name}!", type="success")
                except Exception as e:
                    ui.notification_show(f"Error deleting proposal entry: {e}", type="error")
                finally:
                    data_trigger.set(data_trigger.get() + 1)




app = App(app_ui, server, debug=False)
