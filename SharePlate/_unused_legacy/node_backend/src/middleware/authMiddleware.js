const jwt = require('jsonwebtoken');
require('dotenv').config();

// Verify JWT token middleware
const protect = (req, res, next) => {
  let token;

  if (
    req.headers.authorization &&
    req.headers.authorization.startsWith('Bearer')
  ) {
    try {
      token = req.headers.authorization.split(' ')[1];
      const decoded = jwt.verify(token, process.env.JWT_SECRET || 'shareplate_super_secret_jwt_key_2026');
      req.user = decoded;
      return next();
    } catch (error) {
      console.error('JWT Token Verification Failed:', error.message);
      return res.status(401).json({ success: false, message: 'Not authorized, token failed or expired' });
    }
  }

  if (!token) {
    return res.status(401).json({ success: false, message: 'Not authorized, no bearer token provided' });
  }
};

// Restrict access by user roles (e.g. 'donor', 'ngo', 'volunteer', 'admin')
const requireRole = (...roles) => {
  return (req, res, next) => {
    if (!req.user || !roles.includes(req.user.role)) {
      return res.status(403).json({
        success: false,
        message: `Forbidden: User role '${req.user?.role}' does not have permission to perform this action.`,
      });
    }
    next();
  };
};

module.exports = {
  protect,
  requireRole,
};
