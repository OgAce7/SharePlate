const { query } = require('../config/db');
const AIService = require('../services/aiService');

// Haversine Distance Calculation (in kilometers)
function calculateDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth radius in KM
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) *
      Math.cos(lat2 * (Math.PI / 180)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// @desc    Trigger AI Matching Engine for a specific donation ID
// @route   POST /api/matching/trigger
// @access  Private (Donor / Admin / NGO)
const triggerMatchForDonation = async (req, res, next) => {
  try {
    const { donation_id } = req.body;

    if (!donation_id) {
      return res.status(400).json({ success: false, message: 'Please provide donation_id' });
    }

    // 1. Fetch donation details
    const donationRes = await query('SELECT * FROM donations WHERE id = $1', [donation_id]);
    if (donationRes.rows.length === 0) {
      return res.status(404).json({ success: false, message: 'Donation not found' });
    }
    const donation = donationRes.rows[0];

    // 2. Fetch all candidate NGOs
    const ngosRes = await query('SELECT * FROM ngos');
    const candidateNgos = ngosRes.rows;

    if (candidateNgos.length === 0) {
      return res.status(400).json({ success: false, message: 'No registered NGOs found in database' });
    }

    // 3. Get AI Food Urgency Score
    const foodUrgency = await AIService.scoreFoodUrgency(
      donation.food_type,
      parseFloat(donation.quantity),
      donation.created_at
    );
    const wasteRiskScore = foodUrgency.waste_risk || 0.5;

    // 4. Try AI Python service match first, or perform intelligent spatial + criteria matching
    const rankedMatches = [];

    for (const ngo of candidateNgos) {
      // Dietary filter check
      if (donation.vegetarian === 1 && ngo.vegetarian === 0) continue;
      if (donation.vegan === 1 && ngo.vegan === 0) continue;

      // Distance calculation
      const dist = calculateDistanceKm(
        parseFloat(donation.latitude),
        parseFloat(donation.longitude),
        parseFloat(ngo.latitude),
        parseFloat(ngo.longitude)
      );

      const maxDist = parseFloat(ngo.pickup_radius_km) || 15.0;
      if (dist > maxDist) continue;

      // Composite match score calculation
      // Score = (1 / (1 + distance)) * 0.4 + reliability_score * 0.3 + wasteRiskScore * 0.3
      const distanceScore = 1 / (1 + dist);
      const reliabilityScore = parseFloat(ngo.reliability_score) || 0.85;
      const compositeScore = (distanceScore * 0.4) + (reliabilityScore * 0.3) + (wasteRiskScore * 0.3);

      rankedMatches.push({
        ngo_id: ngo.id,
        ngo_name: ngo.ngo_name,
        distance_km: parseFloat(dist.toFixed(2)),
        match_score: parseFloat(compositeScore.toFixed(4)),
        reliability_score: reliabilityScore,
      });
    }

    // Sort by highest match score
    rankedMatches.sort((a, b) => b.match_score - a.match_score);

    // Save top matches to DB
    const createdMatches = [];
    const topMatches = rankedMatches.slice(0, 5);

    for (const m of topMatches) {
      const matchInsert = await query(
        `INSERT INTO matches (donation_id, ngo_id, match_score, waste_risk_score, distance_km, status)
         VALUES ($1, $2, $3, $4, $5, 'pending')
         RETURNING *`,
        [donation.id, m.ngo_id, m.match_score, wasteRiskScore, m.distance_km]
      );
      createdMatches.push({
        ...matchInsert.rows[0],
        ngo_name: m.ngo_name,
      });
    }

    // Update donation status to matched
    await query("UPDATE donations SET status = 'matched' WHERE id = $1", [donation.id]);

    return res.status(200).json({
      success: true,
      message: `Found ${createdMatches.length} suitable NGO matches for donation ${donation_id}`,
      data: {
        donation,
        waste_risk_score: wasteRiskScore,
        matches: createdMatches,
      },
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Get all matches
// @route   GET /api/matches
// @access  Public / Authenticated
const getAllMatches = async (req, res, next) => {
  try {
    const { status, ngo_id, donation_id } = req.query;

    let sql = `
      SELECT m.*, d.food_type, d.quantity, d.unit, d.perishability, n.ngo_name
      FROM matches m
      JOIN donations d ON m.donation_id = d.id
      JOIN ngos n ON m.ngo_id = n.id
      WHERE 1=1
    `;
    const params = [];

    if (status) {
      params.push(status);
      sql += ` AND m.status = $${params.length}`;
    }
    if (ngo_id) {
      params.push(ngo_id);
      sql += ` AND m.ngo_id = $${params.length}`;
    }
    if (donation_id) {
      params.push(donation_id);
      sql += ` AND m.donation_id = $${params.length}`;
    }

    sql += ' ORDER BY m.matched_at DESC';

    const result = await query(sql, params);

    return res.status(200).json({
      success: true,
      count: result.rows.length,
      data: result.rows,
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Accept or Reject match assignment
// @route   PATCH /api/matches/:id/status
// @access  Private (NGO / Admin)
const updateMatchStatus = async (req, res, next) => {
  try {
    const { id } = req.params;
    const { status } = req.body;

    const allowed = ['accepted', 'rejected', 'in_transit', 'completed', 'cancelled'];
    if (!status || !allowed.includes(status)) {
      return res.status(400).json({
        success: false,
        message: `Invalid status. Allowed values: ${allowed.join(', ')}`,
      });
    }

    const completedAt = status === 'completed' ? new Date() : null;

    const result = await query(
      `UPDATE matches SET status = $1, completed_at = COALESCE($2, completed_at)
       WHERE id = $3 RETURNING *`,
      [status, completedAt, id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ success: false, message: 'Match record not found' });
    }

    return res.status(200).json({
      success: true,
      message: `Match status updated to ${status}`,
      data: result.rows[0],
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  triggerMatchForDonation,
  getAllMatches,
  updateMatchStatus,
};
