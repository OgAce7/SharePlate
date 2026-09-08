const express = require('express');
const router = express.Router();
const {
  createDonation,
  getAllDonations,
  getDonationById,
  updateDonationStatus,
} = require('../controllers/donationController');
const { protect, requireRole } = require('../middleware/authMiddleware');

router.route('/')
  .get(getAllDonations)
  .post(protect, requireRole('donor', 'admin'), createDonation);

router.route('/:id')
  .get(getDonationById);

router.route('/:id/status')
  .patch(protect, updateDonationStatus);

module.exports = router;
