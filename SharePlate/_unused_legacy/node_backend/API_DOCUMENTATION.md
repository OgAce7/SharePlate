# SharePlate Backend API Reference

**Base URL**: `http://localhost:5000/api`

---

## 🔑 Authentication Endpoints (`/api/auth`)

### 1. Register User
- **POST** `/api/auth/register`
- **Request Body**:
```json
{
  "name": "Sanganer Relief NGO",
  "email": "ngo@sanganer.org",
  "password": "password123",
  "role": "ngo",
  "phone": "+919876543210",
  "address": "Sanganer, Jaipur"
}
```
- **Response**: `201 Created` with JWT token.

### 2. Login User
- **POST** `/api/auth/login`
- **Request Body**:
```json
{
  "email": "ngo@sanganer.org",
  "password": "password123"
}
```
- **Response**: `200 OK` with user payload and Bearer `token`.

### 3. Get Current Profile
- **GET** `/api/auth/me`
- **Headers**: `Authorization: Bearer <TOKEN>`

---

## 🍲 Surplus Food Donations Endpoints (`/api/donations`)

### 1. Submit Surplus Food Donation
- **POST** `/api/donations`
- **Headers**: `Authorization: Bearer <TOKEN>` (Role: `donor` or `admin`)
- **Request Body**:
```json
{
  "donor_type": "hotel",
  "food_type": "cooked_meal",
  "quantity": 150,
  "unit": "meals",
  "latitude": 26.9100,
  "longitude": 75.7850,
  "vegetarian": 1,
  "vegan": 0,
  "perishability": "high",
  "hours_until_expiry": 4,
  "pickup_required": 1
}
```

### 2. List All Donations
- **GET** `/api/donations?status=available&perishability=high`

### 3. Update Donation Status
- **PATCH** `/api/donations/:id/status`
- **Request Body**: `{"status": "matched"}` (Options: `available`, `matched`, `picked_up`, `delivered`, `cancelled`)

---

## 🏢 NGO Demand & Capacity Endpoints (`/api/ngos`)

### 1. List All NGOs
- **GET** `/api/ngos?food_type=cooked_meal&min_reliability=0.8`

### 2. Get NGO Profile
- **GET** `/api/ngos/:id`

### 3. Update NGO Capacity & Demand
- **PATCH** `/api/ngos/:id/capacity`
- **Request Body**:
```json
{
  "current_demand_meals": 100,
  "max_capacity_meals": 200,
  "current_demand_kgs": 50,
  "max_capacity_kgs": 100
}
```

---

## 🧠 AI Matching Engine Endpoints (`/api/matching`)

### 1. Trigger AI Match for Donation
- **POST** `/api/matching/trigger`
- **Request Body**:
```json
{
  "donation_id": "D001"
}
```
- **Returns**: Top 5 suitable NGO matches ranked by distance, capacity, dietary preferences, and AI food waste-risk score.

### 2. List Active Matches
- **GET** `/api/matching?status=pending`

### 3. Update Match Status
- **PATCH** `/api/matching/:id/status`
- **Request Body**: `{"status": "accepted"}` (Options: `accepted`, `rejected`, `in_transit`, `completed`, `cancelled`)

---

## 🗺️ Route Optimization & Deliveries (`/api/routes`)

### 1. Assign Volunteer Route
- **POST** `/api/routes/assign`
- **Request Body**:
```json
{
  "match_id": 1,
  "pickup_address": "Hotel Royal, MI Road, Jaipur",
  "delivery_address": "Sanganer Relief NGO, Jaipur"
}
```

### 2. Get Delivery Assignments
- **GET** `/api/routes?status=assigned`

### 3. Analytics Impact Dashboard
- **GET** `/api/routes/analytics/dashboard`
- **Returns**: Total rescued food metrics, active donations, NGOs served, and delivery breakdown.
