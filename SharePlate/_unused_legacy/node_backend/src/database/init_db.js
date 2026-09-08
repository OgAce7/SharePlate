const { Client } = require('pg');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

async function initPostgreSQL() {
  console.log('🔄 Attempting PostgreSQL Database Initialization...');

  const host = process.env.DB_HOST || 'localhost';
  const port = parseInt(process.env.DB_PORT || '5432');
  const user = process.env.DB_USER || 'postgres';
  const password = process.env.DB_PASSWORD || 'postgres';
  const targetDb = process.env.DB_NAME || 'shareplate_db';

  // Step 1: Connect to default 'postgres' database to create 'shareplate_db' if it doesn't exist
  const rootClient = new Client({
    host,
    port,
    user,
    password,
    database: 'postgres',
    connectionTimeoutMillis: 5000,
  });

  try {
    await rootClient.connect();
    console.log('✅ Connected to PostgreSQL server on localhost:5432.');

    // Check if target database exists
    const dbCheck = await rootClient.query(
      "SELECT 1 FROM pg_database WHERE datname = $1",
      [targetDb]
    );

    if (dbCheck.rows.length === 0) {
      console.log(`🔨 Database '${targetDb}' does not exist. Creating database now...`);
      await rootClient.query(`CREATE DATABASE "${targetDb}"`);
      console.log(`✨ Database '${targetDb}' created successfully!`);
    } else {
      console.log(`ℹ️ Database '${targetDb}' already exists.`);
    }

    await rootClient.end();
  } catch (error) {
    console.error(`❌ Failed to connect to PostgreSQL server: ${error.message}`);
    console.log(`
-------------------------------------------------------------
💡 PostgreSQL Connection Guide:
1. Please ensure PostgreSQL service is running on your machine.
2. Check your PostgreSQL password set during installation.
3. Update the DB_PASSWORD value in backend/.env file if needed.
-------------------------------------------------------------
`);
    process.exit(1);
  }

  // Step 2: Run Seed Script to initialize tables and load dataset
  console.log('🚀 Initializing database schema and seeding data...');
  require('./seed.js');
}

initPostgreSQL();
