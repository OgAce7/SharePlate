const app = require('./app');
require('dotenv').config();

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(`🚀 SharePlate Backend Server running on port ${PORT}`);
  console.log(`📡 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🏥 Health Check: http://localhost:${PORT}/api/health`);
  console.log(`====================================================`);
});
