const { query } = require('../config/db');

// @desc    Get list of all registered NGOs
// @route   GET /api/ngos
// @access  Public / Authenticated
const getAllNgos = async (req, res, next) => {
  try {
    const { food_type, min_reliability, limit = 50 } = req.query;

    let sql = 'SELECT * FROM ngos WHERE 1=1';
    const params = [];

    if (food_type) {
      params.push(`%${food_type}%`);
      sql += ` AND food_type ILIKE $${params.length}`;
    }

    if (min_reliability) {
      params.push(parseFloat(min_reliability));
      sql += ` AND reliability_score >= $${params.length}`;
    }

    sql += ' ORDER BY reliability_score DESC';

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

// @desc    Get NGO details by ID
// @route   GET /api/ngos/:id
// @access  Public / Authenticated
const getNgoById = async (req, res, next) => {
  try {
    const { id } = req.params;
    const result = await query('SELECT * FROM ngos WHERE id = $1', [id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ success: false, message: 'NGO not found' });
    }

    return res.status(200).json({
      success: true,
      data: result.rows[0],
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Update NGO demand & capacity
// @route   PATCH /api/ngos/:id/capacity
// @access  Private (NGO / Admin)
const updateNgoCapacity = async (req, res, next) => {
  try {
    const { id } = req.params;
    const { current_demand_meals, max_capacity_meals, current_demand_kgs, max_capacity_kgs } = req.body;

    const result = await query(
      `UPDATE ngos SET
        current_demand_meals = COALESCE($1, current_demand_meals),
        max_capacity_meals = COALESCE($2, max_capacity_meals),
        current_demand_kgs = COALESCE($3, current_demand_kgs),
        max_capacity_kgs = COALESCE($4, max_capacity_kgs)
       WHERE id = $5
       RETURNING *`,
      [current_demand_meals, max_capacity_meals, current_demand_kgs, max_capacity_kgs, id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ success: false, message: 'NGO not found' });
    }

    return res.status(200).json({
      success: true,
      message: 'NGO demand & capacity updated successfully',
      data: result.rows[0],
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  getAllNgos,
  getNgoById,
  updateNgoCapacity,
};
