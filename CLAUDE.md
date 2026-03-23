# Claude Code System Prompt: Project Photon (Hybrid QNN Routing)

## 1. Project Identity and Tone
You are building an executive-grade software prototype codenamed "Project Photon." This is a "Decision Intelligence Cockpit" demonstrating a bleeding-edge payments modernization architecture for a Tier 1 financial institution. The tone of the UI and all generated text must be highly polished, enterprise-focused, and emphasize business value (cost optimization, network resilience, and high approval rates).

## 2. The Core Innovation (The IP Focus)
The core architecture of Project Photon is a continuous hybrid workflow: 
1. **The AI Layer:** Using a simulated 1.58-bit (BitNet) classical neural network to extract semantic business intent from a natural language payment scenario with zero-multiplier efficiency.
2. **The Quantum Layer:** Completely replacing the traditional classical dense layer by injecting that 1.58-bit tensor directly into an IBM Qiskit Quantum Neural Network (QNN) to perform the final combinatorial optimization for route selection.

## 3. Technology Stack & Hardware Constraints
* **Hardware Agnosticism (Apple Silicon):** Code must run seamlessly on Apple Silicon regardless of RAM constraints (scaling from 8GB to 32GB seamlessly). Implement dynamic PyTorch device selection (`device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")`). 
* **Frontend:** `streamlit`. Must use a dark-mode, premium aesthetic. No raw logs, no terminal output visible in the UI. 
* **Backend:** `python 3.10+`. 
* **Classical AI Layer:** `torch` (PyTorch) to simulate the 1-bit feature extraction. Keep tensor operations efficient to prevent Out-Of-Memory (OOM) errors.
* **Quantum Layer:** `qiskit`, `qiskit-aer`, and `qiskit-machine-learning`. You MUST build the circuit using IBM's `QuantumCircuit`, wrap it in an `EstimatorQNN`, and connect it to the PyTorch pipeline using `TorchConnector`.
* **Formatting:** Use clear modularity. Keep the execution linear and easy for an executive to follow via the UI.

## 4. UI Layout Rules
The Streamlit app MUST follow a 3-panel/3-stage flow:
1. **Payment Input:** Scenario selection (e.g., High-Value Cross-Border, Domestic RTP).
2. **Route Intelligence:** Displaying competing route cards with scores.
3. **Project Photon Reasoning Reveal:** A visual explanation of the BitNet-to-IBM QNN pipeline that made the decision, explicitly highlighting the fusion of AI and Quantum mechanics.