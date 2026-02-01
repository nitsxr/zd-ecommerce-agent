/**
 * E2E scenarios: reviewable in the chat interface.
 * Each scenario has steps (messages) and expected last response (agent, responseContains).
 */
const E2E_SCENARIOS = [
  {
    id: "cancel-order",
    name: "Cancel order (ORD-4567)",
    description: "Single turn: cancel order with valid ID -> OrderCancellationAgent, response mentions cancellation.",
    steps: [{ message: "I want to cancel my order ORD-4567" }],
    expectLast: {
      agent: "OrderCancellationAgent",
      responseContains: ["ORD-4567", "cancelled"],
    },
  },
  {
    id: "track-order",
    name: "Track order (ORD-1001)",
    description: "Single turn: track order -> OrderTrackingAgent.",
    steps: [{ message: "Track order ORD-1001" }],
    expectLast: {
      agent: "OrderTrackingAgent",
      responseContains: ["ORD-1001", "status", "delivery"],
    },
  },
  {
    id: "product-question",
    name: "Product question (Bluetooth headphones)",
    description: "Single turn: product/return question -> ProductInfoAgent.",
    steps: [{ message: "Can I return my Bluetooth headphones?" }],
    expectLast: {
      agent: "ProductInfoAgent",
      responseContains: ["return", "Bluetooth", "30"],
    },
  },
  {
    id: "multi-turn-cancel-that",
    name: "Multi-turn: cancel then \"cancel that\"",
    description: "Turn 1: cancel ORD-4567. Turn 2: \"cancel that\" -> same order from context.",
    steps: [
      { message: "I want to cancel my order ORD-4567" },
      { message: "cancel that" },
    ],
    expectLast: {
      agent: "OrderCancellationAgent",
      responseContains: ["ORD-4567", "cancelled"],
    },
  },
  {
    id: "missing-order-id",
    name: "Missing order ID (clarification)",
    description: "Cancel intent without order_id -> OrchestratorAgent asks for order ID.",
    steps: [{ message: "I want to cancel my order" }],
    expectLast: {
      agent: "OrchestratorAgent",
      responseContains: ["order ID", "ORD-"],
    },
  },
  {
    id: "24h-rule-old-order",
    name: "24h rule: old order rejected (ORD-1002)",
    description: "Cancel order older than 24h -> rejection message.",
    steps: [{ message: "Cancel order ORD-1002" }],
    expectLast: {
      agent: "OrderCancellationAgent",
      responseContains: ["couldn't", "24", "older", "not allowed"],
    },
  },
];

function getScenarios() {
  return E2E_SCENARIOS;
}

function getScenarioById(id) {
  return E2E_SCENARIOS.find((s) => s.id === id) || null;
}
