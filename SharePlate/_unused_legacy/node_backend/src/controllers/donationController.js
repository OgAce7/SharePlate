const { query } = require('../config/db');
const AIService = require('../services/aiService');

// @desc    Create new surplus food donation
// @route   POST /api/donations
// @access  Private (Donor / Admin)
const createDonation = async (req, res, next) => {
  try {
    const {
      donor_type,
      food_type,
      quantity,
      unit,
      latitude,
      longitude,
      vegetarian,
      vegan,
      perishability,
      hours_until_expiry,
      pickup_required,
    } = req.body;

    if (!donor_type || !food_type || !quantity || !unit || latitude === undefined || longitude === undefined) {
      return res.status(400).json({
        success: false,
        message: 'Please provide all mandatory fields: donor_type, food_type, quantity, unit, latitude, longitude',
      });
    }

    // Auto-generate donation ID (e.g. D1000 + random suffix or count)
    const idCount = await query('SELECT COUNT(*) FROM donations');
    const newCount = parseInt(idCount.rows[0].count) + 1;
    const donation_id = `D${String(newCount).padStart(4, '0')}`;

    // Get AI Food Urgency / Waste Risk Score
    const urgencyScore = await AIService.scoreFoodUrgency(food_type, parseFloat(quantity), new Date().toISOString());

    const result = await query(
      `INSERT INTO donations (
        id, donor_id, donor_type, food_type, quantity, unit, latitude, longitude,
        vegetarian, vegan, perishability, hours_until_expiry, pickup_required, status
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, 'available')
      RETURNING *`,
      [
        donation_id,
        req.user?.id || null,
        donor_type,
        food_type,
        parseFloat(quantity),
        unit,
        parseFloat(latitude),
        parseFloat(longitude),
        vegetarian !== undefined ? parseInt(vegetarian) : 1,
        vegan !== undefined ? parseInt(vegan) : 0,
        perishability || 'medium',
        hours_until_expiry ? parseFloat(hours_until_expiry) : 12,
        pickup_required !== undefined ? parseInt(pickup_required) : 1,
      ]
    );

    return res.status(201).json({
      success: true,
      message: 'Donation submitted successfully',
      data: {
        donation: result.rows[0],
        ai_assessment: urgencyScore,
      },
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Get all donations (with optional status & filter query params)
// @route   GET /api/donations
// @access  Public / Authenticated
const getAllDonations = async (req, res, next) => {
  try {
    const { status, food_type, perishability, limit = 50 } = req.query;

    let sql = 'SELECT * FROM donations WHERE 1=1';
    const params = [];

    if (status) {
      params.push(status);
      sql += ` AND status = $${params.length}`;
    }

    if (food_type) {
      params.push(`%${food_type}%`);
      sql += ` AND food_type ILIKE $${params.length}`;
    }

    if (perishability) {
      params.push(perishability);
      sql += ` AND perishability = $${params.length}`;
    }

    sql += ' ORDER BY created_at DESC';

    params.push(parseInt(limit));
    sql += ` LIMIT $${params.length}`;

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

// @desc    Get donation details by ID
// @route   GET /api/donations/:id
// @access  Public / Authenticated
const getDonationById = async (req, res, next) => {
  try {
    const { id } = req.params;
    const result = await query('SELECT * FROM donations WHERE id = $1', [id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ success: false, message: 'Donation not found' });
    }

    return res.status(200).json({
      success: true,
      data: result.rows[0],
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Update donation status
// @route   PATCH /api/donations/:id/status
// @access  Private (Donor / NGO / Admin)
const updateDonationStatus = async (req, res, next) => {
  try {
    const { id } = req.params;
    const { status } = req.body;

    const allowedStatuses = ['available', 'matched', 'picked_up', 'delivered', 'cancelled'];
    if (!status || !allowedStatuses.includes(status)) {
      return res.status(400).json({
        success: false,
        message: `Invalid status. Allowed values: ${allowedStatuses.join(', ')}`,
      });
    }

    const result = await query(
      'UPDATE donations SET status = $1 WHERE id = $2 RETURNING *',
      [status, id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ success: false, message: 'Donation not found' });
    }

    return res.status(200).json({
      success: true,
      message: `Donation status updated to ${status}`,
      data: result.rows[0],
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  createDonation,
  getAllDonations,
  getDonationById,
  updateDonationStatus,
};
