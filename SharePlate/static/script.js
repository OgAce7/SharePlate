// ==========================================
// CONFIGURATION & API ROUTING
// ==========================================

function getApiBaseUrl() {
    return window.location.origin;
}

const API_BASE_URL = getApiBaseUrl();
const TRACKING_STEPS = ["PENDING", "ASSIGNED", "PICKED_UP", "IN_TRANSIT", "DELIVERED"];

// Global storage for NGO Dashboard filtering
window.rawNgoDonations = [];

// ==========================================
// ROLLING NUMBER COUNTER ANIMATION
// ==========================================

function animateCounter(element, targetValue, duration = 1200, suffix = "") {
    if (!element) return;

    const numStr = String(targetValue).replace(/,/g, '');
    const target = parseFloat(numStr);
    if (isNaN(target)) {
        element.textContent = targetValue + suffix;
        return;
    }

    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        const easeProgress = 1 - Math.pow(1 - progress, 3);
        const currentVal = Math.floor(start + (target - start) * easeProgress);

        element.textContent = currentVal.toLocaleString() + suffix;

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            element.textContent = Math.round(target).toLocaleString() + suffix;
        }
    }

    requestAnimationFrame(update);
}

function triggerInitialStatRolls() {
    document.querySelectorAll(".stat-card h2").forEach(h2 => {
        const text = h2.textContent.trim();
        const matches = text.match(/^([\d,]+)\s*(.*)$/);
        if (matches) {
            const num = parseInt(matches[1].replace(/,/g, ''), 10);
            const suffix = matches[2] ? " " + matches[2] : "";
            animateCounter(h2, num, 1200, suffix);
        }
    });
}

// ==========================================
// DONOR DASHBOARD - LOCATION DETECTION
// ==========================================

function getLocation() {
    const status = document.getElementById("locationStatus");

    if (!status) return;

    if (!navigator.geolocation) {
        status.textContent = "Location services are not supported by your browser.";
        return;
    }

    status.textContent = "Detecting your location...";

    navigator.geolocation.getCurrentPosition(
        function(position) {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            document.getElementById("latitude").value = latitude;
            document.getElementById("longitude").value = longitude;

            status.textContent = `Location detected (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`;
            status.classList.add("success");
        },
        function(error) {
            status.textContent = "Location permission denied. Using default Jaipur location.";
            document.getElementById("latitude").value = 26.9124;
            document.getElementById("longitude").value = 75.7873;
        }
    );
}

// ==========================================
// DONOR DASHBOARD - FORM SUBMISSION & AI NGO MATCHING
// ==========================================

const donationForm = document.getElementById("donationForm");

if (donationForm) {
    donationForm.addEventListener("submit", async function(event) {
        event.preventDefault();

        const foodType = document.getElementById("food_type").value;
        const quantity = Number(document.getElementById("quantity").value);
        const unit = document.getElementById("unit").value;
        const safeUntil = document.getElementById("safe_until").value;
        
        let latitude = Number(document.getElementById("latitude").value);
        let longitude = Number(document.getElementById("longitude").value);

        if (!latitude || !longitude) {
            latitude = 26.9124;
            longitude = 75.7873;
        }

        const vegetarian = document.getElementById("vegetarian").checked ? 1 : 0;
        const vegan = document.getElementById("vegan").checked ? 1 : 0;
        const pickupRequiredEl = document.getElementById("pickup_required");
        const pickupRequired = pickupRequiredEl ? (pickupRequiredEl.checked ? 1 : 0) : 1;

        let hoursUntilExpiry = 12;
        if (safeUntil) {
            const expiryTime = new Date(safeUntil);
            const currentTime = new Date();
            hoursUntilExpiry = Math.max(1, (expiryTime - currentTime) / (1000 * 60 * 60));
        }

        showMatchLoading();

        const donationPayload = {
            food_type: foodType,
            quantity: quantity,
            latitude: latitude,
            longitude: longitude,
            hours_until_expiry: Number(hoursUntilExpiry.toFixed(2)),
            unit: unit,
            donor_type: "restaurant",
            vegetarian: vegetarian,
            vegan: vegan,
            pickup_required: pickupRequired,
            strict_bounds: false
        };

        console.log("Sending donation payload:", donationPayload);

        try {
            const donationResponse = await fetch(`${API_BASE_URL}/donations`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(donationPayload)
            });

            let donationData;
            const resText = await donationResponse.text();
            try {
                donationData = JSON.parse(resText);
            } catch (e) {
                console.error("Non-JSON server response:", resText);
                throw new Error("Server error: " + (resText || `HTTP ${donationResponse.status}`));
            }

            if (!donationResponse.ok) {
                throw new Error(donationData.detail || donationData.message || "Failed to register donation.");
            }

            console.log("Donation registered and matched:", donationData);

            const bestMatch = donationData.best_match;
            const candidates = donationData.candidate_matches || [];

            if (bestMatch || (candidates && candidates.length > 0)) {
                showMatchResults(bestMatch || candidates[0], candidates);
            } else {
                showNoMatchResult();
            }

            loadAnalyticsSummary();

        } catch (error) {
            console.error("Backend error:", error);
            showMatchError(error.message);
        }
    });
}

// ==========================================
// AI MATCH RESULT UI RENDERING (GLITCH-FREE)
// ==========================================

function showMatchLoading() {
    const matchResult = document.getElementById("matchResult");
    if (!matchResult) return;

    matchResult.style.display = "block";
    document.getElementById("ngoName").textContent = "AI Searching for Best Nearby NGO Partner...";
    document.getElementById("matchScore").textContent = "Match Score: Calculating...";
    document.getElementById("distance").textContent = "Distance: Calculating...";
    document.getElementById("reliability").textContent = "Urgency Score: Calculating...";

    let candidatesContainer = document.getElementById("candidateNgoList");
    if (candidatesContainer) {
        candidatesContainer.innerHTML = "";
    }
}

function extractScore(item) {
    if (!item) return "90.0%";
    const val = item.match_score ?? item.final_score ?? 90.0;
    const num = parseFloat(val);
    return isNaN(num) ? String(val) : num.toFixed(1) + "%";
}

function extractDistance(item) {
    if (!item) return "0.0 km";
    const val = item.distance_km ?? 0.0;
    const num = parseFloat(val);
    return isNaN(num) ? String(val) : num.toFixed(2) + " km";
}

function extractReliability(item) {
    if (!item) return "0.90";
    const val = item.reliability_score ?? 0.90;
    const num = parseFloat(val);
    return isNaN(num) ? String(val) : num.toFixed(2);
}

function showMatchResults(bestMatch, candidateList) {
    const matchResultSection = document.getElementById("matchResult");
    if (!matchResultSection) return;

    matchResultSection.style.display = "block";

    const ngoName = bestMatch ? (bestMatch.ngo_name || bestMatch.ngo_id || "Hope Relief NGO") : "Selected NGO Partner";
    const scoreStr = extractScore(bestMatch);
    const distStr = extractDistance(bestMatch);
    const relStr = extractReliability(bestMatch);

    document.getElementById("ngoName").textContent = `Top NGO Match: ${ngoName}`;
    document.getElementById("matchScore").textContent = `AI Compatibility Score: ${scoreStr}`;
    document.getElementById("distance").textContent = `Pickup Distance: ${distStr}`;
    document.getElementById("reliability").textContent = `Reliability Score: ${relStr}`;

    let candidatesContainer = document.getElementById("candidateNgoList");
    if (!candidatesContainer) {
        candidatesContainer = document.createElement("div");
        candidatesContainer.id = "candidateNgoList";
        candidatesContainer.style.marginTop = "24px";
        matchResultSection.appendChild(candidatesContainer);
    }

    const displayList = (candidateList && candidateList.length > 0) ? candidateList : (bestMatch ? [bestMatch] : []);

    let listHtml = `<h3 style="margin-bottom: 16px; color: #0f172a; font-size: 1.1rem; font-weight: 800;">Top AI Matched NGO Candidates:</h3>`;

    displayList.forEach((ngo, index) => {
        const ngoScore = extractScore(ngo);
        const ngoDist = extractDistance(ngo);
        const ngoRel = extractReliability(ngo);
        const isTop = index === 0;

        listHtml += `
            <div style="background: white; border: ${isTop ? '2px solid #059669' : '1px solid #e2e8f0'}; padding: 18px 22px; border-radius: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04); transition: transform 0.2s ease;">
                <div>
                    <div style="font-weight: 700; font-size: 1rem; color: #0f172a;">
                        #${index + 1} ${ngo.ngo_name || ngo.ngo_id} ${isTop ? '<span style="color:#059669; font-size:0.85rem; margin-left:8px; font-weight:700;">(Top Recommendation)</span>' : ''}
                    </div>
                    <div style="font-size: 0.88rem; color: #64748b; margin-top: 4px;">
                        Proximity: <strong>${ngoDist}</strong> | Reliability Rating: <strong>${ngoRel}</strong>
                    </div>
                </div>
                <div>
                    <span class="badge ${isTop ? 'low' : 'medium'}" style="font-size: 0.85rem; padding: 6px 14px;">AI Score: ${ngoScore}</span>
                </div>
            </div>
        `;
    });

    candidatesContainer.innerHTML = listHtml;
    matchResultSection.scrollIntoView({ behavior: 'smooth' });
}

function showNoMatchResult() {
    const matchResult = document.getElementById("matchResult");
    if (!matchResult) return;

    matchResult.style.display = "block";
    document.getElementById("ngoName").textContent = "No eligible NGO within pickup radius";
    document.getElementById("matchScore").textContent = "Match Score: --";
    document.getElementById("distance").textContent = "Distance: --";
    document.getElementById("reliability").textContent = "Try increasing expiry hours or expanding food types.";
}

function showMatchError(message) {
    const matchResult = document.getElementById("matchResult");
    if (!matchResult) return;

    matchResult.style.display = "block";
    document.getElementById("ngoName").textContent = "Connection Alert";
    document.getElementById("matchScore").textContent = "Match Score: --";
    document.getElementById("distance").textContent = "Distance: --";
    document.getElementById("reliability").textContent = message || "Could not connect to backend.";
}

// ==========================================
// SAFETY & TRACKING UTILITIES
// ==========================================

function getSafetyBadgeInfo(hoursUntilExpiry) {
    const hours = Number(hoursUntilExpiry);
    if (isNaN(hours) || hours <= 0) {
        return { badgeClass: "critical", label: "EXPIRED" };
    } else if (hours <= 3) {
        return { badgeClass: "critical", label: "CRITICAL EXPIRY" };
    } else if (hours <= 6) {
        return { badgeClass: "medium", label: "WARNING EXPIRY" };
    } else {
        return { badgeClass: "low", label: "FRESH & SAFE" };
    }
}

async function updateTrackingStatus(donationId, newStatus, button) {
    if (button) {
        button.disabled = true;
        button.textContent = "Updating...";
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/tracking/${donationId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Failed to update tracking status.");
        }

        console.log(`Tracking updated for ${donationId}:`, data);
        addActivity(donationId, `Tracking updated to ${newStatus}`);
        refreshDonations();
    } catch (err) {
        console.error("Tracking update error:", err);
        alert(err.message);
        if (button) {
            button.disabled = false;
            button.textContent = "Retry";
        }
    }
}

// ==========================================
// NGO DASHBOARD - REFRESH, CLAIM & FILTERING
// ==========================================

async function refreshDonations(button) {
    if (!button) {
        button = document.querySelector("button[onclick='refreshDonations(this)']");
    }

    if (button) {
        button.textContent = "Refreshing...";
        button.disabled = true;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/donations/priority`);
        const donations = await response.json();

        if (!response.ok) {
            throw new Error(donations.detail || "Failed to load donations.");
        }

        console.log("Available priority donations:", donations);
        window.rawNgoDonations = donations || [];
        applyNgoFilters();
        loadAnalyticsSummary();

        if (button) button.textContent = "Refreshed";
    } catch (error) {
        console.error("Failed to load donations:", error);
        if (button) button.textContent = "Failed";
    } finally {
        if (button) {
            button.disabled = false;
            setTimeout(() => { button.textContent = "Refresh Listings"; }, 1500);
        }
    }
}

function applyNgoFilters() {
    if (!window.rawNgoDonations) return;

    let filtered = [...window.rawNgoDonations];

    const foodTypeEl = document.getElementById("filterFoodType");
    const expiryEl = document.getElementById("filterExpiry");
    const sortEl = document.getElementById("filterSort");
    const searchEl = document.getElementById("filterSearch");

    const selectedFoodType = foodTypeEl ? foodTypeEl.value : "all";
    const selectedExpiry = expiryEl ? expiryEl.value : "all";
    const selectedSort = sortEl ? sortEl.value : "urgency_desc";
    const searchQuery = searchEl ? searchEl.value.toLowerCase().trim() : "";

    // 1. Food Type Filter
    if (selectedFoodType !== "all") {
        filtered = filtered.filter(d => (d.food_type || "").toLowerCase() === selectedFoodType.toLowerCase());
    }

    // 2. Expiry Status Filter
    if (selectedExpiry !== "all") {
        filtered = filtered.filter(d => {
            const h = Number(d.hours_until_expiry ?? 12);
            if (selectedExpiry === "safe") return h > 6;
            if (selectedExpiry === "warning") return h > 3 && h <= 6;
            if (selectedExpiry === "critical") return h <= 3;
            return true;
        });
    }

    // 3. Keyword Search Filter
    if (searchQuery) {
        filtered = filtered.filter(d => {
            const id = String(d.donation_id || "").toLowerCase();
            const ft = String(d.food_type || "").toLowerCase();
            const u = String(d.unit || "").toLowerCase();
            return id.includes(searchQuery) || ft.includes(searchQuery) || u.includes(searchQuery);
        });
    }

    // 4. Sort Order
    filtered.sort((a, b) => {
        const hA = Number(a.hours_until_expiry ?? 12);
        const hB = Number(b.hours_until_expiry ?? 12);
        const qA = Number(a.quantity ?? 0);
        const qB = Number(b.quantity ?? 0);

        if (selectedSort === "urgency_desc") return hA - hB; // fewest hours first (most urgent)
        if (selectedSort === "urgency_asc") return hB - hA;  // most hours first
        if (selectedSort === "qty_desc") return qB - qA;      // highest quantity first
        return 0;
    });

    renderDonations(filtered);
}

function renderDonations(donations) {
    const donationList = document.getElementById("donationList");
    if (!donationList) return;

    donationList.innerHTML = "";

    if (!donations || donations.length === 0) {
        donationList.innerHTML = "<p style='padding: 24px; text-align: center; color: #64748b;'>No matching surplus donations available for the selected filters.</p>";
        updateAvailableCount(0);
        return;
    }

    donations.forEach(function(donation) {
        const card = document.createElement("div");
        const hours = donation.hours_until_expiry ?? 12;
        const safety = getSafetyBadgeInfo(hours);
        const isUrgent = hours <= 6;

        card.className = `donation-card ${isUrgent ? 'urgent' : ''}`;

        const currentTracking = (donation.tracking_status || "PENDING").toUpperCase();
        let trackingActionBtn = "";

        const currentIdx = TRACKING_STEPS.indexOf(currentTracking);
        if (currentIdx >= 0 && currentIdx < TRACKING_STEPS.length - 1) {
            const nextStatus = TRACKING_STEPS[currentIdx + 1];
            trackingActionBtn = `<button type="button" class="secondary-btn" style="margin-top: 8px; font-size: 0.82rem;" onclick="updateTrackingStatus('${donation.donation_id}', '${nextStatus}', this)">Status: ${nextStatus}</button>`;
        } else if (currentTracking === "DELIVERED") {
            trackingActionBtn = `<span class="badge low" style="margin-top: 8px; display: inline-block;">DELIVERED</span>`;
        }

        card.innerHTML = `
            <div class="donation-info">
                <span class="badge ${safety.badgeClass}">${safety.label}</span>
                <span class="badge" style="background:#f1f5f9; color:#334155; margin-left:6px;">STATUS: ${currentTracking}</span>
                <h3>${formatFoodType(donation.food_type)}</h3>
                <p>Quantity: ${donation.quantity} ${donation.unit || "meals"}</p>
                <p>Coordinates: ${parseFloat(donation.latitude).toFixed(4)}, ${parseFloat(donation.longitude).toFixed(4)}</p>
                <p>Expiry: ~${hours} hours</p>
                ${trackingActionBtn}
            </div>
            <div>
                <button type="button" class="claim-btn" onclick="claimDonation('${donation.donation_id}', this)">
                    Claim Donation
                </button>
            </div>
        `;

        donationList.appendChild(card);
    });

    updateAvailableCount(donations.length);
}

async function claimDonation(donationId, button) {
    const donationCard = button.closest(".donation-card");
    if (!donationCard) return;

    const confirmed = confirm(`Do you want to claim donation ${donationId}?`);
    if (!confirmed) return;

    button.textContent = "Claiming...";
    button.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/donations/${donationId}/claim`, {
            method: "POST"
        });

        const data = await response.json();
        console.log("Claim result:", data);

        button.textContent = "Claimed";
        donationCard.classList.remove("urgent");

        const badge = donationCard.querySelector(".badge");
        if (badge) {
            badge.textContent = "CLAIMED";
            badge.className = "badge low";
        }

        const countElement = document.getElementById("availableCount");
        if (countElement) {
            let count = parseInt(countElement.textContent);
            if (count > 0) animateCounter(countElement, count - 1, 600);
        }

        addActivity(donationId, "Donation claimed successfully");

    } catch (error) {
        console.error("Claim error:", error);
        button.textContent = "Claim Donation";
        button.disabled = false;
        alert("Failed to claim donation from backend.");
    }
}

// ==========================================
// ANALYTICS & UTILITIES
// ==========================================

async function loadAnalyticsSummary() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/analytics/summary`);
        if (!res.ok) return;
        const data = await res.json();
        console.log("Analytics summary:", data);

        const availableEl = document.getElementById("availableCount");
        if (availableEl && !window.rawNgoDonations.length) {
            animateCounter(availableEl, data.total_donations, 1000);
        }

        const totalSharedEl = document.getElementById("totalSharedCount");
        if (totalSharedEl) {
            animateCounter(totalSharedEl, Math.round(data.total_quantity), 1200, " meals");
        }
    } catch (err) {
        console.warn("Analytics fetch error:", err);
    }
}

function updateAvailableCount(count) {
    const countElement = document.getElementById("availableCount");
    if (countElement) {
        animateCounter(countElement, count, 800);
    }
}

function formatFoodType(foodType) {
    if (!foodType) return "Food Donation";
    return foodType.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
}

function addActivity(donationId, message) {
    const activityList = document.getElementById("activityList");
    if (!activityList) return;

    const activity = document.createElement("div");
    activity.innerHTML = `
        <div>
            <strong>${donationId}</strong>
            <span>${message}</span>
        </div>
    `;
    activityList.prepend(activity);
}

// Auto load NGO priority donations and rolling stats on load
document.addEventListener("DOMContentLoaded", () => {
    triggerInitialStatRolls();
    loadAnalyticsSummary();
    if (document.getElementById("donationList")) {
        refreshDonations();
    }
});
