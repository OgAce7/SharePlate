// ==========================================
// CONFIGURATION
// ==========================================

const API_BASE_URL = "http://127.0.0.1:8001";


// ==========================================
// DONOR DASHBOARD - GET LOCATION
// ==========================================

function getLocation() {

    const status = document.getElementById("locationStatus");

    if (!status) {
        return;
    }

    if (!navigator.geolocation) {
        status.textContent =
            "Location services are not supported by your browser.";
        return;
    }

    status.textContent =
        "📍 Detecting your location...";

    navigator.geolocation.getCurrentPosition(

        function(position) {

            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            document.getElementById("latitude").value = latitude;
            document.getElementById("longitude").value = longitude;

            status.textContent =
                "✓ Location detected successfully";

            status.classList.add("success");

            console.log("Latitude:", latitude);
            console.log("Longitude:", longitude);
        },

        function(error) {

            if (error.code === error.PERMISSION_DENIED) {

                status.textContent =
                    "Location permission denied. Please allow location access.";

            } else {

                status.textContent =
                    "Unable to detect your location. Please try again.";
            }
        }
    );
}


// ==========================================
// DONOR DASHBOARD - FORM SUBMISSION
// ==========================================

const donationForm =
    document.getElementById("donationForm");

if (donationForm) {

    donationForm.addEventListener("submit", async function(event) {

        event.preventDefault();

        const foodType =
            document.getElementById("food_type").value;

        const quantity =
            Number(document.getElementById("quantity").value);

        const unit =
            document.getElementById("unit").value;

        const safeUntil =
            document.getElementById("safe_until").value;

        const latitude =
            Number(document.getElementById("latitude").value);

        const longitude =
            Number(document.getElementById("longitude").value);

        const vegetarian =
            document.getElementById("vegetarian").checked ? 1 : 0;

        const vegan =
            document.getElementById("vegan").checked ? 1 : 0;

        // Check location

        if (!latitude || !longitude) {

            alert(
                "Please detect your location first."
            );

            return;
        }

        // Check expiry

        if (!safeUntil) {

            alert(
                "Please select when the food will be safe until."
            );

            return;
        }

        // Calculate hours until expiry

        const expiryTime =
            new Date(safeUntil);

        const currentTime =
            new Date();

        const hoursUntilExpiry =
            (expiryTime - currentTime) / (1000 * 60 * 60);

        if (hoursUntilExpiry <= 0) {

            alert(
                "The expiry time must be in the future."
            );

            return;
        }

        // Show temporary status

        showMatchLoading();

        // Data expected by backend

        const donation = {

            food_type: foodType,

            quantity: quantity,

            latitude: latitude,

            longitude: longitude,

            hours_until_expiry: Number(
                hoursUntilExpiry.toFixed(2)
            ),

            unit: unit,

            donor_type: "restaurant",

            vegetarian: vegetarian,

            vegan: vegan,

            strict_bounds: false
        };

        console.log(
            "Sending donation to backend:"
        );

        console.log(donation);

        try {

            // ==========================================
            // STEP 1: REGISTER DONATION
            // ==========================================

            const donationResponse =
                await fetch(
                    `${API_BASE_URL}/donations`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(donation)
                    }
                );

            const donationData =
                await donationResponse.json();

            if (!donationResponse.ok) {

                throw new Error(
                    donationData.detail ||
                    "Failed to register donation."
                );
            }

            console.log(
                "Donation registered:",
                donationData
            );


            // ==========================================
            // STEP 2: RUN NGO MATCHING
            // ==========================================

            const matchResponse =
                await fetch(
                    `${API_BASE_URL}/match`,
                    {
                        method: "POST"
                    }
                );

            const matchData =
                await matchResponse.json();

            if (!matchResponse.ok) {

                throw new Error(
                    matchData.detail ||
                    "Failed to find NGO matches."
                );
            }

            console.log(
                "Matching result:",
                matchData
            );


            // ==========================================
            // STEP 3: FIND THIS DONATION'S MATCH
            // ==========================================

            const donationId =
                donationData.donation?.donation_id;

            const match =
                matchData.matches?.find(
                    function(item) {
                        return item.donation_id === donationId;
                    }
                );


            if (match) {

                showMatchResult(match);

            } else {

                showNoMatchResult();
            }

        } catch (error) {

            console.error(
                "Backend error:",
                error
            );

            showMatchError(
                error.message
            );
        }

    });
}


// ==========================================
// MATCH RESULT - LOADING
// ==========================================

function showMatchLoading() {

    const matchResult =
        document.getElementById("matchResult");

    if (!matchResult) {
        return;
    }

    matchResult.style.display = "block";

    document.getElementById("ngoName").textContent =
        "Finding the best NGO...";

    document.getElementById("matchScore").textContent =
        "Match Score: Calculating...";

    document.getElementById("distance").textContent =
        "Distance: Calculating...";

    document.getElementById("reliability").textContent =
        "Reliability: Calculating...";
}


// ==========================================
// MATCH RESULT - SUCCESS
// ==========================================

function showMatchResult(match) {

    const matchResult =
        document.getElementById("matchResult");

    if (!matchResult) {
        return;
    }

    matchResult.style.display = "block";

    document.getElementById("ngoName").textContent =
        match.ngo_name || "NGO matched";

    document.getElementById("matchScore").textContent =
        "Match Score: " +
        (match.match_score ?? "--");

    // Calculate distance from donor and NGO coordinates

    let distanceText = "Distance: --";

    if (
        match.latitude !== undefined &&
        match.longitude !== undefined &&
        match.ngo_latitude !== undefined &&
        match.ngo_longitude !== undefined
    ) {

        const distance =
            calculateDistance(
                Number(match.latitude),
                Number(match.longitude),
                Number(match.ngo_latitude),
                Number(match.ngo_longitude)
            );

        distanceText =
            "Distance: " +
            distance.toFixed(2) +
            " km";
    }

    document.getElementById("distance").textContent =
        distanceText;

    document.getElementById("reliability").textContent =
        "Urgency Score: " +
        (match.urgency_score ?? "--");

    console.log(
        "Best NGO:",
        match.ngo_name
    );

    console.log(
        "Match Score:",
        match.match_score
    );
}


// ==========================================
// MATCH RESULT - NO MATCH
// ==========================================

function showNoMatchResult() {

    const matchResult =
        document.getElementById("matchResult");

    if (!matchResult) {
        return;
    }

    matchResult.style.display = "block";

    document.getElementById("ngoName").textContent =
        "No eligible NGO found";

    document.getElementById("matchScore").textContent =
        "Match Score: --";

    document.getElementById("distance").textContent =
        "Distance: --";

    document.getElementById("reliability").textContent =
        "Try again with different donation details.";
}


// ==========================================
// MATCH RESULT - ERROR
// ==========================================

function showMatchError(message) {

    const matchResult =
        document.getElementById("matchResult");

    if (!matchResult) {
        return;
    }

    matchResult.style.display = "block";

    document.getElementById("ngoName").textContent =
        "Something went wrong";

    document.getElementById("matchScore").textContent =
        "Match Score: --";

    document.getElementById("distance").textContent =
        "Distance: --";

    document.getElementById("reliability").textContent =
        message || "Could not connect to backend.";
}


// ==========================================
// DISTANCE CALCULATION
// ==========================================

function calculateDistance(
    lat1,
    lon1,
    lat2,
    lon2
) {

    const earthRadius = 6371;

    const latDifference =
        toRadians(lat2 - lat1);

    const lonDifference =
        toRadians(lon2 - lon1);

    const a =
        Math.sin(latDifference / 2) *
        Math.sin(latDifference / 2) +

        Math.cos(toRadians(lat1)) *
        Math.cos(toRadians(lat2)) *
        Math.sin(lonDifference / 2) *
        Math.sin(lonDifference / 2);

    const c =
        2 *
        Math.atan2(
            Math.sqrt(a),
            Math.sqrt(1 - a)
        );

    return earthRadius * c;
}


function toRadians(degrees) {

    return degrees *
        (Math.PI / 180);
}


// ==========================================
// NGO DASHBOARD - REFRESH DONATIONS
// ==========================================

async function refreshDonations(button) {

    if (!button) {
        return;
    }

    button.textContent =
        "⏳ Refreshing...";

    button.disabled = true;

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/donations/priority`
            );

        const donations =
            await response.json();

        if (!response.ok) {

            throw new Error(
                donations.detail ||
                "Failed to load donations."
            );
        }

        console.log(
            "Available donations:",
            donations
        );

        renderDonations(donations);

        button.textContent =
            "✓ Refreshed";

    } catch (error) {

        console.error(
            "Failed to load donations:",
            error
        );

        button.textContent =
            "❌ Failed";

    } finally {

        button.disabled = false;

        setTimeout(function() {

            button.textContent =
                "🔄 Refresh";

        }, 1500);
    }
}


// ==========================================
// NGO DASHBOARD - RENDER DONATIONS
// ==========================================

function renderDonations(donations) {

    const donationList =
        document.getElementById("donationList");

    if (!donationList) {
        return;
    }

    donationList.innerHTML = "";

    if (!donations || donations.length === 0) {

        donationList.innerHTML =
            "<p>No donations currently available.</p>";

        updateAvailableCount(0);

        return;
    }

    donations.forEach(function(donation) {

        const card =
            document.createElement("div");

        card.className =
            "donation-card";

        card.innerHTML = `
            <div>
                <strong>${donation.donation_id}</strong>
                <h3>${formatFoodType(donation.food_type)}</h3>
                <p>${donation.quantity} ${donation.unit || ""}</p>
                <p>⏰ ${donation.hours_until_expiry ?? "--"} hours remaining</p>
                <p>📍 ${donation.latitude}, ${donation.longitude}</p>
            </div>

            <button
                onclick="claimDonation('${donation.donation_id}', this)"
            >
                Claim Donation
            </button>
        `;

        donationList.appendChild(card);
    });

    updateAvailableCount(donations.length);
}


// ==========================================
// NGO DASHBOARD - CLAIM DONATION
// ==========================================

function claimDonation(
    donationId,
    button
) {

    const donationCard =
        button.closest(".donation-card");

    if (!donationCard) {
        return;
    }

    const confirmed =
        confirm(
            "Do you want to claim donation " +
            donationId +
            "?"
        );

    if (!confirmed) {
        return;
    }

    // Currently there is NO /claim endpoint
    // in the backend API provided by your teammate.
    // So for now we update the frontend only.

    button.textContent =
        "✓ Claimed";

    button.disabled = true;

    donationCard.classList.remove(
        "urgent"
    );

    const badge =
        donationCard.querySelector(".badge");

    if (badge) {
        badge.textContent =
            "CLAIMED";
    }

    const countElement =
        document.getElementById(
            "availableCount"
        );

    if (countElement) {

        let count =
            parseInt(
                countElement.textContent
            );

        if (count > 0) {

            countElement.textContent =
                count - 1;
        }
    }

    addActivity(
        donationId,
        "Donation successfully claimed"
    );
}


// ==========================================
// NGO DASHBOARD - UPDATE COUNT
// ==========================================

function updateAvailableCount(count) {

    const countElement =
        document.getElementById(
            "availableCount"
        );

    if (countElement) {

        countElement.textContent =
            count;
    }
}


// ==========================================
// NGO DASHBOARD - FOOD TYPE
// ==========================================

function formatFoodType(foodType) {

    if (!foodType) {
        return "Food Donation";
    }

    return foodType
        .replace(/_/g, " ")
        .replace(/\b\w/g, function(letter) {
            return letter.toUpperCase();
        });
}


// ==========================================
// NGO DASHBOARD - ACTIVITY
// ==========================================

function addActivity(
    donationId,
    message
) {

    const activityList =
        document.getElementById(
            "activityList"
        );

    if (!activityList) {
        return;
    }

    const activity =
        document.createElement("div");

    activity.innerHTML =
        `
        <div>
            <strong>${donationId}</strong>
            <span>${message}</span>
        </div>
        `;

    activityList.prepend(activity);
}
