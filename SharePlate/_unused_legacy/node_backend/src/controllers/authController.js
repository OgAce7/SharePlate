const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { query } = require('../config/db');

// Helper to generate JWT Token
const generateToken = (id, email, role, name) => {
  return jwt.sign(
    { id, email, role, name },
    process.env.JWT_SECRET || 'shareplate_super_secret_jwt_key_2026',
    { expiresIn: '7d' }
  );
};

// @desc    Register a new user
// @route   POST /api/auth/register
// @access  Public
const registerUser = async (req, res, next) => {
  try {
    const { name, email, password, role, phone, address } = req.body;

    if (!name || !email || !password || !role) {
      return res.status(400).json({
        success: false,
        message: 'Please provide all required fields: name, email, password, role',
      });
    }

    const validRoles = ['donor', 'ngo', 'volunteer', 'admin'];
    if (!validRoles.includes(role)) {
      return res.status(400).json({
        success: false,
        message: `Invalid role. Allowed roles are: ${validRoles.join(', ')}`,
      });
    }

    // Check if user already exists
    const userCheck = await query('SELECT * FROM users WHERE email = $1', [email]);
    if (userCheck.rows.length > 0) {
      return res.status(400).json({
        success: false,
        message: 'User with this email already exists',
      });
    }

    // Hash password
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);

    // Insert user
    const newUser = await query(
      `INSERT INTO users (name, email, password_hash, role, phone, address)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id, name, email, role, phone, address, created_at`,
      [name, email, hashedPassword, role, phone || null, address || null]
    );

    const user = newUser.rows[0];
    const token = generateToken(user.id, user.email, user.role, user.name);

    return res.status(201).json({
      success: true,
      message: 'User registered successfully',
      data: {
        user,
        token,
      },
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Login user & get token
// @route   POST /api/auth/login
// @access  Public
const loginUser = async (req, res, next) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        success: false,
        message: 'Please provide both email and password',
      });
    }

    // Find user by email
    const userResult = await query('SELECT * FROM users WHERE email = $1', [email]);
    if (userResult.rows.length === 0) {
      return res.status(401).json({
        success: false,
        message: 'Invalid credentials',
      });
    }

    const user = userResult.rows[0];

    // Check password
    const isMatch = await bcrypt.compare(password, user.password_hash);
    if (!isMatch) {
      return res.status(401).json({
        success: false,
        message: 'Invalid credentials',
      });
    }

    const token = generateToken(user.id, user.email, user.role, user.name);

    return res.status(200).json({
      success: true,
      message: 'Login successful',
      data: {
        user: {
          id: user.id,
          name: user.name,
          email: user.email,
          role: user.role,
          phone: user.phone,
          address: user.address,
        },
        token,
      },
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Get current user profile
// @route   GET /api/auth/me
// @access  Private
const getMe = async (req, res, next) => {
  try {
    const userResult = await query(
      'SELECT id, name, email, role, phone, address, created_at FROM users WHERE id = $1',
      [req.user.id]
    );

    if (userResult.rows.length === 0) {
      return res.status(404).json({ success: false, message: 'User not found' });
    }

    return res.status(200).json({
      success: true,
      data: userResult.rows[0],
    });
  } catch (error) {
    next(error);
  }
};

module.exports = {
  registerUser,
  loginUser,
  getMe,
};
