import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.main import (
    health,
    serve_donor_dashboard,
    serve_ngo_dashboard,
    get_donations,
    get_ngos,
    create_donation,
    donations_priority,
    match_donations,
    claim_donation,
    safety_check,
    get_donation_safety,
    get_tracking,
    update_tracking,
    analytics_summary,
    analytics_food_types,
    analytics_tracking,
    analytics_safety,
    NewDonationRequest,
    UpdateTrackingRequest,
)

def run_tests():
    print("=== STARTING DIRECT INTEGRATION TESTS ===")

    # 1. Health check
    h_res = health()
    assert h_res["status"] == "ok", "Health check failed"
    print("[PASS] health() ->", h_res)

    # 2. HTML Dashboards
    donor_html = serve_donor_dashboard()
    assert "Donor Dashboard" in donor_html, "Donor dashboard template serving failed"
    print("[PASS] serve_donor_dashboard()")

    ngo_html = serve_ngo_dashboard()
    assert "NGO Dashboard" in ngo_html, "NGO dashboard template serving failed"
    print("[PASS] serve_ngo_dashboard()")

    # 3. Donations list & priority
    donations = get_donations()
    assert isinstance(donations, list), "get_donations failed"
    print(f"[PASS] get_donations() -> {len(donations)} records")

    priority = donations_priority()
    assert isinstance(priority, list), "donations_priority failed"
    print(f"[PASS] donations_priority() -> {len(priority)} records")

    # 4. NGOs demand scoring
    ngos = get_ngos()
    assert isinstance(ngos, list), "get_ngos failed"
    print(f"[PASS] get_ngos() -> {len(ngos)} NGOs scored")

    # 5. Create new donation across all select food types
    food_types_to_test = ["cooked_meal", "packaged_food", "fruits", "vegetables", "snacks", "beverages", "other", "bakery_items", "dairy_products"]
    created_id = None
    for ft in food_types_to_test:
        new_don_req = NewDonationRequest(
            food_type=ft,
            quantity=60,
            latitude=26.9124,
            longitude=75.7873,
            hours_until_expiry=4.5,
            unit="meals",
            donor_type="restaurant",
            vegetarian=1,
            vegan=0,
            strict_bounds=False,
        )
        don_res = create_donation(new_don_req)
        created_id = don_res["donation"]["donation_id"]
        candidates = don_res.get("candidate_matches", [])
        assert len(candidates) > 0, f"No candidate matches returned for food_type={ft}"
        print(f"[PASS] create_donation('{ft}') -> ID: {created_id}, Best Match: {don_res.get('best_match', {}).get('ngo_name', 'N/A')}, Candidates: {len(candidates)}")

    # 6. Safety check API
    saf_chk = safety_check(hours_until_expiry=4.5, donation_id=created_id)
    assert saf_chk["status"] == "WARNING", f"Safety check status mismatch: {saf_chk}"
    print(f"[PASS] safety_check() -> {saf_chk['status']}: {saf_chk['message']}")

    saf_don = get_donation_safety(created_id)
    assert saf_don["donation_id"] == created_id, "Donation safety lookup failed"
    print(f"[PASS] get_donation_safety('{created_id}') -> Status: {saf_don['status']}")

    # 7. Live Tracking API
    tr_get = get_tracking(created_id)
    print(f"[PASS] get_tracking('{created_id}') -> Status: {tr_get['tracking_status']}")

    tr_upd = update_tracking(created_id, UpdateTrackingRequest(status="ASSIGNED"))
    assert tr_upd["tracking_status"] == "ASSIGNED", "Tracking update failed"
    print(f"[PASS] update_tracking('{created_id}') -> Updated to ASSIGNED")

    # 8. Analytics APIs
    an_sum = analytics_summary()
    assert "total_donations" in an_sum, "Analytics summary failed"
    print(f"[PASS] analytics_summary() -> Total donations: {an_sum['total_donations']}")

    an_ft = analytics_food_types()
    print(f"[PASS] analytics_food_types() -> {len(an_ft)} food categories")

    an_tr = analytics_tracking()
    print(f"[PASS] analytics_tracking() -> {an_tr}")

    an_sf = analytics_safety()
    print(f"[PASS] analytics_safety() -> {an_sf}")

    # 9. Matching API
    match_res = match_donations()
    assert "matches" in match_res, "match_donations failed"
    print(f"[PASS] match_donations() -> Matched: {match_res['matched_count']}")

    # 10. Claim donation API
    claim_res = claim_donation(created_id)
    print(f"[PASS] claim_donation('{created_id}') -> {claim_res['message']}")

    print("\n========================================================")
    print("ALL INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
    print("========================================================")

if __name__ == "__main__":
    run_tests()
