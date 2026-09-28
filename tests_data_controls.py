"""Aceite dos controles observados na amostra do cliente (sem alterar entradas)."""

from pathlib import Path
import duckdb


db = Path(__file__).resolve().parent / "output/canonical.duckdb"
con = duckdb.connect(str(db), read_only=True)
issues = dict(con.execute("""
    select issue, count(*) from int_transaction_integrity,
         unnest(integrity_issues) u(issue) group by issue
""").fetchall())
assert issues == {"brl_local_amount_mismatch": 2, "dropoff_before_request": 2,
                  "ride_after_report_date": 1}, issues
assert con.execute("select count(*) from int_transaction_enrichment where employment_at_ride_status='after_termination'").fetchone()[0] == 3
assert con.execute("select count(*) from int_eats_orders").fetchone()[0] == 72
assert con.execute("select count(*) from compliance_transaction_flags where eats_order_cap_assessment='policy_violation_eats_order_cap'").fetchone()[0] == 4
assert con.execute("select count(*) from compliance_transaction_flags where weekend_policy_status='policy_violation_weekend_program'").fetchone()[0] == 6
assert con.execute("select count(*) from ap_titulos").fetchone()[0] == 0
assert con.execute("select count(*) from ap_rateios").fetchone()[0] == 0
assert con.execute("select count(*) from int_ap_component_candidates where expense_code='ENTRE-UN' and official_cost_center in ('CC300','CC310') and not list_contains(component_blockers,'cost_expense_classification_pending')").fetchone()[0] == 0
assert con.execute("select count(*) from int_ap_component_candidates where employment_at_ride_status='within_employment_period' and (list_contains(component_blockers,'employee_link_employee_inactive') or list_contains(component_blockers,'stage3_gate:inactive_or_suspended'))").fetchone()[0] == 0
assert [[str(x) for x in row] for row in con.execute(
    "select charge_residual, fee_residual from int_statement_detail_reconciliation order by competence"
).fetchall()] == [["110.02", "0.00"], ["104.56", "0.00"]]
print("data_controls=PASS")
