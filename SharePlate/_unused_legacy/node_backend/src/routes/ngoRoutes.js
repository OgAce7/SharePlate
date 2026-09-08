const express = require('express');
const router = express.Router();
const { getAllNgos, getNgoById, updateNgoCapacity } = require('../controllers/ngoController');
const { protect, requireRole } = require('../middleware/authMiddleware');

router.route('/')
  .get(getAllNgos);

router.route('/:id')
  .get(getNgoById);

router.route('/:id/capacity')
  .patch(protect, requireRole('ngo', 'admin'), updateNgoCapacity);

module.exports = router;
