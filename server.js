const express = require("express");
const http = require("http");
const { Server } = require("socket.io");

const { getSafetyStatus } = require("./safety");

const {
    trackingStatuses,
    isValidTrackingStatus,
    isNextTrackingStatus
} = require("./tracking");

const fs = require("fs");
const { parse } = require("csv-parse/sync");

const app = express();
const server = http.createServer(app);

const io = new Server(server);

app.use(express.json());
app.use(express.static("."));


// ===============================
// READ DONATIONS
// ===============================

const csvData = fs.readFileSync("./data/donations.csv", "utf8");

const donations = parse(csvData, {
    columns: true,
    skip_empty_lines: true
});

donations.forEach(donation => {
    donation.tracking_status = "PENDING";
});


// ===============================
// SOCKET.IO
// ===============================

io.on("connection", socket => {

    console.log("A user connected:", socket.id);

    socket.on("disconnect", () => {
        console.log("A user disconnected:", socket.id);
    });

});


// ===============================
// SAFETY ALERTS
// ===============================

app.get("/api/safety/alerts", (req, res) => {

    const alerts = donations
        .map(donation => {

            const hoursUntilExpiry =
                Number(donation.hours_until_expiry);

            const status =
                getSafetyStatus(hoursUntilExpiry);

            return {
                donation_id: donation.donation_id,
                food_type: donation.food_type,
                hours_until_expiry: hoursUntilExpiry,
                status
            };
        })
        .filter(donation => donation.status !== "SAFE");

    res.json(alerts);
});


// ===============================
// ALL SAFETY STATUS
// ===============================

app.get("/api/safety", (req, res) => {

    const results = donations.map(donation => {

        const hoursUntilExpiry =
            Number(donation.hours_until_expiry);

        const status =
            getSafetyStatus(hoursUntilExpiry);

        return {
            donation_id: donation.donation_id,
            food_type: donation.food_type,
            hours_until_expiry: hoursUntilExpiry,
            status
        };
    });

    res.json(results);
});


// ===============================
// MANUAL SAFETY CHECK
// ===============================

app.get("/api/safety/check", (req, res) => {

    const donation_id = req.query.donation_id;

    const hours_until_expiry =
        Number(req.query.hours_until_expiry);

    const status =
        getSafetyStatus(hours_until_expiry);

    let message;

    if (status === "EXPIRED") {
        message = "Food has expired. Do not distribute.";
    } else if (status === "CRITICAL") {
        message = "Food is critically close to expiry.";
    } else if (status === "WARNING") {
        message = "Food is approaching expiry.";
    } else {
        message = "Food is currently safe.";
    }

    res.json({
        donation_id,
        status,
        message
    });
});


// ===============================
// GET TRACKING STATUS
// ===============================

app.get("/api/tracking/:donation_id", (req, res) => {

    const donation = donations.find(
        d => d.donation_id === req.params.donation_id
    );

    if (!donation) {
        return res.status(404).json({
            message: "Donation not found"
        });
    }

    res.json({
        donation_id: donation.donation_id,
        tracking_status: donation.tracking_status
    });
});


// ===============================
// UPDATE TRACKING STATUS
// ===============================

app.put("/api/tracking/:donation_id", (req, res) => {

    const donation = donations.find(
        d => d.donation_id === req.params.donation_id
    );

    if (!donation) {
        return res.status(404).json({
            message: "Donation not found"
        });
    }

    const newStatus = req.body.status;

    if (!isValidTrackingStatus(newStatus)) {

        return res.status(400).json({
            message: "Invalid tracking status",
            allowed_statuses: trackingStatuses
        });
    }

    if (!isNextTrackingStatus(
        donation.tracking_status,
        newStatus
    )) {

        const currentIndex =
            trackingStatuses.indexOf(
                donation.tracking_status
            );

        return res.status(400).json({
            message: "Invalid status progression",
            current_status: donation.tracking_status,
            next_allowed_status:
                trackingStatuses[currentIndex + 1] || null
        });
    }

    const oldStatus =
        donation.tracking_status;

    donation.tracking_status =
        newStatus;


    // Send real-time update
    io.emit("tracking_updated", {
        donation_id: donation.donation_id,
        old_status: oldStatus,
        new_status: newStatus
    });


    res.json({
        donation_id: donation.donation_id,
        tracking_status: donation.tracking_status,
        message: "Tracking status updated successfully"
    });
});


// ===============================
// ONE DONATION SAFETY
// ===============================

app.get("/api/safety/:donation_id", (req, res) => {

    const donation = donations.find(
        d => d.donation_id === req.params.donation_id
    );

    if (!donation) {
        return res.status(404).json({
            message: "Donation not found"
        });
    }

    const hoursUntilExpiry =
        Number(donation.hours_until_expiry);

    const status =
        getSafetyStatus(hoursUntilExpiry);

    let message;

    if (status === "EXPIRED") {
        message = "Food has expired. Do not distribute.";
    } else if (status === "CRITICAL") {
        message = "Food is critically close to expiry.";
    } else if (status === "WARNING") {
        message = "Food is approaching expiry.";
    } else {
        message = "Food is currently safe.";
    }

    res.json({
        donation_id: donation.donation_id,
        food_type: donation.food_type,
        hours_until_expiry: hoursUntilExpiry,
        status,
        message
    });
});


// ==================================================
// ANALYTICS
// ==================================================


// ===============================
// ANALYTICS SUMMARY
// ===============================

app.get("/api/analytics/summary", (req, res) => {

    let totalQuantity = 0;

    let safe = 0;
    let warning = 0;
    let critical = 0;
    let expired = 0;

    let pending = 0;
    let assigned = 0;
    let pickedUp = 0;
    let inTransit = 0;
    let delivered = 0;


    donations.forEach(donation => {

        const quantity =
            Number(donation.quantity);

        totalQuantity += quantity;


        // Safety
        const safetyStatus =
            getSafetyStatus(
                Number(donation.hours_until_expiry)
            );

        if (safetyStatus === "SAFE") {
            safe++;
        } else if (safetyStatus === "WARNING") {
            warning++;
        } else if (safetyStatus === "CRITICAL") {
            critical++;
        } else if (safetyStatus === "EXPIRED") {
            expired++;
        }


        // Tracking
        if (donation.tracking_status === "PENDING") {
            pending++;
        } else if (donation.tracking_status === "ASSIGNED") {
            assigned++;
        } else if (donation.tracking_status === "PICKED_UP") {
            pickedUp++;
        } else if (donation.tracking_status === "IN_TRANSIT") {
            inTransit++;
        } else if (donation.tracking_status === "DELIVERED") {
            delivered++;
        }

    });


    res.json({

        total_donations: donations.length,

        total_quantity: totalQuantity,

        safety: {
            safe,
            warning,
            critical,
            expired
        },

        tracking: {
            pending,
            assigned,
            picked_up: pickedUp,
            in_transit: inTransit,
            delivered
        }

    });

});


// ===============================
// FOOD TYPE ANALYTICS
// ===============================

app.get("/api/analytics/food-types", (req, res) => {

    const foodTypes = {};


    donations.forEach(donation => {

        const foodType =
            donation.food_type;

        const quantity =
            Number(donation.quantity);


        if (!foodTypes[foodType]) {

            foodTypes[foodType] = {
                food_type: foodType,
                donation_count: 0,
                total_quantity: 0
            };

        }


        foodTypes[foodType].donation_count++;

        foodTypes[foodType].total_quantity +=
            quantity;

    });


    res.json(
        Object.values(foodTypes)
    );

});


// ===============================
// TRACKING ANALYTICS
// ===============================

app.get("/api/analytics/tracking", (req, res) => {

    const result = trackingStatuses.map(status => {

        const count =
            donations.filter(
                donation =>
                    donation.tracking_status === status
            ).length;

        return {
            status,
            count
        };

    });


    res.json(result);

});


// ===============================
// SAFETY ANALYTICS
// ===============================

app.get("/api/analytics/safety", (req, res) => {

    const statuses = [
        "SAFE",
        "WARNING",
        "CRITICAL",
        "EXPIRED"
    ];


    const result = statuses.map(status => {

        const count =
            donations.filter(donation => {

                const safetyStatus =
                    getSafetyStatus(
                        Number(
                            donation.hours_until_expiry
                        )
                    );

                return safetyStatus === status;

            }).length;


        return {
            status,
            count
        };

    });


    res.json(result);

});


// ===============================
// HOME
// ===============================

app.get("/", (req, res) => {

    res.send(
        "Safety + Tracking + Analytics server is running!"
    );

});


// ===============================
// START SERVER
// ===============================

server.listen(3000, () => {

    console.log(
        "Server running on http://localhost:3000"
    );

});