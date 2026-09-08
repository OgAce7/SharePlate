const { query } = require('../config/db');

// @desc    Assign volunteer to a delivery route
// @route   POST /api/routes/assign
// @access  Private (Volunteer / Admin)
const assignVolunteerRoute = async (req, res, next) => {
  try {
    const { match_id, pickup_address, delivery_address } = req.body;

    if (!match_id) {
      return res.status(400).json({ success: false, message: 'Please provide match_id' });
    }

    // Verify match exists
    const matchRes = await query('SELECT * FROM matches WHERE id = $1', [match_id]);
    if (matchRes.rows.length === 0) {
      return res.status(404).json({ success: false, message: 'Match record not found' });
    }

    const deliveryRes = await query(
      `INSERT INTO deliveries (match_id, volunteer_id, pickup_address, delivery_address, status)
       VALUES ($1, $2, $3, $4, 'assigned')
       RETURNING *`,
      [
        match_id,
        req.user?.id || null,
        pickup_address || 'Donor Location',
        delivery_address || 'NGO Distribution Center',
      ]
    );

    // Update match status to in_transit
    await query("UPDATE matches SET status = 'in_transit' WHERE id = $1", [match_id]);

    return res.status(201).json({
      success: true,
      message: 'Volunteer route assigned successfully',
      data: deliveryRes.rows[0],
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Get all delivery routes
// @route   GET /api/routes
// @access  Public / Authenticated
const getVolunteerDeliveries = async (req, res, next) => {
  try {
    const { status, volunteer_id } = req.query;

    let sql = `
      SELECT del.*, m.donation_id, m.ngo_id, d.food_type, d.quantity, d.unit, n.ngo_name
      FROM deliveries del
      JOIN matches m ON del.match_id = m.id
      JOIN donations d ON m.donation_id = d.id
      JOIN ngos n ON m.ngo_id = n.id
      WHERE 1=1
    `;
    const params = [];

    if (status) {
      params.push(status);
      sql += ` AND del.status = $${params.length}`;
    }
    if (volunteer_id) {
      params.push(parseInt(volunteer_id));
      sql += ` AND del.volunteer_id = $${params.length}`;
    }

    sql += ' ORDER BY del.assigned_at DESC';

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

// @desc    Update delivery status
// @route   PATCH /api/routes/:id/status
// @access  Private (Volunteer / Admin)
const updateDeliveryStatus = async (req, res, next) => {
  try {
    const { id } = req.params;
    const { status } = req.body;

    const validStatuses = ['assigned', 'en_route_to_pickup', 'picked_up', 'en_route_to_ngo', 'delivered'];
    if (!status || !validStatuses.includes(status)) {
      return res.status(400).json({
        success: false,
        message: `Invalid status. Allowed values: ${validStatuses.join(', ')}`,
      });
    }

    const deliveredAt = status === 'delivered' ? new Date() : null;

    const result = await query(
      `UPDATE deliveries SET status = $1, delivered_at = COALESCE($2, delivered_at)
       WHERE id = $3 RETURNING *`,
      [status, deliveredAt, id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ success: false, message: 'Delivery record not found' });
    }

    // If delivered, mark match as completed
    if (status === 'delivered') {
      const delivery = result.rows[0];
      await query("UPDATE matches SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = $1", [delivery.match_id]);
    }

    return res.status(200).json({
      success: true,
      message: `Delivery status updated to ${status}`,
      data: result.rows[0],
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Analytics & Platform Impact Summary Dashboard
// @route   GET /api/analytics/dashboard
// @access  Public / Authenticated
const getAnalyticsDashboard = async (req, res, next) => {
  try {
    const totalDonationsRes = await query('SELECT COUNT(*) FROM donations');
    const totalNgosRes = await query('SELECT COUNT(*) FROM ngos');
    const totalMatchesRes = await query('SELECT COUNT(*) FROM matches');
    const activeDonationsRes = await query("SELECT COUNT(*) FROM donations WHERE status = 'available'");
    const completedMatchesRes = await query("SELECT COUNT(*) FROM matches WHERE status = 'completed'");

    // Total quantity rescued (converted estimate to meals)
    const quantityRes = await query('SELECT SUM(quantity) as total_qty, unit FROM donations GROUP BY unit');

    return res.status(200).json({
      success: true,
      data: {
        total_donations: parseInt(totalDonationsRes.rows[0].count),
        total_ngos: parseInt(totalNgosRes.rows[0].count),
        total_matches_generated: parseInt(totalMatchesRes.rows[0].count),
        active_available_donations: parseInt(activeDonationsRes.rows[0].count),
        completed_deliveries: parseInt(completedMatchesRes.rows[0].count),
        quantity_breakdown: quantityRes.rows,
      },
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  assignVolunteerRoute,
  getVolunteerDeliveries,
  updateDeliveryStatus,
  getAnalyticsDashboard,
};
