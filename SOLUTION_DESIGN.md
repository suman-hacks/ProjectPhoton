# Solution Design: Project Photon

## Overview
This document outlines the architecture for "Project Photon." The goal is to build a highly polished Streamlit application that fuses ultra-compressed classical AI with quantum mechanics. It simulates a 1.58-bit feature extractor feeding directly into an IBM Qiskit Quantum Neural Network to optimize complex payment routing tradeoffs.

## File Architecture
The project will be contained in four primary Python files:
1. `app.py`: The Streamlit frontend and UI orchestrator.
2. `bitnet_encoder.py`: Simulates the 1.58-bit classical AI extraction via PyTorch.
3. `qiskit_router.py`: The IBM Qiskit QNN that evaluates and ranks the routes.
4. `mock_data.py`: Contains the synthetic payment scenarios and route candidates.

---

## Phase 1: Data Models & UI Shell
**Goal:** Establish the dummy data and the basic 3-stage Streamlit layout.
1. **Create `mock_data.py`**:
    * Define 3 payment scenarios: 
        * Scenario A: High-Value Cross-Border (Needs high approval, balanced cost).
        * Scenario B: Domestic Instant/RTP (Needs ultra-low latency).
        * Scenario C: High-Risk Merchant (Needs high network resilience/fallback).
    * Define 4 static route options (e.g., Direct Issuer, Network Alpha, Least-Cost Processor, Resilient Fallback) with dummy stats for Cost, Latency, Risk, and Approval.
2. **Create `app.py`**:
    * Setup `st.set_page_config` with a premium dark theme. Set the title to "Project Photon: Hybrid QNN Routing".
    * Build the **Sidebar**: Dropdown to select one of the 3 scenarios.
    * Build the **Center Panel**: Display the 4 route options as clean metric cards. 
    * Add a placeholder button: "Initialize Project Photon Optimization".

---

## Phase 2: The Native 1.58-bit BitNet LLM (AI Layer)
**Goal:** Use a true native 1.58-bit LLM architecture to extract semantic payment intent, running highly optimized CPU inference, and feed it to the QNN.
1. **Update `bitnet_encoder.py`**:
    * Import `transformers` and `torch`.
    * Load a true 1.58-bit model implementation: `1bitLLM/bitnet_b1_58-3B` (or equivalent BitNet-compatible Hugging Face repo).
    * **CRITICAL:** Use `AutoModelForCausalLM.from_pretrained(repo, trust_remote_code=True)` and `AutoTokenizer`. `trust_remote_code=True` is required because BitNet uses custom ternary weight loading scripts not built into standard transformers yet.
    * *The Extraction:* Since this is a Causal LLM, do not generate text. Instead, pass the payment scenario string into the model, do a forward pass, and extract the `last_hidden_state` of the final token. 
    * Add a PyTorch `nn.Linear` reduction layer to compress that hidden state down to a normalized 4-dimensional tensor suitable for the 4-qubit IBM Qiskit `AngleEmbedding` layer.
2. **Integrate into `app.py`**:
    * **CRITICAL:** Use `@st.cache_resource` to load the 3B parameter BitNet model into memory ONCE at startup to prevent OOM errors on the 8GB M2 machine.
    * Update the loading spinner text to: *"Running native 1.58-bit CPU inference on Microsoft BitNet architecture..."*

---

## Phase 3: The IBM QNN Reasoning Layer (Quantum Layer)
**Goal:** Replace the standard dense network with an IBM QNN using `qiskit-machine-learning`.
1. **Create `qiskit_router.py`**:
    * Import `QuantumCircuit` from `qiskit`. Import `EstimatorQNN` from `qiskit_machine_learning.neural_networks` and `TorchConnector` from `qiskit_machine_learning.connectors`.
    * Build a 4-qubit parameterized `QuantumCircuit`.
    * **The QNN Creation:** Wrap that circuit inside an `EstimatorQNN`. 
    * **The Hybrid Bridge:** Pass the `EstimatorQNN` into a `TorchConnector`. This creates a PyTorch-compatible neural network layer powered entirely by IBM Qiskit.
    * Build a function `score_routes(intent_tensor, route_data)` that passes the tensor from Phase 2 directly through this `TorchConnector` layer. Ensure tensor device handoffs between `mps` and the QNN evaluate cleanly.
    * Map the QNN's output to the 4 mock routes to generate a final "Photon Match Score" for each route.
2. **Integrate into `app.py`**:
    * After Phase 2 executes, show a spinner ("Injecting ternary tensor into IBM EstimatorQNN...").
    * Update the Route Cards in the UI to show their new Quantum Match Score. Highlight the winning route.

---

## Phase 4: The Executive Polish
**Goal:** Add the "Hybrid Reasoning Reveal" and explainer text.
1. **Update `app.py`**:
    * Generate a plain-English explanation under the winning route (e.g., *"Recommended Route C: Optimal balance of high approval and low network risk determined by the Quantum Neural Network."*)
    * Add a bottom section titled **"Project Photon Pipeline Architecture"**.
    * Use Qiskit's `circuit.draw(output='mpl')` to generate a visual diagram of the quantum circuit and display it cleanly using `st.pyplot()`. Ensure matplotlib dark mode styling matches the Streamlit theme.