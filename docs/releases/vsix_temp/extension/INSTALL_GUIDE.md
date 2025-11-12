# 🚀 BioQL VS Code Extension - Quick Install Guide

## Step 1: Install Extension

### Option A: From File
```bash
code --install-extension bioql-assistant-3.2.0.vsix
```

### Option B: VS Code UI
1. Open VS Code
2. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
3. Type "Install from VSIX"
4. Select `bioql-assistant-3.2.0.vsix`

## Step 2: Configure Extension

1. **Open Settings** (Cmd/Ctrl+,)
2. Search for "bioql"
3. Set the following:

### Required Configuration

```json
{
  "bioql.mode": "modal",
  "bioql.apiKey": "bioql_test_870ce7ae",
  "bioql.modalUrl": "https://spectrix--bioql-inference-codellama-generate-code.modal.run"
}
```

### Settings Explanation

- **bioql.mode**: `modal` for cloud GPU inference
- **bioql.apiKey**: Your authentication key (demo key: `bioql_test_870ce7ae`)
- **bioql.modalUrl**: Production endpoint (pre-configured)

## Step 3: Verify Installation

1. **Open Output Panel**
   - View → Output → Select "BioQL Assistant"

2. **Test Generation**
   - Press `Cmd/Ctrl+Shift+G`
   - Type: "Create a Bell state"
   - Wait 30-120 seconds (first request is slow)

3. **Check Output**
   - You should see:
     ```
     🔄 Calling BioQL inference API...
     💰 Cost Information:
        User Cost: $0.001755
        Balance: $9.998245
     ```

## 🎯 Usage Examples

### Generate Code
```
Cmd/Ctrl+Shift+G → "Create a 3-qubit GHZ state"
```

### Fix Code
```
Select code → Cmd/Ctrl+Shift+F
```

### Chat
```
Open Chat → @bioql create a quantum circuit
```

## 💰 Billing Info

- **Demo Balance**: $10.00
- **Cost per Request**: ~$0.001755 (4 seconds)
- **Requests Available**: ~5,700 with demo key

## ❓ Troubleshooting

### Extension not working?
1. Check Output panel for errors
2. Verify API key is set correctly
3. Reload VS Code window (Cmd/Ctrl+Shift+P → "Reload Window")

### "API key required" error?
→ Set `bioql.apiKey` in settings

### Slow first request?
→ Normal! First request takes 30-120 seconds (cold start)
→ Subsequent requests are much faster (3-5 seconds)

### "Insufficient balance" error?
→ Contact support to add more credits

## 📞 Need Help?

- **Email**: support@bioql.com
- **Docs**: https://bioql.com/docs
- **GitHub**: https://github.com/your-org/bioql

## ✅ You're Ready!

The extension is installed and configured. Try:
```
Cmd/Ctrl+Shift+G → "Create a Bell state with BioQL"
```

Watch the Output panel for cost tracking and results!
