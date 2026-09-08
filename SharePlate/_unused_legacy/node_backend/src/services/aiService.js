const axios = require('axios');
require('dotenv').config();

const AI_BASE_URL = process.env.AI_MATCHING_SERVICE_URL || 'http://127.0.0.1:8000';

// Service helper to communicate with Python AI FastAPI Microservices
class AIService {
  // Score food urgency and waste risk (Module 2)
  static async scoreFoodUrgency(foodCategory, quantityKg, donationTimestamp) {
    try {
      const response = await axios.post(`${AI_BASE_URL}/score/food`, {
        food_category: foodCategory,
        quantity_kg: quantityKg,
        donation_timestamp: donationTimestamp || new Date().toISOString(),
      });
      return response.data;
    } catch (error) {
      console.warn(`[AI Microservice] /score/food unavailable (${error.message}). Using fallback calculation.`);
      // Heuristic fallback if Python API is offline
      const wasteRisk = foodCategory === 'cooked_meal' ? 0.85 : 0.35;
      return {
        food_category: foodCategory,
        quantity_kg: quantityKg,
        waste_risk: wasteRisk,
        estimated_meals: quantityKg * 2.5,
        is_fallback: true,
      };
    }
  }

  // Predict NGO Demand (Module 2)
  static async predictNgoDemand(recipientId, targetDate) {
    try {
      const response = await axios.post(`${AI_BASE_URL}/predict/demand`, {
        recipient_id: recipientId,
        date: targetDate || new Date().toISOString().split('T')[0],
      });
      return response.data;
    } catch (error) {
      console.warn(`[AI Microservice] /predict/demand unavailable (${error.message}). Using fallback.`);
      return {
        recipient_id: recipientId,
        date: targetDate,
        predicted_quantity_kg: 50.0,
        is_fallback: true,
      };
    }
  }

  // Trigger Matching Engine (Module 1)
  static async triggerMatching(donationId, donationData, availableNgos) {
    try {
      const response = await axios.post(`${AI_BASE_URL}/match`, {
        donation_id: donationId,
        donation: donationData,
        ngos: availableNgos,
      });
      return response.data;
    } catch (error) {
      console.warn(`[AI Microservice] /match unavailable (${error.message}). Using spatial score baseline.`);
      // Haversine distance heuristic baseline
      return null;
    }
  }
}

module.exports = AIService;
