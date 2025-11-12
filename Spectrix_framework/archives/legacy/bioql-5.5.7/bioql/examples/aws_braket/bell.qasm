OPENQASM 3.0;

// Circuito de Bell - Crear estado entrelazado |Φ+⟩ = (|00⟩ + |11⟩)/√2
// Este es el circuito cuántico más simple que demuestra entrelazamiento

// Declarar 2 qubits
qubit[2] q;

// Declarar 2 bits clásicos para medición
bit[2] c;

// Puerta Hadamard en qubit 0 - crear superposición
h q[0];

// Puerta CNOT (Controlled-NOT) - crear entrelazamiento
// Si q[0] es |1⟩, flip q[1]
cnot q[0], q[1];

// Medir ambos qubits
c[0] = measure q[0];
c[1] = measure q[1];

// Resultado esperado:
// 50% probabilidad de |00⟩ (ambos qubits miden 0)
// 50% probabilidad de |11⟩ (ambos qubits miden 1)
// 0% probabilidad de |01⟩ o |10⟩ (debido al entrelazamiento)
