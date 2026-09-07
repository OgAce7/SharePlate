function getSafetyStatus(hoursUntilExpiry) {
    if (hoursUntilExpiry <= 0) {
        return "EXPIRED";
    }

    if (hoursUntilExpiry <= 1) {
        return "CRITICAL";
    }

    if (hoursUntilExpiry <= 4) {
        return "WARNING";
    }

    return "SAFE";
}

module.exports = { getSafetyStatus };