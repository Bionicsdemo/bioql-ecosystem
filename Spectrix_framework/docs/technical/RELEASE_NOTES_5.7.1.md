# BioQL 5.7.1 Release Notes

**Release Date:** October 13, 2025

## 🐛 Critical Bug Fixes

This is a hotfix release that addresses critical backend extraction and billing recording issues discovered in 5.7.0.

---

## ✅ Fixed

### 1. Backend Extraction Bug (CRITICAL)

**Problem:** VSCode extension and agent were generating incorrect backend names, causing quantum job failures.

**Example Error:**
```
ERROR: Unknown backend 'ibm'. Supported: simulator, ionq_simulator, ionq_qpu, ibm_eagle, ibm_condor, etc.
```

**Root Cause:**
- File: `modal_servers/bioql_agent_billing.py`
- Code was using substring matching but hardcoding generic backend names
- User specifies: `"Use IBM Quantum hardware (ibm_torino)"`
- Generated code: `backend='ibm'` ❌
- Should generate: `backend='ibm_torino'` ✅

**Fix:**
```python
# Before (WRONG)
elif "ibm" in request_lower:
    params["backend"] = "ibm"  # Hardcoded!

# After (CORRECT)
backend_match = re.search(r'\b(ibm_\w+|ionq_\w+|aws_braket|simulator)\b', request_lower)
if backend_match:
    params["backend"] = backend_match.group(1)  # Extracted!
```

**Impact:** All IBM Quantum hardware backends (ibm_torino, ibm_brisbane, ibm_kyoto, etc.) now work correctly.

---

### 2. Billing Recording Bug (CRITICAL)

**Problem:** Billing system was logging "recorded" but not actually recording usage to database.

**Root Cause:**
- File: `bioql/cloud_auth.py`
- Function `record_usage()` returned `None` in all cases (success AND failure)
- Silent failures when API calls failed
- Missing logger import

**Fix:**
```python
# Before
def record_usage(...) -> None:  # No return value
    # ... API calls ...
    pass  # Silent failure

# After
def record_usage(...) -> bool:  # Returns success status
    if not api_key:
        logger.warning("⚠️  No API key provided")
        return False

    if response.status_code == 200:
        logger.info(f"✅ Billing recorded: {shots} shots on {backend}")
        return True

    logger.warning(f"⚠️  Billing failed: {error}")
    return False
```

**Impact:**
- Billing records now properly saved to database
- Users can check `result.metadata['billing_status']` to verify
- Clear logging of success/failure states

---

### 3. VSCode Extension Backend/Shots Extraction

**Problem:** VSCode extension was not extracting backend and shots from user prompts.

**Fix:** Added regex extraction in `modal_serve_vscode.py`:
```python
# Extract backend (e.g., ibm_torino, ionq_aria)
backend_match = re.search(r'\b(ibm_\w+|ionq_\w+|aws_braket|simulator)\b', prompt_lower)
backend = backend_match.group(1) if backend_match else "ibm_torino"

# Extract shots number
shots_match = re.search(r'(?:with\s+)?(\d+)\s+shots?', prompt_lower)
shots = int(shots_match.group(1)) if shots_match else 5000
```

**Impact:** Generated code now respects user's backend and shots specifications.

---

## 🔧 Changed

### VSCode Extension v4.13.1

**Updates:**
- ✅ Extracts backend name from user prompts (ibm_torino, ionq_aria, etc.)
- ✅ Extracts shots number from user prompts (e.g., "with 8000 shots")
- ✅ Updated to BioQL 5.7.1 API
- ✅ Fixed code generation templates

**Installation:**
```bash
# Install updated extension
code --install-extension bioql-assistant-4.13.1.vsix --force
```

---

## 📊 API Changes

### Backend Usage

**Before (5.7.0):**
```python
# User says: "Use IBM Quantum hardware (ibm_torino)"
# Generated code:
result = quantum("...", backend='ibm')  # ❌ WRONG
# Result: ERROR - Unknown backend 'ibm'
```

**After (5.7.1):**
```python
# User says: "Use IBM Quantum hardware (ibm_torino)"
# Generated code:
result = quantum("...", backend='ibm_torino')  # ✅ CORRECT
# Result: Job submitted successfully
```

### Billing Status Checking

**New in 5.7.1:**
```python
result = quantum("...", backend='ibm_torino', shots=5000, api_key=key)

# Check if billing was recorded
if result.metadata['billing_status'] == 'recorded':
    print("✅ Usage successfully recorded")
elif result.metadata['billing_status'] == 'failed':
    print("⚠️  Billing failed (execution completed)")
```

---

## 🧪 Testing

**Test Script:** `/Users/heinzjungbluth/Desktop/test_fixes_570.py`

**Results:**
```
✅ Backend: ibm_torino (correctly extracted)
✅ Billing: recorded (verified in database)
✅ Bio-interpretation: 10/10 fields populated
✅ ALL TESTS PASSED!
```

---

## 📦 Installation

### Upgrade from 5.7.0

```bash
# Clean upgrade recommended
pip install --upgrade bioql==5.7.1 --no-cache-dir

# Verify version
python -c "import bioql; print(bioql.__version__)"
# Output: 5.7.1
```

### VSCode Extension

```bash
# Install/update extension
code --install-extension bioql-assistant-4.13.1.vsix --force
```

---

## 🔬 Technical Details

### Files Modified

**BioQL Framework:**
1. `bioql/cloud_auth.py` - Added logger import, boolean return value
2. `bioql/quantum_connector.py` - Track actual billing status in metadata
3. `setup.py` - Version 5.7.1
4. `bioql/__init__.py` - Version 5.7.1

**Modal Servers:**
1. `modal_servers/bioql_agent_billing.py` - Regex backend extraction
2. `modal_serve_vscode.py` - Backend/shots extraction from prompts

**VSCode Extension:**
1. `package.json` - Version 4.13.1

### Deployment Status

- ✅ Modal servers deployed
- ✅ VSCode extension packaged and installed
- ✅ BioQL framework built and ready for PyPI

---

## 🚀 What's Next

**Version 5.8.0 (Planned):**
- Enhanced billing analytics dashboard
- Multi-backend job batching
- Advanced quantum circuit optimization
- Real-time job queue monitoring

---

## 📞 Support

- **Documentation**: https://docs.bioql.com
- **Issues**: https://github.com/bioql/bioql/issues
- **PyPI**: https://pypi.org/project/bioql/5.7.1/

---

## 🙏 Acknowledgments

Critical bugs reported and fixed with assistance from Claude Code.

**Happy Quantum Computing! ⚛️🔬**
