-- SharePlate Database Schema (PostgreSQL)

-- Extension for UUID generation if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS TABLE (Auth & Access Control)
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) CHECK (role IN ('donor', 'ngo', 'volunteer', 'admin')) NOT NULL,
  phone VARCHAR(20),
  address TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. NGOS TABLE (Dataset Aligned)
CREATE TABLE IF NOT EXISTS ngos (
  id VARCHAR(50) PRIMARY KEY,
  user_id INT REFERENCES users(id) ON DELETE SET NULL,
  ngo_name VARCHAR(150) NOT NULL,
  latitude DECIMAL(9,6) NOT NULL,
  longitude DECIMAL(9,6) NOT NULL,
  food_type VARCHAR(100),
  vegetarian INT DEFAULT 1,
  vegan INT DEFAULT 0,
  current_demand_meals INT DEFAULT 0,
  max_capacity_meals INT DEFAULT 0,
  current_demand_kgs INT DEFAULT 0,
  max_capacity_kgs INT DEFAULT 0,
  pickup_radius_km DECIMAL(5,2) DEFAULT 10.0,
  reliability_score DECIMAL(3,2) DEFAULT 0.85,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. DONATIONS TABLE (Dataset Aligned)
CREATE TABLE IF NOT EXISTS donations (
  id VARCHAR(50) PRIMARY KEY,
  donor_id INT REFERENCES users(id) ON DELETE SET NULL,
  donor_type VARCHAR(50) NOT NULL,
  food_type VARCHAR(100) NOT NULL,
  quantity DECIMAL(8,2) NOT NULL,
  unit VARCHAR(20) CHECK (unit IN ('kg', 'meals')) NOT NULL,
  latitude DECIMAL(9,6) NOT NULL,
  longitude DECIMAL(9,6) NOT NULL,
  vegetarian INT DEFAULT 1,
  vegan INT DEFAULT 0,
  perishability VARCHAR(20) CHECK (perishability IN ('low', 'medium', 'high')) DEFAULT 'medium',
  hours_until_expiry DECIMAL(5,2) NOT NULL,
  pickup_required INT DEFAULT 1,
  status VARCHAR(30) CHECK (status IN ('available', 'matched', 'picked_up', 'delivered', 'cancelled')) DEFAULT 'available',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. MATCHES TABLE (AI Engine Output & Workflow Tracking)
CREATE TABLE IF NOT EXISTS matches (
  id SERIAL PRIMARY KEY,
  donation_id VARCHAR(50) REFERENCES donations(id) ON DELETE CASCADE,
  ngo_id VARCHAR(50) REFERENCES ngos(id) ON DELETE CASCADE,
  match_score DECIMAL(5,4),
  waste_risk_score DECIMAL(5,4),
  distance_km DECIMAL(6,2),
  status VARCHAR(30) CHECK (status IN ('pending', 'accepted', 'rejected', 'in_transit', 'completed', 'cancelled')) DEFAULT 'pending',
  matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP
);

-- 5. DELIVERIES / ROUTES TABLE (Module 3 Integration)
CREATE TABLE IF NOT EXISTS deliveries (
  id SERIAL PRIMARY KEY,
  match_id INT REFERENCES matches(id) ON DELETE CASCADE,
  volunteer_id INT REFERENCES users(id) ON DELETE SET NULL,
  pickup_address TEXT,
  delivery_address TEXT,
  status VARCHAR(30) CHECK (status IN ('assigned', 'en_route_to_pickup', 'picked_up', 'en_route_to_ngo', 'delivered')) DEFAULT 'assigned',
  assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  delivered_at TIMESTAMP
);

-- 6. SAFETY LOGS TABLE (Module 6 Food Safety Checks)
CREATE TABLE IF NOT EXISTS safety_logs (
  id SERIAL PRIMARY KEY,
  donation_id VARCHAR(50) REFERENCES donations(id) ON DELETE CASCADE,
  inspector_id INT REFERENCES users(id) ON DELETE SET NULL,
  temperature_c DECIMAL(4,1),
  hygiene_checked BOOLEAN DEFAULT TRUE,
  packaging_intact BOOLEAN DEFAULT TRUE,
  safety_status VARCHAR(20) CHECK (safety_status IN ('passed', 'flagged', 'rejected')) DEFAULT 'passed',
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- INDEXES FOR PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_donations_status ON donations(status);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_ngos_coords ON ngos(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_donations_coords ON donations(latitude, longitude);
