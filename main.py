import pandas as pd

from src.matching_engine import (
    find_eligible_ngos,
    add_distances,
    calculate_final_score
)


# Load data
donations = pd.read_csv("data/donations.csv")
ngos = pd.read_csv("data/ngos.csv")


# Remove accidental spaces from column names
donations.columns = donations.columns.str.strip()
ngos.columns = ngos.columns.str.strip()


print("=" * 50)
print("AI FOOD DONATION MATCH")
print("=" * 50)


# Process every donation
for _, donation in donations.iterrows():

    # Find eligible NGOs
    eligible_ngos = find_eligible_ngos(
        donation,
        ngos
    )

    # If no NGO is eligible
    if eligible_ngos.empty:
        print(
            f"\nNo eligible NGO found for "
            f"{donation['donation_id']}"
        )
        continue


    # Calculate distance
    eligible_ngos = add_distances(
        donation,
        eligible_ngos
    )


    # Calculate final score
    eligible_ngos = calculate_final_score(
        donation,
        eligible_ngos
    )


    # Rank NGOs
    ranked_ngos = eligible_ngos.sort_values(
        "final_score",
        ascending=False
    )


    # Best match
    best_match = ranked_ngos.iloc[0]


    print("\n")
    print("=" * 50)
    print("AI FOOD DONATION MATCH")
    print("=" * 50)

    print(f"\nDonation: {donation['donation_id']}")
    print(f"Food Type: {donation['food_type']}")
    print(f"Quantity: {donation['quantity']} {donation['unit']}")
    print(f"Expiry: {donation['hours_until_expiry']} hours")


    print("\nBEST NGO MATCH")
    print("-" * 45)

    print(f"NGO: {best_match['ngo_name']}")
    print(f"Match Score: {best_match['final_score']:.2f}%")
    print(f"Distance: {best_match['distance_km']:.2f} km")

    # Show demand safely depending on donation unit
    if donation["unit"] == "meals":
        print(
            f"Current Demand: "
            f"{best_match.get('current_demand_meals', 'N/A')} meals"
        )

    elif donation["unit"] == "kg":
        print(
            f"Current Demand: "
            f"{best_match.get('current_demand_kg', 'N/A')} kg"
        )

    print(f"Reliability Score: {best_match['reliability_score']}")