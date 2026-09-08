const express = require('express');
const router = express.Router();
const {
  assignVolunteerRoute,
  getVolunteerDeliveries,
  updateDeliveryStatus,
  getAnalyticsDashboard,
} = require('../controllers/routeController');
const { protect } = require('../middleware/authMiddleware');

router.get('/analytics/dashboard', getAnalyticsDashboard);
router.post('/assign', protect, assignVolunteerRoute);
router.get('/', getVolunteerDeliveries);
router.patch('/:id/status', protect, updateDeliveryStatus);

module.exports = router;
