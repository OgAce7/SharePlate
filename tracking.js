const trackingStatuses = [
    "PENDING",
    "ASSIGNED",
    "PICKED_UP",
    "IN_TRANSIT",
    "DELIVERED"
];

function isValidTrackingStatus(status) {
    return trackingStatuses.includes(status);
}

function isNextTrackingStatus(currentStatus, newStatus) {
    const currentIndex = trackingStatuses.indexOf(currentStatus);
    const newIndex = trackingStatuses.indexOf(newStatus);

    return newIndex === currentIndex + 1;
}

module.exports = {
    trackingStatuses,
    isValidTrackingStatus,
    isNextTrackingStatus
};