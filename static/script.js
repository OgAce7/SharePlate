// ==========================================
// SHAREPLATE FRONTEND SCRIPT
// ==========================================


// ==========================================
// DONOR - LOCATION
// ==========================================

function getLocation() {

    const status =
        document.getElementById("locationStatus");

    if (!status) {
        return;
    }

    if (!navigator.geolocation) {

        status.textContent =
            "Location services are not supported.";

        return;
    }

    status.textContent =
        "📍 Detecting your location...";


    navigator.geolocation.getCurrentPosition(

        function(position) {

            const latitude =
                position.coords.latitude;

            const longitude =
                position.coords.longitude;


            document.getElementById("latitude").value =
                latitude;

            document.getElementById("longitude").value =
                longitude;


            status.textContent =
                "✓ Location detected successfully";

            status.classList.add("success");


            console.log("Latitude:", latitude);
            console.log("Longitude:", longitude);

        },


        function(error) {

            if (error.code === 1) {

                status.textContent =
                    "Location permission denied.";

            } else {

                status.textContent =
                    "Unable to detect location.";

            }

        }

    );
}



// ==========================================
// DONOR - FORM SUBMISSION
// ==========================================

const donationForm =
    document.getElementById("donationForm");


if (donationForm) {

    donationForm.addEventListener(
        "submit",
        function(event) {

            event.preventDefault();


            const foodType =
                document.getElementById("food_type").value;


            const quantity =
                Number(
                    document.getElementById("quantity").value
                );


            const unit =
                document.getElementById("unit").value;


            const safeUntil =
                document.getElementById("safe_until").value;


            const latitude =
                document.getElementById("latitude").value;


            const longitude =
                document.getElementById("longitude").value;


            // Check location

            if (!latitude || !longitude) {

                alert(
                    "Please detect your location first."
                );

                return;
            }


            // Check expiry

            const expiryTime =
                new Date(safeUntil);

            const currentTime =
                new Date();


            if (
                !safeUntil ||
                expiryTime <= currentTime
            ) {

                alert(
                    "Please select a future expiry time."
                );

                return;
            }


            // Generate demo donation ID

            const donationId =
                "D" +
                String(
                    Math.floor(
                        Math.random() * 900
                    ) + 100
                );


            // Show match

            showMatchResult(
                foodType,
                quantity,
                unit,
                donationId
            );


            // Show tracking

            showDonorTracking(
                donationId
            );


            // Add activity

            addActivity(
                donationId,
                "Donation created successfully"
            );


            // Increase donation count

            const total =
                document.getElementById(
                    "totalDonations"
                );


            if (total) {

                total.textContent =
                    Number(total.textContent) + 1;

            }


            alert(
                "Donation created successfully!"
            );

        }
    );

}



// ==========================================
// DONOR - NGO MATCH
// ==========================================

function showMatchResult(
    foodType,
    quantity,
    unit,
    donationId
) {

    const result =
        document.getElementById("matchResult");


    if (!result) {
        return;
    }


    result.style.display =
        "block";


    // Demo NGO

    document.getElementById(
        "ngoName"
    ).textContent =
        "Hope Foundation";


    document.getElementById(
        "matchScore"
    ).textContent =
        "Match Score: 94%";


    document.getElementById(
        "distance"
    ).textContent =
        "Distance: 1.2 km";


    document.getElementById(
        "reliability"
    ).textContent =
        "Reliability: 96%";


    console.log(
        "Donation:",
        donationId
    );

    console.log(
        "Food:",
        foodType
    );

    console.log(
        "Quantity:",
        quantity,
        unit
    );
}



// ==========================================
// DONOR - TRACKING
// ==========================================

function showDonorTracking(
    donationId
) {

    const section =
        document.getElementById(
            "trackingSection"
        );


    if (!section) {
        return;
    }


    section.style.display =
        "block";


    section.dataset.donationId =
        donationId;


    // Reset timeline

    resetDonorTracking();


    // Demo progression

    setTimeout(
        function() {

            updateDonorTracking(
                "accepted"
            );

        },
        1500
    );


    setTimeout(
        function() {

            updateDonorTracking(
                "picked"
            );

        },
        4000
    );


    setTimeout(
        function() {

            updateDonorTracking(
                "transit"
            );

        },
        7000
    );


    setTimeout(
        function() {

            updateDonorTracking(
                "delivered"
            );

        },
        10000
    );
}



// ==========================================
// DONOR - RESET TRACKING
// ==========================================

function resetDonorTracking() {

    const steps = [
        "pending",
        "accepted",
        "picked",
        "transit",
        "delivered"
    ];


    steps.forEach(
        function(step) {

            const element =
                document.getElementById(
                    "step-" + step
                );


            if (element) {

                element.classList.remove(
                    "active"
                );

            }

        }
    );


    document.getElementById(
        "step-pending"
    ).classList.add(
        "active"
    );


    document.getElementById(
        "trackingStatus"
    ).textContent =
        "Pending";
}



// ==========================================
// DONOR - UPDATE TRACKING
// ==========================================

function updateDonorTracking(
    status
) {

    const order = [
        "pending",
        "accepted",
        "picked",
        "transit",
        "delivered"
    ];


    const index =
        order.indexOf(status);


    if (index === -1) {
        return;
    }


    for (
        let i = 0;
        i <= index;
        i++
    ) {

        const step =
            document.getElementById(
                "step-" + order[i]
            );


        if (step) {

            step.classList.add(
                "active"
            );

        }

    }


    const statusText = {

        pending: "Pending",

        accepted: "Accepted",

        picked: "Picked Up",

        transit: "In Transit",

        delivered: "Delivered"

    };


    document.getElementById(
        "trackingStatus"
    ).textContent =
        statusText[status];


    if (status === "delivered") {

        addActivity(
            document
                .getElementById(
                    "trackingSection"
                )
                .dataset.donationId,

            "Donation successfully delivered"
        );

    }

}



// ==========================================
// NGO - REFRESH
// ==========================================

function refreshDonations() {

    const button =
        document.getElementById(
            "refreshButton"
        );


    if (!button) {
        return;
    }


    button.disabled =
        true;


    button.textContent =
        "⏳ Refreshing...";


    setTimeout(
        function() {

            button.textContent =
                "✓ Refreshed";


            button.disabled =
                false;


            setTimeout(
                function() {

                    button.textContent =
                        "🔄 Refresh";

                },
                1200
            );

        },
        700
    );

}



// ==========================================
// NGO - CLAIM DONATION
// ==========================================

function claimDonation(
    donationId,
    button
) {

    const card =
        button.closest(
            ".donation-card"
        );


    if (!card) {
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


    button.textContent =
        "✓ Claimed";


    button.disabled =
        true;


    card.classList.remove(
        "urgent"
    );


    const badge =
        card.querySelector(
            ".badge"
        );


    if (badge) {

        badge.textContent =
            "CLAIMED";

        badge.className =
            "badge low";

    }


    // Update count

    const count =
        document.getElementById(
            "availableCount"
        );


    if (count) {

        const current =
            Number(
                count.textContent
            );


        if (current > 0) {

            count.textContent =
                current - 1;

        }

    }


    // Show tracking

    showNGOTracking(
        donationId
    );


    // Activity

    addActivity(
        donationId,
        "Donation successfully claimed"
    );

}



// ==========================================
// NGO - SHOW TRACKING
// ==========================================

function showNGOTracking(
    donationId
) {

    const section =
        document.getElementById(
            "ngoTrackingSection"
        );


    if (!section) {
        return;
    }


    section.style.display =
        "block";


    document.getElementById(
        "trackingDonationId"
    ).textContent =
        donationId;


    document.getElementById(
        "ngoTrackingStatus"
    ).textContent =
        "Accepted";


    resetNGOTracking();

}



// ==========================================
// NGO - RESET TRACKING
// ==========================================

function resetNGOTracking() {

    const steps = [
        "pending",
        "accepted",
        "picked",
        "transit",
        "delivered"
    ];


    steps.forEach(
        function(step) {

            const element =
                document.getElementById(
                    "ngo-step-" + step
                );


            if (element) {

                element.classList.remove(
                    "active"
                );

            }

        }
    );


    document.getElementById(
        "ngo-step-pending"
    ).classList.add(
        "active"
    );


    document.getElementById(
        "ngo-step-accepted"
    ).classList.add(
        "active"
    );

}



// ==========================================
// NGO - UPDATE TRACKING
// ==========================================

function updateNGOTracking(
    status
) {

    const order = [
        "pending",
        "accepted",
        "picked",
        "transit",
        "delivered"
    ];


    const index =
        order.indexOf(status);


    if (index === -1) {
        return;
    }


    for (
        let i = 0;
        i <= index;
        i++
    ) {

        const step =
            document.getElementById(
                "ngo-step-" +
                order[i]
            );


        if (step) {

            step.classList.add(
                "active"
            );

        }

    }


    const statusText = {

        picked: "Picked Up",

        transit: "In Transit",

        delivered: "Delivered"

    };


    document.getElementById(
        "ngoTrackingStatus"
    ).textContent =
        statusText[status];


    if (status === "delivered") {

        addActivity(
            document.getElementById(
                "trackingDonationId"
            ).textContent,

            "Donation successfully delivered"
        );

    }

}



// ==========================================
// ACTIVITY
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
        document.createElement(
            "div"
        );


    activity.innerHTML =
        `
        <strong>${donationId}</strong>
        <span>${message}</span>
        `;


    activityList.prepend(
        activity
    );

}