const express = require('express');
const cors = require('cors');
const errorHandler = require('./middleware/errorHandler');

// Route Imports
const authRoutes = require('./routes/authRoutes');
const donationRoutes = require('./routes/donationRoutes');
const ngoRoutes = require('./routes/ngoRoutes');
const matchRoutes = require('./routes/matchRoutes');
const routeRoutes = require('./routes/routeRoutes');

const app = express();

// Middlewares
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Health Check Route
app.get('/api/health', (req, res) => {
  res.status(200).json({
    status: 'online',
    service: 'SharePlate Backend API',
    module: 'Member 4 - Backend & Database',
    timestamp: new Date().toISOString(),
    endpoints: [
      '/api/auth',
      '/api/donations',
      '/api/ngos',
      '/api/matching',
      '/api/routes',
      '/api/routes/analytics/dashboard',
    ],
  });
});

// Root Welcome Endpoint
app.get('/', (req, res) => {
  res.json({
    message: 'Welcome to SharePlate AI Surplus Food Rescue Backend API',
    health: '/api/health',
  });
});

// Mount Routes
app.use('/api/auth', authRoutes);
app.use('/api/donations', donationRoutes);
app.use('/api/ngos', ngoRoutes);
app.use('/api/matching', matchRoutes);
app.use('/api/routes', routeRoutes);

// 404 Route Handler
app.use((req, res, next) => {
  const error = new Error(`Not Found - ${req.originalUrl}`);
  res.status(404);
  next(error);
});

// Central Error Handler
app.use(errorHandler);

module.exports = app;
