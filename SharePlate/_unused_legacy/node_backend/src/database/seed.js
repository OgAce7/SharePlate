const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');
const { pool } = require('../config/db');

const runSeed = async () => {
  console.log('🌱 Starting Database Seeding Process...');

  try {
    // 1. Run Schema Creation Script
    const schemaPath = path.join(__dirname, 'schema.sql');
    const schemaSql = fs.readFileSync(schemaPath, 'utf-8');
    await pool.query(schemaSql);
    console.log('✅ Database schema initialized.');

    // 2. Insert Default Users (Auth Test Accounts)
    const salt = await bcrypt.genSalt(10);
    const defaultPassword = await bcrypt.hash('password123', salt);

    const usersToInsert = [
      ['System Admin', 'admin@shareplate.org', defaultPassword, 'admin', '+919876543210', 'Jaipur HQ'],
      ['Grand Hotel Donor', 'donor@hotel.com', defaultPassword, 'donor', '+919876543211', 'MI Road, Jaipur'],
      ['Sanganer NGO Center', 'ngo@sanganer.org', defaultPassword, 'ngo', '+919876543212', 'Sanganer, Jaipur'],
      ['Ramesh Volunteer', 'volunteer@hero.com', defaultPassword, 'volunteer', '+919876543213', 'Malviya Nagar, Jaipur'],
    ];

    for (const u of usersToInsert) {
      await pool.query(
        `INSERT INTO users (name, email, password_hash, role, phone, address)
         VALUES ($1, $2, $3, $4, $5, $6)
         ON CONFLICT (email) DO NOTHING`,
        u
      );
    }
    console.log('✅ Default users seeded.');

    // 3. Parse and Seed ngos.csv
    const ngosCsvPath = path.join(__dirname, '../../data/ngos.csv');
    if (fs.existsSync(ngosCsvPath)) {
      const csvData = fs.readFileSync(ngosCsvPath, 'utf-8').trim().split('\n');
      const headers = csvData[0].split(',');

      for (let i = 1; i < csvData.length; i++) {
        const row = csvData[i].split(',');
        if (row.length >= 13) {
          const ngo_id = row[0].trim();
          const ngo_name = row[1].trim();
          const latitude = parseFloat(row[2]);
          const longitude = parseFloat(row[3]);
          const food_type = row[4].trim();
          const vegetarian = parseInt(row[5]);
          const vegan = parseInt(row[6]);
          const current_demand_meals = parseInt(row[7]);
          const max_capacity_meals = parseInt(row[8]);
          const current_demand_kgs = parseInt(row[9]);
          const max_capacity_kgs = parseInt(row[10]);
          const pickup_radius_km = parseFloat(row[11]);
          const reliability_score = parseFloat(row[12]);

          await pool.query(
            `INSERT INTO ngos (
              id, ngo_name, latitude, longitude, food_type, vegetarian, vegan,
              current_demand_meals, max_capacity_meals, current_demand_kgs, max_capacity_kgs,
              pickup_radius_km, reliability_score
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            ON CONFLICT (id) DO UPDATE SET
              current_demand_meals = EXCLUDED.current_demand_meals,
              current_demand_kgs = EXCLUDED.current_demand_kgs,
              reliability_score = EXCLUDED.reliability_score`,
            [
              ngo_id, ngo_name, latitude, longitude, food_type, vegetarian, vegan,
              current_demand_meals, max_capacity_meals, current_demand_kgs, max_capacity_kgs,
              pickup_radius_km, reliability_score
            ]
          );
        }
      }
      console.log('✅ NGO dataset seeded.');
    }

    // 4. Parse and Seed donations.csv
    const donationsCsvPath = path.join(__dirname, '../../data/donations.csv');
    if (fs.existsSync(donationsCsvPath)) {
      const csvData = fs.readFileSync(donationsCsvPath, 'utf-8').trim().split('\n');
      for (let i = 1; i < csvData.length; i++) {
        const row = csvData[i].split(',');
        if (row.length >= 11) {
          const donation_id = row[0].trim();
          const food_type = row[1].trim();
          const quantity = parseFloat(row[2]);
          const unit = row[3].trim();
          const latitude = parseFloat(row[4]);
          const longitude = parseFloat(row[5]);
          const vegetarian = parseInt(row[6]);
          const vegan = parseInt(row[7]);
          const perishability = row[8].trim();
          const hours_until_expiry = parseFloat(row[9]);
          const pickup_required = parseInt(row[10]);

          await pool.query(
            `INSERT INTO donations (
              id, donor_type, food_type, quantity, unit, latitude, longitude,
              vegetarian, vegan, perishability, hours_until_expiry, pickup_required, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 'available')
            ON CONFLICT (id) DO NOTHING`,
            [
              donation_id, 'restaurant', food_type, quantity, unit, latitude, longitude,
              vegetarian, vegan, perishability, hours_until_expiry, pickup_required
            ]
          );
        }
      }
      console.log('✅ Donation dataset seeded.');
    }

    console.log('🚀 Database seeding complete!');
    process.exit(0);
  } catch (error) {
    console.error('❌ Error seeding database:', error);
    process.exit(1);
  }
};

runSeed();
