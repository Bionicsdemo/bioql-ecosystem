# 🧬 BioQL - Quantum Computing for Bioinformatics

Natural Language Quantum Computing Platform for Drug Discovery

**Version:** 3.0.2  
**Status:** Production Ready ✅

---

## 🚀 Quick Start

### Installation
```bash
pip install bioql
```

### Demo with API Key
```python
from bioql import quantum

API_KEY = "__BIOQL_REDACTED__"

result = quantum(
    "create a bell state with two qubits and measure both",
    backend='simulator',
    api_key=API_KEY,
    shots=1000
)

print(result.counts)
```

---

## 📚 Documentation

### 🎯 Getting Started
- **[Demo Quick Start](docs/demo/START_HERE.md)** - Start here for demos
- **[API Key Guide](docs/demo/API_KEY_ONLY.txt)** - Demo credentials
- **[Complete Demo Guide](docs/demo/DEMO_CREDENTIALS.md)** - All examples

### ⚛️ IonQ Integration
- **[IonQ Quick Start](docs/ionq/IONQ_QUICK_START.txt)** - IonQ setup
- **[IonQ Working Guide](docs/ionq/IONQ_WORKING_GUIDE.md)** - Verified examples
- **[IonQ Simulators](docs/ionq/IONQ_SIMULATORS_GUIDE.md)** - All simulators

### 🔍 Service Monitoring
- **[Monitor Quick Start](docs/monitor/INICIAR_MONITOR.txt)** - Start monitoring
- **[Monitor Guide](docs/monitor/SERVICE_MONITOR_GUIDE.md)** - Complete guide
- **[Monitor Summary](docs/monitor/MONITOR_SYSTEM_SUMMARY.md)** - Overview

### 📖 Technical Docs
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Architecture
- **[Technical Reference](docs/technical/)** - API docs
- **[Examples](examples/)** - Code examples

---

## 🛠️ Management Scripts

All management scripts are in the root directory:

```bash
# Service Management
./start_services.sh       # Start all services
./stop_services.sh        # Stop all services
./check_services.sh       # Check status

# Monitoring
./monitor_services.sh     # 24h health monitor
./test_monitor.sh         # Test monitoring

# Development
./start_server.sh         # Start dev server
```

---

## 📁 Project Structure

```
bioql/
├── bioql/                    # Main package
├── docs/                     # Documentation
│   ├── demo/                 # Demo guides
│   ├── ionq/                 # IonQ guides
│   └── monitor/              # Monitor guides
├── examples/                 # Example scripts
├── scripts/                  # Utility scripts
├── tests/                    # Test suite
└── *.sh                      # Management scripts
```

---

## 🔑 Demo API Key

```
__BIOQL_REDACTED__
```

- **Access:** Unlimited simulator access
- **Cost:** FREE
- **Backends:** simulator, ionq_simulator (with qiskit-ionq)

---

## 💻 Features

- ✅ 100% Natural Language - No quantum gates needed
- ✅ Drug Discovery - Molecular simulations
- ✅ Multiple Backends - Local, IonQ, IBM Quantum
- ✅ Auto-Monitoring - 24/7 health checks
- ✅ Production Ready - Enterprise-grade code

---

## 📞 Support

- **Docs:** docs/demo/START_HERE.md
- **Examples:** examples/
- **Email:** support@bioql.com

---

## 📄 License

MIT License - See [LICENSE](LICENSE)

---

**Ready to start?** Read [docs/demo/START_HERE.md](docs/demo/START_HERE.md)
