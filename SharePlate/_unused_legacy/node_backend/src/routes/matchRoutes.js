const express = require('express');
const router = express.Router();
const {
  triggerMatchForDonation,
  getAllMatches,
  updateMatchStatus,
} = require('../controllers/matchController');
const { protect, requireRole } = require('../middleware/authMiddleware');

router.post('/trigger', protect, triggerMatchForDonation);
router.get('/', getAllMatches);
router.patch('/:id/status', protect, updateMatchStatus);

module.exports = router;
